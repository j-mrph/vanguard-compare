import pytest
import pandas as pd
from testing import get_price_history
import requests_mock
import requests


@pytest.fixture
def sample_data():
    # Generate sample data for the tests
    return {
        "name": "LS20",
        "fund_code": "9235",
        "start_date": "2023-03-20",
    }


def test_get_price_history_returns_dataframe(sample_data):
    # Test that the function returns a Pandas DataFrame
    df = get_price_history(
        sample_data["name"], sample_data["fund_code"], sample_data["start_date"]
    )
    assert isinstance(df, pd.DataFrame)


def test_get_price_history_dataframe_columns(sample_data):
    # Test that the function returns a DataFrame with the expected columns
    df = get_price_history(
        sample_data["name"], sample_data["fund_code"], sample_data["start_date"]
    )
    expected_columns = ["price", "asOfDate", "currencyCode", "fund_name"]
    assert all(col in df.columns for col in expected_columns)


def test_get_price_history_date_conversion(sample_data):
    # Test that the function correctly converts the date string to a datetime object
    df = get_price_history(
        sample_data["name"], sample_data["fund_code"], sample_data["start_date"]
    )
    assert isinstance(df["asOfDate"][0], pd.Timestamp)
    assert df["asOfDate"][0].strftime("%Y-%m-%d") == sample_data["start_date"]
