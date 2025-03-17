import requests
import csv
import time
import random
import re
import os
from urllib.parse import quote_plus, urlparse
from bs4 import BeautifulSoup
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection parameters
DB_URL = os.getenv('SUPABASE_URL')
DB_PASSWORD = os.getenv('SUPABASE_PW')

# tickers
TICKERS = [
    "ACX.TO",
    "AKT-A.TO",
    "ATH.TO",
    "BIR.TO",
    "CNE.TO",
    "CJ.TO",
    "FRU.TO",
    "FEC.TO",
    "GFR.TO",
    "IPCO.TO",
    "JOY.TO",
    "KEC.TO",
    "MEG.TO",
    "NVA.TO",
    "BR.TO",
    "SOY.TO",
    "ADW-A.TO",
    "CSW-A.TO",
    "CSW-B.TO",
    "RSI.TO",
    "DOL.TO",
    "EMP-A.TO",
    "WN-PA.TO",
    "BU.TO",
    "DTEA.V",
    "HLF.TO",
    "JWEL.TO",
    "MFI.TO",
    "OTEX.TO",
    "DSG.TO",
    "KXS.TO",
    "SHOP.TO",
    "CSU.TO",
    "LSPD.TO",
    "DCBO.TO",
    "ENGH.TO",
    "HAI.TO",
    "TIXT.TO",
    "DND.TO",
    "ET.TO",
    "BLN.TO",
    "TSAT.TO",
    "ALYA.TO",
    "BTE.TO",
]


# List of companies
COMPANIES = [
    "ACT ENERGY TECHNOLOGIES LTD",
    "AKITA DRILLING LTD., CL.A, NV",
    "ATHABASCA OIL CORP",
    "BIRCHCLIFF ENERGY LTD.",
    "CANACOL ENERGY LTD",
    "CARDINAL ENERGY LTD",
    "FREEHOLD ROYALTIES LTD.",
    "FRONTERA ENERGY CORPORATION",
    "GREENFIRE RESOURCES LTD",
    "INTERNATIONAL PETROLEUM CORPORA",
    "JOURNEY ENERGY INC",
    "KIWETINOHK ENERGY CORP",
    "MEG ENERGY CORP.",
    "NUVISTA ENERGY LTD.",
    "BIG ROCK BREWERY INC.",
    "MOLSON COORS CANADA INC., CL.A",
    "LASSONDE INDUSTRIES INC., CL A",
    "SUNOPTA, INC.",
    "ANDREW PELLER LIMITED, CL.A",
    "CORBY SPIRIT AND WINE LTD CLASS",
    "ROGERS SUGAR INC",
    "DOLLARAMA INC",
    "EMPIRE COMPANY LIMITED",
    "GEORGE WESTON LIMITED PR SERIES",
    "BURCON NUTRASCIENCE CORPORATION",
    "DAVIDSTEA INC",
    "HIGH LINER",
    "JAMIESON WELLNESS INC",
    "MAPLE LEAF FOODS",
    "OPEN TEXT CORPORATION",
    "DESCARTES SYS",
    "KINAXIS INC",
    "SHOPIFY INC",
    "CONSTELLATION SOFTWARE INC.",
    "LIGHTSPEED COMMERCE INC",
    "DOCEBO INC",
    "ENGHOUSE SYSTEMS LIMITED",
    "HAIVISION SYSTEMS INC",
    "TELUS INTERNATIONAL CDA INC",
    "DYE AND DURHAM LIMITED",
    "EVERTZ TECHNOLOGIES LIMITED",
    "BLACKLINE SAFETY CORP",
    "TELESAT CORPORATION",
    "ALITHYA GROUP INC",
    "BAYTEX ENERGY CORP."
]

# User agents to rotate - more diverse selection to appear more like regular browsers
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1"
    ]

# Search engines including DuckDuckGo
search_engines = [
    {
    "name": "DuckDuckGo",
    "url": "https://html.duckduckgo.com/html/?q={query}",
    "link_selector": "a.result__a",
    "delay": (6, 10)  # Longer delay for DuckDuckGo to avoid rate limiting
    },
    {
    "name": "Brave Search",
    "url": "https://search.brave.com/search?q={query}",
    "delay": (4, 7)
    },
    {
    "name": "Mojeek",
    "url": "https://www.mojeek.com/search?q={query}",
    "delay": (3, 6)
    }
]

# Valid sectors (temp)
correct_sectors = ['Consumer Defensive', 'Consumer Cyclical', 'Energy']

def search_2025_reports(sorted_companies):
    """
    Search for 2025 reports for a list of companies.
    Includes DuckDuckGo as one of the search engines.

    Args:
        companies (list): List of company names

    Returns:
        str: Path to the CSV file with results
    """
    results = {}

    for company in companies:
        print(f"\n==== Searching for {company} 2025 reports ====")
        company_pdfs = []

        # Try different search queries
        queries = [
            f"{company} 2025 annual report filetype:pdf",
            f"{company} 2025 financial statements filetype:pdf",
            f"{company} 2025 quarterly report filetype:pdf",
            f"{company} 2025 Q1 filetype:pdf",
            f"{company} 2025 report filetype:pdf"
        ]

        for query_index, query in enumerate(queries):
            if len(company_pdfs) >= 5:  # Stop if we found enough PDFs
                break

            print(f"\nQuery: {query}")

            # Try each search engine
            for engine in search_engines:
                if len(company_pdfs) >= 5:  # Stop if we found enough PDFs
                    break

                # Encode the query
                encoded_query = quote_plus(query)
                search_url = engine["url"].format(query=encoded_query)

                print(f"  Trying {engine['name']}...")

                # Set headers with random user agent
                headers = {
                    "User-Agent": random.choice(user_agents),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q= 0.9,*/*;q= 0.8",
                    "Accept-Language": "en-US,en;q= 0.5",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1"
                }

                try:
                    # Make the request
                    response = requests.get(search_url, headers=headers, timeout=15)

                    # Check status code
                    if response.status_code == 200:
                        # Parse the HTML
                        soup = BeautifulSoup(response.text, 'html.parser')

                        # Find all links (first try the selector if available, then fallback)
                        links = []
                        if "link_selector" in engine:
                            try:
                                links = soup.select(engine["link_selector"])
                            except:
                                pass

                        # If no links found with selector or no selector provided, find all 'a' tags
                        if not links:
                            links = soup.find_all('a', href=True)

                        # Check for PDF links with 2025 in URL or content
                        pdf_links_found = 0

                        for link in links:
                            href = link.get('href', '')

                            # Skip empty links and JavaScript links
                            if not href or href.startswith('javascript:'):
                                continue

                            # Clean URL for DDG (which often redirects)
                            if engine["name"] == "DuckDuckGo" and href.startswith('/'):
                                continue  # Skip internal DuckDuckGo links

                            # Check if it's a PDF with 2025 in the URL or link text
                            is_pdf = href.lower().endswith('.pdf') or '.pdf' in href.lower()
                            link_text = link.get_text(strip=True)
                            has_2025 = '2025' in href or '2025' in link_text

                            if is_pdf and has_2025:
                                # For DuckDuckGo, extract actual URL from redirects
                                if engine["name"] == "DuckDuckGo" and 'uddg=' in href:
                                    try:
                                        from urllib.parse import unquote
                                        href = unquote(re.search(r'uddg=([^&]+)', href).group(1))
                                    except:
                                        pass  # If extraction fails, use original URL

                                try:
                                    # Extract the filename from URL
                                    file_name = os.path.basename(urlparse(href).path)
                                except:
                                    file_name = f"{company}_2025_report_{pdf_links_found+1}.pdf"

                                # Get link text as title
                                title = link_text or "Untitled"

                                company_pdfs.append({
                                    "url": href,
                                    "file_name": file_name,
                                    "title": title,
                                    "source": f"{engine['name']} - Query {query_index + 1}"
                                })

                                print(f"    ✓ Found PDF: {file_name}")
                                pdf_links_found += 1

                                # Limit to 3 PDFs per engine per query
                                if pdf_links_found >= 3:
                                    break

                        if pdf_links_found == 0:
                            print(f"    No 2025 PDFs found on {engine['name']}")
                    elif response.status_code == 202 and engine["name"] == "DuckDuckGo":
                        print(f"    DuckDuckGo rate limited (status 202) - trying different approach")

                        # Try the alternative DuckDuckGo URL
                        try:
                            alt_url = f"https://duckduckgo.com/?q={encoded_query}&ia=web"
                            alt_response = requests.get(alt_url, headers=headers, timeout=15)

                            if alt_response.status_code == 200:
                                soup = BeautifulSoup(alt_response.text, 'html.parser')

                                # Try to find organic results
                                links = soup.find_all('a', {'class': 'result__a'})

                                # Process links (same as above)
                                # Code would be similar to the previous block
                                print(f"    Alternative approach found {len(links)} potential links")
                        except Exception as e:
                            print(f"    Alternative approach failed: {str(e)}")
                    else:
                        print(f"    {engine['name']} returned status code {response.status_code}")

                except Exception as e:
                    print(f"    Error with {engine['name']}: {str(e)}")

                # Add a random delay between searches to avoid rate limiting
                delay = random.uniform(
                    engine["delay"][0] if isinstance(engine["delay"], tuple) else engine["delay"],
                    engine["delay"][1] if isinstance(engine["delay"], tuple) else engine["delay"]+3
                )
                time.sleep(delay)

                # Additional delay for DuckDuckGo to avoid rate limiting
                if engine["name"] == "DuckDuckGo":
                    print(f"    Adding extra delay for DuckDuckGo...")
                    time.sleep(random.uniform(3, 5))

        # Remove duplicates
        unique_pdfs = []
        seen_urls = set()

        for pdf in company_pdfs:
            if pdf["url"] not in seen_urls:
                unique_pdfs.append(pdf)
                seen_urls.add(pdf["url"])

        # Group results by company
        if unique_pdfs:
            results[company] = {
                "file_names": [pdf["file_name"] for pdf in unique_pdfs],
                "titles": [pdf["title"] for pdf in unique_pdfs],
                "urls": [pdf["url"] for pdf in unique_pdfs],
                "sources": [pdf["source"] for pdf in unique_pdfs]
            }

        # Print summary
        if not unique_pdfs:
            print(f"\n❌ No 2025 PDF reports found for {company}")
        else:
            print(f"\n✅ Found {len(unique_pdfs)} 2025 PDF reports for {company}:")
            for pdf in unique_pdfs:
                print(f"  - {pdf['file_name']} ({pdf['source']})")

    # Save results to CSV
    csv_filename = "company_2025_reports.csv"

    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['company', 'file_names', 'titles', 'urls', 'sources']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for company, data in results.items():
            writer.writerow({
                "company": company,
                "file_names": ", ".join(data["file_names"]),
                "titles": ", ".join(data["titles"]),
                "urls": ", ".join(data["urls"]),
                "sources": ", ".join(data["sources"])
            })

    print(f"\nTotal 2025 PDF links found: {sum(len(data['urls']) for data in results.values())}")
    print(f"Results saved to {csv_filename}")

    return csv_filename


def get_companies(supabase_client):

    # gather company names
    response = (
        supabase_client.table('companies')
        .select('name, headquarters, sector')
        .execute()
    )
    data = response.data
    companies = []

    #filter data
    for item in data:
        name = item['name']
        if name and item['sector'] in correct_sectors:
            companies.append(item['name'])

    sorted_companies = sorted(companies)
    return sorted_companies

if __name__ == "__main__":
    supabase_url = 'https://zwfponltzmrnwcgjevik.supabase.co'
    supabase_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp3ZnBvbmx0em1ybndjZ2pldmlrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIwNzA4NjksImV4cCI6MjA1NzY0Njg2OX0.efK6dWbpOLIlGb-4ORnIYmiiyjg11gCnB1gGquC2lH8'
    supabase_client = create_client(supabase_url, supabase_key)

    companies = get_companies(supabase_client)

    search_2025_reports(companies)