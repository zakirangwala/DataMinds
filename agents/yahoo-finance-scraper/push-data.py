import os
import sys
import json
import time
import subprocess
import psycopg2
from psycopg2 import sql
from datetime import datetime, date
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import logging
import argparse
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_upload.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database connection parameters
DB_URL = os.getenv('SUPABASE_URL')
DB_PASSWORD = os.getenv('SUPABASE_PW')


def connect_to_db():
    """Establish connection to Supabase PostgreSQL database"""
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = False  # Use transactions
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return None


def run_test_data_script(ticker):
    """Run test-data.py for a specific ticker and return the data"""
    max_retries = 3
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            # Save current ticker to a temporary environment variable
            os.environ['CURRENT_TICKER'] = ticker

            # Modify the test-data.py script to use the environment variable
            # This is a temporary solution - in production, you'd modify test-data.py to accept a ticker parameter
            original_script_path = os.path.join(
                os.path.dirname(__file__), 'test-data.py')
            temp_script_path = os.path.join(
                os.path.dirname(__file__), 'temp-test-data.py')

            with open(original_script_path, 'r') as f:
                script_content = f.read()

            # Replace the hardcoded ticker with the environment variable
            modified_content = script_content.replace(
                'ticker_symbol = "ACX.TO"',
                'ticker_symbol = os.environ.get("CURRENT_TICKER")'
            )

            # Add timeout parameters to requests to prevent hanging
            modified_content = modified_content.replace(
                'response = requests.get(url)',
                'response = requests.get(url, timeout=30)'
            )

            # Modify the JSON encoder to handle NaN values
            modified_content = modified_content.replace(
                'class CustomJSONEncoder(json.JSONEncoder):',
                '''class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime, pd.Timestamp)):
            return obj.isoformat()
        if isinstance(obj, pd.DataFrame):
            return convert_keys_to_str(obj.to_dict())
        if pd.isna(obj) or (isinstance(obj, float) and np.isnan(obj)):
            return None
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)'''
            )

            with open(temp_script_path, 'w') as f:
                f.write(modified_content)

            # Run the modified script
            logger.info(f"Running test-data.py for {ticker}")
            result = subprocess.run([sys.executable, temp_script_path],
                                    capture_output=True,
                                    text=True,
                                    check=False)

            # Check if the script ran successfully
            if result.returncode != 0:
                logger.error(
                    f"Error running test-data.py for {ticker}: {result.stderr}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    logger.error(
                        f"Failed to process {ticker} after {max_retries} attempts")
                    return None

            # Clean up
            try:
                os.remove(temp_script_path)
            except Exception as e:
                logger.warning(f"Could not remove temporary script: {str(e)}")

            # Read the generated JSON file
            try:
                with open('dat.json', 'r') as f:
                    data = json.load(f)

                # Validate the data
                if not data or not isinstance(data, dict):
                    logger.warning(f"Invalid data format for {ticker}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        return None

                # Log what data categories we have
                categories = list(data.keys())
                logger.info(
                    f"Retrieved data for {ticker} with categories: {categories}")

                return data
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON data for {ticker}: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                return None
            except FileNotFoundError:
                logger.error(f"dat.json file not found for {ticker}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                return None

        except subprocess.CalledProcessError as e:
            logger.error(
                f"Error running test-data.py for {ticker} (attempt {attempt+1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(
                    f"Failed to process {ticker} after {max_retries} attempts")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON data for {ticker}: {str(e)}")
            return None

        except FileNotFoundError as e:
            logger.error(f"File not found while processing {ticker}: {str(e)}")
            return None

        except Exception as e:
            logger.error(
                f"Unexpected error processing {ticker} (attempt {attempt+1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(
                    f"Failed to process {ticker} after {max_retries} attempts")
                return None


def insert_company_data(conn, ticker, data):
    """Insert company information into the companies table"""
    if 'Company Info' not in data:
        logger.warning(f"No company info available for {ticker}")
        return False

    info = data['Company Info']

    try:
        with conn.cursor() as cur:
            # Check if company already exists
            cur.execute(
                "SELECT ticker FROM companies WHERE ticker = %s", (ticker,))

            # Extract additional fields
            name = info.get('shortName', info.get('longName', None))
            sector = info.get('sector', None)
            industry = info.get('industry', None)
            website = info.get('website', None)
            headquarters = info.get('city', None)
            employees = info.get('fullTimeEmployees', None)
            long_business_summary = info.get('longBusinessSummary', None)
            market_cap = info.get('marketCap', None)

            if cur.fetchone():
                logger.info(f"Company {ticker} already exists, updating...")
                cur.execute("""
                    UPDATE companies 
                    SET name = %s, sector = %s, industry = %s, website = %s, 
                        headquarters = %s, employees = %s, long_business_summary = %s, market_cap = %s
                    WHERE ticker = %s
                """, (
                    name,
                    sector,
                    industry,
                    website,
                    headquarters,
                    employees,
                    long_business_summary,
                    market_cap,
                    ticker
                ))
            else:
                logger.info(f"Inserting new company {ticker}")
                cur.execute("""
                    INSERT INTO companies 
                    (ticker, name, sector, industry, website, headquarters, employees, long_business_summary, market_cap)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    ticker,
                    name,
                    sector,
                    industry,
                    website,
                    headquarters,
                    employees,
                    long_business_summary,
                    market_cap
                ))
        return True
    except Exception as e:
        logger.error(f"Error inserting company data for {ticker}: {str(e)}")
        conn.rollback()
        return False


def parse_date_string(date_str):
    """Parse various date string formats into a date object"""
    if not isinstance(date_str, str):
        return None

    # Remove timezone information if present
    date_str = re.sub(r'[-+]\d{2}:\d{2}$', '', date_str)

    # Try different date formats
    formats = [
        '%Y-%m-%d',                  # 2024-12-31
        '%Y-%m-%d %H:%M:%S',         # 2024-12-31 00:00:00
        '%Y-%m-%d %H:%M:%S%z',       # 2024-12-31 00:00:00-05:00
        '%Y-%m-%dT%H:%M:%S',         # 2024-12-31T00:00:00
        '%Y-%m-%dT%H:%M:%S.%f',      # 2024-12-31T00:00:00.000
        '%Y-%m-%dT%H:%M:%S.%fZ',     # 2024-12-31T00:00:00.000Z
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.date()
        except ValueError:
            continue

    # If we get here, try to extract just the date part
    match = re.search(r'(\d{4}-\d{2}-\d{2})', date_str)
    if match:
        try:
            return datetime.strptime(match.group(1), '%Y-%m-%d').date()
        except ValueError:
            pass

    return None


def insert_financial_data(conn, ticker, data):
    """Insert financial data into the financials table"""
    if 'Quarterly Income Statement' not in data and 'Company Info' not in data:
        logger.warning(f"No financial data available for {ticker}")
        return False

    try:
        # Get company info for additional financial metrics
        company_info = data.get('Company Info', {})

        # Process quarterly income statement data
        if 'Quarterly Income Statement' in data:
            income_stmt = data['Quarterly Income Statement']

            # Convert dictionary to DataFrame for easier processing
            if isinstance(income_stmt, dict):
                # Process each date key properly
                with conn.cursor() as cur:
                    for date_str in income_stmt.keys():
                        # Try to parse the date string
                        report_date = parse_date_string(date_str)
                        if not report_date:
                            logger.warning(
                                f"Skipping non-date key: {date_str}")
                            continue

                        # Get the data for this date
                        quarter_data = income_stmt[date_str]

                        # Skip if 'Net Income Continuous Operations' is missing
                        if 'Net Income Continuous Operations' not in quarter_data:
                            logger.warning(
                                f"Skipping record for {ticker} on {report_date} - missing 'Net Income Continuous Operations'")
                            continue

                        # Extract relevant financial metrics
                        revenue = quarter_data.get('Total Revenue')
                        net_income = quarter_data.get('Net Income')
                        ebitda = quarter_data.get('EBITDA')
                        gross_profit = quarter_data.get('Gross Profit')

                        # Store the entire quarter data as JSON
                        other_data_json = json.dumps(quarter_data)

                        # Check if record already exists
                        cur.execute("""
                            SELECT id FROM financials 
                            WHERE ticker = %s AND report_date = %s
                        """, (ticker, report_date))

                        if cur.fetchone():
                            logger.info(
                                f"Financial data for {ticker} on {report_date} already exists, updating...")
                            cur.execute("""
                                UPDATE financials 
                                SET revenue = %s, net_income = %s, ebitda = %s, gross_profit = %s, other_data = %s
                                WHERE ticker = %s AND report_date = %s
                            """, (
                                revenue,
                                net_income,
                                ebitda,
                                gross_profit,
                                other_data_json,
                                ticker,
                                report_date
                            ))
                        else:
                            logger.info(
                                f"Inserting financial data for {ticker} on {report_date}")
                            cur.execute("""
                                INSERT INTO financials 
                                (ticker, report_date, revenue, net_income, ebitda, gross_profit, other_data)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """, (
                                ticker,
                                report_date,
                                revenue,
                                net_income,
                                ebitda,
                                gross_profit,
                                other_data_json
                            ))
        # If no quarterly data but we have company info, create a record with just the company info data
        elif company_info:
            with conn.cursor() as cur:
                # Use today's date for the report
                report_date = datetime.now().date()

                # Check if record already exists
                cur.execute("""
                    SELECT id FROM financials 
                    WHERE ticker = %s AND report_date = %s
                """, (ticker, report_date))

                if cur.fetchone():
                    logger.info(
                        f"Financial data for {ticker} on {report_date} already exists, but no quarterly data available")
                else:
                    # Store company info as other_data
                    other_data_json = json.dumps(company_info)

                    logger.info(
                        f"Inserting minimal financial data for {ticker} from company info")
                    cur.execute("""
                        INSERT INTO financials 
                        (ticker, report_date, other_data)
                        VALUES (%s, %s, %s)
                    """, (
                        ticker,
                        report_date,
                        other_data_json
                    ))

        return True
    except Exception as e:
        logger.error(f"Error inserting financial data for {ticker}: {str(e)}")
        conn.rollback()
        return False


def insert_market_data(conn, ticker, data):
    """Insert market data into the market_data table"""
    success = False

    try:
        with conn.cursor() as cur:
            # Process historical price data
            if 'History' in data:
                history = data['History']

                # Get dates from the first available metric
                if 'Close' in history:
                    dates = list(history['Close'].keys())

                    for date_str in dates:
                        # Parse the date
                        price_date = parse_date_string(date_str)
                        if not price_date:
                            logger.warning(
                                f"Skipping invalid date format: {date_str}")
                            continue

                        # Get price data
                        open_price = history.get('Open', {}).get(date_str)
                        close_price = history.get('Close', {}).get(date_str)
                        high_price = history.get('High', {}).get(date_str)
                        low_price = history.get('Low', {}).get(date_str)
                        volume = history.get('Volume', {}).get(date_str)

                        # Check if record already exists
                        cur.execute("""
                            SELECT id FROM market_data 
                            WHERE ticker = %s AND date = %s
                        """, (ticker, price_date))

                        if cur.fetchone():
                            logger.info(
                                f"Market data for {ticker} on {price_date} already exists, updating...")
                            cur.execute("""
                                UPDATE market_data 
                                SET open_price = %s, close_price = %s, day_high = %s, day_low = %s, volume = %s
                                WHERE ticker = %s AND date = %s
                            """, (
                                open_price,
                                close_price,
                                high_price,
                                low_price,
                                volume,
                                ticker,
                                price_date
                            ))
                        else:
                            logger.info(
                                f"Inserting market data for {ticker} on {price_date}")
                            cur.execute("""
                                INSERT INTO market_data 
                                (ticker, date, open_price, close_price, day_high, day_low, volume)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """, (
                                ticker,
                                price_date,
                                open_price,
                                close_price,
                                high_price,
                                low_price,
                                volume
                            ))
                    success = True

        return success
    except Exception as e:
        logger.error(f"Error inserting market data for {ticker}: {str(e)}")
        conn.rollback()
        return False


def insert_esg_data(conn, ticker, data):
    """Insert ESG data into the esg_scores table"""
    if 'Sustainability' not in data:
        logger.warning(f"No sustainability data available for {ticker}")
        return False

    try:
        sustainability = data['Sustainability']

        # Get historical ESG scores if available
        historical_scores = None
        if 'Historical ESG Scores' in data:
            historical_scores = json.dumps(data['Historical ESG Scores'])

        with conn.cursor() as cur:
            # Check if record already exists
            cur.execute(
                "SELECT id FROM esg_scores WHERE ticker = %s", (ticker,))

            # Extract and normalize ESG data
            esg_risk_score = sustainability.get('ESG Risk Score')
            esg_risk_severity = sustainability.get('ESG Risk Severity')
            environment_score = sustainability.get('Environment Score')
            social_score = sustainability.get('Social Score')
            governance_score = sustainability.get('Governance Score')

            # Convert string values to appropriate numeric types
            if esg_risk_score is not None and not isinstance(esg_risk_score, (int, float)):
                try:
                    esg_risk_score = float(esg_risk_score)
                except (ValueError, TypeError):
                    esg_risk_score = None

            if environment_score is not None and not isinstance(environment_score, (int, float)):
                try:
                    environment_score = float(environment_score)
                except (ValueError, TypeError):
                    environment_score = None

            if social_score is not None and not isinstance(social_score, (int, float)):
                try:
                    social_score = float(social_score)
                except (ValueError, TypeError):
                    social_score = None

            if governance_score is not None and not isinstance(governance_score, (int, float)):
                try:
                    governance_score = float(governance_score)
                except (ValueError, TypeError):
                    governance_score = None

            if cur.fetchone():
                logger.info(
                    f"ESG data for {ticker} already exists, updating...")
                cur.execute("""
                    UPDATE esg_scores 
                    SET esg_risk_score = %s, esg_risk_severity = %s, 
                        environment_score = %s, social_score = %s, governance_score = %s,
                        historical_scores = %s, last_updated = %s
                    WHERE ticker = %s
                """, (
                    esg_risk_score,
                    esg_risk_severity,
                    environment_score,
                    social_score,
                    governance_score,
                    historical_scores,
                    datetime.now(),
                    ticker
                ))
            else:
                logger.info(f"Inserting ESG data for {ticker}")
                cur.execute("""
                    INSERT INTO esg_scores 
                    (ticker, esg_risk_score, esg_risk_severity, environment_score, social_score, governance_score, historical_scores, last_updated)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    ticker,
                    esg_risk_score,
                    esg_risk_severity,
                    environment_score,
                    social_score,
                    governance_score,
                    historical_scores,
                    datetime.now()
                ))
        return True
    except Exception as e:
        logger.error(f"Error inserting ESG data for {ticker}: {str(e)}")
        conn.rollback()
        return False


def insert_governance_risk_data(conn, ticker, data):
    """Insert governance risk data into the governance_risk table"""
    # Get company info for financial and analyst metrics
    company_info = data.get('Company Info', {})

    # Initialize variables
    total_debt = company_info.get('totalDebt')
    operating_cashflow = company_info.get('operatingCashflow')
    free_cashflow = company_info.get('freeCashflow')
    return_on_assets = company_info.get('returnOnAssets')
    return_on_equity = company_info.get('returnOnEquity')
    revenue_growth = company_info.get('revenueGrowth')
    earnings_growth = company_info.get('earningsGrowth')

    # Extract customPriceAlertConfidence from company info
    custom_price_alert_confidence = company_info.get(
        'customPriceAlertConfidence')
    if custom_price_alert_confidence is None:
        logger.info(
            f"customPriceAlertConfidence not found for {ticker}, using default value")
        custom_price_alert_confidence = "0.5"
    else:
        logger.info(
            f"Found customPriceAlertConfidence for {ticker}: {custom_price_alert_confidence}")

    # Create otherData JSON object with selected fields
    other_data = {}
    financial_keys = [
        'exDividendDate', 'payoutRatio', 'fiveYearAvgDividendYield', 'forwardPE',
        'averageVolume', 'averageVolume10days', 'marketCap', 'fiftyTwoWeekLow',
        'fiftyTwoWeekHigh', 'priceToSalesTrailing12Months', 'fiftyDayAverage',
        'twoHundredDayAverage', 'trailingAnnualDividendRate', 'trailingAnnualDividendYield',
        'currency', 'enterpriseValue', 'profitMargins', 'floatShares',
        'sharesOutstanding', 'sharesShort', 'sharesShortPriorMonth',
        'sharesShortPreviousMonthDate', 'dateShortInterest', 'sharesPercentSharesOut',
        'heldPercentInsiders', 'heldPercentInstitutions', 'shortRatio',
        'impliedSharesOutstanding', 'bookValue', 'priceToBook',
        'lastFiscalYearEnd', 'nextFiscalYearEnd', 'mostRecentQuarter',
        'netIncomeToCommon', 'trailingEps', 'forwardEps',
        'enterpriseToRevenue', 'enterpriseToEbitda', '52WeekChange',
        'lastDividendValue', 'lastDividendDate', 'quoteType',
        'currentPrice', 'totalCash',
        'totalCashPerShare', 'ebitda', 'quickRatio',
        'currentRatio', 'debtToEquity', 'revenuePerShare',
        'grossProfits', 'operatingMargins', 'ebitdaMargins',
        'grossMargins'
    ]

    for key in financial_keys:
        if key in company_info:
            other_data[key] = company_info[key]

    # Get analyst price targets
    target_high = None
    target_low = None
    target_mean = None
    recommendation = company_info.get('recommendationKey')

    # Try to get analyst targets from Analyst Price Targets first
    if 'Analyst Price Targets' in data:
        targets = data['Analyst Price Targets']
        target_high = targets.get('high', company_info.get('targetHighPrice'))
        target_low = targets.get('low', company_info.get('targetLowPrice'))
        target_mean = targets.get('mean', company_info.get('targetMeanPrice'))
    # If not available, get from Company Info
    else:
        target_high = company_info.get('targetHighPrice')
        target_low = company_info.get('targetLowPrice')
        target_mean = company_info.get('targetMeanPrice')

    # First try to get governance risk data from Company Info directly
    audit_risk = company_info.get('auditRisk')
    board_risk = company_info.get('boardRisk')
    compensation_risk = company_info.get('compensationRisk')
    shareholder_rights_risk = company_info.get(
        'shareHolderRightsRisk', company_info.get('shareholder_rights_risk'))
    overall_risk = company_info.get(
        'overallRisk', company_info.get('governanceEpochDate'))

    # Convert otherData to JSON string
    other_data_json = json.dumps(other_data)

    try:
        with conn.cursor() as cur:
            # Check if record already exists
            cur.execute(
                "SELECT id FROM governance_risk WHERE ticker = %s", (ticker,))

            # Ensure all values are properly converted
            if audit_risk is not None and not isinstance(audit_risk, int):
                try:
                    audit_risk = int(float(audit_risk))
                except (ValueError, TypeError):
                    audit_risk = None

            if board_risk is not None and not isinstance(board_risk, int):
                try:
                    board_risk = int(float(board_risk))
                except (ValueError, TypeError):
                    board_risk = None

            if compensation_risk is not None and not isinstance(compensation_risk, int):
                try:
                    compensation_risk = int(float(compensation_risk))
                except (ValueError, TypeError):
                    compensation_risk = None

            if shareholder_rights_risk is not None and not isinstance(shareholder_rights_risk, int):
                try:
                    shareholder_rights_risk = int(
                        float(shareholder_rights_risk))
                except (ValueError, TypeError):
                    shareholder_rights_risk = None

            if overall_risk is not None and not isinstance(overall_risk, int):
                try:
                    overall_risk = int(float(overall_risk))
                except (ValueError, TypeError):
                    overall_risk = None

            if cur.fetchone():
                logger.info(
                    f"Governance risk data for {ticker} already exists, updating...")
                cur.execute("""
                    UPDATE governance_risk 
                    SET audit_risk = %s, board_risk = %s, compensation_risk = %s, 
                        shareholder_rights_risk = %s, overall_risk = %s, 
                        total_debt = %s, operating_cashflow = %s, free_cashflow = %s,
                        return_on_assets = %s, return_on_equity = %s, revenue_growth = %s,
                        earnings_growth = %s, other_data = %s, custom_price_alert_confidence = %s,
                        analyst_target_high = %s, analyst_target_low = %s, analyst_target_mean = %s,
                        recommendation_key = %s, governance_last_updated = %s
                    WHERE ticker = %s
                """, (
                    audit_risk,
                    board_risk,
                    compensation_risk,
                    shareholder_rights_risk,
                    overall_risk,
                    total_debt,
                    operating_cashflow,
                    free_cashflow,
                    return_on_assets,
                    return_on_equity,
                    revenue_growth,
                    earnings_growth,
                    other_data_json,
                    custom_price_alert_confidence,
                    target_high,
                    target_low,
                    target_mean,
                    recommendation,
                    datetime.now(),
                    ticker
                ))
            else:
                logger.info(f"Inserting governance risk data for {ticker}")
                cur.execute("""
                    INSERT INTO governance_risk 
                    (ticker, audit_risk, board_risk, compensation_risk, shareholder_rights_risk, 
                    overall_risk, total_debt, operating_cashflow, free_cashflow, return_on_assets, 
                    return_on_equity, revenue_growth, earnings_growth, other_data, 
                    custom_price_alert_confidence, analyst_target_high, analyst_target_low, 
                    analyst_target_mean, recommendation_key, governance_last_updated)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    ticker,
                    audit_risk,
                    board_risk,
                    compensation_risk,
                    shareholder_rights_risk,
                    overall_risk,
                    total_debt,
                    operating_cashflow,
                    free_cashflow,
                    return_on_assets,
                    return_on_equity,
                    revenue_growth,
                    earnings_growth,
                    other_data_json,
                    custom_price_alert_confidence,
                    target_high,
                    target_low,
                    target_mean,
                    recommendation,
                    datetime.now()
                ))
            return True
    except Exception as e:
        logger.error(
            f"Error inserting governance risk data for {ticker}: {str(e)}")
        conn.rollback()
        return False

    # If we get here, no governance data was found
    logger.warning(f"No governance risk data available for {ticker}")
    return False


def process_ticker(ticker):
    """Process a single ticker: fetch data and upload to database"""
    logger.info(f"Processing ticker: {ticker}")

    # Run test-data.py to get data for this ticker
    data = run_test_data_script(ticker)
    if not data:
        logger.error(f"Failed to get data for {ticker}")
        return False

    # Connect to database
    conn = connect_to_db()
    if not conn:
        logger.error(f"Failed to connect to database for {ticker}")
        return False

    try:
        # Insert data into various tables
        company_success = insert_company_data(conn, ticker, data)
        financial_success = insert_financial_data(conn, ticker, data)
        market_success = insert_market_data(conn, ticker, data)
        esg_success = insert_esg_data(conn, ticker, data)
        governance_success = insert_governance_risk_data(conn, ticker, data)

        # Commit transaction if at least one insertion was successful
        if any([company_success, financial_success, market_success, esg_success, governance_success]):
            conn.commit()
            logger.info(f"Successfully processed {ticker}")
            return True
        else:
            logger.warning(f"No data was inserted for {ticker}")
            conn.rollback()
            return False
    except Exception as e:
        logger.error(f"Error processing {ticker}: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()


def main():
    """Main function to process all tickers"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Process stock data and upload to Supabase')
    parser.add_argument(
        '--ticker', '-t', help='Process a single ticker (for testing)')
    parser.add_argument('--delay', '-d', type=int, default=2,
                        help='Delay between processing tickers (seconds)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    args = parser.parse_args()

    # Set logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    logger.info("Starting data upload process")

    # Process a single ticker if specified
    if args.ticker:
        logger.info(f"Processing single ticker: {args.ticker}")
        success = process_ticker(args.ticker)
        if success:
            logger.info(f"Successfully processed {args.ticker}")
        else:
            logger.error(f"Failed to process {args.ticker}")
        return

    # Read tickers from companies.txt
    try:
        # Try multiple possible locations for companies.txt
        possible_paths = [
            '../companies.txt',  # If running from data/ directory
            'companies.txt',     # If running from project root
            os.path.join(os.path.dirname(__file__),
                         '../companies.txt'),  # Relative to script
            os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         '../companies.txt')  # Absolute path
        ]

        tickers = None
        for path in possible_paths:
            try:
                if os.path.exists(path):
                    logger.info(f"Found companies.txt at {path}")
                    with open(path, 'r') as f:
                        tickers = [line.strip() for line in f if line.strip()]
                    break
            except Exception:
                continue

        if not tickers:
            logger.error(
                "Could not find companies.txt in any expected location")
            return
    except Exception as e:
        logger.error(f"Error reading tickers file: {str(e)}")
        return

    logger.info(f"Found {len(tickers)} tickers to process")

    # Process each ticker
    success_count = 0
    for i, ticker in enumerate(tickers):
        logger.info(f"Processing ticker {i+1}/{len(tickers)}: {ticker}")

        if process_ticker(ticker):
            success_count += 1

        # Add a small delay to avoid overwhelming APIs
        if i < len(tickers) - 1:  # Don't delay after the last ticker
            logger.debug(f"Waiting {args.delay} seconds before next ticker...")
            time.sleep(args.delay)

    logger.info(
        f"Completed processing {success_count}/{len(tickers)} tickers successfully")


if __name__ == "__main__":
    main()
