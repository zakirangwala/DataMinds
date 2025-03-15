# Action Plan for Data Upload to Supabase

## Overview

Created a script (push-data.py) that:

1. Processes each ticker from companies.txt
2. Runs test-data.py for each ticker to collect data
3. Uploads the collected data to Supabase using credentials from .env
4. Handles errors gracefully

## Database Structure

Based on queries.txt, the database has these tables:

- companies
- financials
- market_data
- governance_risk
- esg_scores
- sentiment_data

## Data Mapping

Map data from test-data.py output to database tables:

1. **Company Info** → companies table

   - ticker, name, sector, industry, website, headquarters, employees

2. **Calendar** → No direct mapping, may extract relevant dates

3. **Analyst Price Targets** → market_data table

   - analyst_target_high, analyst_target_low, analyst_target_mean, recommendation_key

4. **Quarterly Income Statement** → financials table

   - revenue, net_income, ebitda, gross_profit, etc.

5. **History** → market_data table

   - open_price, close_price, day_high, day_low, volume

6. **Option Chain** → No direct mapping, skipped

7. **Sustainability** → esg_scores table

   - esg_risk_score, esg_risk_severity, environment_score, social_score, governance_score

8. **Historical ESG Scores** → governance_risk table
   - audit_risk, board_risk, compensation_risk, shareholder_rights_risk, overall_risk

## Implementation Details

### Key Functions

1. `run_test_data_script(ticker)`: Runs test-data.py for a specific ticker by creating a temporary modified version
2. `insert_company_data(conn, ticker, data)`: Inserts/updates company information
3. `insert_financial_data(conn, ticker, data)`: Inserts/updates quarterly financial data
4. `insert_market_data(conn, ticker, data)`: Inserts/updates market data and analyst targets
5. `insert_esg_data(conn, ticker, data)`: Inserts/updates ESG scores
6. `insert_governance_risk_data(conn, ticker, data)`: Inserts/updates governance risk data
7. `process_ticker(ticker)`: Orchestrates the data collection and insertion for a single ticker
8. `main()`: Processes all tickers from the companies.txt file

### Error Handling

- Each function has comprehensive error handling
- Database operations use transactions to ensure data integrity
- Missing data categories are gracefully skipped
- API errors are logged but don't stop the process
- Database connection issues are handled

### Logging

- Detailed logging to both console and file (data_upload.log)
- Tracks progress, successes, and failures
- Provides visibility into the data processing pipeline

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

5. Monitor the output and check data_upload.log for detailed progress

## Potential Improvements

1. Add command-line arguments to:

   - Process a single ticker
   - Skip certain data categories
   - Control logging verbosity

2. Implement rate limiting for API calls

3. Add parallel processing for faster execution

4. Create a dashboard to monitor the data collection process

5. Add data validation before insertion

6. Implement retry logic for failed API calls
