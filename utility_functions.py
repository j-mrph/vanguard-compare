import requests
import pandas as pd
import json

import plotly.graph_objects as go
from datetime import datetime
from prophet import Prophet
from io import StringIO


def list_funds():
    # list all vanguard funds
    resp = requests.get("https://www.vanguardinvestor.co.uk/api/productList/")

    df = pd.read_json(StringIO(resp.text))

    df = df[df["shareClass"] == "Accumulation"]

    return df[["name", "portId"]]


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


def add_prophet_forecast(
    returns_df: pd.DataFrame, name: str, prophet: bool
) -> pd.DataFrame:
    days_ago = (datetime.now() - returns_df["asOfDate"].min()).days

    if not prophet or days_ago <= 1096:
        return returns_df

    # create a new dataframe with column names 'ds' and 'y'
    df = returns_df[["asOfDate", "price"]].rename(
        columns={"asOfDate": "ds", "price": "y"}
    )

    # create and fit a Prophet model
    model = Prophet()
    model.fit(df)

    # make a forecast for the next 3 years
    future = model.make_future_dataframe(periods=1095, include_history=False)
    forecast = model.predict(future)

    forecast_dates = forecast["ds"].tolist()

    # create a new dataframe for the forecast
    forecast_df = pd.DataFrame(
        {
            "asOfDate": forecast_dates,
            "price": forecast["yhat"].tolist(),
            "fund_name": f"+3 year prediction: {name}",
        }
    )

    return pd.concat(
        [returns_df[["asOfDate", "price", "fund_name"]], forecast_df],
        ignore_index=True,
    )



def calculate_investment_value(
    df: pd.DataFrame, initial_investment: float
) -> pd.DataFrame:
    # Check if input dataframe has required columns
    if "price" not in df.columns:
        raise ValueError("Input dataframe must contain 'price' column")

    # Check if input dataframe has at least two rows
    if len(df) < 2:
        raise ValueError("Input dataframe must have at least two rows")

    # Check if initial investment is a positive number
    if initial_investment <= 0:
        raise ValueError("Initial investment must be a positive number")

    # Calculate daily change percentage
    df["Daily Change %"] = df["price"].pct_change()

    # Calculate cumulative daily change percentage
    df["Cumulative Change %"] = (1 + df["Daily Change %"]).cumprod() - 1

    # Calculate value of investment
    df["price"] = (1 + df["Cumulative Change %"]) * initial_investment

    # drop first row as no change on investment date
    df = df.drop(index=0)

    return df


def get_price_history(
    initial_investment: float, name: str, fund_code: str, start_date: str, arima: bool
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

    # calculate investment value
    df = calculate_investment_value(df, initial_investment)

    # apply arima forecast (if applicable)
    df = add_prophet_forecast(df, name, arima)

    return df


def build_table_with_forecasts(plus_3, df_filtered):

    # Create a new column 'prediction_type' to distinguish current and predicted prices
    df_filtered['prediction_type'] = df_filtered['fund_name'].apply(lambda x: 'predicted' if '+3 year prediction' in x else 'current')

    # Remove the '+3 year prediction: ' prefix from fund names
    df_filtered['clean_fund_name'] = df_filtered['fund_name'].replace(r'\+3 year prediction: ', '', regex=True)

    # Pivot the table
    df_pivoted = df_filtered.pivot(index='clean_fund_name', columns='prediction_type', values='price')

    # Rename the columns
    df_pivoted.columns = ['price today', 'price +3 years']

    # Reset index and rename the index column
    df_final = df_pivoted.reset_index().rename(columns={'clean_fund_name': 'fund_name'})
    df_final.columns = ["Fund", "Today Value", "Predicted +3y Value"]

    # format the price columns
    df_final["Today Value"] = df_final["Today Value"].apply(
        lambda x: "£{:0,.2f}".format(float(x))
    )
    df_final["Predicted +3y Value"] = df_final["Predicted +3y Value"].apply(
        lambda x: "£{:0,.2f}".format(float(x))
    )

    # convert the dataframe to a list of dictionaries
    return df_final.to_dict(orient="records")


def prepare_results_table(full_df):
    # select only the last row for each fund
    df_filtered = full_df.groupby("fund_name").tail(1).copy()

    # select only the necessary columns
    df_filtered = df_filtered[["fund_name", "price"]]

    # filter funds starting with "+3"
    plus_3 = df_filtered.loc[df_filtered.fund_name.str.startswith("+3", na=False)]

    if not plus_3.empty:
        return build_table_with_forecasts(plus_3, df_filtered)

    # if no forecast has been carried out
    df_filtered.columns = ["Fund", "Today Value"]

    # format the price column
    df_filtered["Today Value"] = df_filtered["Today Value"].apply(
        lambda x: "£{:0,.2f}".format(float(x))
    )

    # convert the dataframe to a list of dictionaries
    return df_filtered.to_dict(orient="records")
