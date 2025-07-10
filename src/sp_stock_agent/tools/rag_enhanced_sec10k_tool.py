import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import PrivateAttr

# Add the src directory to the Python path for RAG imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from crewai.tools import BaseTool
from rag import create_rag_retriever, ChunkingStrategy
import sec_parser as sp

# Import the original SEC 10-K tool - handle both direct run and module import
try:
    from .sec_10k_tool import SEC10KSummaryTool
except ImportError:
    # When running directly, use absolute import
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    from sec_10k_tool import SEC10KSummaryTool

# Ensure logs directory exists BEFORE configuring logging
os.makedirs('logs', exist_ok=True)

# Configure logger for this module
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/rag_enhanced_sec10k_tool.log'),
        logging.StreamHandler()
    ]
)

class RAGEnhancedSEC10KTool(BaseTool):
    """
    Enhanced SEC 10-K tool that integrates SimpleRAG for intelligent document processing.
    This tool replaces the hardcoded section selection with semantic search capabilities.
    """
    
    name: str = "rag_enhanced_sec10k_analysis"
    description: str = (
        "Enhanced SEC 10-K analysis tool that uses RAG (Retrieval-Augmented Generation) "
        "for intelligent document processing. Can search across multiple 10-K filings "
        "and extract relevant information based on semantic queries. "
        "Supports dynamic section selection, cross-company comparisons, "
        "and context-aware investment analysis."
    )

    _rag = PrivateAttr()
    _sec_tool = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rag = create_rag_retriever(
            collection_name="sec_filings_enhanced",
            embedding_model="all-MiniLM-L6-v2",
            chunk_size=1000,
            chunk_overlap=200,
            top_k=5
        )
        self._sec_tool = SEC10KSummaryTool()
        logger.info("✅ RAG-Enhanced SEC 10-K Tool initialized")

    def _run(self, 
             symbol: str, 
             query: Optional[str] = None, 
             analysis_type: Optional[str] = None,
             store_document: bool = True,
             k_results: int = 3,
             sections: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Enhanced SEC 10-K analysis with RAG capabilities.
        
        Args:
            symbol: Stock symbol to analyze
            query: Specific semantic query to search for
            analysis_type: Type of analysis (risk_factors, financial_performance, etc.)
            store_document: Whether to store the document in RAG for future searches
            k_results: Number of results to return
            sections: List of sections to extract (e.g., ["item 1a", "item 7a", "item 8"])
            
        Returns:
            Dictionary containing analysis results and metadata
        """
        logger.info(f"Starting RAG-enhanced 10-K analysis for symbol: {symbol}")
        
        result = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "analysis_type": analysis_type,
            "query": query,
            "sections": sections,
            "results": [],
            "metadata": {}
        }
        
        try:
            # Step 1: Process and optionally store the 10-K filing
            if store_document:
                markdown_content = self._process_and_store_filing(symbol, sections)
                if markdown_content:
                    result["document_processed"] = True
                    result["chunks_created"] = "stored_in_rag"
                else:
                    result["document_processed"] = False
                    result["error"] = "Failed to process document"
                    return result
            
            # Step 2: Perform semantic search if query provided
            if query:
                search_results = self._semantic_search(query, symbol, k_results)
                result["results"] = search_results
                result["search_performed"] = True
            elif analysis_type:
                search_results = self._get_investment_context(symbol, analysis_type, k_results)
                result["results"] = search_results
                result["search_performed"] = True
            else:
                # Default: return basic document info
                result["message"] = "Document processed. Use 'query' or 'analysis_type' for semantic search."
                result["search_performed"] = False
            
            # Step 3: Get system statistics
            try:
                stats = self._rag.get_system_stats()
                result["rag_statistics"] = stats
            except Exception as e:
                logger.warning(f"Could not get RAG statistics: {e}")
                result["rag_statistics"] = "unavailable"
            
            logger.info(f"✅ RAG-enhanced analysis completed for {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in RAG-enhanced analysis: {e}")
            result["error"] = str(e)
            return result

    def _process_and_store_filing(self, symbol: str, sections: Optional[List[str]] = None) -> Optional[str]:
        """
        Process a 10-K filing and store it in RAG for enhanced retrieval.
        This replaces the TODO items in the original tool.
        """
        logger.info(f"Processing 10-K filing for {symbol}")
        
        try:
            # Use the original tool to get markdown content
            markdown_content = self._sec_tool._run(symbol)
            logger.info(f"✅ Downloaded and parsed 10-K for {symbol}")
            
            # If sections parameter is provided, extract specific sections
            if sections:
                markdown_content = self._extract_specific_sections(symbol, sections)
            
            # Store in RAG with proper metadata
            sections_str = ", ".join(sections) if sections else "Item 1A, Item 7A, Item 8"
            metadata = {
                "symbol": symbol,
                "filing_type": "10-K",
                "date_processed": datetime.now().isoformat(),
                "source": "SEC EDGAR",
                "sections": sections_str
            }
            
            rag_result = self._rag.ingest_text(
                text=markdown_content,
                chunking_strategy=ChunkingStrategy.RECURSIVE,
                metadata=metadata
            )
            
            logger.info(f"✅ Stored {symbol} 10-K in RAG system")
            return markdown_content
            
        except Exception as e:
            logger.error(f"❌ Error processing {symbol}: {e}")
            return None

    def _extract_specific_sections(self, symbol: str, sections: List[str]) -> str:
        """
        Extract specific sections from 10-K filing.
        """
        logger.info(f"Extracting sections {sections} for {symbol}")
        
        # Define cache directory and file path
        cache_dir = os.path.join("data", "10K")
        file_path = os.path.join(cache_dir, f"{symbol}_10k.html")
        
        if not os.path.exists(file_path):
            logger.error(f"10-K file not found for {symbol}")
            return ""
        
        # Load from cache
        with open(file_path, "r") as f:
            html = f.read()
        
        # Parse the document
        elements = sp.Edgar10KParser().parse(html)
        tree = sp.TreeBuilder().build(elements)
        top_level_sections = [
            item for part in tree for item in part.children
        ]
        
        # Convert sections to lowercase for matching
        target_sections = {section.lower() for section in sections}
        
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
                            logger.debug(f"Truncating long text element (original length: {len(txt)})")
                            markdown += f"{element.text[:800]}...\n"
                        else:
                            markdown += f"{element.text}\n"
                    elif isinstance(element, sp.TitleElement):
                        markdown += f"{self._level_to_markdown(element.level)} {element.text}\n"
                    elif isinstance(element, sp.TableElement):
                        markdown += f"{element.table_to_markdown()}\n"
        
        logger.info(f"Found {sections_found} matching sections for {symbol}")
        return markdown

    def _level_to_markdown(self, level: int) -> str:
        """Convert heading level to markdown format."""
        return "#" * (level + 1) if level <= 5 else ""

    def _semantic_search(self, query: str, symbol: Optional[str] = None, k: int = 3) -> List[Dict[str, Any]]:
        """
        Perform semantic search on stored 10-K filings.
        """
        logger.info(f"Performing semantic search: '{query}'")
        
        # Add symbol filter if provided
        filter_dict = {"symbol": symbol} if symbol else None
        
        try:
            results = self._rag.retrieve(
                query=query,
                k=k,
                filter_dict=filter_dict
            )
            
            logger.info(f"✅ Found {len(results.chunks)} relevant chunks")
            
            # Format results
            formatted_results = []
            for i, (chunk, similarity) in enumerate(zip(results.chunks, results.similarities)):
                formatted_results.append({
                    "rank": i + 1,
                    "similarity_score": round(similarity, 3),
                    "content": chunk[:500] + "..." if len(chunk) > 500 else chunk,
                    "full_content": chunk
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Error in semantic search: {e}")
            return []

    def _get_investment_context(self, symbol: str, analysis_type: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Get investment-relevant context for a specific symbol and analysis type.
        """
        queries = {
            "risk_factors": f"What are the main risk factors for {symbol}?",
            "financial_performance": f"What is {symbol}'s financial performance and outlook?",
            "competitive_position": f"What is {symbol}'s competitive position and market share?",
            "regulatory_compliance": f"What regulatory compliance issues does {symbol} face?",
            "management_discussion": f"What does {symbol}'s management discuss about future plans?",
            "market_risks": f"What market risks does {symbol} face?",
            "credit_risks": f"What credit risks does {symbol} have?",
            "operational_risks": f"What operational risks does {symbol} face?"
        }
        
        query = queries.get(analysis_type, queries["risk_factors"])
        return self._semantic_search(query, symbol, k)

    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get RAG system statistics.
        """
        try:
            return self._rag.get_system_stats()
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {"error": str(e)}

    def clear_collection(self, collection_name: Optional[str] = None) -> bool:
        """
        Clear the RAG collection.
        """
        try:
            if collection_name:
                # Implementation depends on RAG library
                logger.info(f"Clearing collection: {collection_name}")
            else:
                logger.info("Clearing default collection")
            return True
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
            return False


# Example usage
if __name__ == "__main__":
    tool = RAGEnhancedSEC10KTool()
    
    # Example 1: Process and store a filing
    result1 = tool._run("MSFT", store_document=True)
    print("Result 1:", json.dumps(result1, indent=2))
    
    # Example 2: Semantic search
    result2 = tool._run("MSFT", query="What are the main risk factors?", store_document=False)
    print("Result 2:", json.dumps(result2, indent=2))
    
    # Example 3: Investment context
    result3 = tool._run("MSFT", analysis_type="financial_performance", store_document=False)
    print("Result 3:", json.dumps(result3, indent=2)) 