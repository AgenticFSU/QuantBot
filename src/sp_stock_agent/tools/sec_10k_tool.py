"""
SEC 10-K Filing Parser Tool

This module provides a CrewAI tool for downloading, caching, and parsing SEC 10-K filings
to extract specific sections like Risk Factors (Item 1A) and other relevant sections.
"""

import json
import logging
import os
import sec_parser as sp
from crewai.tools import BaseTool
from sec_downloader import Downloader
from html_to_markdown import convert_to_markdown
from rag.core import create_rag_retriever

# Constants
CACHE_DIR = "data/10K"
OUTPUT_DIR = "data/generated"
LOGS_DIR = "logs"
DEFAULT_USER_AGENT = "MyCompanyName"
DEFAULT_EMAIL = "email@example.com"

# Target sections configuration
TARGET_SECTIONS = {
    "item 1a": "all",
    "item 7a": "text"
}

# Setup simple global logger
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'{LOGS_DIR}/sec_10k_tool.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def _level_to_markdown(level: int) -> str:
    """Convert hierarchy level to markdown heading format.
    
    Args:
        level: The hierarchy level (0-based)
        
    Returns:
        String of '#' characters for markdown heading
    """
    return "#" * (level + 1) if level <= 5 else ""


class Sec10KTool(BaseTool):
    """
    A CrewAI tool for fetching, parsing, and extracting sections from SEC 10-K filings.
    
    This tool downloads the latest 10-K filing for a given stock symbol, caches it locally,
    parses the document to extract specific sections (like Risk Factors), and returns
    the data as markdown text.
    """
    
    name: str = "get_10k_risk_factors_as_json"
    description: str = (
        "Fetch, parse, and extract 'Item 1A' (Risk Factors) "
        "from the latest 10-K filing for a given stock symbol. "
        "Returns the data as a hierarchical JSON object."
    )
    ignore_table: bool = True

    
    def _load_and_cache(self, symbol: str) -> tuple[bool, str]:
        """Handle all cache operations: check cache, download if needed, save to cache.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            HTML content of the 10-K filing
        """
        # Set up cache directory and file path
        os.makedirs(CACHE_DIR, exist_ok=True)
        file_path = os.path.join(CACHE_DIR, f"{symbol}_10k.html")

        # Try to load from cache first
        if os.path.exists(file_path):
            logger.info(f"Loading from cache: {file_path}")
            with open(file_path, "r") as f:
                return True, f.read()
        
        # Download from SEC if not cached
        logger.info(f"Downloading 10-K filing from SEC for symbol: {symbol}")
        downloader = Downloader(DEFAULT_USER_AGENT, DEFAULT_EMAIL)
        html_content = downloader.get_filing_html(ticker=symbol, form="10-K")
        
        # Save to cache with error handling
        try:
            with open(file_path, "wb") as f:
                f.write(html_content)
            logger.info("Successfully cached 10-K filing")
        except Exception as e:
            logger.error(f"Error saving to cache: {e}")
            # Clean up corrupted cache file
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up corrupted cache file: {file_path}")
                except Exception as cleanup_error:
                    logger.error(f"Error deleting file {file_path}: {cleanup_error}")
            raise
        
        # Convert bytes to string for consistency
        return False, html_content.decode('utf-8') if isinstance(html_content, bytes) else html_content

    def _process_and_save_sections(self, html: str, symbol: str) -> str:
        """Parse document, extract target sections, and save output.
        
        Args:
            html: HTML content of the 10-K filing
            symbol: Stock ticker symbol
            
        Returns:
            Markdown content of extracted sections
        """
        # Parse the document
        logger.info("Parsing 10-K document")
        elements = sp.Edgar10KParser().parse(html)
        tree = sp.TreeBuilder().build(elements)
        top_level_sections = [item for part in tree for item in part.children]
        
        # Extract and process target sections
        markdown = ""
        sections_found = 0

        for section in top_level_sections:
            section_text = section.semantic_element.text.lower().strip()
            
            # Find which target section matches the current section
            matching_key = next(
                (title for title in TARGET_SECTIONS.keys() if section_text.startswith(title)), 
                None
            )
            
            if matching_key:
                sections_found += 1
                section_type = TARGET_SECTIONS[matching_key]

                logger.info(f"Found matching section: {section.semantic_element.text}")
                markdown += f"# {section.semantic_element.text}\n"
                
                # Process all descendants of this section
                for node in section.get_descendants():
                    element = node.semantic_element
                    
                    # Process different element types based on section configuration
                    if isinstance(element, sp.TextElement) and section_type in ["all", "text"]:
                        markdown += f"{element.text}\n"
                    
                    elif isinstance(element, sp.TitleElement) and section_type in ["all", "text"]:
                        markdown += f"{_level_to_markdown(element.level)} {element.text}\n"
                    
                    elif (isinstance(element, sp.TableElement) and section_type in ["all", "table"] 
                          and not self.ignore_table):
                        
                        # markdown += f"{element.table_to_markdown()}\n"
                        # Existing function from sec_parser does not work
                        # TODO: Find a way to make existing function work
                        
                        html_tables = element.html_tag.get_source_code()
                        markdown += convert_to_markdown(html_tables)

        logger.info(f"Found {sections_found} matching sections")
        
        # Save the processed content
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_file = os.path.join(OUTPUT_DIR, f"{symbol}_10k_parsed.md")
        
        with open(output_file, "w") as f:
            f.write(markdown)
        
        logger.info(f"Saved parsed 10-K data to: {output_file}")
        return markdown

    def _run(self, symbol: str) -> str:
        """
        Main execution method for the tool.
        Args:
            symbol: Stock ticker symbol 
        Returns:
            Markdown content of extracted sections
        """
        logger.info(f"Starting 10-K processing for symbol: {symbol}")
        
        # Get 10-K filing content (handles caching automatically)
        #TODO: Quick fix to check if the report was cached. If it was, chunking would not be needed.
        was_cached, html = self._load_and_cache(symbol)
        
        # Process document and save results
        # TODO: Parameterizing required for section selection based on user prompt.
        # TODO: Advanced chunking and sorting approach needed.
        markdown = self._process_and_save_sections(html, symbol)

        if markdown and not was_cached:
            retriever =  create_rag_retriever(
                    collection_name = "sec10k_chunks",
                    chunk_size = 1000,
                    chunk_overlap = 200,
                    top_k = 8
                ) 
            return retriever.ingest_text(markdown)

        return markdown

# Example usage
if __name__ == "__main__":
    tool = Sec10KTool()
    result = tool._run("AAPL")
    print(json.dumps(result, indent=2))
    