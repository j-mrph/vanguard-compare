from dash import Dash, dcc, html, Input, Output, dash_table
from dash.dependencies import State
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import requests
from datetime import datetime
from dateutil import parser


# from testing import get_price_history, add_arima_forecast
import utility_functions

# list all vanguard funds
resp = requests.get("https://www.vanguardinvestor.co.uk/api/productList/")

df = pd.read_json(resp.text)

df = df[df["shareClass"] == "Accumulation"]

named_funds = df[["name", "portId"]]


app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
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
            # html.H3("Fund Comparison Dashboard"),
            html.Div(
                id="intro",
                children=dcc.Markdown(
                    """
        Analyze and compare the historic returns of all funds listed by
        [vanguardinvestor.co.uk](https://www.vanguardinvestor.co.uk).

        *Note: Accumulation funds only, calculated using daily variations in purchase price for the fund.*
        """
                ),
            ),
        ],
    )


def generate_control_card():
    """
    :return: A Div containing controls for graphs.
    """
    return html.Div(
        id="control-card",
        children=[
            html.P("Initial lump sum (£)"),
            dbc.Input(
                id="initial-lump-sum", type="number", min=1, max=999999999, value=10000
            ),
            html.Br(),
            html.P("Investment date (mm/dd/yyyy)"),
            dcc.DatePickerSingle(
                id="date-picker-select",
                min_date_allowed=datetime(1999, 1, 1),
                max_date_allowed=datetime(2999, 12, 31),
                initial_visible_month=datetime(2018, 1, 1),
                date=datetime(2017, 1, 1),
            ),
            html.Br(),
            html.Br(),
            html.P("Select Funds"),
            dcc.Dropdown(
                id="fundlist",
                options=[{"label": i, "value": i} for i in df.name.unique()],
                multi=True,
                value=[
                    " FTSE Global All Cap Index Fund",
                ],
            ),
            html.Br(),
            dcc.Checklist(
                id="arima",
                options=[
                    " Experimental - Include +3 Year forecast (Fitted to the timeframe that has been selected, calculated only with at least 3 years of data available)"
                ],
            ),
            html.Br(),
            dbc.Button("Submit", id="submit-val", n_clicks=0, color="primary"),
        ],
    )


app.layout = html.Div(
    id="app-container",
    children=[
        # Banner
        html.Div(
            id="banner",
            className="banner",
            children=[
                html.A(
                    [
                        html.Img(
                            src=app.get_asset_url(
                                "/GitHub-Mark/PNG/GitHub-Mark-64px.png"
                            )
                        )
                    ],
                    href="https://github.com/j-mrph/vanguard-compare",
                )
            ],
        ),
        html.Div(
            id="left-column",
            className="four columns",
            children=[description_card(), generate_control_card()]
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
                        html.Output(id="results-label"),
                        html.Div(
                            id="results_table",
                            children=dash_table.DataTable(
                                id="data-table-id",
                                style_table={"overflowX": "auto"},
                                fill_width=False,
                            ),
                        ),
                    ],
                ),
                html.Div(
                    dcc.Markdown(
                        """This app is for educational purposes only, past performance is not a reliable indicator of future returns. Purchase prices and sale prices will differ.
                For comprehensive fund details including ongoing charges visit the vanguard uk fund page. 
                """
                    )
                ),
            ],
        ),
    ],
)


# main callback to update graph, table and results message
@app.callback(
    Output("graph-container", "figure"),
    Output("data-table-id", "data"),
    Output("results-label", "children"),
    [Input("submit-val", "n_clicks")],
    [
        State("fundlist", "value"),
        State("date-picker-select", "date"),
        State("initial-lump-sum", "value"),
        State("arima", "value"),
    ],
    prevent_initial_call=True,
)
def update_line_chart(
    n_clicks, dropdown_value, date_value, initial_lump_value, arima_value
):
    if not all([dropdown_value, date_value, initial_lump_value]):
        # handling lack of inputs
        placeholder_fig = utility_functions.create_placeholder_chart()

        dt = pd.DataFrame().to_dict(orient="records")
        return placeholder_fig, dt, []
    else:
        fundcodes = named_funds[
            named_funds["name"].str.contains("|".join(dropdown_value))
        ]

        names = fundcodes.name.tolist()
        codes = fundcodes.portId.tolist()

        # here we are applying the get price history function to the funds
        # including the investment date and initial lump sum
        result = list(
            map(
                utility_functions.get_price_history,
                [initial_lump_value] * len(names),
                names,
                codes,
                [date_value] * len(names),
                [arima_value] * len(names),
            )
        )

        # combine all fund results for visualisation
        full_df = pd.concat(result)

        fig = px.line(
            full_df,
            x="asOfDate",
            y="price",
            color="fund_name",
            template="simple_white",
            labels={
                "asOfDate": "Date",
                "price": "Value (£)",
                "fund_name": "Fund",
            },
        )

        fig.update_layout(legend=dict(orientation="h", y=-0.3, title_text=""))

        dt = utility_functions.prepare_results_table(full_df)

        # table message
        message = dcc.Markdown(
            "With an initial investment of **£"
            + "{:0,.2f}".format(float(initial_lump_value))
            + "** on **"
            + str(date_value)[:10]
            + "**:"
        )

        return fig, dt, message


if __name__ == "__main__":
    app.run_server(debug=True)
