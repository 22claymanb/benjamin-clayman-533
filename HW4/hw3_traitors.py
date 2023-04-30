import pandas as pd
import numpy as np
import math


def blotter_to_ledger(blotter):
    blotter['Date'] = pd.to_datetime(blotter['Date'])
    
    ledger_df = pd.DataFrame(columns=['trade_id', 'asset', 'dt_enter', 'dt_exit', 'success', 'n', 'rtn'])
    for i in set(blotter['Trade ID']):
        trade_blotter = blotter[blotter['Trade ID'] == i]
        
        trade_id = i
        asset = trade_blotter.iloc[0]['Asset']
        dt_enter = trade_blotter.iloc[0]['Date']
        
        dt_exit = trade_blotter.iloc[-1]['Date']
        
        n = len(pd.bdate_range(dt_enter, dt_exit))
        
        success = 0
        rtn = 0.0
        
        if trade_blotter.iloc[-1]['Trip'] != 'ENTER':
            rtn = math.log(trade_blotter.iloc[-1]['Price'] / trade_blotter.iloc[0]['Price']) / n
            
            success = 1
            
            if trade_blotter.iloc[-1]['Type'] == 'MKT':
                success = -1
        else:
            dt_exit = np.nan
                
        if trade_blotter.iloc[-1]['Status'] == 'LIVE':
            dt_exit = np.nan
            success = np.nan
            n = np.nan
            rtn = np.nan

        trade_ledger_dict = {
            'trade_id': [trade_id],
            'asset': [asset],
            'dt_enter': [dt_enter],
            'dt_exit': [dt_exit],
            'success': [success],
            'n': [n],
            'rtn': [rtn],
        }         
    
        trade_ledger_df = pd.DataFrame(data=trade_ledger_dict)
        ledger_df = pd.concat([ledger_df, trade_ledger_df], ignore_index=True)

    return ledger_df.replace(np.nan, '')
