import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import sys
from pathlib import Path

# Add the project root directory to Python path
sys.path.append(str(Path(__file__).parent.parent))
from utils.db import get_companies

# Load environment variables
load_dotenv()


def fetch_esg_news(company_name, api_key):
    # Define ESG-related keywords
    esg_keywords = [
        'environment', 'environmental', 'sustainability', 'carbon', 'emissions', 'climate',
        'social', 'diversity', 'inclusion', 'human rights', 'labor', 'community',
        'governance', 'ethics', 'corruption', 'board', 'executive', 'compliance', 'greenhouse',
        'gas', 'emissions', 'energy', 'renewable', 'fossil fuels', 'water', 'waste', 'recycling',
        'wages', 'corporate social responsibility', 'CSR', 'quality', 'safety', 'customer satisfaction',
        'shareholder', 'transparency', 'reporting', 'audit', 'law', 'internal controls', 'ethical', 'corrupt'
    ]

    # Calculate the date 7 days ago
    from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    # Define the NewsAPI endpoint
    url = 'https://newsapi.org/v2/everything'

    # Define the query parameters
    params = {
        'q': f'{company_name} ESG',
        'from': from_date,
        'sortBy': 'publishedAt',
        'language': 'en',
        'apiKey': api_key
    }

    # Make the request to NewsAPI
    response = requests.get(url, params=params)

    # Check if the request was successful
    if response.status_code != 200:
        print(f"Failed to fetch news: {response.status_code}")
        return []

    # Parse the JSON response
    data = response.json()

    # Filter articles based on ESG keywords
    esg_news = []
    for article in data.get('articles', []):
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        if any(keyword in title or keyword in description for keyword in esg_keywords):
            esg_news.append({
                'title': article.get('title'),
                'description': article.get('description'),
                'publishedAt': article.get('publishedAt'),
                'url': article.get('url'),
                'source': article.get('source', {}).get('name')
            })

    return esg_news


if __name__ == "__main__":
    # Get API key from environment variables
    api_key = os.getenv('NEWS_API_KEY')
    if not api_key:
        print("Error: News API key not found in environment variables")
        exit(1)

    # Get companies using direct SQL query
    # companies = get_companies()
    companies = [
        "ACT ENERGY TECHNOLOGIES LTD",
        "AKITA DRILLING LTD., CL.A, NV",
        "ATHABASCA OIL CORP",
        "BIRCHCLIFF ENERGY LTD.",
        "CANACOL ENERGY LTD",
        "CARDINAL ENERGY LTD",
        "FREEHOLD ROYALTIES LTD.",
        "FRONTERA ENERGY CORPORATION",
        "GREENFIRE RESOURCES LTD",
        "INTERNATIONAL PETROLEUM CORPORA"]

    for company in companies:
        esg_news = fetch_esg_news(company, api_key)

        print(
            f"Found {len(esg_news)} ESG-related news articles for {company}:\n")
        for news in esg_news:
            print(f"Title: {news['title']}")
            print(f"Description: {news['description']}")
            print(f"URL: {news['url']}")
            print("-" * 80)
