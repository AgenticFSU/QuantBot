import json
import os
import requests
from crewai.tools import BaseTool

CIK_JSON_PATH = os.path.join(os.path.dirname(__file__), 'cik.json')

def get_cik_from_symbol(symbol: str) -> str:
    """
    Look up the CIK for a given stock ticker symbol from cik.json.
    Pads it with leading zeros to 10 digits.
    """
    with open(CIK_JSON_PATH, 'r') as f:
        data = json.load(f)

    for entry in data.values():
        if entry["ticker"].lower() == symbol.lower():
            cik_int = int(entry["cik_str"])
            return f"{cik_int:010d}"

    raise ValueError(f"CIK not found for symbol: {symbol}")

class SEC10KSummaryTool(BaseTool):
    name: str = "get_10k_data"
    description: str = "Fetch the latest 10-K filing for the given stock symbol"

    def _run(self, symbol: str) -> str:
                
        CIK = get_cik_from_symbol(symbol)  # Microsoft; change this to another CIK if needed
        USER_AGENT = "Your Name your.email@example.com"  # <-- Use your real info!

        # === STEP 1: Download submissions JSON ===
        submissions_url = f"https://data.sec.gov/submissions/CIK{CIK}.json"
        headers = {"User-Agent": USER_AGENT}

        print(f"Fetching submissions JSON for CIK {CIK}...")
        resp = requests.get(submissions_url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        # === STEP 2: Find the latest 10-K filing ===
        recent = data['filings']['recent']
        forms = recent['form']
        accessions = recent['accessionNumber']
        documents = recent['primaryDocument']

        try:
            idx = forms.index("10-K")
        except ValueError:
            raise Exception("No 10-K filing found in recent filings.")

        accession = accessions[idx].replace("-", "")
        primary_doc = documents[idx]
        cik_no_leading_zeros = str(int(CIK))  # Remove leading zeros

        print(f"Latest 10-K accession: {accessions[idx]}")
        print(f"Primary document: {primary_doc}")

        # === STEP 3: Build document URL ===
        doc_url = (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{cik_no_leading_zeros}/{accession}/{primary_doc}"
        )
        print(f"10-K document URL: {doc_url}")

        # === STEP 4: Download the 10-K document ===
        output_filename = f"{cik_no_leading_zeros}-10k-{accessions[idx]}.html"
        print(f"Downloading 10-K document to {output_filename}...")
        doc_resp = requests.get(doc_url, headers=headers)
        doc_resp.raise_for_status()

        with open(output_filename, "wb") as f:
            f.write(doc_resp.content)

        print("Done!")


# Example usage
if __name__ == "__main__":
    url = SEC10KSummaryTool()._run("MSFT")
    if url:
        print("[SUCCESS] 10-K URL:", url)
