import json
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import google.generativeai as genai
import time
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('esg_scoring.log'),
        logging.StreamHandler()
    ]
)


class ESGScoringAgent:
    def __init__(self):
        # Initialize Supabase client
        load_dotenv()
        url = os.getenv("SUPABASE_STRING")
        key = os.getenv("SUPABASE_API_KEY")
        self.supabase: Client = create_client(url, key)

        # Initialize Gemini
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-2.0-flash')

        # Rate limiting settings (15 RPM)
        self.request_timestamps = []
        self.max_requests_per_minute = 15
        self.request_window = 60  # seconds

        # Default scores when data is missing
        self.default_scores = {
            'environmental': 50,
            'social': 50,
            'governance': 50,
            'total_esg': 50
        }

        logging.info("ESGScoringAgent initialized successfully")

    def _rate_limit(self):
        """
        Implement rate limiting for Gemini API
        """
        current_time = time.time()

        # Remove timestamps older than our window
        self.request_timestamps = [ts for ts in self.request_timestamps
                                   if current_time - ts < self.request_window]

        # If we've hit our limit, wait
        if len(self.request_timestamps) >= self.max_requests_per_minute:
            sleep_time = self.request_timestamps[0] + \
                self.request_window - current_time
            if sleep_time > 0:
                logging.info(
                    f"Rate limit reached. Waiting for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
            self.request_timestamps = self.request_timestamps[1:]

        # Add current request timestamp
        self.request_timestamps.append(current_time)

    def _validate_scores(self, scores: Dict[str, float]) -> bool:
        """
        Validate the scores returned by Gemini
        """
        required_keys = ['environmental_score', 'social_score',
                         'governance_score', 'total_esg_score']

        # Check if all required keys exist
        if not all(key in scores for key in required_keys):
            logging.error(f"Missing required keys in scores: {scores}")
            return False

        # Check if all values are floats and within reasonable range (0-100)
        for key in required_keys:
            value = scores[key]
            if not isinstance(value, (int, float)):
                logging.error(f"Invalid score type for {key}: {type(value)}")
                return False
            if not (0 <= value <= 100):
                logging.error(f"Score out of range for {key}: {value}")
                return False

        return True

    def _generate_prompt(self, company_data: Dict[str, Any]) -> str:
        """
        Generate the prompt for Gemini API using a structured ESG framework with boolean criteria
        """
        company_name = company_data['company'].get('name', 'Unknown Company')
        ticker = company_data['company'].get('ticker', 'Unknown Ticker')

        prompt = f"""Given the following ESG data for {company_name} ({ticker}), evaluate and score the company using this structured ESG framework.

SCORING SYSTEM:
- Each category (Environmental, Social, Governance) has specific criteria
- Each criterion is evaluated as TRUE or FALSE based on evidence in the data
- TRUE means there is ANY evidence that the company meets this criterion
- FALSE means there is NO evidence that the company meets this criterion
- Points are tallied by counting the number of TRUE values
- Calculate percentage scores as (number of TRUE values / total possible criteria) * 100

ENVIRONMENTAL CRITERIA (10 possible points):
1. Climate Change Management: Evidence of emissions reduction targets or initiatives
2. Carbon Emissions: Data on emissions measurement or reporting
3. Energy Efficiency: Energy management programs or renewable energy use
4. Water Management: Water conservation or efficiency initiatives
5. Waste Management: Waste reduction or recycling programs
6. Resource Use: Material efficiency or sustainable sourcing
7. Biodiversity Protection: Policies or actions to protect biodiversity
8. Environmental Policy: Existence of environmental policy
9. Environmental Management System: Evidence of management systems
10. Environmental Reporting: Evidence of environmental disclosure

SOCIAL CRITERIA (10 possible points):
1. Labor Practices: Evidence of fair labor practices
2. Health and Safety: Worker health and safety programs
3. Human Capital Development: Training or development programs
4. Diversity and Inclusion: Workforce or leadership diversity initiatives
5. Human Rights: Human rights policies
6. Community Relations: Community engagement or investment
7. Product Safety: Product safety measures
8. Data Privacy and Security: Data protection policies
9. Access and Affordability: Accessibility initiatives for products/services
10. Supply Chain Management: Social standards in supply chain

GOVERNANCE CRITERIA (10 possible points):
1. Board Structure: Evidence of independent or diverse board
2. Board Oversight: Board oversight of management
3. Executive Compensation: Transparent executive compensation
4. Shareholder Rights: Protection of shareholder rights
5. Business Ethics: Code of ethics or ethics program
6. Tax Transparency: Tax policy disclosure
7. Bribery and Corruption: Anti-corruption policies
8. Political Involvement: Political contributions or lobbying disclosure
9. Regulatory Compliance: Evidence of regulatory compliance
10. Risk Management: Systems to identify and manage ESG risks

Company Data:
{json.dumps(company_data, indent=2)}

RESPONSE FORMAT:
For each criterion, provide:
1. TRUE or FALSE evaluation
2. Brief justification for the evaluation based on company data
3. Calculate subtotal scores for each category as a percentage (count of TRUE values / 10 * 100)
4. Calculate the total ESG score as weighted average: 40% Environmental, 30% Social, 30% Governance

Then provide the final scores in the following JSON format:
{{
  "environmental_score": float,  # Percentage score (0-100)
  "social_score": float,         # Percentage score (0-100)
  "governance_score": float,     # Percentage score (0-100)
  "total_esg_score": float       # Weighted average of the above scores
}}"""
        return prompt

    def _store_scores(self, ticker: str, scores: Dict[str, float]) -> None:
        """
        Store the computed scores in Supabase
        """
        try:
            logging.info(f"Attempting to store scores for {ticker}")
            logging.debug(f"Scores to store: {scores}")

            # First try to update if record exists
            update_result = self.supabase.table('final_esg_scores').update({
                'environmental_score': scores['environmental_score'],
                'social_score': scores['social_score'],
                'governance_score': scores['governance_score'],
                'total_esg_score': scores['total_esg_score']
            }).eq('ticker', ticker).execute()

            logging.debug(f"Update result: {update_result}")

            # If no record was updated, insert new record
            if not update_result.data:
                logging.info(
                    f"No existing record found for {ticker}, creating new record")
                insert_result = self.supabase.table('final_esg_scores').insert({
                    'ticker': ticker,
                    'environmental_score': scores['environmental_score'],
                    'social_score': scores['social_score'],
                    'governance_score': scores['governance_score'],
                    'total_esg_score': scores['total_esg_score']
                }).execute()
                logging.debug(f"Insert result: {insert_result}")

            logging.info(f"Successfully stored scores for {ticker}")

        except Exception as e:
            logging.error(
                f"Error storing scores for {ticker}: {str(e)}", exc_info=True)
            raise

    def fetch_company_data(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch all relevant data for a company from different tables
        """
        try:
            # Fetch data from each table
            company = self.supabase.table('companies').select(
                '*').eq('ticker', ticker).execute()
            financials = self.supabase.table('financials').select(
                '*').eq('ticker', ticker).execute()
            market_data = self.supabase.table('market_data').select(
                '*').eq('ticker', ticker).execute()
            governance_risk = self.supabase.table('governance_risk').select(
                '*').eq('ticker', ticker).execute()
            esg_scores = self.supabase.table('esg_scores').select(
                '*').eq('ticker', ticker).execute()
            sentiment_data = self.supabase.table('sentiment_data').select(
                '*').eq('ticker', ticker).execute()
            esg_report = self.supabase.table('esg_report_analysis').select(
                '*').eq('ticker', ticker).execute()

            return {
                'company': company.data[0] if company.data else None,
                'financials': financials.data,
                'market_data': market_data.data[0] if market_data.data else None,
                'governance_risk': governance_risk.data[0] if governance_risk.data else None,
                'esg_scores': esg_scores.data[0] if esg_scores.data else None,
                'sentiment_data': sentiment_data.data,
                'esg_report': esg_report.data[0] if esg_report.data else None
            }
        except Exception as e:
            print(f"Error fetching data for {ticker}: {str(e)}")
            return None

    def preprocess_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess and structure the raw data
        """
        if not raw_data:
            return None

        processed_data = {
            "company": {},
            "esg_report_analysis": {},
            "esg_scores": {},
            "financials": [],
            "governance_risk": {},
            "sentiment_data": []
        }

        # Process company data
        if raw_data['company']:
            processed_data['company'] = {
                "ticker": raw_data['company'].get('ticker'),
                "name": raw_data['company'].get('name'),
                "sector": raw_data['company'].get('sector'),
                "industry": raw_data['company'].get('industry'),
                "long_business_summary": raw_data['company'].get('long_business_summary'),
                "market_cap": raw_data['market_data'].get('market_cap') if raw_data['market_data'] else None,
                "employees": raw_data['company'].get('employees')
            }

        # Process ESG report analysis
        if raw_data['esg_report']:
            processed_data['esg_report_analysis'] = {
                "environmental_summary": raw_data['esg_report'].get('environmental_summary'),
                "environmental_breakdown": raw_data['esg_report'].get('environmental_breakdown'),
                "social_summary": raw_data['esg_report'].get('social_summary'),
                "social_breakdown": raw_data['esg_report'].get('social_breakdown'),
                "governance_summary": raw_data['esg_report'].get('governance_summary'),
                "governance_breakdown": raw_data['esg_report'].get('governance_breakdown')
            }

        # Process ESG scores (these will be used as reference/validation)
        if raw_data['esg_scores']:
            processed_data['esg_scores'] = {
                "esg_risk_score": raw_data['esg_scores'].get('esg_risk_score'),
                "esg_risk_severity": raw_data['esg_scores'].get('esg_risk_severity'),
                "environmental_score": raw_data['esg_scores'].get('environmental_score'),
                "social_score": raw_data['esg_scores'].get('social_score'),
                "governance_score": raw_data['esg_scores'].get('governance_score')
            }

        # Process financials (last 2 quarters)
        if raw_data['financials']:
            sorted_financials = sorted(raw_data['financials'],
                                       key=lambda x: x.get('report_date', ''),
                                       reverse=True)[:2]
            processed_data['financials'] = [
                {
                    "report_date": fin.get('report_date'),
                    "revenue": fin.get('revenue'),
                    "net_income": fin.get('net_income'),
                    "ebitda": fin.get('ebitda'),
                    "debt": fin.get('debt'),
                    "gross_profit": fin.get('gross_profit')
                }
                for fin in sorted_financials
            ]

        # Process governance risk
        if raw_data['governance_risk']:
            processed_data['governance_risk'] = {
                "audit_risk": raw_data['governance_risk'].get('audit_risk'),
                "board_risk": raw_data['governance_risk'].get('board_risk'),
                "compensation_risk": raw_data['governance_risk'].get('compensation_risk'),
                "shareholder_rights_risk": raw_data['governance_risk'].get('shareholder_rights_risk'),
                "overall_risk": raw_data['governance_risk'].get('overall_risk')
            }

        # Process sentiment data (remove duplicates based on search_title)
        if raw_data['sentiment_data']:
            seen_titles = set()
            unique_sentiments = []
            for item in raw_data['sentiment_data']:
                title = item.get('search_title')
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    unique_sentiments.append({
                        "search_title": title,
                        "search_summary": item.get('search_summary'),
                        "article_text": item.get('article_text')
                    })
            processed_data['sentiment_data'] = unique_sentiments

        return processed_data

    def compute_scores(self, processed_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Use Gemini to compute ESG scores
        """
        if not processed_data:
            logging.error("No processed data provided for scoring")
            return None

        try:
            # Apply rate limiting
            self._rate_limit()

            # Generate prompt
            prompt = self._generate_prompt(processed_data)
            logging.info(
                f"Generated prompt for {processed_data['company'].get('ticker', 'Unknown')}")
            logging.debug(f"Prompt content: {prompt}")

            # Get response from Gemini
            logging.info("Sending request to Gemini API")
            response = self.model.generate_content(prompt)
            logging.info("Received response from Gemini API")
            logging.debug(f"Raw response: {response.text}")

            # Extract JSON from response
            response_text = response.text
            json_str = response_text[response_text.find(
                '{'):response_text.rfind('}')+1]
            logging.debug(f"Extracted JSON string: {json_str}")

            try:
                scores = json.loads(json_str)
                logging.info(f"Successfully parsed JSON response: {scores}")

                # Replace any None values with default scores
                for key in ['environmental_score', 'social_score', 'governance_score']:
                    if scores.get(key) is None:
                        logging.warning(
                            f"Missing {key}, using default score of 50")
                        scores[key] = 50.0

                # Recompute total_esg_score if missing or invalid
                if scores.get('total_esg_score') is None:
                    scores['total_esg_score'] = round(
                        0.4 * scores['environmental_score'] +
                        0.3 * scores['social_score'] +
                        0.3 * scores['governance_score'],
                        1
                    )
                    logging.info(
                        f"Recomputed total_esg_score: {scores['total_esg_score']}")

            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON response: {e}")
                logging.error(f"Response text: {response_text}")
                return None

            # Validate scores
            if not self._validate_scores(scores):
                logging.error("Score validation failed")
                return None

            return scores

        except Exception as e:
            logging.error(f"Error computing scores: {str(e)}", exc_info=True)
            return None

    def process_company(self, ticker: str) -> None:
        """
        Process a single company's ESG data and compute scores
        """
        try:
            logging.info(f"Starting processing for {ticker}")

            # Fetch raw data
            raw_data = self.fetch_company_data(ticker)
            if not raw_data:
                logging.error(f"No data found for {ticker}")
                return

            # Preprocess data
            processed_data = self.preprocess_data(raw_data)
            if not processed_data:
                logging.error(f"Failed to process data for {ticker}")
                return

            # Log processed data structure
            logging.info(f"Processed data structure for {ticker}:")
            for key in processed_data:
                logging.info(
                    f"- {key}: {'Present' if processed_data[key] else 'Missing'}")

            # Compute scores using Gemini
            scores = self.compute_scores(processed_data)
            if not scores:
                logging.error(f"Failed to compute scores for {ticker}")
                return

            # Store scores in database
            self._store_scores(ticker, scores)
            logging.info(
                f"Successfully processed and stored scores for {ticker}")

        except Exception as e:
            logging.error(
                f"Error processing {ticker}: {str(e)}", exc_info=True)

    def process_companies(self, tickers_file: str) -> None:
        """
        Process multiple companies' ESG data from a file containing tickers
        """
        try:
            # Read tickers from file
            with open(tickers_file, 'r') as f:
                tickers = [line.strip() for line in f if line.strip()]

            logging.info(f"Processing {len(tickers)} companies...")
            for ticker in tickers:
                logging.info(f"\nProcessing {ticker}...")
                self.process_company(ticker)

        except Exception as e:
            logging.error(
                f"Error processing companies: {str(e)}", exc_info=True)


# Example usage
if __name__ == "__main__":
    # Initialize the agent
    agent = ESGScoringAgent()

    # Process all companies from companies.txt
    agent.process_companies('companies.txt')
