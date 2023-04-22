import sklearn.model_selection
import pandas as pd
import numpy as np
import math
from sklearn.linear_model import Perceptron
from sklearn.preprocessing import StandardScaler

from hw3_traitors import *

blotter = pd.read_csv('blotter.csv')
ledger = blotter_to_ledger(blotter)

# build your set of features here.
# merge them by date to add to this dataframe.
features = pd.read_csv('daily-treasury-rates.csv')
features['Date'] = pd.to_datetime(features['Date'])
del features['30 Yr']

#vix = pd.read_csv('^VIX.csv')[['Date', 'Open']]
#vix['Date'] = pd.to_datetime(vix['Date'])

hw4_data = pd.read_excel('hw4_data.xlsx')
hw4_data['Date'] = pd.to_datetime(hw4_data['Date'])
hw4_data = hw4_data[['Date', 'IVV AU Equity', 'JPYUSD Curncy']]

features = features.merge(hw4_data, on='Date')
features.sort_values('Date', inplace=True)
features.dropna(inplace=True)
features = features[features['Date'].isin(list(ledger['dt_enter']))]
features.reset_index(drop=True, inplace=True)
features = features[['Date', 'IVV AU Equity', 'JPYUSD Curncy']]

# Make a training set and let's try it out on two upcoming trades.
# Choose a subset of data:
X = features.drop('Date', axis=1).head(10)
x_test = features.drop('Date', axis=1).iloc[[10, 11]]
y = np.asarray(ledger.success.head(10), dtype="|S6")

sc = StandardScaler()

sc.fit(X)
X_std = sc.transform(X)
x_test_std = sc.transform(x_test)

ppn = Perceptron(eta0=0.1)
ppn.fit(X_std, y)

y_pred = ppn.predict(x_test_std)

print("Perceptron's predictions: ")
print(y_pred)

print("Actual Performance")
print(ledger.iloc[[10, 11]])
