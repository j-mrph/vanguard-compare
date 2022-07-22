from dash import Dash, dcc, html, Input, Output, dash_table
from dash.dependencies import State
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import requests
from datetime import datetime
from dateutil import parser


from utility_functions import *

# list all vanguard funds
resp = requests.get('https://www.vanguardinvestor.co.uk/api/productList/')

df = pd.read_json(resp.text)

df = df[df['shareClass'] == 'Accumulation']

named_funds = df[['name', 'portId']]


app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

app.title = "Vanguard U.K. Fund Comparison"

# app layout functions
def description_card():
    """
    :return: A Div containing dashboard title & descriptions.
    """
    return html.Div(
        id="description-card",
        children=[
            html.H5("Vanguard U.K. Fund Comparison"),
            #html.H3("Fund Comparison Dashboard"),
            html.Div(
                id="intro",
                children=dcc.Markdown('''
        Analyze and compare the historic returns of all funds listed by
        [vanguardinvestor.co.uk](https://www.vanguardinvestor.co.uk).

        *Note: Accumulation funds only, calculated using monthly percentage change values.*
        ''')
            ),
        ]
    )

def generate_control_card():
    """
    :return: A Div containing controls for graphs.
    """
    return html.Div(
        id="control-card",
        children=[
            html.P("Initial lump sum (£)"),
            dbc.Input(id='initial-lump-sum',type="number", min=1, max=999999999, value = 10000),
            html.Br(),

            html.P("Investment date"),
            dcc.DatePickerSingle(
                id="date-picker-select",
                min_date_allowed=datetime(1999, 1, 1),
                max_date_allowed=datetime(2999, 12, 31),
                initial_visible_month=datetime(2018, 1, 1),
                date=datetime(2017, 1, 1)
            ),

            html.Br(),
            html.Br(),

            html.P("Select Funds"),
            dcc.Dropdown(
                id="fundlist",
                options=[{'label': i, 'value': i} for i in df.name.unique()],

                multi=True,
                value = [" FTSE Global All Cap Index Fund",],

            ),
            html.Br(),

            dcc.Checklist(id = 'arima', options = [' Include +3 Year ARIMA forecast (Fitted to the timeframe that has been selected, calculated only with at least 3 years of data available)']),

            html.Br(),
            
            dbc.Button('Submit', id='submit-val', n_clicks=0, color = 'primary')
        ],
    )

app.layout = html.Div(
    id="app-container",
   children=[
        # Banner
        html.Div(
            id="banner",
            className="banner",
            children=[html.A([
            html.Img(src=app.get_asset_url("/GitHub-Mark/PNG/GitHub-Mark-64px.png"))
    ], href='https://www.google.com')]
        ),

    html.Div(
            id="left-column",
            className="four columns",
            children=[description_card(),generate_control_card()]
            + [
                html.Div(
                    ["initial child"], id="output-clientside", style={"display": "none"}
                )
            ],
        ), 

         # Right column
        html.Div(
            id="right-column",
            className="eight columns",
            children=[
                # fund return card
                html.Div(
                    id="fund_return_card",
                    children=[
                        html.B("Fund Returns"),
                        html.Hr(),
                        dcc.Graph(id="graph-container"),
                    ],
                ),
                # Results Table
                html.Div(
                    id="results_table_card",
                    children=[
                        html.B("Results"),
                        html.Hr(),
                        html.Output(id = 'results-label'),
                        html.Div(id="results_table", children=dash_table.DataTable(id = 'data-table-id',
                                                                                   style_table={'overflowX': 'auto'},
                                                                                   fill_width=False))
                    ],
                ),

                html.Div(dcc.Markdown('''This app is for educational purposes only, past performance is not a reliable indicator of future returns. 
                For comprehensive fund details including ongoing charges visit the vanguard uk fund page. 
                '''))
            ],
        ),
    ],
)



# main callback to update graph, table and results message
@app.callback(
    Output("graph-container", "figure"), 
    Output('data-table-id', 'data'),
    Output('results-label', 'children'),
    [Input('submit-val', 'n_clicks')],
    [State('fundlist','value'),
    State('date-picker-select','date'),
    State('initial-lump-sum', 'value'),
    State('arima', 'value')], prevent_initial_call=True
    )
def update_line_chart(n_clicks, dropdown_value, date_value, initial_lump_value, arima_value):
  
     if any(not elem for elem in [dropdown_value, date_value, initial_lump_value]):
        # handling lack of inputs 
        placeholder_fig = create_placeholder_chart()

        dt = pd.DataFrame().to_dict(orient = 'records')
        return placeholder_fig, dt, []
     else:

        fundcodes = named_funds[named_funds['name'].str.contains('|'.join(dropdown_value))]

        names = fundcodes.name.tolist()
        codes = fundcodes.portId.tolist()


        # here we are applying the get return function to the funds
        # including the investment date and initial lump sum
        result = list(map(get_return,
                          names,
                          codes,
                          [date_value] * len(names),
                          [initial_lump_value] * len(names),
                          [arima_value] * len(names)))
        
        # combine all fund results for visualisation
        full_df = pd.concat(result)


        fig = px.line(full_df, x="newdate", y="calculated", color = 'fund_name', template = 'simple_white',
        labels=dict(newdate="Date", calculated="Value (£)", fund_name="Fund"))

        fig.update_layout(legend=dict(orientation="h",  y=-0.3, title_text =''))



       # data preparation for the results table
        df_filtered = full_df.groupby('fund_name').tail(1).copy()

        df_filtered = df_filtered[['fund_name','calculated']]

        plus_3 = df_filtered.loc[df_filtered.fund_name.str.startswith('+3', na=False)]

        if plus_3.empty:

            # if no forecast has been carried out

            df_filtered.columns = ['Fund', 'This Month Value']
            
            df_filtered['This Month Value'] = df_filtered['This Month Value'].apply(lambda x: "£{:0,.2f}".format(float(x)))

            dt = df_filtered.to_dict(orient='records')
        
        else:

            # if there was a forecast make table wide and add predicted value as col
            plus_3['fund_name'] = plus_3['fund_name'].str.replace(r'^.{19}', '')
            with_forecast = plus_3.merge(df_filtered, on='fund_name', how='left')
            with_forecast = with_forecast[['fund_name', 'calculated_y', 'calculated_x']]
            with_forecast.columns = ['Fund', 'This Month Value', 'Predicted +3y Value']

            # number formatting

            with_forecast['This Month Value'] = with_forecast['This Month Value'].apply(lambda x: "£{:0,.2f}".format(float(x)))
            with_forecast['Predicted +3y Value'] = with_forecast['Predicted +3y Value'].apply(lambda x: "£{:0,.2f}".format(float(x)))

            dt = with_forecast.to_dict(orient='records')        

        # table message
        message = dcc.Markdown('With an initial investment of **£' + "{:0,.2f}".format(float(initial_lump_value)) + '** on **' + str(date_value)[:10] + '**:')


        return fig, dt, message


if __name__ == "__main__":
    app.run_server(debug=True)