from dash import Dash, html, dcc, dash_table, Input, Output, State
import refinitiv.dataplatform.eikon as ek
import pandas as pd
import numpy as np
from datetime import date
import plotly.express as px
import os

ek.set_app_key(os.getenv('EIKON_API_KEY'))

dt_prc_div_splt = pd.read_csv('unadjusted_price_history.csv')
date_col = pd.Series()

app = Dash(__name__)
app.layout = html.Div([
    html.Div([
        html.Span([
            html.H4("Benchmark:", style={'display':'inline-block', 'margin-right':10}),
            dcc.Input(id = 'benchmark-id', type = 'text', value="IVV")
        ]),
        html.Span([
            html.H4("Asset:", style={'display':'inline-block', 'margin-right':10, 'margin-left':20}),
            dcc.Input(id = 'asset-id', type = 'text', value="AAPL.O")
        ])
    ]),
    html.Div([
        html.H4("Pick Data Range:", style={'display':'inline-block', 'margin-right':10}),
        dcc.DatePickerRange(
            id="date-range",
            min_date_allowed=date(2017, 1, 1),
            max_date_allowed=date.today(),
            initial_visible_month=date(2017, 1, 1),
            end_date=date.today()
        )
    ]),
    html.Button('QUERY Refinitiv', id = 'run-query', n_clicks = 0),
    html.H2('Raw Data from Refinitiv'),
    dash_table.DataTable(
        id = "history-tbl",
        page_action='none',
        style_table={'height': '300px', 'overflowY': 'auto'}
    ),
    html.H2('Historical Returns'),
    dash_table.DataTable(
        id = "returns-tbl",
        page_action='none',
        style_table={'height': '300px', 'overflowY': 'auto'}
    ),
    html.H2('Alpha & Beta Scatter Plot'),
    html.Div([
        html.H4("Pick Data Range For Plot:", style={'display':'inline-block', 'margin-right':10}),
        dcc.DatePickerRange(
            id="plot-date-range",
            min_date_allowed=date(2017, 1, 1),
            max_date_allowed=date.today(),
            initial_visible_month=date(2017, 1, 1),
            end_date=date.today()
        )
    ]),
    html.Button('Plot Graph', id='plot', n_clicks=0),
    html.H2(html.Div(id="ab-display", style={'text-align':'center'})),
    dcc.Graph(id="ab-plot"),
    html.P(id='summary-text', children="")
])

@app.callback(
    Output("history-tbl", "data"),
    Input("run-query", "n_clicks"),
    [State('benchmark-id', 'value'), State('asset-id', 'value'),
     State("date-range", "start_date"), State("date-range", "end_date")],
    prevent_initial_call=True
)
def query_refinitiv(n_clicks, benchmark_id, asset_id, start_date, end_date):
    start_date_object = date.fromisoformat(start_date)
    start_date_string = start_date_object.strftime("%Y-%m-%d")

    end_date_object = date.fromisoformat(end_date)
    end_date_string = end_date_object.strftime("%Y-%m-%d")

    assets = [benchmark_id, asset_id]
    prices, prc_err = ek.get_data(
        instruments=assets,
        fields=[
            'TR.OPENPRICE(Adjusted=0)',
            'TR.HIGHPRICE(Adjusted=0)',
            'TR.LOWPRICE(Adjusted=0)',
            'TR.CLOSEPRICE(Adjusted=0)',
            'TR.PriceCloseDate'
        ],
        parameters={
            'SDate': start_date_string, #'2017-01-01',
            'EDate': end_date_string, #'2023-01-31'
            'Frq': 'D'
        }
    )

    divs, div_err = ek.get_data(
        instruments=assets,
        fields=[
            'TR.DivExDate',
            'TR.DivUnadjustedGross',
            'TR.DivType',
            'TR.DivPaymentType'
        ],
        parameters={
            'SDate': start_date_string, #'2017-01-01',
            'EDate': end_date_string, #'2023-01-31'
            'Frq': 'D'
        }
    )

    splits, splits_err = ek.get_data(
        instruments=assets,
        fields=['TR.CAEffectiveDate', 'TR.CAAdjustmentFactor'],
        parameters={
            "CAEventType": "SSP",
            'SDate': start_date_string, #'2017-01-01',
            'EDate': end_date_string, #'2023-01-31'
            'Frq': 'D'
        }
    )

    prices.rename(
        columns={
            'Open Price': 'open',
            'High Price': 'high',
            'Low Price': 'low',
            'Close Price': 'close'
        },
        inplace=True
    )
    prices.dropna(inplace=True)
    prices['Date'] = pd.to_datetime(prices['Date']).dt.date

    divs.rename(
        columns={
            'Dividend Ex Date': 'Date',
            'Gross Dividend Amount': 'div_amt',
            'Dividend Type': 'div_type',
            'Dividend Payment Type': 'pay_type'
        },
        inplace=True
    )
    divs.dropna(inplace=True)
    divs['Date'] = pd.to_datetime(divs['Date']).dt.date
    divs = divs[(divs.Date.notnull()) & (divs.div_amt > 0)]
    divs = divs.groupby(['Instrument', 'Date'], as_index=False).agg({
        'div_amt': 'sum',
        'div_type': lambda x: ", ".join(x),
        'pay_type': lambda x: ", ".join(x)
    })

    splits.rename(
        columns={
            'Capital Change Effective Date': 'Date',
            'Adjustment Factor': 'split_rto'
        },
        inplace=True
    )
    splits.dropna(inplace=True)
    splits['Date'] = pd.to_datetime(splits['Date']).dt.date

    unadjusted_price_history = pd.merge(
        prices, divs[['Instrument', 'Date', 'div_amt']],
        how='outer',
        on=['Date', 'Instrument']
    )
    unadjusted_price_history['div_amt'].fillna(0, inplace=True)

    unadjusted_price_history = pd.merge(
        unadjusted_price_history, splits,
        how='outer',
        on=['Date', 'Instrument']
    )
    unadjusted_price_history['split_rto'].fillna(1, inplace=True)
    unadjusted_price_history.drop_duplicates(inplace=True)

    unadjusted_price_history.dropna(inplace=True)

    return(unadjusted_price_history.to_dict('records'))

@app.callback(
    Output("returns-tbl", "data"),
    Input("history-tbl", "data"),
    prevent_initial_call = True
)
def calculate_returns(history_tbl):

    dt_prc_div_splt = pd.DataFrame(history_tbl)

    # Define what columns contain the Identifier, date, price, div, & split info
    ins_col = 'Instrument'
    dte_col = 'Date'
    prc_col = 'close'
    div_col = 'div_amt'
    spt_col = 'split_rto'

    dt_prc_div_splt[dte_col] = pd.to_datetime(dt_prc_div_splt[dte_col])
    dt_prc_div_splt = dt_prc_div_splt.sort_values([ins_col, dte_col])[
        [ins_col, dte_col, prc_col, div_col, spt_col]].groupby(ins_col)
    numerator = dt_prc_div_splt[[dte_col, ins_col, prc_col, div_col]].tail(-1)
    denominator = dt_prc_div_splt[[prc_col, spt_col]].head(-1)

    return_df = pd.DataFrame({
        'Date': numerator[dte_col].reset_index(drop=True),
        'Instrument': numerator[ins_col].reset_index(drop=True),
        'rtn': np.log(
            (numerator[prc_col] + numerator[div_col]).reset_index(drop=True) / (
                    denominator[prc_col] * denominator[spt_col]
            ).reset_index(drop=True)
        )
    }).pivot_table(
            values='rtn', index='Date', columns='Instrument'
       )

    global date_col
    date_col = return_df.index

    return(
        return_df.to_dict('records')
    )

@app.callback(
    Output("ab-plot", "figure"),
    #Input("returns-tbl", "data"),
    Input("plot", "n_clicks"),
    [State("returns-tbl", "data"), State('benchmark-id', 'value'), State('asset-id', 'value'),
     State("plot-date-range", "start_date"), State("plot-date-range", "end_date")],
    prevent_initial_call = True
)
def render_ab_plot(n_clicks, returns, benchmark_id, asset_id, start_date, end_date):
    returns_df = pd.DataFrame(returns)
    returns_df['Date'] = date_col

    filtered_df = returns_df[(returns_df.Date >= start_date) & (returns_df.Date <= end_date)]

    return(
        px.scatter(filtered_df, x=benchmark_id, y=asset_id, trendline='ols')
    )

@app.callback(
    Output("ab-display", "children"),
    Input("ab-plot", "figure"),
    [State("returns-tbl", "data"), State('benchmark-id', 'value'), State('asset-id', 'value'), State("plot-date-range", "start_date"), State("plot-date-range", "end_date")],
    prevent_initial_call=True
)
def show_alpha_and_beta(ab_plot, returns, benchmark_id, asset_id, start_date, end_date):
    returns_df = pd.DataFrame(returns)
    returns_df['Date'] = date_col
    filtered_df = returns_df[(returns_df.Date >= start_date) & (returns_df.Date <= end_date)]

    scatter = px.scatter(filtered_df, x=benchmark_id, y=asset_id, trendline='ols')
    fit = px.get_trendline_results(scatter)
    parameters = fit.iloc[0]["px_fit_results"].params

    alpha = round(parameters[0], 5)
    beta = round(parameters[1], 5)

    return "Alpha: " + str(alpha) + " Beta: " + str(beta)

if __name__ == '__main__':
    app.run_server(debug=True)
