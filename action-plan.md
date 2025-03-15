# Action Plan for Data Upload to Supabase

## Overview

Created a script (push-data.py) that:

1. Processes each ticker from companies.txt
2. Runs test-data.py for each ticker to collect data
3. Uploads the collected data to Supabase using credentials from .env
4. Handles errors gracefully

## Database Structure

Based on queries.txt, the database has these tables:

- companies (ticker, name, sector, industry, website, headquarters, employees, long_business_summary, market_cap)
- financials (ticker, report_date, revenue, net_income, ebitda, gross_profit, total_debt, operating_cashflow, free_cashflow, return_on_assets, return_on_equity, earnings_growth, revenue_growth, other_data, custom_price_alert_confidence)
- market_data (ticker, date, open_price, close_price, day_high, day_low, volume, analyst_target_high, analyst_target_low, analyst_target_mean, recommendation_key)
- governance_risk (ticker, audit_risk, board_risk, compensation_risk, shareholder_rights_risk, overall_risk, governance_last_updated)
- esg_scores (ticker, esg_risk_score, esg_risk_severity, environment_score, social_score, governance_score, last_updated)
- sentiment_data (ticker, source, sentiment_score, date)

## Data Mapping

Map data from test-data.py output to database tables:

1. **Company Info** → companies table

   - ticker, name, sector, industry, website, headquarters, employees
   - Added: long_business_summary, market_cap
   - Also used for governance_risk and market_data (analyst targets)
   - Also used for financials (revenue_growth, return_on_equity, return_on_assets, free_cashflow, operating_cashflow, total_debt)

2. **Calendar** → No direct mapping, may extract relevant dates

3. **Analyst Price Targets** → market_data table

   - analyst_target_high, analyst_target_low, analyst_target_mean, recommendation_key

4. **Quarterly Income Statement** → financials table

   - revenue, net_income, ebitda, gross_profit, etc.
   - Added: other_data (JSONB field containing additional financial metrics)
   - Added: custom_price_alert_confidence

5. **History** → market_data table

   - open_price, close_price, day_high, day_low, volume

6. **Option Chain** → No direct mapping, skipped

7. **Sustainability** → esg_scores table

   - esg_risk_score, esg_risk_severity, environment_score, social_score, governance_score
   - Also used as fallback for governance_risk

8. **Historical ESG Scores** → governance_risk table
   - audit_risk, board_risk, compensation_risk, shareholder_rights_risk, overall_risk

## Implementation Details

### Key Functions

1. `run_test_data_script(ticker)`: Runs test-data.py for a specific ticker by creating a temporary modified version

   - Enhanced to capture script output and handle errors
   - Improved JSON encoding to handle NumPy types and NaN values
   - Added validation of returned data
   - Added logging of available data categories

2. `parse_date_string(date_str)`: Helper function to parse various date formats

   - Handles multiple date formats including timezone information
   - Uses regex to extract date components when needed
   - Gracefully handles invalid date strings

3. `insert_company_data(conn, ticker, data)`: Inserts/updates company information

   - Added support for long_business_summary and market_cap fields

4. `insert_financial_data(conn, ticker, data)`: Inserts/updates quarterly financial data

   - Fixed date parsing to handle various formats
   - Added support for financial ratios (ROA, ROE)
   - Added support for revenue_growth, free_cashflow, operating_cashflow, total_debt
   - Added other_data JSONB field with additional financial metrics
   - Added custom_price_alert_confidence field
   - Now extracts data from both Quarterly Income Statement and Company Info
   - Creates a record with just Company Info data if Quarterly Income Statement is not available

5. `insert_market_data(conn, ticker, data)`: Inserts/updates market data and analyst targets

   - Fixed date parsing for market history data
   - Added support for creating new records with analyst data
   - Improved handling of missing data fields
   - Now checks both Analyst Price Targets and Company Info for analyst data
   - Properly normalizes data types before insertion

6. `insert_esg_data(conn, ticker, data)`: Inserts/updates ESG scores

   - Added data type normalization for numeric fields
   - Converts string values to appropriate numeric types
   - Handles conversion errors gracefully

7. `insert_governance_risk_data(conn, ticker, data)`: Inserts/updates governance risk data

   - Now checks Company Info first for governance risk data
   - Added fallback to use Sustainability data if other sources not available
   - Added data type normalization for all integer fields
   - Improved error handling and logging

8. `process_ticker(ticker)`: Orchestrates the data collection and insertion for a single ticker

9. `main()`: Processes all tickers from the companies.txt file
   - Added command-line arguments for single ticker processing and verbosity

### Data Normalization

- All numeric data is properly converted to the correct data type before insertion
- String values that should be numeric are converted appropriately
- Integer fields in governance_risk are properly converted from strings or floats
- Decimal fields in esg_scores are properly converted from strings
- All conversion errors are handled gracefully with fallback to NULL values
- Multiple data sources are checked to ensure complete data coverage

### Error Handling

- Each function has comprehensive error handling
- Database operations use transactions to ensure data integrity
- Missing data categories are gracefully skipped
- API errors are logged but don't stop the process
- Database connection issues are handled
- Added retry logic with exponential backoff for transient errors
- Data type conversion errors are handled gracefully

### Logging

- Detailed logging to both console and file (data_upload.log)
- Tracks progress, successes, and failures
- Provides visibility into the data processing pipeline
- Added logging of available data categories for each ticker

## How to Run

1. Ensure all dependencies are installed:

   ```
   pip install psycopg2 pandas numpy yfinance selenium requests python-dotenv
   ```

2. Make sure the .env file contains all required credentials:

   - FMP_API_KEY
   - SUPABASE_URL
   - SUPABASE_PW
   - SUPABASE_API_KEY

3. Ensure companies.txt contains the list of tickers to process

4. Run the script:

   ```
   cd data
   python push-data.py
   ```

5. For a single ticker (useful for testing):

   ```
   python push-data.py --ticker SHOP.TO
   ```

6. For more verbose logging:

   ```
   python push-data.py --verbose
   ```

7. To adjust the delay between processing tickers:

   ```
   python push-data.py --delay 5
   ```

8. Monitor the output and check data_upload.log for detailed progress

## Troubleshooting

### Date Format Issues

- The script now handles various date formats including those with timezone information
- A custom date parser handles multiple formats and extracts date components when needed
- Invalid dates are logged and skipped rather than causing errors

### Data Type Issues

- All numeric data is properly normalized before insertion
- String values are converted to appropriate numeric types (int, float)
- Conversion errors are handled gracefully with fallback to NULL values
- Database constraints are respected by ensuring correct data types

### Empty Tables

- If tables remain empty, check the logs for specific errors
- Verify that the data from test-data.py contains the expected categories
- Use the `--ticker` and `--verbose` options to test with a single ticker
- Check database constraints and data types

### API Errors

- FMP API errors (402 Payment Required) are expected and handled gracefully
- ESG data scraping errors are handled and won't stop the process
- Network timeouts now have retry logic with exponential backoff

## Potential Improvements

1. Add command-line arguments to:

   - Process a subset of tickers
   - Skip certain data categories
   - Control logging verbosity

2. Implement rate limiting for API calls

3. Add parallel processing for faster execution

4. Create a dashboard to monitor the data collection process

5. Add data validation before insertion

6. Implement retry logic for failed API calls
