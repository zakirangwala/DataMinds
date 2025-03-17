from pygooglenews import GoogleNews
import json
import time
from bs4 import BeautifulSoup
import html
import newspaper
import json
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os
from datetime import datetime, timedelta
import logging
import psycopg2
from psycopg2.extras import execute_batch
from dateutil import parser
import sys
from pathlib import Path

# Add the root directory to Python path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))
from utils.db import get_companies

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection parameters
DB_URL = os.getenv('SUPABASE_URL')
DB_PASSWORD = os.getenv('SUPABASE_PW')

# Rate limiting settings
REQUESTS_PER_MINUTE = 60  # Adjust this value based on API limits
# Minimum time between requests in seconds
MIN_REQUEST_INTERVAL = 60.0 / REQUESTS_PER_MINUTE
last_request_time = time.time()


def rate_limit():
    """Implement rate limiting"""
    global last_request_time
    current_time = time.time()
    time_since_last_request = current_time - last_request_time

    if time_since_last_request < MIN_REQUEST_INTERVAL:
        sleep_time = MIN_REQUEST_INTERVAL - time_since_last_request
        time.sleep(sleep_time)

    last_request_time = time.time()


# tickers
TICKERS = [
    "BTE.TO",
]


# List of companies
COMPANIES = [
    "BAYTEX ENERGY CORP."
]


def setup_selenium():
    """Set up and return a Selenium WebDriver."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def get_article_content(url, driver):
    """Get article content using newspaper3k with resolved URL."""
    try:
        driver.get(url)
        time.sleep(2)
        final_url = driver.current_url

        article = newspaper.Article(url=final_url, language='en')
        article.download()
        article.parse()

        return {
            "title": str(article.title),
            "text": str(article.text),
            "authors": article.authors,
            "published_date": str(article.publish_date),
            "top_image": str(article.top_image),
            "videos": article.movies,
            "keywords": article.keywords,
            "summary": str(article.summary),
            "original_url": url,
            "resolved_url": final_url
        }
    except Exception as e:
        logger.error(f"Error processing article {url}: {str(e)}")
        return None


def process_company(company_name, driver):
    """Process news for a single company."""
    logger.info(f"Processing news for: {company_name}")
    rate_limit()  # Apply rate limiting

    gn = GoogleNews()
    search_query = f"{company_name} ESG sustainability"
    results = []

    try:
        s = gn.search(search_query)
        count = 0

        for entry in s['entries']:
            if count >= 10:
                break

            rate_limit()  # Apply rate limiting for each article request

            # Clean the summary
            soup = BeautifulSoup(entry["summary"], "html.parser")
            clean_summary = html.unescape(soup.get_text())

            # Get full article content
            article_content = get_article_content(entry['link'], driver)

            if article_content:
                result = {
                    "search_entry": {
                        "title": entry['title'],
                        "published": entry['published'],
                        "link": entry['link'],
                        "summary": clean_summary,
                        "source": entry['source']
                    },
                    "article_content": article_content
                }
                results.append(result)
                count += 1

    except Exception as e:
        logger.error(f"Error processing company {company_name}: {str(e)}")

    return results


def connect_to_db():
    """Establish connection to Supabase PostgreSQL database"""
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = False  # Use transactions
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return None


def insert_news_data(conn, company_name, ticker, results):
    """Insert news data into Supabase"""
    cursor = conn.cursor()

    insert_query = """
        INSERT INTO sentiment_data (
            ticker, company_name, search_title, search_published, search_link,
            search_summary, search_source_href, search_source_title,
            article_title, article_text, article_authors, article_published,
            article_top_image, article_keywords, article_summary,
            article_original_url, article_resolved_url
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """

    try:
        batch_data = []
        for result in results:
            search_entry = result['search_entry']
            article_content = result['article_content']

            # Parse the published date
            try:
                search_published = parser.parse(search_entry['published'])
            except:
                search_published = None

            try:
                article_published = parser.parse(
                    article_content['published_date'])
            except:
                article_published = None

            # Prepare data tuple for insertion
            data_tuple = (
                ticker,                                    # ticker
                company_name,                             # company_name
                search_entry['title'],                    # search_title
                search_published,                         # search_published
                search_entry['link'],                     # search_link
                search_entry['summary'],                  # search_summary
                search_entry['source']['href'],           # search_source_href
                search_entry['source']['title'],          # search_source_title
                article_content['title'],                 # article_title
                article_content['text'],                  # article_text
                article_content['authors'],               # article_authors
                article_published,                        # article_published
                article_content['top_image'],             # article_top_image
                article_content['keywords'],              # article_keywords
                search_entry['summary'],               # article_summary
                # article_original_url
                article_content['original_url'],
                # article_resolved_url
                article_content['resolved_url']
            )
            batch_data.append(data_tuple)

        # Execute batch insert
        execute_batch(cursor, insert_query, batch_data)
        conn.commit()
        logger.info(
            f"Successfully inserted {len(batch_data)} articles for {company_name}")

    except Exception as e:
        conn.rollback()
        logger.error(f"Error inserting data for {company_name}: {str(e)}")
        raise
    finally:
        cursor.close()


def main(companies, tickers):
    # Initialize Selenium once for all companies
    driver = setup_selenium()

    # Connect to database
    conn = connect_to_db()
    if not conn:
        logger.error("Failed to connect to database. Exiting.")
        return

    try:
        # Find the index of OPEN TEXT CORPORATION
        # try:
        #     start_index = companies.index("OPEN TEXT CORPORATION")
        #     logger.info(
        #         f"Starting from OPEN TEXT CORPORATION at index {start_index}")
        # except ValueError:
        #     logger.error(
        #         "OPEN TEXT CORPORATION not found in companies list. Starting from beginning.")
        start_index = 0

        # Process each company starting after OPEN TEXT CORPORATION
        for i in range(start_index, len(companies)):
            company = companies[i]
            ticker = tickers[i]
            logger.info(f"Processing {company} ({ticker})")

            # Process company
            results = process_company(company, driver)

            if results:
                # Upload to Supabase
                try:
                    insert_news_data(conn, company, ticker, results)
                except Exception as e:
                    logger.error(
                        f"Failed to insert data for {company}: {str(e)}")
                    continue

            rate_limit()  # Apply rate limiting between companies

    finally:
        driver.quit()
        if conn:
            conn.close()


if __name__ == "__main__":
    companies = COMPANIES
    tickers = TICKERS
    main(companies, tickers)
