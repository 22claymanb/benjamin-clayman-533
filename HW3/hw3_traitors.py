import pandas as pd
import numpy as np
import math

def blotter_to_ledger(blotter):
    blotter_df = pd.read_csv(blotter)
    blotter_df.set_index('trade_id', inplace=True)
    blotter_df['date'] = pd.to_datetime(blotter_df['date'])
    
    ledger_df = pd.DataFrame(columns=['trade_id', 'asset', 'dt_enter', 'dt_exit', 'success', 'n', 'rtn'])
    trade_df = pd.DataFrame()
    for i in len(set(blotter_df.index)):
        trade_blotter = blotter_df.loc[i]
        
        trade_df['trade_id'] = i
        trade_df['asset'] = trade_blotter.iloc[0]['asset']
        trade_df['dt_enter'] = trade_blotter.iloc[0]['date']
        trade_df['dt_exit'] = trade_blotter.iloc[-1]['date']
        trade_df['n'] = (trade_df['dt_exit'].iloc[0] - trade_df['dt_enter'].iloc[0]).days
        
        if trade_blotter.iloc[-1]['trip'] == 'ENTER':
            trade_df['success'] = 0
            trade_df['rtn'] = 0.0
        else:
            rtn = math.log(trade_blotter.iloc[0]['price'] / trade_blotter.iloc[-1]['price']) / trade_df['n']
            trade_df['rtn'] = rtn
            
            if rtn > 0:
                trade_df['success'] = 1
            else:
                trade_df['success'] = 0
                
        ledger_df = pd.concat([ledger_df, trade_df], ignore_index=True)         
            
    return ledger_df

blotter_df = blotter_to_ledger('blotter.csv').head(10)
    