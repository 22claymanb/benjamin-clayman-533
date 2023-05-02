import pandas as pd
import numpy as np
import math
from fetchy_refinitiv import *


def get_ivv_us_and_au():
    ivv_df = get_ivv_data()

    ivv_us = ivv_df[ivv_df['Instrument'] == 'IVV'][['Date', 'close', 'div_amt', 'split_rto']]
    ivv_au = ivv_df[ivv_df['Instrument'] == 'IVV.AX'][['Date', 'close', 'div_amt', 'split_rto']]

    ivv_us['IVV US Equity'] = (ivv_us['close'] + ivv_us['div_amt']) / (ivv_us['close'].shift(1) * ivv_us['split_rto'].shift(1))
    ivv_us['IVV US Equity'] = ivv_us['IVV US Equity'].dropna().apply(math.log)
    ivv_us = ivv_us[['Date', 'IVV US Equity', 'close']]
    ivv_us.dropna(inplace=True)

    ivv_au['IVV AU Equity'] = (ivv_au['close'] + ivv_au['div_amt']) / (ivv_au['close'].shift(1) * ivv_au['split_rto'].shift(1))
    ivv_au['IVV AU Equity'] = ivv_au['IVV AU Equity'].dropna().apply(math.log)
    ivv_au = ivv_au[['Date', 'IVV AU Equity']]
    ivv_au.dropna(inplace=True)

    ivv_df = ivv_us.merge(ivv_au, how='left', on='Date')
    ivv_df.fillna(method='ffill', inplace=True)
    ivv_df['Date'] = pd.to_datetime(ivv_df['Date'])

    return ivv_df


