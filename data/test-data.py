import yfinance as yf
import json
from datetime import date, datetime
import pandas as pd
import numpy as np
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_historical_esg_data(ticker):
    """Fetch historical ESG data from Financial Modeling Prep API"""
    # Remove .TO suffix if present for FMP API
    base_ticker = ticker.split('.')[0]

    api_key = os.getenv('FMP_API_KEY')
    if not api_key:
        print("Warning: FMP_API_KEY not found in environment variables")
        return None

    url = f"https://financialmodelingprep.com/stable/esg-disclosures?symbol={base_ticker}&apikey={api_key}"

    try:
        # Add timeout to prevent hanging
        response = requests.get(url, timeout=10)

        # Check status code first
        if response.status_code == 401:
            print("Error: Invalid API key or unauthorized access")
            return None
        elif response.status_code == 403:
            print("Error: API access forbidden. Please check your subscription plan")
            return None
        elif response.status_code == 429:
            print("Error: API rate limit exceeded")
            return None
        elif response.status_code == 404:
            print(f"Error: No ESG data found for ticker {base_ticker}")
            return None
        elif response.status_code != 200:
            print(
                f"Error: API request failed with status code {response.status_code}")
            return None

        # Try to parse JSON response
        try:
            data = response.json()
            if not data or (isinstance(data, list) and len(data) == 0):
                print(f"No ESG data available for {base_ticker}")
                return None
            return data
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response: {str(e)}")
            return None

    except requests.exceptions.Timeout:
        print(f"Error: API request timed out for {base_ticker}")
        return None
    except requests.exceptions.ConnectionError:
        print(f"Error: Connection failed. Please check your internet connection")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error while fetching ESG data: {str(e)}")
        return None


def scrape_sustainability_data(ticker):
    # Setup Chrome options
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run in headless mode
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    # Initialize the driver
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)  # Wait up to 10 seconds

    try:
        # Navigate to the sustainability page
        url = f'https://finance.yahoo.com/quote/{ticker}/sustainability?p={ticker}'
        driver.get(url)

        # Add a small delay to ensure page loads
        time.sleep(2)

        # Dictionary to store all sustainability data
        sustainability_data = {}

        # Get main ESG score and severity
        try:
            esg_scores = driver.find_elements(
                By.CLASS_NAME, 'scoreRank.yf-y3c2sq')
            if len(esg_scores) >= 1:
                sustainability_data['ESG Risk Score'] = esg_scores[0].text

            severity = driver.find_element(By.CLASS_NAME, 'perf.yf-y3c2sq')
            if severity:
                sustainability_data['ESG Risk Severity'] = severity.text

            # Environment, Social, and Governance scores are the next elements
            if len(esg_scores) >= 4:
                sustainability_data['Environment Score'] = esg_scores[1].text
                sustainability_data['Social Score'] = esg_scores[2].text
                sustainability_data['Governance Score'] = esg_scores[3].text

        except (NoSuchElementException, IndexError) as e:
            print(f"Error getting ESG scores: {str(e)}")
            sustainability_data['ESG Risk Score'] = None
            sustainability_data['ESG Risk Severity'] = None
            sustainability_data['Environment Score'] = None
            sustainability_data['Social Score'] = None
            sustainability_data['Governance Score'] = None

        # Get all tables on the page for additional ESG data
        try:
            tables = driver.find_elements(By.TAG_NAME, 'table')
            for table in tables:
                rows = table.find_elements(By.TAG_NAME, 'tr')
                table_data = {}
                for row in rows:
                    try:
                        cols = row.find_elements(By.TAG_NAME, 'td')
                        if len(cols) >= 2:
                            table_data[cols[0].text.strip()
                                       ] = cols[1].text.strip()
                    except:
                        continue

                # Try to identify the table based on its first row
                if rows and len(rows) > 0:
                    first_row = rows[0].text.strip().lower()
                    if 'controversy' in first_row:
                        sustainability_data['Controversy Data'] = table_data
                    elif 'involvement' in first_row:
                        sustainability_data['ESG Activities Involvement'] = table_data
                    else:
                        sustainability_data['Additional ESG Data'] = table_data

        except NoSuchElementException as e:
            print(f"Error getting tables: {str(e)}")

        # Print the data for debugging
        print("Scraped sustainability data:", sustainability_data)

        return sustainability_data

    finally:
        driver.quit()

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


if __name__ == "__main__":
    # fetch data from yfinance
    ticker_symbol = "ACX.TO"
    dat = yf.Ticker(ticker_symbol)

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

        # Current Sustainability Data from Yahoo Finance
        sustainability_data = scrape_sustainability_data(ticker_symbol)
        if sustainability_data:
            data["Sustainability"] = sustainability_data

        # Historical ESG Data from Financial Modeling Prep
        historical_esg = get_historical_esg_data(ticker_symbol)
        if historical_esg:
            data["Historical ESG Scores"] = historical_esg

        # Write the data to file
        json.dump(data, f, cls=CustomJSONEncoder, indent=4)

    print("Data has been saved to dat.json")
