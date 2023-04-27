import sklearn.model_selection
import pandas as pd
import numpy as np
import math
from sklearn.linear_model import Perceptron
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier

from hw3_traitors import *

blotter = pd.read_csv('blotter.csv')
ledger = blotter_to_ledger(blotter)
ledger = ledger[ledger['success'] != '']
ledger.to_csv("ledger.csv")


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

def convert_to_returns(column):
    features[column] = features[column] / 100
    features[column] = features[column].shift(1) / features[column]
    features[column] = features[column].apply(math.log)


#vix = pd.read_csv('^VIX.csv')[['Date', 'Open']]
#vix['Date'] = pd.to_datetime(vix['Date'])

hw4_data = pd.read_excel('hw4_data.xlsx')
hw4_data['Date'] = pd.to_datetime(hw4_data['Date'])
hw4_data = hw4_data[['Date', 'IVV US Equity', 'IVV AU Equity', 'JPYUSD Curncy']]

features = features.merge(hw4_data, on='Date')
features = features.merge(implied_vol_features, on='Date')
features.sort_values('Date', inplace=True)
features.dropna(inplace=True)
features = features[features['Date'].isin(list(ledger['dt_enter']))]

features['Forward Price'] /= features['IVV US Equity']
features['Forward Price'] = features['Forward Price'].apply(math.log)
#features['Forward Price'] = features['Forward Price'].shift(1)

features.reset_index(drop=True, inplace=True)
#features = features[['Date', 'IVV US Equity', 'IVV AU Equity', 'JPYUSD Curncy', 'Forward Price', 'Forward Vol']]

features['IVV US Equity'] = features['IVV US Equity'].shift(1) / features['IVV US Equity']
features['IVV US Equity'] = features['IVV US Equity'].apply(math.log)
features['IVV US Equity'] = features['IVV US Equity'].shift(1)

features['IVV AU Equity'] = features['IVV AU Equity'].shift(1) / features['IVV AU Equity']
features['IVV AU Equity'] = features['IVV AU Equity'].apply(math.log)

features['JPYUSD Curncy'] = features['JPYUSD Curncy'].shift(1) / features['JPYUSD Curncy']
features['JPYUSD Curncy'] = features['JPYUSD Curncy'].apply(math.log)
features['JPYUSD Curncy'] = features['JPYUSD Curncy'].shift(1)

features.dropna(inplace=True, ignore_index=True)

ledger = ledger[ledger['dt_enter'].isin(features['Date'])]
ledger.reset_index(drop=True, inplace=True)

# Make a training set and let's try it out on two upcoming trades.
# Choose a subset of data:
lookback_window = 50
prediction_list = []
for i in range(features.shape[0] - lookback_window):
    X = features.drop('Date', axis=1).iloc[i:i + lookback_window]
    x_test = features.drop('Date', axis=1).iloc[[i + lookback_window]]
    y = np.asarray(ledger.success.iloc[i:i + lookback_window], dtype="|S6")

    sc = StandardScaler()

    sc.fit(X)
    X_std = sc.transform(X)
    x_test_std = sc.transform(x_test)

    ppn = Perceptron(eta0=.1)
    #ppn = DecisionTreeClassifier()
    #ppn = KNeighborsClassifier()
    ppn.fit(X_std, y)

    y_pred = ppn.predict(x_test_std)
    prediction_list.append(int(y_pred[0]))

ledger = ledger.iloc[50:]
ledger.reset_index(drop=True, inplace=True)

print("List of predictions")
print(prediction_list)

prediction_series = pd.Series(prediction_list)
prediction_ledger = ledger.copy()
prediction_ledger['success'] = prediction_series

print("Ledger with predictions")
print(prediction_ledger)

print("Perceptron Return")
print(prediction_ledger[prediction_ledger['success'] == 1]['rtn'].sum())

print("Return without Perceptron")
print(ledger['rtn'].sum())

print(list(prediction_ledger['success']))
print(list(ledger['success']))
