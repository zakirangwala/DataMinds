# !pip install supabase pandas requests pymupdf langchain

import pandas as pd
import json
import re
import requests
import fitz  # PyMuPDF
import concurrent.futures
from supabase import create_client, Client

# ------------------------------------------------------------
# 1) Initialize Supabase client
# ------------------------------------------------------------
url = "https://zwfponltzmrnwcgjevik.supabase.co/"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp3ZnBvbmx0em1ybndjZ2pldmlrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIwNzA4NjksImV4cCI6MjA1NzY0Njg2OX0.efK6dWbpOLIlGb-4ORnIYmiiyjg11gCnB1gGquC2lH8"
supabase: Client = create_client(url, key)

# ------------------------------------------------------------
# 2) Fetch company + URLs from 'resources'
# ------------------------------------------------------------
resources_response = supabase.table('resources').select('company, urls').execute()
print("Raw Response:", resources_response)

if resources_response.data:
    resources_df = pd.DataFrame(resources_response.data)
    print(f"Retrieved {len(resources_df)} records from 'resources'.")
else:
    raise Exception("Failed to retrieve resources:", resources_response)

# Display the DataFrame for debugging
pd.set_option('display.max_colwidth', None)
pd.options.display.colheader_justify = 'left'
print(resources_df.to_string(index=False, justify='left'))

# ------------------------------------------------------------
# 3) Configure DeepSeek API (OpenRouter)
# ------------------------------------------------------------
deepseek_api_key = "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"
deepseek_api_base = "https://openrouter.ai/api/v1"

def deepseek_chat_completion(prompt, max_tokens, temperature):
    url = f"{deepseek_api_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {deepseek_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek/deepseek-r1-distill-llama-70b:free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

print("Using DeepSeek API with base:", deepseek_api_base)

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
    aggregated = {pillar: {cat: [] for cat in cats} for pillar, cats in pillars.items()}

    for res in results:
        if isinstance(res, dict) and "ESG Metrics" in res:
            for pillar, cats in pillars.items():
                for cat in cats:
                    data = res["ESG Metrics"].get(pillar, {}).get(cat, "").strip()
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
                return filename
            else:
                print("❌ Error downloading PDF:", response.status_code)
                return None
        except Exception as e:
            print("❌ Download error:", e)
            return None

    def extract_text_from_pdf(self, pdf_path):
        try:
            doc = fitz.open(pdf_path)
            return "\n".join(page.get_text("text") for page in doc)
        except Exception as e:
            print("❌ Text extraction error:", e)
            return ""

    def process(self, urls):
        extracted_texts = []
        for idx, url in enumerate(urls):
            filename = f"document_{idx+1}.pdf"
            pdf_path = self.download_pdf(url, filename)
            if pdf_path:
                print(f"✅ PDF Downloaded: {pdf_path}")
                text = self.extract_text_from_pdf(pdf_path)
                print(f"✅ Extracted text preview from {pdf_path} (first 300 characters):\n{text[:300]}")
                extracted_texts.append(text)
        return extracted_texts

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
            response = deepseek_chat_completion(prompt, max_tokens=2000, temperature=0.2)
            result_text = response["choices"][0]["message"]["content"]
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(1)
            return json.loads(result_text)
        except json.JSONDecodeError:
            print("⚠️ JSON parsing failed. Returning raw response.")
            return result_text
        except Exception as e:
            print("❌ DeepSeek API Error:", e)
            return None

    def process(self, combined_text):
        esg_results = []
        chunks = list(chunk_text(combined_text))
        print(f"📌 Total chunks to process: {len(chunks)}")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.extract_esg_metrics_from_chunk, chunk) for chunk in chunks]
            for idx, future in enumerate(concurrent.futures.as_completed(futures)):
                result = future.result()
                esg_results.append(result)
                if isinstance(result, dict):
                    print(f"✅ ESG Metrics for chunk {idx+1}:\n{json.dumps(result, indent=2)}")
                else:
                    print(f"✅ ESG Metrics for chunk {idx+1} (raw):\n{result}")
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
            response = deepseek_chat_completion(prompt, max_tokens=1200, temperature=0.2)
            return response["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print("❌ Error generating pillar summary:", e)
            return "Summary not available."

    def process(self, aggregated_metrics):
        summaries = {}
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_pillar = {
                executor.submit(self.generate_pillar_summary, pillar, data): pillar
                for pillar, data in aggregated_metrics.items()
            }
            for future in concurrent.futures.as_completed(future_to_pillar):
                pillar = future_to_pillar[future]
                summaries[pillar] = future.result()
                print(f"✅ Summary generated for {pillar} pillar.")
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
            response = deepseek_chat_completion(prompt, max_tokens=1500, temperature=0.2)
            result_text = response["choices"][0]["message"]["content"]
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", result_text, re.DOTALL)
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
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_pillar = {
                executor.submit(self.generate_key_metric_breakdown, pillar, data): pillar
                for pillar, data in aggregated_metrics.items()
            }
            for future in concurrent.futures.as_completed(future_to_pillar):
                pillar = future_to_pillar[future]
                breakdowns[pillar] = future.result()
                print(f"✅ Key metrics breakdown generated for {pillar} pillar.")
        return breakdowns

# ------------------------------------------------------------
# 6) ESG pipeline function
# ------------------------------------------------------------
def run_esg_pipeline(pdf_urls):
    """
    Runs the full ESG pipeline on a list of PDF URLs and returns
    a dict with the final summaries & breakdowns.
    """
    # 1) PDF Extraction
    pdf_agent = PDFExtractorAgent()
    pdf_texts = pdf_agent.process(pdf_urls)
    if not pdf_texts:
        return {
            "environmental_summary": "",
            "environmental_breakdown": {},
            "social_summary": "",
            "social_breakdown": {},
            "governance_summary": "",
            "governance_breakdown": {}
        }

    combined_text = "\n".join(pdf_texts)

    # 2) ESG Analysis
    esg_agent = ESGAnalystAgent()
    esg_results = esg_agent.process(combined_text)

    # 3) Aggregate raw metrics
    aggregated_metrics = aggregate_raw_metrics(esg_results)

    # 4) Summaries
    summarizer_agent = ReportSummarizerAgent()
    summaries = summarizer_agent.process(aggregated_metrics)

    # 5) Key metrics breakdown
    breakdown_agent = KeyMetricsBreakdownAgent()
    breakdowns = breakdown_agent.process(aggregated_metrics)

    return {
        "environmental_summary": summaries.get("Environmental", ""),
        "environmental_breakdown": breakdowns.get("Environmental", {}),
        "social_summary": summaries.get("Social", ""),
        "social_breakdown": breakdowns.get("Social", {}),
        "governance_summary": summaries.get("Governance", ""),
        "governance_breakdown": breakdowns.get("Governance", {})
    }

# ------------------------------------------------------------
# 7) Main loop: For each company, run pipeline & insert results
# ------------------------------------------------------------
for idx, row in resources_df.iterrows():
    company_name = row["company"]
    pdf_urls = row["urls"]  # This should be a list of PDF URLs

    if not pdf_urls or len(pdf_urls) == 0:
        print(f"[SKIP] No URLs for company: {company_name}")
        continue

    print(f"\n=== Processing ESG for company: {company_name} ===")
    try:
        results = run_esg_pipeline(pdf_urls)
    except Exception as e:
        print(f"Error processing {company_name}: {e}")
        continue

    # Prepare data for insert
    insert_payload = {
        "company": company_name,
        "environmental_summary": results["environmental_summary"],
        "environmental_breakdown": results["environmental_breakdown"],  # JSONB
        "social_summary": results["social_summary"],
        "social_breakdown": results["social_breakdown"],               # JSONB
        "governance_summary": results["governance_summary"],
        "governance_breakdown": results["governance_breakdown"]        # JSONB
    }

    # Insert into the esg_report_analysis table
    insert_response = supabase.table('esg_report_analysis').insert(insert_payload).execute()

    # Convert the response to a dict using model_dump()
    insert_response_dict = insert_response.model_dump()
    if insert_response_dict.get("error"):
        print(f"❌ Failed to insert data for {company_name}. Error: {insert_response_dict.get('error')}")
        print("Response data:", insert_response_dict.get("data"))
    else:
        print(f"✅ ESG analysis inserted for {company_name}!")

print("\nAll done!")
