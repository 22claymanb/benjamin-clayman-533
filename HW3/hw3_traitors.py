import pandas as pd
import numpy as np
import math


def blotter_to_ledger(blotter):
    blotter['date'] = pd.to_datetime(blotter['date'])
    
    ledger_df = pd.DataFrame(columns=['trade_id', 'asset', 'dt_enter', 'dt_exit', 'success', 'n', 'rtn'])
    for i in set(blotter['trade_id']):
        trade_blotter = blotter[blotter['trade_id'] == i]
        
        trade_id = i
        asset = trade_blotter.iloc[0]['asset']
        dt_enter = trade_blotter.iloc[0]['date']
        
        dt_exit = trade_blotter.iloc[-1]['date']
        
        n = len(pd.bdate_range(dt_enter, dt_exit))
        
        success = 0
        rtn = 0.0
        
        if trade_blotter.iloc[-1]['trip'] != 'ENTER':
            rtn = math.log(trade_blotter.iloc[-1]['price'] / trade_blotter.iloc[0]['price']) / n
            
            success = 1
            
            if trade_blotter.iloc[-1]['type'] == 'MKT':
                success = -1
        else:
            dt_exit = np.nan
                
        if trade_blotter.iloc[-1]['status'] == 'LIVE':
            dt_exit = np.nan
            success = np.nan
            n = np.nan
            rtn = np.nan

        trade_ledger_dict = {
            'trade_id' : [trade_id],
            'asset' : [asset],
            'dt_enter' : [dt_enter],
            'dt_exit' : [dt_exit],
            'success' : [success],
            'n' : [n],
            'rtn' : [rtn],
        }         
    
        trade_ledger_df = pd.DataFrame(data=trade_ledger_dict)
        ledger_df = pd.concat([ledger_df, trade_ledger_df], ignore_index=True)

    return ledger_df.replace(np.nan, '')


print(blotter_to_ledger(pd.read_csv('blotter.csv')).head(25))
