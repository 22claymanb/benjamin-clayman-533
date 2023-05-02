import sklearn.model_selection
import pandas as pd
import numpy as np
import math
from sklearn.linear_model import Perceptron
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier

from hw3_traitors import *
from pandas.tseries.holiday import AbstractHolidayCalendar, Holiday, nearest_workday, \
    USMartinLutherKingJr, USPresidentsDay, GoodFriday, USMemorialDay, \
    USLaborDay, USThanksgivingDay

#Taken from outside source because the builtin holiday calendar does not contain every holiday
class USTradingCalendar(AbstractHolidayCalendar):
    rules = [
        Holiday('NewYearsDay', month=1, day=1, observance=nearest_workday),
        USMartinLutherKingJr,
        USPresidentsDay,
        GoodFriday,
        USMemorialDay,
        Holiday('USIndependenceDay', month=7, day=4, observance=nearest_workday),
        Holiday('BushDay', year=2018, month=12, day=5),
        USLaborDay,
        USThanksgivingDay,
        Holiday('Christmas', month=12, day=25, observance=nearest_workday)
    ]


def percepto_ledger(blotter, n3):
    ledger = blotter_to_ledger(blotter)
    ledger = ledger[ledger['success'] != '']

    # build your set of features here.
    # merge them by date to add to this dataframe.
    features = pd.read_csv('daily-treasury-rates.csv')
    del features['30 Yr']
    del features['4 Mo']
    features['Date'] = pd.to_datetime(features['Date'])
    features.sort_values('Date', inplace=True)

    implied_vol_features = pd.read_csv('implied-vol.csv')
    implied_vol_features.rename(columns={'IVOL_IMPLIED_FORWARD': 'Forward Price', 'IVOL_DELTA': 'Forward Vol', 'Dates':'Date'}, inplace=True)
    implied_vol_features['Date'] = pd.to_datetime(implied_vol_features['Date'])

    #vix = pd.read_csv('^VIX.csv')[['Date', 'Open']]
    #vix['Date'] = pd.to_datetime(vix['Date'])

    hw4_data = pd.read_excel('hw4_data.xlsx')
    hw4_data['Date'] = pd.to_datetime(hw4_data['Date'])
    hw4_data = hw4_data[['Date', 'IVV US Equity', 'IVV AU Equity', 'JPYUSD Curncy']]

    """
    ivv_return_list = []
    for i in range(ledger.shape[0]):
        ret_date = pd.to_datetime(ledger.iloc[i]['dt_enter']) + pd.tseries.offsets.CustomBusinessDay(n=(ledger.iloc[i]['n']) + 1, calendar=USTradingCalendar())
        current_price = hw4_data[hw4_data['Date'] == ledger.iloc[i]['dt_enter']]['IVV US Equity'].iloc[0]
        future_price = hw4_data[hw4_data['Date'] == ret_date]['IVV US Equity'].iloc[0]
        ivv_return_list.append(math.log(future_price/current_price) / ledger.iloc[i]['n'])
    ivv_return_series = pd.Series(ivv_return_list)"""


    features = features.merge(hw4_data, on='Date')
    features = features.merge(implied_vol_features, on='Date')
    features.sort_values('Date', inplace=True)
    features.dropna(inplace=True)
    features.reset_index(drop=True, inplace=True)

    features['Forward Price'] /= features['IVV US Equity'].shift(1)
    features['Forward Price'] = features['Forward Price'].apply(math.log)
    #features['Forward Price'] = features['Forward Price'].shift(1)

    features.reset_index(drop=True, inplace=True)
    #features = features[['Date', 'IVV US Equity', 'IVV AU Equity', 'JPYUSD Curncy', 'Forward Price', 'Forward Vol']]

    features['IVV US Equity'] = features['IVV US Equity'] / features['IVV US Equity'].shift(1)
    features['IVV US Equity'] = features['IVV US Equity'].apply(math.log)
    ivv_df = features[['Date', 'IVV US Equity']].copy()
    features['IVV US Equity'] = features['IVV US Equity'].shift(1)

    features['IVV AU Equity'] = features['IVV AU Equity'] / features['IVV AU Equity'].shift(1)
    features['IVV AU Equity'] = features['IVV AU Equity'].apply(math.log)

    features['JPYUSD Curncy'] = features['JPYUSD Curncy'] / features['JPYUSD Curncy'].shift(1)
    features['JPYUSD Curncy'] = features['JPYUSD Curncy'].apply(math.log)
    features['JPYUSD Curncy'] = features['JPYUSD Curncy'].shift(1)

    features.dropna(inplace=True)
    features.reset_index(drop=True, inplace=True)

    features = features[features['Date'].isin(list(ledger['dt_enter']))]
    ledger = ledger[ledger['dt_enter'].isin(features['Date'])]
    ledger.reset_index(drop=True, inplace=True)

    # Make a training set and let's try it out on two upcoming trades.
    # Choose a subset of data:
    lookback_window = n3
    prediction_list = []
    #weight_array = np.array([[1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0, 4.0, 2.5, 3.0, 4.0]])
    #classes_array = np.array([b'1', b'0'])
    for i in range(features.shape[0] - lookback_window):

        X = features.drop('Date', axis=1).iloc[i:i + lookback_window]
        x_test = features.drop('Date', axis=1).iloc[[i + lookback_window]]
        y = np.asarray(ledger.success.iloc[i:i + lookback_window], dtype="|S6")

        sc = StandardScaler()

        sc.fit(X)
        X_std = sc.transform(X)
        x_test_std = sc.transform(x_test)

        ppn = Perceptron(eta0=.01, shuffle=True, n_iter_no_change=15, warm_start=True)
        ppn.fit(X_std, y)

        y_pred = ppn.predict(x_test_std)
        prediction_list.append(int(y_pred[0]))

    ledger = ledger.iloc[n3:]
    ledger.reset_index(drop=True, inplace=True)

    prediction_series = pd.Series(prediction_list)
    ledger['perceptron success'] = prediction_series

    ivv_df = ivv_df[ivv_df['Date'].isin(list(ledger['dt_enter']))]
    ledger['IVV return'] = ivv_df['IVV US Equity'].iloc[n3:].reset_index(drop=True)
    ledger = ledger[['trade_id', 'asset', 'dt_enter', 'dt_exit', 'success', 'perceptron success',
                     'n', 'rtn', 'IVV return']]

    ledger['dt_enter'] = pd.to_datetime(ledger['dt_enter'])
    ledger['dt_enter'] = ledger['dt_enter'].dt.strftime("%Y-%m-%d")

    ledger['dt_exit'] = pd.to_datetime(ledger['dt_exit'])
    ledger['dt_exit'] = ledger['dt_exit'].dt.strftime("%Y-%m-%d")

    ledger.columns = ['Trade ID', 'Asset', 'Enter Date', 'Exit Date', 'Success', 'Perceptron Prediction', 'Number of Days', 'Return', 'IVV Return']
    #ledger['Return'] = ledger['Return'].astype('float')
    #ledger['IVV Return'] = ledger['Return'].astype('float')

    return ledger



