# Vanguard U.K. Fund Comparison
Web app to compare Vanguard UK accumulation funds monthly returns. Fetches direct from Vanguard UK website. Built using python Dash.

Check it out deployed [here](https://vanguard-dash-app.herokuapp.com/).

Set an initial lump sum and investment date to see today's value based on monthly changes of fund value. 

 This is a personal project which icludes arima prediction based on historic returns just for fun. Historic returns are not a reliable indicator of future performance. This tool is **not** investment advice. For in-depth information on each fund visit it's respective page on the Vanguard UK website. 

## Running locally
To run this app locally clone this repo and create a virtual environment with:

```
python -m venv .venv
```
Then activate your virtual environment with:

Windows: `.venv\Scripts\activate.bat`

Other OSes: `source .venv/bin/activate`

Once you have activated your virtual environment you can install the necessary python packages:

```
pip install -r requirements.txt
```

Then run `app.py` for a local instance.

## Acknowledgements
- [Dash Sample Apps](https://github.com/plotly/dash-sample-apps) by plotly team for useful reference and templates 