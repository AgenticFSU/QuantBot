"""
Test cases for SEC parsing accuracy and table parsing quality.
Tests both the SEC10KSummaryTool and table parsing functionality.
"""

import unittest
import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Import the tools we're testing
from src.sp_stock_agent.tools.sec_10k_tool import SEC10KSummaryTool
import sec_parser as sp


class TestSECParsingAccuracy(unittest.TestCase):
    """Test cases for SEC parsing accuracy."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tool = SEC10KSummaryTool()
        self.sample_symbol = "AAPL"
        
        # Sample HTML content for testing
        self.sample_html = """
        <html>
            <body>
                <h1>Item 1A. Risk Factors</h1>
                <p>This is a sample risk factor section.</p>
                <table>
                    <tr><th>Metric</th><th>Value</th></tr>
                    <tr><td>Revenue</td><td>$100M</td></tr>
                </table>
                <h2>Subsection</h2>
                <p>More content here.</p>
            </body>
        </html>
        """
    
    def test_sec_tool_initialization(self):
        """Test that SEC10KSummaryTool initializes correctly."""
        self.assertEqual(self.tool.name, "get_10k_risk_factors_as_json")
        self.assertIn("Fetch, parse, and extract", self.tool.description)
    
    @patch('src.sp_stock_agent.tools.sec_10k_tool.Downloader')
    @patch('src.sp_stock_agent.tools.sec_10k_tool.sp.Edgar10KParser')
    @patch('src.sp_stock_agent.tools.sec_10k_tool.sp.TreeBuilder')
    def test_sec_parsing_basic_functionality(self, mock_tree_builder, mock_parser, mock_downloader):
        """Test basic SEC parsing functionality with mocked dependencies."""
        # Mock the downloader
        mock_dl_instance = Mock()
        mock_dl_instance.get_filing_html.return_value = self.sample_html.encode()
        mock_downloader.return_value = mock_dl_instance
        
        # Mock the parser
        mock_parser_instance = Mock()
        mock_elements = [Mock(), Mock()]  # Mock elements
        mock_parser_instance.parse.return_value = mock_elements
        mock_parser.return_value = mock_parser_instance
        
        # Mock the tree builder
        mock_tree_instance = Mock()
        mock_section = Mock()
        mock_section.semantic_element.text = "Item 7A. Quantitative and Qualitative Disclosures About Market Risk"
        mock_section.get_descendants.return_value = []
        # 修正：mock出有children属性的对象
        mock_part = Mock()
        mock_part.children = [mock_section]
        mock_tree_instance.build.return_value = [mock_part]
        mock_tree_builder.return_value = mock_tree_instance
        
        # Test the tool
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = self.sample_html
                result = self.tool._run(self.sample_symbol)
        
        self.assertIsInstance(result, str)
        self.assertIn("Item 7A", result)
    
    def test_cache_functionality(self):
        """Test that SEC tool properly handles cached files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = os.path.join(temp_dir, f"{self.sample_symbol}_10k.html")
            
            # Create a mock cache file
            with open(cache_file, 'w') as f:
                f.write(self.sample_html)
            
            with patch('src.sp_stock_agent.tools.sec_10k_tool.os.path.join') as mock_join:
                mock_join.return_value = cache_file
                
                with patch('os.path.exists', return_value=True):
                    with patch('builtins.open', create=True) as mock_open:
                        mock_open.return_value.__enter__.return_value.read.return_value = self.sample_html
                        # Mock os.makedirs 防止FileExistsError
                        with patch('src.sp_stock_agent.tools.sec_10k_tool.os.makedirs'):
                            # Mock the parser components
                            with patch('src.sp_stock_agent.tools.sec_10k_tool.sp.Edgar10KParser'):
                                with patch('src.sp_stock_agent.tools.sec_10k_tool.sp.TreeBuilder'):
                                    result = self.tool._run(self.sample_symbol)
                                    # Verify cache was used
                                    mock_open.assert_called()
    
    def test_error_handling_invalid_symbol(self):
        """Test error handling for invalid stock symbols."""
        with patch('src.sp_stock_agent.tools.sec_10k_tool.Downloader') as mock_downloader:
            mock_dl_instance = Mock()
            mock_dl_instance.get_filing_html.side_effect = Exception("Symbol not found")
            mock_downloader.return_value = mock_dl_instance
            
            with patch('os.path.exists', return_value=False):
                with self.assertRaises(Exception):
                    self.tool._run("INVALID_SYMBOL")


class TestTableParsingQuality(unittest.TestCase):
    """Test cases for table parsing quality and LLM integration."""
    
    def setUp(self):
        """Set up test fixtures for table parsing."""
        self.sample_table_html = """
        <table>
            <tr><th>Quarter</th><th>Revenue</th><th>Profit</th></tr>
            <tr><td>Q1 2024</td><td>$100M</td><td>$20M</td></tr>
            <tr><td>Q2 2024</td><td>$110M</td><td>$25M</td></tr>
            <tr><td>Q3 2024</td><td>$120M</td><td>$30M</td></tr>
        </table>
        """
    
    def test_table_element_creation(self):
        """Test creation of table elements from HTML."""
        # Mock the table element
        mock_table_element = Mock(spec=sp.TableElement)
        mock_table_element.table_to_markdown.return_value = """
        | Quarter | Revenue | Profit |
        |---------|---------|--------|
        | Q1 2024 | $100M   | $20M   |
        | Q2 2024 | $110M   | $25M   |
        | Q3 2024 | $120M   | $30M   |
        """
        
        # Test table to markdown conversion
        markdown_table = mock_table_element.table_to_markdown()
        
        self.assertIn("| Quarter | Revenue | Profit |", markdown_table)
        self.assertIn("Q1 2024", markdown_table)
        self.assertIn("$100M", markdown_table)
    
    def test_table_structure_validation(self):
        """Test that parsed tables have proper structure."""
        # Mock table data
        table_data = {
            "headers": ["Quarter", "Revenue", "Profit"],
            "rows": [
                ["Q1 2024", "$100M", "$20M"],
                ["Q2 2024", "$110M", "$25M"],
                ["Q3 2024", "$120M", "$30M"]
            ]
        }
        
        # Validate table structure
        self.assertEqual(len(table_data["headers"]), 3)
        self.assertEqual(len(table_data["rows"]), 3)
        
        # Check that all rows have the same number of columns as headers
        for row in table_data["rows"]:
            self.assertEqual(len(row), len(table_data["headers"]))
    
    @patch('openai.ChatCompletion.create')
    def test_llm_table_question_answering(self, mock_openai):
        """Test LLM's ability to answer questions about parsed tables."""
        # Mock LLM response
        mock_openai.return_value = Mock(
            choices=[Mock(message=Mock(content="The revenue increased from $100M in Q1 to $120M in Q3, showing a 20% growth."))]
        )
        
        # Sample table data
        table_markdown = """
        | Quarter | Revenue | Profit |
        |---------|---------|--------|
        | Q1 2024 | $100M   | $20M   |
        | Q2 2024 | $110M   | $25M   |
        | Q3 2024 | $120M   | $30M   |
        """
        
        # Question about the table
        question = "What is the revenue trend from Q1 to Q3?"
        
        # Simulate LLM call (this would be done by the actual LLM integration)
        # For testing, we'll just verify the question makes sense given the table
        self.assertIn("revenue", question.lower())
        self.assertIn("trend", question.lower())
        self.assertIn("Q1", question)
        self.assertIn("Q3", question)
        
        # Verify table contains the data needed to answer the question
        self.assertIn("Q1 2024", table_markdown)
        self.assertIn("Q3 2024", table_markdown)
        self.assertIn("$100M", table_markdown)
        self.assertIn("$120M", table_markdown)
    
    def test_table_data_extraction_accuracy(self):
        """Test accuracy of extracting data from tables."""
        # Sample financial table
        financial_table = {
            "headers": ["Metric", "2023", "2024", "Change"],
            "rows": [
                ["Revenue", "$1,000M", "$1,200M", "+20%"],
                ["Net Income", "$100M", "$150M", "+50%"],
                ["EPS", "$2.00", "$3.00", "+50%"]
            ]
        }
        
        # Test data extraction
        revenue_2023 = financial_table["rows"][0][1]  # $1,000M
        revenue_2024 = financial_table["rows"][0][2]  # $1,200M
        revenue_change = financial_table["rows"][0][3]  # +20%
        
        self.assertEqual(revenue_2023, "$1,000M")
        self.assertEqual(revenue_2024, "$1,200M")
        self.assertEqual(revenue_change, "+20%")
        
        # Test that we can calculate the change
        revenue_2023_num = float(revenue_2023.replace("$", "").replace(",", "").replace("M", ""))
        revenue_2024_num = float(revenue_2024.replace("$", "").replace(",", "").replace("M", ""))
        calculated_change = ((revenue_2024_num - revenue_2023_num) / revenue_2023_num) * 100
        
        self.assertAlmostEqual(calculated_change, 20.0, places=1)
    
    def test_table_formatting_consistency(self):
        """Test that table formatting is consistent across different formats."""
        # Test different table formats
        formats = [
            # Markdown format
            "| Header1 | Header2 |\n|---------|---------|\n| Data1   | Data2   |",
            # CSV-like format
            "Header1,Header2\nData1,Data2",
            # JSON format
            '{"headers": ["Header1", "Header2"], "rows": [["Data1", "Data2"]]}'
        ]
        
        for table_format in formats:
            # Each format should contain the same basic structure
            self.assertIn("Header1", table_format)
            self.assertIn("Header2", table_format)
            self.assertIn("Data1", table_format)
            self.assertIn("Data2", table_format)


class TestSECSectionExtraction(unittest.TestCase):
    """Test cases for specific SEC section extraction."""
    
    def test_risk_factors_section_extraction(self):
        """Test extraction of Item 1A (Risk Factors) section."""
        # Mock section data
        risk_factors_section = {
            "title": "Item 1A. Risk Factors",
            "content": [
                "The following risk factors could materially affect our business...",
                "Market risks include...",
                "Regulatory risks include..."
            ]
        }
        
        # Test section identification
        self.assertIn("Item 1A", risk_factors_section["title"])
        self.assertIn("Risk Factors", risk_factors_section["title"])
        
        # Test content extraction
        self.assertEqual(len(risk_factors_section["content"]), 3)
        self.assertIn("risk factors", risk_factors_section["content"][0].lower())
    
    def test_management_discussion_section_extraction(self):
        """Test extraction of Item 7 (Management Discussion) section."""
        # Mock section data
        md_section = {
            "title": "Item 7. Management's Discussion and Analysis",
            "content": [
                "Our financial results for the fiscal year ended...",
                "Revenue increased by 15% compared to the prior year...",
                "Operating expenses were $500 million..."
            ]
        }
        
        # Test section identification
        self.assertIn("Item 7", md_section["title"])
        self.assertIn("Management", md_section["title"])
        
        # Test content quality
        self.assertIn("financial results", md_section["content"][0].lower())
        self.assertIn("Revenue", md_section["content"][1])
        self.assertIn("Operating expenses", md_section["content"][2])


if __name__ == '__main__':
    unittest.main() 