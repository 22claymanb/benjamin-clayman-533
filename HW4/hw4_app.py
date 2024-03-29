import dash
from dash import Dash, html, dcc, dash_table, Input, Output, State, ctx
import dash_bootstrap_components as dbc
from datetime import datetime, date, timedelta
import plotly.express as px
import pandas as pd
from datetime import datetime
import numpy as np
import os
import refinitiv.dataplatform.eikon as ek
import refinitiv.data as rd
import simple_trade_logic
from percepto import *
from hoeffding import *

app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

percentage = dash_table.FormatTemplate.percentage(3)

perceptron_alpha = 0.0
normal_alpha = 0.0

controls = dbc.Card(
    [
        dbc.Row([
            html.H5('Asset:',
                    style={'display': 'inline-block', 'margin-right': 20}),
            dcc.Input(id='asset', type='text', value="IVV",
                      style={'display': 'inline-block',
                             'border': '1px solid black'})
            ]),
        dbc.Row([
            dcc.DatePickerRange(
                id='refinitiv-date-range',
                min_date_allowed=date(2020, 1, 6),
                max_date_allowed=date(2023, 3, 20),
                start_date=date(2020, 1, 6),
                end_date=date(2023, 4, 13)
            )
        ]),
        dbc.Row(html.Button('QUERY Refinitiv', id='run-query', n_clicks=0)),
        dbc.Row([
            dbc.Table(
                [
                    html.Thead(html.Tr([html.Th("α1"), html.Th("n1")])),
                    html.Tbody([
                        html.Tr([
                            html.Td(
                                dbc.Input(
                                    id='alpha1',
                                    type='number',
                                    value=-0.01,
                                    max=1,
                                    min=-1,
                                    step=0.01
                                )
                            ),
                            html.Td(
                                dcc.Input(
                                    id='n1',
                                    type='number',
                                    value=3,
                                    min=2,
                                    step=1
                                )
                            )
                        ])
                    ])
                ],
                bordered=True
            ),
            dbc.Table(
                [
                    html.Thead(html.Tr([html.Th("α2"), html.Th("n2")])),
                    html.Tbody([
                        html.Tr([
                            html.Td(
                                dbc.Input(
                                    id='alpha2',
                                    type='number',
                                    value=0.01,
                                    max=1,
                                    min=-1,
                                    step=0.01
                                )
                            ),
                            html.Td(
                                dcc.Input(
                                    id='n2',
                                    type='number',
                                    value=5,
                                    min=2,
                                    step=1
                                )
                            )
                        ])
                    ])
                ],
                bordered=True
            ),
            dbc.Table(
                [
                    html.Thead(html.Tr([html.Th("n3 (Lookback Window)")])),
                    html.Tbody([
                        html.Tr([
                            html.Td(
                                dbc.Input(
                                    id='n3',
                                    type='number',
                                    value=50,
                                    max=100,
                                    min=30,
                                    step=1
                                )
                            )
                        ])
                    ])
                ],
                bordered=True
            )
        ]),
        dbc.Row(html.Button('Update Parameter', id='update-param', n_clicks=0)),

    ],
    body=True
)

app.layout = dbc.Container(
    [
        dbc.Alert("If you change the Asset or Dates, please query Refinitiv first", id='alert', is_open=False, color="warning"),
        dbc.Row(
            [
                dbc.Col(controls, md=4),
                dbc.Col(
                    html.Img(src='assets/Reactive.png'),
                    md = 8
                )
            ],
            align="center",
        ),
        html.H2('Trade Blotter:'),
        dash_table.DataTable(id="blotter", fixed_rows={'headers': True}, style_table={'height': 500, 'overflowY': 'auto'},
                            style_cell = {
                                # all three widths are needed
                                'minWidth': '180px', 'width': '180px', 'maxWidth': '180px',
                                'overflow': 'hidden',
                                'textOverflow': 'ellipsis',
                            }),
        html.H5('\n'),
        html.H2('Ledger With Perceptron Predictions'),
        dash_table.DataTable(id="ledger", fixed_rows={'headers': True}, style_table={'height': 500, 'overflowY': 'auto'},
                             style_cell={
                                 # all three widths are needed
                                 'minWidth': '160px', 'width': '160px', 'maxWidth': '160px',
                                 'overflow': 'hidden',
                                 'textOverflow': 'ellipsis',
                             }),
        html.H5('\n'),
        dcc.Graph(id="ledger-abplot"),
        html.H5('\n'),
        dcc.Graph(id="perceptron-abplot"),
        html.H5('\n'),
        html.H2(html.Div(id="hoeffding-display", style={'text-align':'center'})),
        html.H5('\n'),
        html.H5('Author:'),
        html.Div('Ryan Claypool, Benjamin Clayman, and Jiqing Fan')
    ],
    fluid=True
)

#store the query data
query_result = None
query_asset = None
query_startdate = None
query_enddate = None

@app.callback(
    [Output("blotter", "data"), Output("alert", "is_open")],
    [Input("run-query", "n_clicks"),Input("update-param", "n_clicks")],
    [State("alpha1", "value"),State("n1","value"),State("alpha2","value"),State("n2","value"),
     State("refinitiv-date-range", "start_date"), State("refinitiv-date-range", "end_date"),
     State("asset","value")],
    prevent_initial_call=True
)
def query_refinitiv (run_query, update_param, alpha1, n1, alpha2, n2, start_date, end_date, asset):
    #record the query at a global scale
    if ctx.triggered[0]["prop_id"].split(".")[0] == "run-query":
        global query_result
        global query_asset
        global query_startdate
        global query_enddate
        query_result = simple_trade_logic.query_refinitiv(start_date, end_date, asset)
        query_asset = asset

        query_startdate = start_date
        query_enddate = end_date

    #did not query refinitiv first
    elif asset != query_asset or start_date != query_startdate or end_date != query_enddate:
        return dash.no_update, True

    return simple_trade_logic.get_blotter(query_result, alpha1, n1, alpha2, n2, start_date, end_date, asset), False

# @app.callback(
#     Output("blotter", "data"),
#     Input("update-param", "n_clicks"),
#     [State("alpha1", "value"),State("n1","value"),State("alpha2","value"),State("n2","value"),
#      State("refinitiv-date-range", "start_date"), State("refinitiv-date-range", "end_date"),
#      State("asset","value")],
#     prevent_initial_call=True
# )
# def get_blotter (n_clicks, alpha1, n1, alpha2, n2, start_date, end_date, asset):
#     return simple_trade_logic.get_blotter(query_result, alpha1, n1, alpha2, n2, start_date, end_date, asset)


@app.callback(
    Output("ledger", "data"),
    Input("blotter", "data"),
    State("n3", "value"),
    prevent_initial_call=True
)
def create_ledger(blotter, n3):
    blotter_df = pd.DataFrame(blotter)
    return percepto_ledger(blotter_df, n3).to_dict('records')

@app.callback(
    Output("ledger-abplot", "figure"),
    Input("ledger", "data"),
    prevent_initial_call=True
)
def ledger_plot(ledger):
    ledger_df = pd.DataFrame(ledger)

    scatter = px.scatter(ledger_df, x='IVV Return', y='Return', trendline='ols')

    fit = px.get_trendline_results(scatter)
    parameters = fit.iloc[0]["px_fit_results"].params

    global normal_alpha
    normal_alpha = round(parameters[0], 5)
    beta = round(parameters[1], 5)

    scatter.update_layout(
        title={
            'text': "Normal Strategy Return vs. IVV Return; Alpha: {}, Beta: {}".format(normal_alpha, beta),
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
        }
    )

    return scatter

@app.callback(
    Output("perceptron-abplot", "figure"),
    Input("ledger", "data"),
    prevent_initial_call=True
)
def perceptron_plot(ledger):
    ledger_df = pd.DataFrame(ledger)

    ledger_df = ledger_df[ledger_df['Perceptron Prediction'] == 1]

    scatter = px.scatter(ledger_df, x='IVV Return', y='Return', trendline='ols')

    fit = px.get_trendline_results(scatter)
    parameters = fit.iloc[0]["px_fit_results"].params

    global perceptron_alpha
    perceptron_alpha = round(parameters[0], 5)
    beta = round(parameters[1], 5)

    scatter.update_layout(
        title={
            'text': "Perceptron-assisted Strategy Return vs. IVV Return; Alpha: {}, Beta: {}".format(perceptron_alpha, beta),
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
        }
    )

    return scatter

@app.callback(
    Output('hoeffding-display', 'children'),
    Input("perceptron-abplot", "figure"),
    State('ledger', 'data'),
    prevent_initial_call=True
)
def calculate_hoeffding(percept_plot, ledger):
    t = perceptron_alpha - normal_alpha
    n = pd.DataFrame(ledger).shape[0]
    bound = apply_hoeffding(n, t)

    return "According to the Hoeffding Inequality. The upper bound on the probability that the actual alpha of our Perceptron strategy is less than the alpha of our unassisted strategy is {}".format(bound)


if __name__ == '__main__':
    app.run_server(debug=True)
