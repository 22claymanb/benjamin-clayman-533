import pandas as pd
import numpy as np
import math

def blotter_to_ledger(blotter):
    blotter_df = pd.read_csv(blotter)
    blotter_df['date'] = pd.to_datetime(blotter_df['date'])
    
    ledger_df = pd.DataFrame(columns=['trade_id', 'asset', 'dt_enter', 'dt_exit', 'success', 'n', 'rtn'])
    for i in set(blotter_df['trade_id']):
        trade_blotter = blotter_df[blotter_df['trade_id'] == i]
        
        trade_id = i
        asset = trade_blotter.iloc[0]['asset']
        dt_enter = trade_blotter.iloc[0]['date']
        dt_exit = trade_blotter.iloc[-1]['date']
        
        n = (dt_exit - dt_enter).days + 1
        success = 0
        rtn = 0.0
        
        if trade_blotter.iloc[-1]['trip'] != 'ENTER':
            rtn = math.log(trade_blotter.iloc[-1]['price'] / trade_blotter.iloc[0]['price']) / n
            
            if rtn > 0:
                success = 1
                
                
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
            
    return ledger_df

ledger_df = blotter_to_ledger('blotter.csv')
print(ledger_df.head(25))
    