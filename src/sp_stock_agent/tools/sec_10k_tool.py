import json
import logging
import os
import sec_parser as sp
from crewai.tools import BaseTool
from sec_downloader import Downloader

# Ensure logs directory exists BEFORE configuring logging
os.makedirs('logs', exist_ok=True)

# Configure logger for this module
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/sec_10k_tool.log'),
        logging.StreamHandler()
    ]
)

def level_to_markdown(level: int) -> str:
    return "#" * (level + 1) if level <= 5 else ""

class SEC10KSummaryTool(BaseTool):
    name: str = "get_10k_risk_factors_as_json"
    description: str = (
        "Fetch, parse, and extract 'Item 1A' (Risk Factors) "
        "from the latest 10-K filing for a given stock symbol. "
        "Returns the data as a hierarchical JSON object."
    )

    def _run(self, symbol: str) -> dict:
        logger.info(f"Starting 10-K processing for symbol: {symbol}")
        
        # Define cache directory and file path
        cache_dir = os.path.join("data", "10K")
        os.makedirs(cache_dir, exist_ok=True)
        file_path = os.path.join(cache_dir, f"{symbol}_10k.html")

        if os.path.exists(file_path):
            logger.info(f"Loading from cache: {file_path}")
            # Load from cache
            with open(file_path, "r") as f:
                html = f.read()
        else:
            logger.info(f"Downloading from SEC for symbol {symbol}: {file_path}")
            # Initialize the downloader with a generic user-agent
            dl = Downloader("MyCompanyName", "email@example.com")
            # Download the latest 10-K filing for the given stock symbol
            html = dl.get_filing_html(ticker=symbol, form="10-K")
            # Save to cache
            try:
                with open(file_path, "wb") as f:
                    f.write(html)
                logger.info(f"Successfully cached 10-K filing for {symbol}")
            except Exception as e:
                logger.error(f"Error saving to cache: {e}")
                # Delete the file if it was created
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.info(f"Cleaned up corrupted cache file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error deleting file {file_path}: {e}")
        
        logger.info(f"Parsing 10-K document for {symbol}")
        elements = sp.Edgar10KParser().parse(html)
        tree = sp.TreeBuilder().build(elements)
        top_level_sections = [
            item for part in tree for item in part.children
        ]


        # Define titles to search for
        # TODO: Parameterizing required for section selection based on user prompt.
        # TODO: Advanced chunking and sorting approach needed.
        target_sections = {"item 7a"}
        # Find matching sections

        markdown = ""
        sections_found = 0
        for section in top_level_sections:
            section_text = section.semantic_element.text.lower().strip()
            if any(section_text.startswith(title) for title in target_sections):
                sections_found += 1
                logger.info(f"Found matching section: {section.semantic_element.text}")
                markdown += f"# {section.semantic_element.text}\n"
                for node in section.get_descendants():
                    element = node.semantic_element
                    if isinstance(element, sp.TextElement):
                        txt = element.text
                        if len(txt) > 1000:
                            # TODO: Need advanced approach to summarize long text, possibly as another agent and tool.
                            # Current approach simply truncates long text.
                            logger.debug(f"Truncating long text element (original length: {len(txt)})")
                            markdown += f"{element.text[:800]}...\n"
                        else:
                            markdown += f"{element.text}\n"

                    elif isinstance(element, sp.TitleElement):
                        markdown += f"{level_to_markdown(element.level)} {element.text}\n"
                    elif isinstance(element, sp.TableElement):
                        markdown += f"{element.table_to_markdown()}\n"

        logger.info(f"Found {sections_found} matching sections for {symbol}")
        
        # Save parsed data
        os.makedirs("data/generated", exist_ok=True)
        output_file = f"data/generated/{symbol}_10k_parsed.md"
        with open(output_file, "w") as f:
            f.write(markdown)
        logger.info(f"Saved parsed 10-K data to: {output_file}")
        
        return markdown


# Example usage
if __name__ == "__main__":
    tool = SEC10KSummaryTool()
    result = tool._run("MSFT")
    print(json.dumps(result, indent=2))
    