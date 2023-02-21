import numpy as np
import pandas as pd

my_data = pd.read_csv('some_data.csv').loc[::-1].reset_index(drop=True)
my_data['Date'] = pd.to_datetime(my_data['Date'])


def submit_orders(alpha, asset):
    orders_df = pd.DataFrame()
    orders_df['Trade ID'] = pd.Series(range(1, len(my_data) + 1))
    orders_df['Date'] = my_data['Date'] + pd.DateOffset(days=1)
    orders_df['Asset'] = asset
    orders_df['Trip'] = 'ENTER'
    orders_df['Action'] = 'BUY'
    orders_df['Type'] = 'LMT'
    orders_df['Price'] = (1 + alpha) * my_data['Close']
    orders_df['Status'] = 'SUBMITTED'

    return orders_df


new_df = submit_orders(-.01, 'IVV')

canceled_entry_orders = pd.DataFrame(columns=['Trade ID', 'Date', 'Asset', 'Trip', 'Action', 'Type', 'Price', 'Status'])
for i in range(len(new_df)):
    filled = False
    not_known = False
    for x in range(0, 3):
        if new_df.iloc[i]['Date'] + pd.DateOffset(days=x) in my_data['Date'].values:
            print(((my_data[my_data.Date == new_df.iloc[i]['Date'] + pd.DateOffset(days=x)])['Low'])[0])
            if my_data[my_data.Date == new_df.iloc[i]['Date'] + pd.DateOffset(days=x)]['Low'] <= new_df.iloc[i]['Price']:
                filled = True
                break
        else:
            not_known = True
            break

    if filled or not_known:
        continue

    canceled_entry_orders = canceled_entry_orders.append(new_df.iloc[i], ignore_index=True)

print(canceled_entry_orders)
