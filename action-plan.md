🚀 Action Plan for ESG Score Processing Agent
Objective
Extract relevant data from Supabase tables (Companies, Financials, ESG Reports, Sentiment Data, Market Data, Governance Risk).
Preprocess & Structure the extracted data for the LLM.
Use an LLM prompt to compute Environmental (E), Social (S), Governance (G), and Overall ESG Scores.
Store final scores in final_esg_scores table.

📌 Implementation Steps
Step 1: Extract Data from Supabase
Use SQL queries to fetch relevant data from all tables for the given tickers.

Step 2: Preprocess & Structure Data
Convert JSONB fields into structured dictionaries.
Normalize text-heavy fields (like summaries) using NLP preprocessing.
Aggregate sentiment data (average sentiment score).
Merge financials & governance risk into company profiles.
Step 3: Send Structured Data to LLM
Construct a structured JSON input for the LLM using all data fields.
Use LangChain or OpenAI API for processing.
Step 4: Compute ESG Scores via LLM
Pass structured company data to LLM.
LLM will return weighted E, S, G scores + Final ESG Score.
Step 5: Store in final_esg_scores
Insert computed scores into Supabase.

input example : 
{
  "company": {
    "ticker": "BIR.TO",
    "name": "BIRCHCLIFF ENERGY LTD.",
    "sector": "Energy",
    "industry": "Oil & Gas",
    "long_business_summary": "Birchcliff Energy Ltd. is engaged in the exploration, development, and production of oil and natural gas in Western Canada.",
    "market_cap": 15000000000,
    "employees": 1200
  },
  "esg_report_analysis": {
    "environmental_summary": "Company has strong carbon-neutral policies.",
    "environmental_breakdown": {
      whatever json supabase has
    },
    "social_summary": "Active in local community investments.",
    "social_breakdown": {
      whatever json supabase has
    },
    "governance_summary": "Strong independent board oversight.",
    "governance_breakdown": {
      whatever json supabase has
    }
  },
  "esg_scores": {
    "esg_risk_score": 42.5,
    "esg_risk_severity": "Medium",
    "environmental_score": 74,
    "social_score": 68,
    "governance_score": 80
  },
  "financials": [
    {
      "report_date": "2024-12-31",
      "revenue": 5000000000,
      "net_income": 400000000,
      "ebitda": 900000000,
      "debt": 200000000,
      "gross_profit": 1200000000
    },
    {
      "report_date": "2024-09-30",
      "revenue": 4500000000,
      "net_income": 380000000,
      "ebitda": 870000000,
      "debt": 210000000,
      "gross_profit": 1150000000
    }
  ],
  "governance_risk": {
    "audit_risk": 3,
    "board_risk": 2,
    "compensation_risk": 4,
    "shareholder_rights_risk": 3,
    "overall_risk": 3
  },
  "sentiment_data": [
    {
      "search_title": "Tourmaline-Backed LNG Group Files for Environmental Permits",
      "search_summary": "A group of Canada’s largest natural gas producers is pushing forward with a gas-export project.",
      "article_text": "The project is backed by major energy companies and aims to expand Canada’s LNG capabilities."
    },
    {
      "search_title": "Shaping the Future For Sustainability Disclosure In Canada",
      "search_summary": "New sustainability reporting standards could impact energy companies.",
      "article_text": "Stakeholders have until June 10, 2024, to submit feedback on the proposed reporting framework."
    }
  ]
}


llm response example : 
{
  "ticker": "BIR.TO",
  "environmental_score": 74,
  "social_score": 68,
  "governance_score": 80,
  "total_esg_score": 74
}

Where to Start?
Set up Python data pipeline to fetch data from Supabase.
Format structured JSON input from all tables.
Test LLM prompt with sample data.
Store returned ESG scores into final_esg_scores.
