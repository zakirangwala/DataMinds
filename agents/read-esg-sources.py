import pandas as pd
import json
import re
import requests
import fitz
import concurrent.futures
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import google.generativeai as genai
import time
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
from datetime import datetime
from typing import List, Dict
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        # logging.FileHandler(
        #     f'esg_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

# Suppress verbose logging from libraries
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('PyPDF2').setLevel(logging.WARNING)
logging.getLogger('fitz').setLevel(logging.WARNING)

# Load environment variables
load_dotenv()
gemini_api_key = os.getenv('GEMINI_API_KEY')
supabase_url = os.getenv('SUPABASE_STRING')
supabase_key = os.getenv('SUPABASE_API_KEY')

if not all([gemini_api_key, supabase_url, supabase_key]):
    logging.error("Missing required environment variables")
    raise ValueError("Missing required environment variables")

# Initialize Supabase client
try:
    supabase: Client = create_client(supabase_url, supabase_key)
    logging.info(
        f"Successfully initialized Supabase client with URL: {supabase_url[:30]}...")
except Exception as e:
    logging.error(f"Failed to initialize Supabase client: {str(e)}")
    raise

# ------------------------------------------------------------
# 2) Fetch company + URLs from 'resources'
# ------------------------------------------------------------
try:
    logging.info("Fetching resources from Supabase...")
    resources_response = supabase.table('resources').select(
        'company, ticker, urls').execute()
    logging.info(
        f"Raw Response from resources table: {json.dumps(resources_response.model_dump(), indent=2)}")

    if not resources_response.data:
        raise Exception("No data returned from resources table")

    resources_df = pd.DataFrame(resources_response.data)
    logging.info(
        f"Retrieved {len(resources_df)} records from 'resources' table")
    logging.info(f"Sample data:\n{resources_df.head().to_string()}")
except Exception as e:
    logging.error(f"Failed to fetch resources: {str(e)}", exc_info=True)
    raise

# Display the DataFrame for debugging
pd.set_option('display.max_colwidth', None)
pd.options.display.colheader_justify = 'left'
print(resources_df.to_string(index=False, justify='left'))

# ------------------------------------------------------------
# 3) Configure Gemini API
# ------------------------------------------------------------
genai.configure(api_key=gemini_api_key)

# Add rate limiting decorator


def rate_limit():
    """Rate limit decorator to ensure we don't exceed Gemini API limits"""
    last_call = [0.0]  # Using list to maintain state in closure
    min_interval = 4.0  # Minimum 2 seconds between calls (15 RPM)

    def decorator(func):
        def wrapper(*args, **kwargs):
            current_time = time.time()
            elapsed = current_time - last_call[0]
            if elapsed < min_interval:
                sleep_time = min_interval - elapsed
                print(f"⏳ Rate limiting: Waiting {sleep_time:.1f} seconds...")
                time.sleep(sleep_time)
            last_call[0] = time.time()
            return func(*args, **kwargs)
        return wrapper
    return decorator


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
@rate_limit()
def gemini_chat_completion(prompt, max_tokens, temperature):
    model = genai.GenerativeModel('gemini-2.0-flash')

    # Configure generation parameters
    generation_config = {
        "max_output_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 1,
        "top_k": 32
    }

    # Configure safety settings to be more permissive for business analysis
    safety_settings = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_NONE",
        },
    ]

    try:
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings,
            stream=False
        )

        # Log the raw response for debugging
        logging.debug(f"Raw Gemini response: {response.text}")

        # Check if response is empty or malformed
        if not response.text or not response.text.strip():
            raise ValueError("Empty response from Gemini API")

        # Try to extract JSON from the response
        # Look for JSON block in markdown format
        json_match = re.search(r"```json\s*(.*?)\s*```",
                               response.text, re.DOTALL)
        if json_match:
            try:
                return {"choices": [{"message": {"content": json.loads(json_match.group(1))}}]}
            except json.JSONDecodeError:
                logging.error(
                    f"Failed to parse JSON from markdown block: {json_match.group(1)}")

        # If no JSON block found or parsing failed, try to parse the entire response
        try:
            json_data = json.loads(response.text)
            return {"choices": [{"message": {"content": json_data}}]}
        except json.JSONDecodeError:
            logging.error(f"Failed to parse response as JSON: {response.text}")
            # Return the raw text as fallback
            return {"choices": [{"message": {"content": response.text}}]}

    except Exception as e:
        logging.error(f"Gemini API Error: {str(e)}")
        raise


print("Using Gemini API directly with model: gemini-2.0-flash-lite-001")

# ------------------------------------------------------------
# 4) Helper functions for chunking & aggregation
# ------------------------------------------------------------
CHUNK_SIZE = 100000


def chunk_text(text, chunk_size=CHUNK_SIZE):
    """Yield successive chunks of text."""
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]


def aggregate_raw_metrics(results):
    """Aggregate ESG metrics from all chunks."""
    pillars = {
        "Environmental": ["Carbon Emissions", "Energy Use", "Water Usage", "Waste Management", "Climate Risk Disclosures"],
        "Social": ["Labour Practices", "Diversity & Inclusion", "Community Impact", "Product/Service Responsibility", "Human Rights"],
        "Governance": ["Board Composition", "Executive Compensation", "Transparency", "Regulatory Compliance", "Ethical Practices", "Governance Risk"]
    }
    aggregated = {pillar: {cat: [] for cat in cats}
                  for pillar, cats in pillars.items()}

    for res in results:
        if isinstance(res, dict) and "ESG Metrics" in res:
            for pillar, cats in pillars.items():
                for cat in cats:
                    data = res["ESG Metrics"].get(
                        pillar, {}).get(cat, "").strip()
                    if data and data.lower() not in ["not mentioned", ""]:
                        # Split by common list delimiters
                        points = re.split(r'[\n•-]+', data)
                        for pt in points:
                            pt = pt.strip()
                            if pt and pt.lower() not in ["not mentioned", ""] and pt not in aggregated[pillar][cat]:
                                aggregated[pillar][cat].append(pt)
    return aggregated

# ------------------------------------------------------------
# 5) Define the Agent classes
# ------------------------------------------------------------


class PDFExtractorAgent:
    """
    🚀 PDF Extractor Agent
    - Downloads PDFs from URLs.
    - Extracts text using PyMuPDF.
    - Returns a list of raw texts (one per PDF).
    """

    def download_pdf(self, url, filename):
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(filename, "wb") as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                logging.info(f"Downloaded PDF from {url}")
                return filename
            else:
                logging.error(
                    f"Failed to download PDF from {url}: {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Error downloading PDF from {url}: {str(e)}")
            return None

    def extract_text_from_pdf(self, pdf_path):
        try:
            doc = fitz.open(pdf_path)
            text = "\n".join(page.get_text("text") for page in doc)
            doc.close()
            text_length = len(text)
            logging.info(f"Extracted {text_length} characters from {pdf_path}")
            return text
        except Exception as e:
            logging.error(f"Error extracting text from {pdf_path}: {str(e)}")
            return ""

    def cleanup_pdf(self, pdf_path):
        """Delete a temporary PDF file after processing."""
        try:
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)
                logging.debug(f"Cleaned up {pdf_path}")
        except Exception as e:
            logging.warning(f"Could not delete {pdf_path}: {str(e)}")

    def process(self, urls):
        """Process a list of URLs and return combined extracted text."""
        extracted_texts = []
        os.makedirs("temp", exist_ok=True)

        for idx, url in enumerate(urls):
            filename = f"temp/document_{idx+1}.pdf"
            pdf_path = self.download_pdf(url, filename)
            if pdf_path:
                text = self.extract_text_from_pdf(pdf_path)
                if text:
                    extracted_texts.append(text)
                self.cleanup_pdf(pdf_path)

        try:
            os.rmdir("temp")
            logging.debug("Cleaned up temp directory")
        except:
            pass

        combined_text = "\n\n".join(extracted_texts) if extracted_texts else ""
        if combined_text:
            logging.info(
                f"Successfully extracted {len(combined_text)} total characters from {len(urls)} PDFs")
        else:
            logging.warning("No text was extracted from PDFs")
        return combined_text


class ESGAnalystAgent:
    """
    🚀 ESG Analyst Agent
    - Splits the combined text into chunks.
    - Processes each chunk in parallel via DeepSeek API.
    - Returns a list of ESG metrics (one per chunk).
    """
    json_format = '''```json
{
  "ESG Metrics": {
    "Environmental": {
      "Carbon Emissions": "...",
      "Energy Use": "...",
      "Water Usage": "...",
      "Waste Management": "...",
      "Climate Risk Disclosures": "..."
    },
    "Social": {
      "Labour Practices": "...",
      "Diversity & Inclusion": "...",
      "Community Impact": "...",
      "Product/Service Responsibility": "...",
      "Human Rights": "..."
    },
    "Governance": {
      "Board Composition": "...",
      "Executive Compensation": "...",
      "Transparency": "...",
      "Regulatory Compliance": "...",
      "Ethical Practices": "...",
      "Governance Risk": "..."
    }
  }
}
```'''

    def extract_esg_metrics_from_chunk(self, text_chunk):
        prompt = f"""
You are an expert ESG analyst with exceptional ability to extract key ESG performance metrics from corporate reports. Analyze the following text and extract all available explicit data—including both quantitative figures (numbers, percentages, targets) and key qualitative statements—that indicate performance for ESG scoring.

For each category below, if quantitative data is available, include it. Otherwise, include qualitative details. Do not simply return "Not mentioned". Always provide some detail.

**Environmental:**
- Carbon Emissions: Data or qualitative insights.
- Energy Use: Renewable vs. fossil details or performance descriptions.
- Water Usage: Consumption, efficiency measures or insights.
- Waste Management: Recycling or waste reduction details.
- Climate Risk Disclosures: Numerical data or descriptive risk disclosures.

**Social:**
- Labour Practices: Safety, turnover, wages, or workplace practices.
- Diversity & Inclusion: Workforce or board diversity data.
- Community Impact: Investment figures or qualitative assessments.
- Product/Service Responsibility: Quality or safety metrics.
- Human Rights: Numerical or qualitative compliance details.

**Governance:**
- Board Composition: Data on independence, diversity or expertise.
- Executive Compensation: Metrics linking pay to performance.
- Transparency: Disclosure quality or reporting standards.
- Regulatory Compliance: Data on compliance measures.
- Ethical Practices: Anti-corruption or whistleblower metrics.
- Governance Risk: Indicators of risk or qualitative assessments.

Return your answer in JSON format exactly as follows:
{self.json_format}

**Text to analyze:**
{text_chunk}
"""
        try:
            response = gemini_chat_completion(
                prompt, max_tokens=2000, temperature=0.2)
            result_text = response["choices"][0]["message"]["content"]
            json_match = re.search(
                r"```json\s*(\{.*?\})\s*```", result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(1)
            return json.loads(result_text)
        except json.JSONDecodeError:
            print("⚠️ JSON parsing failed. Returning raw response.")
            return result_text
        except Exception as e:
            print("❌ Gemini API Error:", e)
            return None

    def process(self, combined_text):
        esg_results = []
        chunks = list(chunk_text(combined_text))
        print(f"📌 Total chunks to process: {len(chunks)}")

        # Process chunks sequentially to avoid rate limits
        for idx, chunk in enumerate(chunks):
            try:
                result = self.extract_esg_metrics_from_chunk(chunk)
                esg_results.append(result)
                if isinstance(result, dict):
                    print(
                        f"✅ ESG Metrics for chunk {idx+1}:\n{json.dumps(result, indent=2)}")
                else:
                    print(f"✅ ESG Metrics for chunk {idx+1} (raw):\n{result}")
            except Exception as e:
                print(f"❌ Error processing chunk {idx+1}: {str(e)}")
                esg_results.append(None)

        return esg_results


class ReportSummarizerAgent:
    """
    🚀 Report Summarizer Agent
    - Aggregates ESG metrics for each pillar.
    - Generates a detailed summary analysis per ESG pillar.
    - Processes each pillar in parallel.
    """

    def generate_pillar_summary(self, pillar_name, pillar_data):
        summary_prompt_content = f"For the {pillar_name} pillar, use the following aggregated metrics as context:\n"
        for category, metrics in pillar_data.items():
            if metrics:
                summary_prompt_content += f"- {category}: {'; '.join(metrics)}\n"
            else:
                summary_prompt_content += f"- {category}: [No data available]\n"

        prompt = f"""
You are an expert ESG analyst. Based solely on the aggregated ESG metrics below for the {pillar_name} pillar, generate a thorough summary analysis in at least 5 to 7 detailed sentences. Your analysis should explain what the data shows, why it matters, discuss potential implications for the company's ESG performance, and highlight any data gaps.

Aggregated Metrics:
{summary_prompt_content}

Provide only the summary text.
"""
        try:
            response = gemini_chat_completion(
                prompt, max_tokens=1200, temperature=0.2)
            return response["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print("❌ Error generating pillar summary:", e)
            return "Summary not available."

    def process(self, aggregated_metrics):
        summaries = {}
        for pillar, data in aggregated_metrics.items():
            try:
                summaries[pillar] = self.generate_pillar_summary(pillar, data)
                print(f"✅ Summary generated for {pillar} pillar.")
            except Exception as e:
                print(f"❌ Error generating summary for {pillar}: {str(e)}")
                summaries[pillar] = "Summary not available."
        return summaries


class KeyMetricsBreakdownAgent:
    """
    🚀 Key Metrics Breakdown Agent
    - Generates a structured breakdown for each ESG metric.
    - Suggests scoring benchmarks for future ESG evaluations.
    - Returns the breakdowns in JSON format.
    """

    def generate_key_metric_breakdown(self, pillar_name, pillar_data):
        breakdown_prompt_content = f"For the {pillar_name} pillar, analyze the following key metrics and provide a detailed breakdown for each metric. For each category, describe the available quantitative and qualitative data, discuss its implications, and suggest how it might be used to score the pillar in future analyses. Return your output in JSON format where each key is the category name and the value is a string with the detailed breakdown.\n"
        for category, metrics in pillar_data.items():
            if metrics:
                breakdown_prompt_content += f'- {category}: {"; ".join(metrics)}\n'
            else:
                breakdown_prompt_content += f'- {category}: [No data available]\n'

        prompt = f"""
You are an expert ESG analyst. Based solely on the aggregated ESG metrics below for the {pillar_name} pillar, provide a detailed breakdown analysis for each key metric. Explain what the data indicates, why it is important for assessing ESG performance, and how it could be used to determine a quantitative score for the pillar. Return your response strictly in JSON format with the following structure:

{{
  "Key Metrics Breakdown": {{
    "Category1": "Detailed analysis",
    "Category2": "Detailed analysis",
    ...
  }}
}}

Aggregated Metrics:
{breakdown_prompt_content}

Provide only the JSON output.
"""
        try:
            response = gemini_chat_completion(
                prompt, max_tokens=1500, temperature=0.2)
            result_text = response["choices"][0]["message"]["content"]
            json_match = re.search(
                r"```json\s*(\{.*?\})\s*```", result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(1)
            return json.loads(result_text)
        except json.JSONDecodeError:
            print("⚠️ JSON parsing failed in breakdown. Returning raw response.")
            return result_text
        except Exception as e:
            print("❌ Error generating key metrics breakdown:", e)
            return None

    def process(self, aggregated_metrics):
        breakdowns = {}
        for pillar, data in aggregated_metrics.items():
            try:
                breakdowns[pillar] = self.generate_key_metric_breakdown(
                    pillar, data)
                print(
                    f"✅ Key metrics breakdown generated for {pillar} pillar.")
            except Exception as e:
                print(f"❌ Error generating breakdown for {pillar}: {str(e)}")
                breakdowns[pillar] = None
        return breakdowns

# ------------------------------------------------------------
# 6) ESG pipeline function
# ------------------------------------------------------------


def generate_analysis_prompt(text: str, company: str) -> str:
    """Generate the prompt for ESG analysis."""

    # Determine industry context based on company name
    industry_context = ""
    if "AIR" in company.upper() or "AIRLINES" in company.upper() or "AIRWAYS" in company.upper():
        industry_context = """
Industry Context: Aviation/Airlines
- Core business: Passenger and cargo air transportation
- Key ESG considerations:
  * Environmental: Aircraft emissions, fuel efficiency, noise pollution
  * Social: Passenger safety, employee training, customer service
  * Governance: Safety compliance, route management, fleet maintenance
- Regulatory framework: Aviation safety regulations, emissions standards
- Industry peers: Major international and regional airlines
"""
    # Add more industry contexts as needed

    return f"""You are an expert ESG analyst providing a comprehensive assessment of {company}. 

VALIDATION REQUIREMENTS:
1. FIRST, verify that the text being analyzed corresponds to {company}:
   - Check for company name mentions, trademarks, and industry-specific terms
   - If the text appears to be about a different company, focus ONLY on content that is definitely about {company}
   - If no relevant content is found for {company}, respond with:
     {{"error": "No relevant content found for {company}"}}

{industry_context}

COMPANY CONTEXT:
Company Name: {company}
Analysis Rules:
1. EVERY statement must explicitly reference {company} - never make generic statements
2. Make specific, confident assertions about {company}'s actual practices
3. Base analysis on:
   - Industry standards for {company}'s sector
   - {company}'s size and operational scope
   - Regulatory requirements in {company}'s markets
   - Common practices among {company}'s direct competitors
4. NEVER use phrases like:
   - "The text/document shows/indicates"
   - "There is no information about"
   - "It is not clear whether"
   - "The company may have"
5. Instead, make definitive statements like:
   - "{company} implements..."
   - "{company} maintains..."
   - "{company} operates..."
   - "{company} achieves..."
6. When making inferences:
   - Base them on industry knowledge and regulatory requirements
   - Be specific about {company}'s practices
   - Connect statements to {company}'s actual operations
   - Maintain confident, authoritative tone
7. Industry-Specific Focus:
   - Analyze practices specific to {company}'s industry
   - Compare against industry benchmarks
   - Reference relevant regulatory requirements
   - Consider market-specific challenges and opportunities

ANALYSIS REQUIREMENTS:
Provide a detailed ESG assessment covering:

Environmental Performance:
- Carbon footprint and emissions management (industry-specific metrics)
- Energy efficiency initiatives (relevant to operations)
- Resource consumption and conservation (sector-appropriate measures)
- Waste reduction and recycling programs (industry context)
- Climate risk management and adaptation (market-specific)

Social Impact:
- Workforce management and safety (industry standards)
- Diversity and inclusion programs (company-wide)
- Community engagement initiatives (local impact)
- Customer service standards (industry-specific)
- Human rights practices (supply chain focus)

Governance Structure:
- Board composition and oversight (industry expertise)
- Executive compensation framework (market alignment)
- Risk management systems (sector-specific)
- Compliance programs (regulatory focus)
- Corporate ethics initiatives (industry context)

RESPONSE FORMAT:
You MUST respond with ONLY a JSON object matching this exact structure:
{{
    "environmental_summary": "A detailed paragraph specifically about {company}'s environmental performance...",
    "environmental_breakdown": {{
        "Carbon Emissions": "Specific analysis of {company}'s emissions management...",
        "Energy Use": "Details of {company}'s energy efficiency programs...",
        "Water Usage": "Analysis of {company}'s water management practices...",
        "Waste Management": "Description of {company}'s waste reduction initiatives...",
        "Climate Risk Disclosures": "Overview of {company}'s climate risk strategies..."
    }},
    "social_summary": "A detailed paragraph about {company}'s social impact and initiatives...",
    "social_breakdown": {{
        "Labour Practices": "Analysis of {company}'s workforce programs...",
        "Diversity & Inclusion": "Details of {company}'s diversity initiatives...",
        "Community Impact": "Description of {company}'s community engagement...",
        "Product/Service Responsibility": "Analysis of {company}'s service standards...",
        "Human Rights": "Overview of {company}'s human rights practices..."
    }},
    "governance_summary": "A detailed paragraph about {company}'s governance structure...",
    "governance_breakdown": {{
        "Board Composition": "Analysis of {company}'s board structure...",
        "Executive Compensation": "Details of {company}'s compensation framework...",
        "Transparency": "Overview of {company}'s disclosure practices...",
        "Regulatory Compliance": "Analysis of {company}'s compliance programs...",
        "Ethical Practices": "Description of {company}'s ethics initiatives...",
        "Governance Risk": "Analysis of {company}'s risk management..."
    }}
}}

Text to analyze:
{text[:100000]}"""


async def analyze_with_gemini(text: str, company: str) -> Dict:
    """Analyze text using Gemini API and return structured ESG analysis."""
    logging.info(f"Starting Gemini analysis for {company}")

    try:
        response = gemini_chat_completion(
            prompt=generate_analysis_prompt(text, company),
            max_tokens=2000,
            temperature=0.2
        )

        content = response["choices"][0]["message"]["content"]

        # If content is already a dict, validate its structure
        if isinstance(content, dict):
            parsed_content = content
        else:
            # Try to parse as JSON if it's a string
            try:
                parsed_content = json.loads(content)
            except json.JSONDecodeError:
                logging.error(
                    f"Failed to parse Gemini response for {company}: {content}")
                raise ValueError(
                    f"Invalid JSON format from Gemini API for {company}")

        # Validate the structure
        required_fields = {
            "environmental_summary": str,
            "environmental_breakdown": {
                "Carbon Emissions": str,
                "Energy Use": str,
                "Water Usage": str,
                "Waste Management": str,
                "Climate Risk Disclosures": str
            },
            "social_summary": str,
            "social_breakdown": {
                "Labour Practices": str,
                "Diversity & Inclusion": str,
                "Community Impact": str,
                "Product/Service Responsibility": str,
                "Human Rights": str
            },
            "governance_summary": str,
            "governance_breakdown": {
                "Board Composition": str,
                "Executive Compensation": str,
                "Transparency": str,
                "Regulatory Compliance": str,
                "Ethical Practices": str,
                "Governance Risk": str
            }
        }

        # Check if all required fields are present and have correct types
        def validate_structure(data: Dict, template: Dict, path: str = "") -> None:
            for key, expected_type in template.items():
                if key not in data:
                    raise ValueError(f"Missing required field: {path + key}")
                if isinstance(expected_type, dict):
                    if not isinstance(data[key], dict):
                        raise ValueError(
                            f"Field {path + key} should be an object")
                    validate_structure(
                        data[key], expected_type, f"{path + key}.")
                elif not isinstance(data[key], expected_type):
                    raise ValueError(
                        f"Field {path + key} should be of type {expected_type.__name__}")

        validate_structure(parsed_content, required_fields)
        return parsed_content

    except Exception as e:
        logging.error(
            f"Failed to analyze text with Gemini for {company}: {str(e)}")
        raise


async def run_esg_pipeline(resources: List[Dict]) -> Dict:
    """Run the ESG analysis pipeline for the given resources."""
    logging.info(f"Starting ESG pipeline for {len(resources)} resources")

    for resource in resources:
        ticker = resource['ticker']
        company = resource['company']

        try:
            # Check if record exists
            existing_record = supabase.table('esg_report_analysis').select(
                "*").eq('ticker', ticker).execute()

            if existing_record.data:
                logging.info(f"Skipping {ticker} - record already exists")
                continue

            logging.info(f"Processing {ticker} - {company}")

            # Extract text from PDFs
            pdf_extractor = PDFExtractorAgent()
            combined_text = pdf_extractor.process(resource['urls'])

            if not combined_text:
                logging.warning(f"Skipping {ticker} - no text extracted")
                continue

            # Analyze with Gemini
            analysis = await analyze_with_gemini(combined_text, company)

            # Prepare results
            results = {
                'ticker': ticker,
                'company': company,
                'environmental_summary': analysis['environmental_summary'],
                'environmental_breakdown': analysis['environmental_breakdown'],
                'social_summary': analysis['social_summary'],
                'social_breakdown': analysis['social_breakdown'],
                'governance_summary': analysis['governance_summary'],
                'governance_breakdown': analysis['governance_breakdown'],
                'created_at': datetime.utcnow().isoformat()
            }

            # Upsert to Supabase
            try:
                result = supabase.table('esg_report_analysis').upsert(
                    results,
                    on_conflict='ticker'
                ).execute()

                if result.data:
                    logging.info(
                        f"Successfully processed and stored analysis for {ticker}")
                else:
                    logging.warning(
                        f"Upsert completed but no data returned for {ticker}")

            except Exception as e:
                logging.error(
                    f"Failed to store analysis for {ticker}: {str(e)}")
                continue

        except Exception as e:
            logging.error(f"Failed to process {ticker}: {str(e)}")
            continue

    logging.info("ESG pipeline completed")


async def main():
    """Main entry point for the ESG analysis pipeline."""
    logging.info("Starting ESG analysis pipeline")

    for idx, row in resources_df.iterrows():
        company_name = row["company"]
        ticker = row["ticker"]
        pdf_urls = row["urls"]

        if not pdf_urls or len(pdf_urls) == 0:
            logging.warning(f"Skipping {ticker} - no URLs found")
            continue

        try:
            resource = {
                'ticker': ticker,
                'company': company_name,
                'urls': pdf_urls
            }
            await run_esg_pipeline([resource])
        except Exception as e:
            logging.error(f"Failed to process {ticker}: {str(e)}")
            continue

    logging.info("Pipeline completed")

# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())
