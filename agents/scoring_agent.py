import json
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from supabase import create_client, Client
import os
from dotenv import load_dotenv


class ESGScoringAgent:
    def __init__(self):
        # Initialize Supabase client
        load_dotenv()
        url = os.getenv("SUPABASE_STRING")
        key = os.getenv("SUPABASE_API_KEY")
        self.supabase: Client = create_client(url, key)

        # Create llm_input directory if it doesn't exist
        os.makedirs('llm_input', exist_ok=True)

        # Default scores when data is missing
        self.default_scores = {
            'environmental': 50,
            'social': 50,
            'governance': 50,
            'total_esg': 50
        }

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

    def compute_scores(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare data for LLM scoring by ensuring all necessary information is present
        """
        if not processed_data:
            return None

        # Add default scores where missing
        if not processed_data.get('esg_scores'):
            processed_data['esg_scores'] = self.default_scores

        return processed_data

    def process_company(self, ticker: str) -> None:
        """
        Process a single company's ESG data and store for LLM input
        """
        try:
            # Fetch raw data
            raw_data = self.fetch_company_data(ticker)
            if not raw_data:
                print(f"No data found for {ticker}")
                return

            # Preprocess data
            processed_data = self.preprocess_data(raw_data)
            if not processed_data:
                print(f"Failed to process data for {ticker}")
                return

            # Prepare for LLM scoring
            llm_ready_data = self.compute_scores(processed_data)
            if not llm_ready_data:
                print(f"Failed to prepare LLM data for {ticker}")
                return

            # Save processed data
            output_path = f'llm_input/{ticker}.json'
            with open(output_path, 'w') as f:
                json.dump(llm_ready_data, f, indent=4)
            print(f"Successfully processed and stored data for {ticker}")

        except Exception as e:
            print(f"Error processing {ticker}: {str(e)}")

    def process_companies(self, tickers_file: str) -> None:
        """
        Process multiple companies' ESG data from a file containing tickers
        """
        try:
            # Read tickers from file
            with open(tickers_file, 'r') as f:
                tickers = [line.strip() for line in f if line.strip()]

            print(f"Processing {len(tickers)} companies...")
            for ticker in tickers:
                print(f"\nProcessing {ticker}...")
                self.process_company(ticker)

        except Exception as e:
            print(f"Error processing companies: {str(e)}")


# Example usage
if __name__ == "__main__":
    # Initialize the agent
    agent = ESGScoringAgent()

    # Process all companies from companies.txt
    agent.process_companies('companies.txt')
