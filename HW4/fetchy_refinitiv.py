# fetch_refinitiv_data.py
# by Jake Vestal
#  - fetch simple (adjusted) time series data using get_timeseries()
#  - fetch unadjusted time series data using get_data()
#  - perform some cleaning steps
#  - save data as csv

# Imports
from datetime import datetime
import refinitiv.dataplatform.eikon as ek
import pandas as pd
import os


###### Before running this script:
# 1) Create an app key within Refinitiv
# 2) Create an environmental variable on your computer that stores your key.
#      (I named mine 'EIKON_API')
######
def get_ivv_data():
    # 3) Use your app key in this Python session w the following line:
    ek.set_app_key(os.getenv('EIKON_API_KEY'))

    # 4) Use get_timeseries() to get historical prices for 2 stocks and an ETF
    #    --> if this command fails... don't forget to check and make sure you have
    #        Refinitiv Workstation open and running on your computer :)
    get_timeseries_output = ek.get_timeseries(
        rics=["IVV"],
        start_date="2020-01-06",
        end_date="2023-03-20"
    )

    ### Open your get_timeseries_output.csv and take a look at it. Note that the
    ###   prices are ADJUSTED. That's not ideal for algorithmic trading because:
    ###     1) You need to re-fetch the entire set of adjusted prices every time the
    ###          company has a split or announces a dividend.
    ###     2) You can't be sure that the adjustment method used is correct, or the
    ###          same method that you think it should be.
    ###     3) You can't identify cash earned from dividends
    ###     4) You can't properly backtest because all of your historical orders
    ###          will have the wrong prices.

    ### We need a full set of information:
    ###     - unadjusted prices
    ###     - dividends
    ###     - splits
    ###     - any other weird corporate actions like M&A, ticker changes, etc

    ### We're not worried about the last one in this case, but we do need to worry
    ###   about the first 3, so let's pull that data from Refinitiv.

    # And let's throw in a few other assets because why not:
    assets = ['IVV', 'IVV.AX']

    # 5) use get_data() to fetch historical UNADJUSTED prices for those assets
    # There are many other data varaiables you can fetch like this. The call to
    # get_data() below was created using the Rocket Ship icon in Refinitiv CODEBK.
    prices, prc_err = ek.get_data(
        instruments = assets,
        fields = [
            'TR.OPENPRICE(Adjusted=0)',
            'TR.HIGHPRICE(Adjusted=0)',
            'TR.LOWPRICE(Adjusted=0)',
            'TR.CLOSEPRICE(Adjusted=0)',
            'TR.PriceCloseDate'
        ],
        parameters = {
            'SDate': '2020-01-01',
            'EDate': "2023-04-13",
            'Frq': 'D'
        }
    )

    # 6) Same, but for dividends:
    divs, div_err = ek.get_data(
        instruments = assets,
        fields = [
            'TR.DivExDate',
            'TR.DivUnadjustedGross',
            'TR.DivType',
            'TR.DivPaymentType'
        ],
        parameters = {
            'SDate': '2020-01-06',
            'EDate': "2023-03-20",
            'Frq': 'D'
        }
    )

    # 7) Same, but for splits:
    splits, splits_err = ek.get_data(
        instruments = assets,
        fields = ['TR.CAEffectiveDate', 'TR.CAAdjustmentFactor'],
        parameters = {
            "CAEventType": "SSP",
            'SDate': '2020-01-06',
            'EDate': "2023-03-20",
            'Frq': 'D'
        }
    )

    # 8) Do a little bit of data cleaning.
    #      - simplify the column names
    #      - drop rows with missing data - can't use them.
    #      - cast date columns as pandas datetime objects

    ##### prices
    prices.rename(
        columns = {
            'Open Price':'open',
            'High Price':'high',
            'Low Price':'low',
            'Close Price':'close'
        },
        inplace = True
    )
    prices.dropna(inplace=True)
    prices['Date'] = pd.to_datetime(prices['Date']).dt.date
    # save as csv so you can open in Excel if you want

    ##### divs
    divs.rename(
        columns = {
            'Dividend Ex Date':'Date',
            'Gross Dividend Amount':'div_amt',
            'Dividend Type': 'div_type',
            'Dividend Payment Type': 'pay_type'
        },
        inplace = True
    )
    divs.dropna(inplace=True)
    divs['Date'] = pd.to_datetime(divs['Date']).dt.date

    # At this point, I'm saving the divs df as a csv called 'dirty_divs.csv' because
    #   I want you to open it and see something.
    # Run the above line of code to create 'dirty_divs.csv', open it up in Excel,
    # and take a look. You should note two issues:
    #   1) SHY is missing a date for one of its entries
    #   2) An extra FINAL dividend is reported for IVV.
    #   3) A few zero-dividend entries for SHY which are there for end-of-year
    #        accounting reasons but aren't relevant to us.
    # Some of these are probably accounting artifacts; others might simply be errors
    #   in the data (esp the missing date). Things like this occur in all data
    #   streams -- and this should increase your skepticism about vendor-side
    #   calculations like adjusted price.
    # We're going to solve this by applying our data requirements. To be useful to
    #   us, a div must have an Ex Date and an amount greater than zero:
    divs = divs[(divs.Date.notnull()) & (divs.div_amt > 0)]
    # save as csv so you can open in Excel if you want

    ##### splits
    splits.rename(
        columns = {
            'Capital Change Effective Date':'Date',
            'Adjustment Factor':'split_rto'
        },
        inplace = True
    )
    splits.dropna(inplace=True)
    splits['Date'] = pd.to_datetime(splits['Date']).dt.date
    # save as csv so you can open in Excel if you want
    splits.to_csv('splits.csv', index=False)

    # 9) Merge prices & divs dfs together by date, and fill the missing values in
    #      the merged dividends dataframe with "0".
    unadjusted_price_history = pd.merge(
        prices, divs[['Instrument', 'Date', 'div_amt']],
        how='outer',
        on=['Date', 'Instrument']
    )
    unadjusted_price_history['div_amt'].fillna(0, inplace=True)

    # 10) Same thing for splits, but use "1" for the fill value.
    unadjusted_price_history = pd.merge(
        unadjusted_price_history, splits,
        how='outer',
        on=['Date', 'Instrument']
    )
    unadjusted_price_history['split_rto'].fillna(1, inplace=True)

    # 11) We shouldn't have any missing data in our dataframe now. Verify that:
    unadjusted_price_history.dropna(inplace=True)
    if unadjusted_price_history.isnull().values.any():
        raise Exception('missing values detected!')

    return unadjusted_price_history
