import pandas as pd
from datetime import datetime
import numpy as np
import os
import refinitiv.dataplatform.eikon as ek
import refinitiv.data as rd

#####################################################

ek.set_app_key(os.getenv('EIKON_API_KEY'))

start_date_str = '2023-01-30'
end_date_str = '2023-02-08'

ivv_prc, ivv_prc_err = ek.get_data(
    instruments = ["IVV"],
    fields = [
        'TR.OPENPRICE(Adjusted=0)',
        'TR.HIGHPRICE(Adjusted=0)',
        'TR.LOWPRICE(Adjusted=0)',
        'TR.CLOSEPRICE(Adjusted=0)',
        'TR.PriceCloseDate'
    ],
    parameters = {
        'SDate': start_date_str,
        'EDate': end_date_str,
        'Frq': 'D'
    }
)

ivv_prc['Date'] = pd.to_datetime(ivv_prc['Date']).dt.date
ivv_prc.drop(columns='Instrument', inplace=True)

##### Get the next business day from Refinitiv!!!!!!!
rd.open_session()

next_business_day = rd.dates_and_calendars.add_periods(
    start_date= ivv_prc['Date'].iloc[-1].strftime("%Y-%m-%d"),
    period="1D",
    calendars=["USA"],
    date_moving_convention="NextBusinessDay",
)

rd.close_session()
######################################################

# Parameters:
alpha1 = -0.01
n1 = 3
alpha2 = .01
n2 = 5

# submitted entry orders
submitted_entry_orders = pd.DataFrame({
    "trade_id": range(1, ivv_prc.shape[0]),
    "date": list(pd.to_datetime(ivv_prc["Date"].iloc[1:]).dt.date),
    "asset": "IVV",
    "trip": 'ENTER',
    "action": "BUY",
    "type": "LMT",
    "price": round(
        ivv_prc['Close Price'].iloc[:-1] * (1 + alpha1),
        2
    ),
    'status': 'SUBMITTED'
})

# if the lowest traded price is still higher than the price you bid, then the
# order never filled and was cancelled.
with np.errstate(invalid='ignore'):
    cancelled_entry_orders = submitted_entry_orders[
        np.greater(
            ivv_prc['Low Price'].iloc[1:][::-1].rolling(n1).min()[::-1].to_numpy(),
            submitted_entry_orders['price'].to_numpy()
        )
    ].copy()
cancelled_entry_orders.reset_index(drop=True, inplace=True)
cancelled_entry_orders['status'] = 'CANCELLED'
cancelled_entry_orders['date'] = pd.DataFrame(
    {'cancel_date': submitted_entry_orders['date'].iloc[(n1-1):].to_numpy()},
    index=submitted_entry_orders['date'].iloc[:(1-n1)].to_numpy()
).loc[cancelled_entry_orders['date']]['cancel_date'].to_list()

filled_entry_orders = submitted_entry_orders[
    submitted_entry_orders['trade_id'].isin(
        list(
            set(submitted_entry_orders['trade_id']) - set(
                cancelled_entry_orders['trade_id']
            )
        )
    )
].copy()
filled_entry_orders.reset_index(drop=True, inplace=True)
filled_entry_orders['status'] = 'FILLED'
for i in range(0, len(filled_entry_orders)):

    idx1 = np.flatnonzero(
        ivv_prc['Date'] == filled_entry_orders['date'].iloc[i]
    )[0]

    ivv_slice = ivv_prc.iloc[idx1:(idx1+n1)]['Low Price']

    fill_inds = ivv_slice <= filled_entry_orders['price'].iloc[i]

    if (len(fill_inds) < n1) & (not any(fill_inds)):
        filled_entry_orders.at[i, 'status'] = 'LIVE'
    else:
        filled_entry_orders.at[i, 'date'] = ivv_prc['Date'].iloc[
            fill_inds.idxmax()
        ]

live_entry_orders = pd.DataFrame({
    "trade_id": ivv_prc.shape[0],
    "date": pd.to_datetime(next_business_day).date(),
    "asset": "IVV",
    "trip": 'ENTER',
    "action": "BUY",
    "type": "LMT",
    "price": round(ivv_prc['Close Price'].iloc[-1] * (1 + alpha1), 2),
    'status': 'LIVE'
},
    index=[0]
)

if any(filled_entry_orders['status'] =='LIVE'):
    live_entry_orders = pd.concat([
        filled_entry_orders[filled_entry_orders['status'] == 'LIVE'],
        live_entry_orders
    ])
    live_entry_orders['date'] = pd.to_datetime(next_business_day).date()

filled_entry_orders = filled_entry_orders[
    filled_entry_orders['status'] == 'FILLED'
    ]

submitted_exit_orders = pd.DataFrame({
    'trade_id': filled_entry_orders['trade_id'],
    'date': filled_entry_orders['date'],
    'asset': filled_entry_orders['asset'],
    'trip': 'EXIT',
    'action': 'SELL',
    'type': 'LMT',
    'price': round(filled_entry_orders['price'] * (1 + alpha2), 2),
    'status': 'SUBMITTED',
})

ivv_for_exit = ivv_prc.copy()
ivv_for_exit['High Price'] = ivv_for_exit['High Price'][::-1].rolling(n2-1).max()[::-1]

shifted_exit = submitted_exit_orders[np.greater(submitted_exit_orders['price'].to_numpy(),
                                                ivv_prc.merge(submitted_exit_orders, how="right", left_on="Date", right_on="date")['Close Price'].to_numpy())].copy()

shifted_exit['date'] = (pd.to_datetime(shifted_exit["date"]) + pd.tseries.offsets.BusinessDay(n=1)).dt.date

cut_exit = shifted_exit[shifted_exit['date'] <= ivv_prc.iloc[-1]['Date']].copy()
filtered_ivv_for_exit = ivv_for_exit.merge(cut_exit, how="right", left_on="Date", right_on="date")

cancelled_exit_orders = cut_exit[np.greater(cut_exit['price'].to_numpy(), filtered_ivv_for_exit['High Price'].to_numpy())].copy()
cancelled_exit_orders['status'] = 'CANCELLED'
cancelled_exit_orders['date'] = (pd.to_datetime(cancelled_exit_orders['date']) + pd.tseries.offsets.BusinessDay(n=(n2-2))).dt.date

market_sell_orders = pd.DataFrame({
    'trade_id': cancelled_exit_orders['trade_id'],
    'date': cancelled_exit_orders['date'],
    'asset': cancelled_exit_orders['asset'],
    'trip': 'EXIT',
    'action': 'SELL',
    'type': 'MKT',
    'price': ivv_prc.merge(cancelled_exit_orders, how="right", left_on="Date", right_on="date")['Close Price'].to_numpy(),
    'status': 'SUBMITTED',
})

filled_exit_orders = submitted_exit_orders[
    submitted_exit_orders['trade_id'].isin(
        list(set(submitted_exit_orders['trade_id']) - set(cancelled_exit_orders['trade_id']))
    )
].copy()
filled_exit_orders.reset_index(drop=True, inplace=True)

filled_exit_orders['status'] = 'FILLED'
for i in range(0, len(filled_exit_orders)):

    idx1 = np.flatnonzero(
        ivv_prc['Date'] == filled_exit_orders['date'].iloc[i]
    )[0]

    if ivv_prc['Close Price'].iloc[idx1] > filled_exit_orders['price'].iloc[i]:
        filled_exit_orders.at[i, 'date'] = ivv_prc['Date'].iloc[idx1]
        continue

    ivv_slice = ivv_prc.iloc[idx1 + 1:(idx1+n2)]['High Price']

    fill_inds = ivv_slice > filled_exit_orders['price'].iloc[i]

    if (len(fill_inds) < (n2-1)) & (not any(fill_inds)):
        filled_exit_orders.at[i, 'status'] = 'LIVE'
    else:
        filled_exit_orders.at[i, 'date'] = ivv_prc['Date'].iloc[
            fill_inds.idxmax()
        ]

if any(filled_exit_orders['status'] =='LIVE'):
    live_exit_orders = filled_exit_orders[filled_exit_orders['status'] == 'LIVE'].copy()
    live_exit_orders['date'] = pd.to_datetime(next_business_day).date()

filled_exit_orders = filled_exit_orders[
    filled_exit_orders['status'] == 'FILLED'
    ]


entry_orders = pd.concat(
    [
        submitted_entry_orders,
        cancelled_entry_orders,
        filled_entry_orders,
        live_entry_orders,
    ]
).sort_values(["date", 'trade_id'])

exit_orders = pd.concat(
    [
        submitted_exit_orders,
        cancelled_exit_orders,
        market_sell_orders,
        filled_exit_orders,
        live_exit_orders,
    ]
).sort_values(['date', 'trade_id'])

blotter = pd.concat(
    [
        submitted_entry_orders,
        cancelled_entry_orders,
        filled_entry_orders,
        live_entry_orders,
        submitted_exit_orders,
        cancelled_exit_orders,
        market_sell_orders,
        filled_exit_orders,
        live_exit_orders,
    ]
).sort_values(['trade_id', 'trip', 'date'])

print("submitted_entry_orders:")
print(submitted_entry_orders)

print("cancelled_entry_orders:")
print(cancelled_entry_orders)

print("filled_entry_orders:")
print(filled_entry_orders)

print("live_entry_orders:")
print(live_entry_orders)

print("entry_orders:")
print(entry_orders)

print("submitted_exit_orders:")
print(submitted_exit_orders)

print("cancelled_exit_orders:")
print(cancelled_exit_orders)

print("market_sell_orders:")
print(market_sell_orders)

print("filled_exit_orders:")
print(filled_exit_orders)

print("live_exit_orders:")
print(live_exit_orders)

print("exit_orders:")
print(exit_orders)

print("blotter:")
print(blotter)

print(ivv_prc)
