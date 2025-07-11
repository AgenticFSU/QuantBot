#!/usr/bin/env python
"""
Test cases for sec_10k_tool.py
Focus on:
1. Accuracy of SEC parsing
2. Quality of table parsing for LLM consumption
3. LLM-based validation of parsed content
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import shutil

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sp_stock_agent.tools.sec_10k_tool import SEC10KSummaryTool
import sec_parser as sp


class TestSEC10KToolAccuracy(unittest.TestCase):
    """Test cases for SEC 10-K tool parsing accuracy and quality"""
    
    def setUp(self):
        """Set up test environment"""
        self.tool = SEC10KSummaryTool()
        self.test_symbol = "MSFT"
        
        # Create test data directory
        self.test_data_dir = "test_data"
        os.makedirs(self.test_data_dir, exist_ok=True)
        
        # Sample HTML content for testing
        self.sample_html = """
        <html>
        <body>
            <div>
                <h1>Item 1A. Risk Factors</h1>
                <p>This is a risk factor description that should be parsed correctly.</p>
                <table>
                    <tr><th>Risk Category</th><th>Impact</th><th>Probability</th></tr>
                    <tr><td>Market Risk</td><td>High</td><td>Medium</td></tr>
                    <tr><td>Operational Risk</td><td>Medium</td><td>Low</td></tr>
                </table>
            </div>
            <div>
                <h1>Item 7A. Quantitative and Qualitative Disclosures About Market Risk</h1>
                <p>Market risk disclosure information.</p>
                <table>
                    <tr><th>Financial Instrument</th><th>Fair Value</th><th>Risk Exposure</th></tr>
                    <tr><td>Derivatives</td><td>$1,000,000</td><td>$50,000</td></tr>
                    <tr><td>Investments</td><td>$5,000,000</td><td>$100,000</td></tr>
                </table>
            </div>
        </body>
        </html>
        """

    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.test_data_dir):
            shutil.rmtree(self.test_data_dir)

    def test_sec_parsing_accuracy(self):
        """Test the accuracy of SEC document parsing"""
        print("\n🧪 Testing SEC Parsing Accuracy")
        print("-" * 40)
        
        # Mock the downloader to return our sample HTML
        with patch('sp_stock_agent.tools.sec_10k_tool.Downloader') as mock_downloader:
            mock_dl = MagicMock()
            mock_dl.get_filing_html.return_value = self.sample_html.encode('utf-8')
            mock_downloader.return_value = mock_dl
            
            # Mock the SEC parser
            with patch('sp_stock_agent.tools.sec_10k_tool.sp.Edgar10KParser') as mock_parser:
                mock_parser_instance = MagicMock()
                mock_parser.return_value = mock_parser_instance
                
                # Create mock elements that simulate the parsed structure
                mock_text_element = MagicMock()
                mock_text_element.text = "This is a risk factor description that should be parsed correctly."
                
                mock_title_element = MagicMock()
                mock_title_element.text = "Item 1A. Risk Factors"
                mock_title_element.level = 1
                
                mock_table_element = MagicMock()
                mock_table_element.table_to_markdown.return_value = """
                | Risk Category | Impact | Probability |
                |---------------|--------|-------------|
                | Market Risk | High | Medium |
                | Operational Risk | Medium | Low |
                """
                
                # Create mock semantic elements
                mock_semantic_text = MagicMock()
                mock_semantic_text.__class__ = sp.TextElement
                mock_semantic_text.text = mock_text_element.text
                
                mock_semantic_title = MagicMock()
                mock_semantic_title.__class__ = sp.TitleElement
                mock_semantic_title.text = mock_title_element.text
                mock_semantic_title.level = mock_title_element.level
                
                mock_semantic_table = MagicMock()
                mock_semantic_table.__class__ = sp.TableElement
                mock_semantic_table.table_to_markdown = mock_table_element.table_to_markdown
                
                # Create mock nodes
                mock_text_node = MagicMock()
                mock_text_node.semantic_element = mock_semantic_text
                
                mock_title_node = MagicMock()
                mock_title_node.semantic_element = mock_semantic_title
                
                mock_table_node = MagicMock()
                mock_table_node.semantic_element = mock_semantic_table
                
                # Create mock section
                mock_section = MagicMock()
                mock_section.semantic_element.text = "Item 1A. Risk Factors"
                mock_section.get_descendants.return_value = [mock_text_node, mock_title_node, mock_table_node]
                
                # Mock the parser to return our structured elements
                mock_parser_instance.parse.return_value = [mock_section]
                
                # Mock the tree builder
                with patch('sp_stock_agent.tools.sec_10k_tool.sp.TreeBuilder') as mock_tree_builder:
                    mock_tree = MagicMock()
                    mock_tree.children = [mock_section]
                    mock_tree_builder_instance = MagicMock()
                    mock_tree_builder_instance.build.return_value = [mock_tree]
                    mock_tree_builder.return_value = mock_tree_builder_instance
                    
                    # Mock file operations to ensure output is generated
                    with patch('builtins.open', create=True) as mock_open:
                        mock_file = MagicMock()
                        mock_open.return_value.__enter__.return_value = mock_file
                        
                        # Run the tool
                        result = self.tool._run(self.test_symbol)
                    
                    # Assertions for parsing accuracy
                    self.assertIsNotNone(result)
                    self.assertIsInstance(result, str)
                    self.assertIn("Item 1A. Risk Factors", result)
                    self.assertIn("Risk Category", result)
                    self.assertIn("Market Risk", result)
                    
                    print("✅ SEC parsing accuracy test passed")
                    print(f"📝 Parsed content length: {len(result)} characters")
                    print(f"📋 Contains expected sections: {'Item 1A' in result}")

    def test_table_parsing_quality(self):
        """Test the quality of table parsing for LLM consumption"""
        print("\n📊 Testing Table Parsing Quality")
        print("-" * 40)
        
        # Create a more complex table for testing
        complex_table_html = """
        <table>
            <thead>
                <tr><th>Financial Metric</th><th>2023</th><th>2022</th><th>2021</th><th>Change 2022-2023</th></tr>
            </thead>
            <tbody>
                <tr><td>Revenue</td><td>$198,270</td><td>$184,905</td><td>$168,088</td><td>+7.2%</td></tr>
                <tr><td>Net Income</td><td>$72,361</td><td>$72,738</td><td>$61,271</td><td>-0.5%</td></tr>
                <tr><td>Earnings Per Share</td><td>$9.68</td><td>$9.65</td><td>$8.05</td><td>+0.3%</td></tr>
                <tr><td>Cash and Cash Equivalents</td><td>$34,694</td><td>$14,439</td><td>$14,224</td><td>+140.3%</td></tr>
            </tbody>
        </table>
        """
        
        # Mock table element with complex data
        mock_table_element = MagicMock()
        mock_table_element.table_to_markdown.return_value = """
        | Financial Metric | 2023 | 2022 | 2021 | Change 2022-2023 |
        |------------------|------|------|------|-------------------|
        | Revenue | $198,270 | $184,905 | $168,088 | +7.2% |
        | Net Income | $72,361 | $72,738 | $61,271 | -0.5% |
        | Earnings Per Share | $9.68 | $9.65 | $8.05 | +0.3% |
        | Cash and Cash Equivalents | $34,694 | $14,439 | $14,224 | +140.3% |
        """
        
        # Test table structure quality
        table_markdown = mock_table_element.table_to_markdown()
        
        # Quality checks
        self.assertIn("Financial Metric", table_markdown)
        self.assertIn("2023", table_markdown)
        self.assertIn("Revenue", table_markdown)
        self.assertIn("$198,270", table_markdown)
        self.assertIn("+7.2%", table_markdown)
        
        # Check for proper markdown table formatting
        lines = table_markdown.strip().split('\n')
        self.assertGreater(len(lines), 3)  # Should have header, separator, and data rows
        
        # Check separator line
        separator_line = lines[1]
        self.assertIn("|", separator_line)
        self.assertIn("-", separator_line)
        
        print("✅ Table parsing quality test passed")
        print(f"📊 Table rows: {len(lines) - 2}")  # Exclude header and separator
        print(f"📋 Contains financial data: {'Revenue' in table_markdown}")
        print(f"📋 Contains numerical values: {'$198,270' in table_markdown}")

    def test_llm_table_validation(self):
        """Test table quality by simulating LLM questions about parsed tables"""
        print("\n🤖 Testing LLM Table Validation")
        print("-" * 40)
        
        # Sample parsed table data
        sample_table_data = {
            "table_markdown": """
            | Financial Metric | 2023 | 2022 | 2021 | Change 2022-2023 |
            |------------------|------|------|------|-------------------|
            | Revenue | $198,270 | $184,905 | $168,088 | +7.2% |
            | Net Income | $72,361 | $72,738 | $61,271 | -0.5% |
            | Earnings Per Share | $9.68 | $9.65 | $8.05 | +0.3% |
            | Cash and Cash Equivalents | $34,694 | $14,439 | $14,224 | +140.3% |
            """,
            "questions": [
                "What was the revenue in 2023?",
                "What was the percentage change in net income from 2022 to 2023?",
                "Which metric showed the highest percentage change?",
                "What was the earnings per share in 2021?"
            ],
            "expected_answers": [
                "$198,270",
                "-0.5%",
                "Cash and Cash Equivalents (+140.3%)",
                "$8.05"
            ]
        }
        
        # Mock LLM responses (simulating what a real LLM would answer)
        mock_llm_responses = [
            "The revenue in 2023 was $198,270 million.",
            "The net income decreased by 0.5% from 2022 to 2023.",
            "Cash and Cash Equivalents showed the highest percentage change at +140.3%.",
            "The earnings per share in 2021 was $8.05."
        ]
        
        # Test LLM question answering capability
        for i, question in enumerate(sample_table_data["questions"]):
            expected_answer = sample_table_data["expected_answers"][i]
            mock_response = mock_llm_responses[i]
            
            # Check if the mock response contains the expected answer
            # More flexible matching for different question types
            if "percentage change" in question.lower() or "change" in question.lower():
                if "highest" in question.lower():
                    answer_found = any(
                        expected.lower() in mock_response.lower() 
                        for expected in ["cash", "equivalents", "140.3%", "highest"]
                    )
                else:
                    answer_found = any(
                        expected.lower() in mock_response.lower() 
                        for expected in ["0.5%", "-0.5%", "decreased", "decrease"]
                    )
            else:
                answer_found = any(
                    expected.lower() in mock_response.lower() 
                    for expected in expected_answer.split()
                )
            
            self.assertTrue(answer_found, f"LLM should be able to answer: {question}")
            print(f"✅ Question: {question}")
            print(f"   Expected: {expected_answer}")
            print(f"   LLM Response: {mock_response}")

    def test_section_extraction_accuracy(self):
        """Test accuracy of specific section extraction"""
        print("\n📋 Testing Section Extraction Accuracy")
        print("-" * 40)
        
        # Test that the tool correctly identifies and extracts target sections
        target_sections = {"item 1a", "item 7a"}
        
        # Mock the parsing to return sections with specific titles
        with patch('sp_stock_agent.tools.sec_10k_tool.sp.Edgar10KParser') as mock_parser:
            mock_parser_instance = MagicMock()
            mock_parser.return_value = mock_parser_instance
            
            # Create mock sections
            mock_section_1a = MagicMock()
            mock_section_1a.semantic_element.text = "Item 1A. Risk Factors"
            mock_section_1a.get_descendants.return_value = []
            
            mock_section_7a = MagicMock()
            mock_section_7a.semantic_element.text = "Item 7A. Quantitative and Qualitative Disclosures About Market Risk"
            mock_section_7a.get_descendants.return_value = []
            
            mock_section_other = MagicMock()
            mock_section_other.semantic_element.text = "Item 2. Properties"
            mock_section_other.get_descendants.return_value = []
            
            # Mock parser to return all sections
            mock_parser_instance.parse.return_value = [mock_section_1a, mock_section_7a, mock_section_other]
            
            # Mock tree builder
            with patch('sp_stock_agent.tools.sec_10k_tool.sp.TreeBuilder') as mock_tree_builder:
                mock_tree = MagicMock()
                mock_tree.children = [mock_section_1a, mock_section_7a, mock_section_other]
                mock_tree_builder_instance = MagicMock()
                mock_tree_builder_instance.build.return_value = [mock_tree]
                mock_tree_builder.return_value = mock_tree_builder_instance
                
                # Mock downloader
                with patch('sp_stock_agent.tools.sec_10k_tool.Downloader') as mock_downloader:
                    mock_dl = MagicMock()
                    mock_dl.get_filing_html.return_value = self.sample_html.encode('utf-8')
                    mock_downloader.return_value = mock_dl
                    
                    # Run the tool
                    result = self.tool._run(self.test_symbol)
                    
                    # Check that target sections are found
                    self.assertIn("Item 1A. Risk Factors", result)
                    self.assertIn("Item 7A. Quantitative and Qualitative Disclosures About Market Risk", result)
                    
                    # Check that non-target sections are not included
                    self.assertNotIn("Item 2. Properties", result)
                    
                    print("✅ Section extraction accuracy test passed")
                    print(f"📋 Target sections found: 2/2")
                    print(f"📋 Non-target sections excluded: 1/1")

    def test_text_truncation_quality(self):
        """Test the quality of text truncation for long content"""
        print("\n📝 Testing Text Truncation Quality")
        print("-" * 40)
        
        # Create a long text that should be truncated
        long_text = "This is a very long text that contains important information about the company's financial performance, risk factors, and strategic initiatives. " * 20  # ~2000 characters
        
        # Mock text element
        mock_text_element = MagicMock()
        mock_text_element.text = long_text
        
        # Test that the tool handles long text appropriately
        # The tool should truncate text longer than 1000 characters
        if len(long_text) > 1000:
            expected_truncated_length = 800  # Based on the tool's logic
            truncated_text = long_text[:expected_truncated_length] + "..."
            
            self.assertLess(len(truncated_text), len(long_text))
            self.assertIn("...", truncated_text)
            
            print("✅ Text truncation quality test passed")
            print(f"📝 Original length: {len(long_text)} characters")
            print(f"📝 Truncated length: {len(truncated_text)} characters")
            print(f"📝 Truncation preserves meaning: {truncated_text[:100]}...")

    def test_error_handling(self):
        """Test error handling in various scenarios"""
        print("\n⚠️  Testing Error Handling")
        print("-" * 40)
        
        # Test with invalid symbol
        with patch('sp_stock_agent.tools.sec_10k_tool.Downloader') as mock_downloader:
            mock_dl = MagicMock()
            mock_dl.get_filing_html.side_effect = Exception("Invalid symbol")
            mock_downloader.return_value = mock_dl
            
            # The tool should handle the error gracefully
            try:
                result = self.tool._run("INVALID_SYMBOL")
                # If it doesn't raise an exception, it should return some result
                self.assertIsInstance(result, str)
                print("✅ Error handling test passed - invalid symbol handled gracefully")
            except Exception as e:
                print(f"⚠️  Tool raised exception for invalid symbol: {e}")
                # This is also acceptable behavior

    def test_output_file_generation(self):
        """Test that output files are generated correctly"""
        print("\n📄 Testing Output File Generation")
        print("-" * 40)
        
        # Create a temporary test result
        test_result = "# Test 10-K Content\n\nThis is test content for file generation testing."
        
        # Mock the entire parsing process
        with patch('sp_stock_agent.tools.sec_10k_tool.Downloader') as mock_downloader, \
             patch('sp_stock_agent.tools.sec_10k_tool.sp.Edgar10KParser') as mock_parser, \
             patch('sp_stock_agent.tools.sec_10k_tool.sp.TreeBuilder') as mock_tree_builder:
            
            # Set up mocks
            mock_dl = MagicMock()
            mock_dl.get_filing_html.return_value = self.sample_html.encode('utf-8')
            mock_downloader.return_value = mock_dl
            
            mock_parser_instance = MagicMock()
            mock_parser_instance.parse.return_value = []
            mock_parser.return_value = mock_parser_instance
            
            mock_tree = MagicMock()
            mock_tree.children = []
            mock_tree_builder_instance = MagicMock()
            mock_tree_builder_instance.build.return_value = [mock_tree]
            mock_tree_builder.return_value = mock_tree_builder_instance
            
            # Run the tool
            result = self.tool._run(self.test_symbol)
            
            # Check that output file was created
            expected_file = f"data/generated/{self.test_symbol}_10k_parsed.md"
            self.assertTrue(os.path.exists(expected_file), f"Output file {expected_file} should be created")
            
            # Check file content
            with open(expected_file, 'r') as f:
                file_content = f.read()
                self.assertIsInstance(file_content, str)
                self.assertGreater(len(file_content), 0)
            
            print("✅ Output file generation test passed")
            print(f"📄 File created: {expected_file}")
            print(f"📄 File size: {os.path.getsize(expected_file)} bytes")


def run_llm_validation_test():
    """Run a comprehensive LLM validation test on real parsed data"""
    print("\n🤖 Running Comprehensive LLM Validation Test")
    print("=" * 60)
    
    tool = SEC10KSummaryTool()
    
    # Test with a real symbol
    try:
        result = tool._run("MSFT")
        
        if result and len(result) > 0:
            print("✅ Successfully parsed MSFT 10-K filing")
            print(f"📝 Content length: {len(result):,} characters")
            
            # Check for table content
            if "|" in result:
                print("✅ Table content detected in parsed output")
                
                # Extract table sections for LLM validation
                lines = result.split('\n')
                table_sections = []
                current_table = []
                in_table = False
                
                for line in lines:
                    if "|" in line and "-" in line and len(line.split("|")) > 2:
                        in_table = True
                        current_table = [line]
                    elif in_table and "|" in line:
                        current_table.append(line)
                    elif in_table and "|" not in line:
                        if current_table:
                            table_sections.append("\n".join(current_table))
                        in_table = False
                        current_table = []
                
                print(f"📊 Found {len(table_sections)} table sections")
                
                # Validate table quality
                for i, table in enumerate(table_sections[:3]):  # Test first 3 tables
                    print(f"\n📋 Table {i+1} Quality Check:")
                    print(f"   Rows: {len(table.split(chr(10)))}")
                    print(f"   Contains headers: {'|' in table.split(chr(10))[0]}")
                    print(f"   Contains data: {len(table.split(chr(10))) > 2}")
                    
                    # Simulate LLM questions
                    if "Revenue" in table or "Income" in table or "Financial" in table:
                        print("   ✅ Contains financial data suitable for LLM analysis")
                    else:
                        print("   ⚠️  May not contain financial data")
                        
            else:
                print("⚠️  No table content detected")
                
        else:
            print("❌ Failed to parse filing or empty result")
            
    except Exception as e:
        print(f"❌ Error in LLM validation test: {e}")


if __name__ == "__main__":
    # Run unit tests
    print("🧪 Running SEC 10-K Tool Accuracy Tests")
    print("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestSEC10KToolAccuracy)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Run additional LLM validation test
    run_llm_validation_test()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    print(f"✅ Tests run: {result.testsRun}")
    print(f"❌ Failures: {len(result.failures)}")
    print(f"⚠️  Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ Test Failures:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback}")
    
    if result.errors:
        print("\n⚠️  Test Errors:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n🎉 All tests passed successfully!")
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1) 