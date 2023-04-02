import requests
import pandas as pd
import json
from pmdarima.arima import auto_arima
import plotly.graph_objects as go
from datetime import datetime


def create_placeholder_chart():
    fig_none = go.Figure()
    fig_none.add_trace(
        go.Scatter(
            x=[0, 1, 2, 3, 4, 5, 6, 7, 8, 10],
            y=[0, 4, 5, 1, 2, 3, 2, 4, 2, 1],
            mode="lines+markers+text",
            text=["", "", "", "", "Please complete inputs!", "", "", "", "", ""],
            textfont_size=40,
        )
    ),

    fig_none.update_layout(template="simple_white")

    return fig_none


def add_arima_forecast(
    returns_df: pd.DataFrame, name: str, arima: bool
) -> pd.DataFrame:
    days_ago = (datetime.now() - returns_df["asOfDate"].min()).days

    if not arima or days_ago <= 1096:
        return returns_df

    # make a forecast using auto ARIMA
    model = auto_arima(returns_df["price"], seasonal=False)
    forecast = model.predict(n_periods=1095)

    # create a new dataframe for the forecast
    last_date = returns_df["asOfDate"].max()
    dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1),
        end=last_date + pd.Timedelta(days=1095),
        freq="D",
    )
    forecast_df = pd.DataFrame(
        {
            "asOfDate": dates,
            "price": forecast,
            "fund_name": f"+1 year prediction: {name}",
        }
    )

    return pd.concat(
        [returns_df[["asOfDate", "price", "fund_name"]], forecast_df], ignore_index=True
    )


def get_price_history(
    name: str, fund_code: str, start_date: str, arima: bool
) -> pd.DataFrame:
    # query url
    url = "https://www.vanguardinvestor.co.uk/gpx/graphql"

    #  body of the API req
    body = """query PriceDetailsQuery($portIds: [String!]!, $startDate: String!, $endDate: String!, $limit: Float) {
    funds(portIds: $portIds) {
        pricingDetails {
        navPrices(startDate: $startDate, endDate: $endDate, limit: $limit) {
            items {
            price
            asOfDate
            currencyCode
            __typename
            }
            __typename
        }
        marketPrices(startDate: $startDate, endDate: $endDate, limit: $limit) {
            items {
            portId
            items {
                price
                asOfDate
                currencyCode
                __typename
            }
            __typename
            }
            __typename
        }
        __typename
        }
        __typename
    }
    }
    """

    # Set the variables for the GraphQL query
    variables = {
        "portIds": [fund_code],
        "startDate": start_date,
        "endDate": datetime.now().strftime("%Y-%m-%d"),
        "limit": 0,
    }

    # Set headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/109.0",
        "Content-Type": "application/json",
    }

    # Send the API request with the GraphQL query
    try:
        response = requests.post(
            url, headers=headers, json={"query": body, "variables": variables}
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(err)

    price_data = json.loads(response.text)["data"]["funds"][0]["pricingDetails"][
        "navPrices"
    ]["items"]

    df = pd.DataFrame(price_data)

    # adding fund name to the df
    df["fund_name"] = name

    # managing dates so starting point can be set
    df["asOfDate"] = pd.to_datetime(df["asOfDate"], format="%Y-%m-%d")

    # arrange by date
    df = df.sort_values(by=["asOfDate"], ascending=True, ignore_index=True)

    # apply arima forecast (if applicable)
    df = add_arima_forecast(df, name, arima)

    return df
