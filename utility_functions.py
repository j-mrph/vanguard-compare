import requests
import pandas as pd
import json
from pmdarima.arima import auto_arima
import plotly.graph_objects as go

# This is the main function which will calculate final value of a fund given initial lump sum 
# and start date - will forecast for +3 years if arima variable is populated

def get_return(name, fund_code, start_date, initial_value, arima):

    print('Fetching returns for fund ' + name)

    resp = requests.get('https://www.vanguardinvestor.co.uk/api/fund-data/'+ fund_code +'/S/past-performance-returns')

    returns_df = pd.DataFrame(json.loads(resp.text)['returns'])

    # adding fund name to the df
    returns_df['fund_name'] = name

    # managing dates so starting point can be set
    returns_df['newdate'] = pd.to_datetime(returns_df['asOfDate'].str[:10], format = "%Y-%m-%d")
    returns_df = returns_df[(returns_df['newdate'] >= start_date[:10]) ]

    # cleaning missing values and calculating cumulative percentage change
    returns_df = returns_df.dropna(subset=['monthPercent'])
    returns_df = returns_df.sort_values(by = ['asOfDate'], ascending = True, ignore_index=True)

    returns_df['divided'] = returns_df['monthPercent'] / 100

    # initial value becomes 1 (100%)
    returns_df.at[0, 'divided'] = 1
    
    returns_df['calculated'] = returns_df['divided'].cumsum() * initial_value

    # arima forecasting if checkbox ticked
    if arima and len(returns_df.index) > 36:

        train = returns_df[['newdate', 'calculated']]
        train.set_index('newdate', inplace = True)
        test = train[-36:] 

        arima_model = auto_arima(train, p = 3, d = 1, q = 0)

        prediction = pd.DataFrame(arima_model.predict(n_periods = 36), index = test.index + pd.Timedelta(1096, 'd'))

        prediction.columns = ['calculated']

        prediction['fund_name'] = '+3 year prediction:' + name

        # print(returns_df[['newdate', 'calculated', 'fund_name']])
        prediction.reset_index(inplace=True)

        combined = pd.concat([returns_df[['newdate', 'calculated', 'fund_name']], prediction])

        return combined
    else: 

        return returns_df



def create_placeholder_chart():

    fig_none = go.Figure()
    fig_none.add_trace(go.Scatter(
    x=[0, 1, 2, 3, 4, 5, 6, 7, 8, 10],
    y=[0, 4, 5, 1, 2, 3, 2, 4, 2, 1],
    mode="lines+markers+text",
    text=["","","","", "Please complete inputs!", "","","", "", ''],
    textfont_size=40,
    )),

    fig_none.update_layout(template = 'simple_white')

    return fig_none

