import yfinance as yf
import json
from datetime import date, datetime
import pandas as pd
import numpy as np

# convert all keys to strings
def convert_keys_to_str(obj):
    if isinstance(obj, dict):
        # Remove NaN values and convert remaining keys to strings
        return {str(key): convert_keys_to_str(value)
                for key, value in obj.items()
                if not (isinstance(value, float) and np.isnan(value))}
    elif isinstance(obj, list):
        return [convert_keys_to_str(element) for element in obj]
    return obj

# custom json encoder for pandas dataframes
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime, pd.Timestamp)):
            return obj.isoformat()
        if isinstance(obj, pd.DataFrame):
            return convert_keys_to_str(obj.to_dict())
        if pd.isna(obj) or (isinstance(obj, float) and np.isnan(obj)):
            return None
        return super().default(obj)


# safe get data from yfinance
def safe_get_data(func, default=None):
    try:
        data = func()
        return data if data is not None else default
    except Exception:
        return default


# fetch data from yfinance
dat = yf.Ticker("SHOP.TO")

# save all data to a json file
with open('dat.json', 'w') as f:
    data = {}

    # Company Info
    info = safe_get_data(lambda: dat.info, {})
    if info:
        data["Company Info"] = info

    # Calendar
    calendar = safe_get_data(lambda: dat.calendar, {})
    if calendar:
        data["Calendar"] = calendar

    # Analyst Price Targets
    targets = safe_get_data(lambda: dat.analyst_price_targets, [])
    if targets is not None and len(targets) > 0:
        data["Analyst Price Targets"] = targets

    # Quarterly Income Statement
    income_stmt = safe_get_data(lambda: dat.quarterly_income_stmt)
    if isinstance(income_stmt, pd.DataFrame) and not income_stmt.empty:
        data["Quarterly Income Statement"] = convert_keys_to_str(
            income_stmt.to_dict())

    # History
    history = safe_get_data(lambda: dat.history(period='1mo'))
    if isinstance(history, pd.DataFrame) and not history.empty:
        data["History"] = convert_keys_to_str(history.to_dict())

    # Option Chain
    try:
        if dat.options and len(dat.options) > 0:
            option_chain = dat.option_chain(dat.options[0])
            if option_chain:
                data["Option Chain"] = option_chain._asdict()
    except Exception:
        pass

    # Write the data to file
    json.dump(data, f, cls=CustomJSONEncoder, indent=4)

# https://www.csrhub.com/CSR_and_sustainability_information/Apple-Inc
# https://finance.yahoo.com/quote/SHOP.TO/sustainability/?p=SHOP.TO
# https://www.sustainalytics.com/esg-rating/shopify-inc/