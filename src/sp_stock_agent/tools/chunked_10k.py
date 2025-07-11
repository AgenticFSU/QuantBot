"""
SEC 10-K Chunked Parser Tool

This module provides a CrewAI tool for downloading, parsing, and chunking SEC 10-K filings
into smaller, manageable segments for enhanced processing and analysis.
"""

import logging
import os
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from rag.core import create_rag_retriever


LOGS_DIR = "logs"
# Setup simple global logger
os.makedirs(LOGS_DIR, exist_ok=True)
logger = logging.getLogger(__name__)

# Avoid duplicate handlers if already configured
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'{LOGS_DIR}/chunked_10k_tool.log'),
            logging.StreamHandler()
        ]
    )

class Query(BaseModel):
    query: str = Field(
        ...,
        description="Queries about the specific company from finacial 10K document report."
    )

class ChunkedSEC10KTool(BaseTool):
    """
    "Fetch chunked SEC 10-K filings "
    """
    
    name: str = "get_chunked_10k_sections"
    description: str = (
        "A tool to fetch company financial data extracted from SEC 10-K filings."
        "This tool can provide relevant chunks of data needed for financial analysis of the company."
        "The query made to this tool should be specific so that it responds with most relevant information."
    )

    args_schema: Type[Query] = Query

    def _run(self, query: str) -> str:
        """
        Main execution method for the chunked 10-K tool.
        
        Args:
            symbol: Stock ticker symbol
            chunk_strategy: Strategy for chunking ("semantic", "overlapping", "hybrid")
            
        Returns:
            JSON string containing chunks and metadata
        """
        logger.info(f"Getting response for query: {query}")
        retriever = create_rag_retriever(collection_name = "sec10k_chunks")
        return retriever.retrieve(query=query, k=10, return_metadata=False)


# Example usage
if __name__ == "__main__":
    tool = ChunkedSEC10KTool()
    result = tool._run(query="What kind of areas is the company providing the services?")
    print(result)
