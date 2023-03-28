import pandas as pd
import numpy as np

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
        
        if trade_blotter.iloc[-1]['trip'] == 'ENTER':
            trade_df['success'] = 0
            trade_df['rtn'] = 0.0
        else:
            
            
            
    return blotter_df

blotter_df = blotter_to_ledger('blotter.csv')
    