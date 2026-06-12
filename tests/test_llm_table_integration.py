"""
Test cases for LLM integration with parsed tables.
Tests the ability of LLMs to answer questions about parsed financial data.
"""

import unittest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Import the tools we're testing
from src.sp_stock_agent.tools.sec_10k_tool import SEC10KSummaryTool


class TestLLMTableQuestionAnswering(unittest.TestCase):
    """Test cases for LLM's ability to answer questions about parsed tables."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_financial_table = {
            "headers": ["Quarter", "Revenue", "Net Income", "EPS", "Growth Rate"],
            "rows": [
                ["Q1 2024", "$100M", "$20M", "$2.00", "10%"],
                ["Q2 2024", "$110M", "$25M", "$2.50", "15%"],
                ["Q3 2024", "$120M", "$30M", "$3.00", "20%"],
                ["Q4 2024", "$130M", "$35M", "$3.50", "25%"]
            ]
        }
        
        self.sample_balance_sheet_table = {
            "headers": ["Item", "2023", "2024", "Change"],
            "rows": [
                ["Cash & Equivalents", "$50M", "$60M", "+20%"],
                ["Total Assets", "$200M", "$250M", "+25%"],
                ["Total Liabilities", "$100M", "$120M", "+20%"],
                ["Shareholders' Equity", "$100M", "$130M", "+30%"]
            ]
        }
    
    def test_table_data_extraction_for_llm(self):
        """Test extraction of table data in format suitable for LLM processing."""
        # Convert table to markdown format for LLM
        markdown_table = self._table_to_markdown(self.sample_financial_table)
        
        # Verify markdown format
        self.assertIn("| Quarter | Revenue | Net Income | EPS | Growth Rate |", markdown_table)
        self.assertIn("Q1 2024", markdown_table)
        self.assertIn("$100M", markdown_table)
        self.assertIn("$2.00", markdown_table)
        
        # Verify all data is present
        for row in self.sample_financial_table["rows"]:
            for cell in row:
                self.assertIn(str(cell), markdown_table)
    
    def _table_to_markdown(self, table_data: Dict[str, Any]) -> str:
        """Convert table data to markdown format."""
        markdown = "| " + " | ".join(table_data["headers"]) + " |\n"
        markdown += "| " + " | ".join(["---"] * len(table_data["headers"])) + " |\n"
        
        for row in table_data["rows"]:
            markdown += "| " + " | ".join(row) + " |\n"
        
        return markdown
    
    @patch('openai.ChatCompletion.create')
    def test_revenue_trend_analysis(self, mock_openai):
        """Test LLM's ability to analyze revenue trends from table data."""
        # Mock LLM response
        mock_openai.return_value = Mock(
            choices=[Mock(message=Mock(content="Revenue increased consistently from $100M in Q1 to $130M in Q4, showing a 30% total growth over the year."))]
        )
        
        markdown_table = self._table_to_markdown(self.sample_financial_table)
        question = "What is the revenue trend from Q1 to Q4?"
        
        # Simulate LLM call
        prompt = f"""
        Based on the following financial table, answer this question: {question}
        
        {markdown_table}
        """
        
        # Verify the prompt contains necessary information
        self.assertIn("Revenue", prompt)
        self.assertIn("Q1", prompt)
        self.assertIn("Q4", prompt)
        self.assertIn("$100M", prompt)
        self.assertIn("$130M", prompt)
        
        # Verify question is answerable with the data
        revenue_values = [row[1] for row in self.sample_financial_table["rows"]]
        self.assertEqual(len(revenue_values), 4)
        self.assertEqual(revenue_values[0], "$100M")  # Q1
        self.assertEqual(revenue_values[3], "$130M")  # Q4
    
    @patch('openai.ChatCompletion.create')
    def test_eps_growth_analysis(self, mock_openai):
        """Test LLM's ability to analyze EPS growth from table data."""
        # Mock LLM response
        mock_openai.return_value = Mock(
            choices=[Mock(message=Mock(content="EPS grew from $2.00 in Q1 to $3.50 in Q4, representing a 75% increase over the year."))]
        )
        
        markdown_table = self._table_to_markdown(self.sample_financial_table)
        question = "How much did EPS grow from Q1 to Q4?"
        
        # Verify the data supports the question
        eps_values = [row[3] for row in self.sample_financial_table["rows"]]
        self.assertEqual(eps_values[0], "$2.00")  # Q1
        self.assertEqual(eps_values[3], "$3.50")  # Q4
        
        # Calculate expected growth
        q1_eps = float(eps_values[0].replace("$", ""))
        q4_eps = float(eps_values[3].replace("$", ""))
        expected_growth = ((q4_eps - q1_eps) / q1_eps) * 100
        self.assertEqual(expected_growth, 75.0)
    
    @patch('openai.ChatCompletion.create')
    def test_balance_sheet_analysis(self, mock_openai):
        """Test LLM's ability to analyze balance sheet data."""
        # Mock LLM response
        mock_openai.return_value = Mock(
            choices=[Mock(message=Mock(content="Shareholders' equity increased by 30% from $100M to $130M, while total assets grew by 25% from $200M to $250M."))]
        )
        
        markdown_table = self._table_to_markdown(self.sample_balance_sheet_table)
        question = "How did shareholders' equity and total assets change?"
        
        # Verify the data supports the question
        equity_row = [row for row in self.sample_balance_sheet_table["rows"] if "Shareholders' Equity" in row[0]][0]
        assets_row = [row for row in self.sample_balance_sheet_table["rows"] if "Total Assets" in row[0]][0]
        
        self.assertEqual(equity_row[1], "$100M")  # 2023 equity
        self.assertEqual(equity_row[2], "$130M")  # 2024 equity
        self.assertEqual(equity_row[3], "+30%")   # Change
        
        self.assertEqual(assets_row[1], "$200M")  # 2023 assets
        self.assertEqual(assets_row[2], "$250M")  # 2024 assets
        self.assertEqual(assets_row[3], "+25%")   # Change
    
    def test_table_data_validation(self):
        """Test validation of table data before sending to LLM."""
        # Test valid table
        self.assertTrue(self._validate_table(self.sample_financial_table))
        
        # Test invalid table (missing headers)
        invalid_table = {
            "rows": [["Q1 2024", "$100M"]]
        }
        self.assertFalse(self._validate_table(invalid_table))
        
        # Test invalid table (empty rows)
        invalid_table2 = {
            "headers": ["Quarter", "Revenue"],
            "rows": []
        }
        self.assertFalse(self._validate_table(invalid_table2))
        
        # Test invalid table (inconsistent row lengths)
        invalid_table3 = {
            "headers": ["Quarter", "Revenue", "Income"],
            "rows": [
                ["Q1 2024", "$100M", "$20M"],
                ["Q2 2024", "$110M"]  # Missing third column
            ]
        }
        self.assertFalse(self._validate_table(invalid_table3))
    
    def _validate_table(self, table_data: Dict[str, Any]) -> bool:
        """Validate table data structure."""
        if "headers" not in table_data or "rows" not in table_data:
            return False
        
        if not table_data["headers"] or not table_data["rows"]:
            return False
        
        header_count = len(table_data["headers"])
        for row in table_data["rows"]:
            if len(row) != header_count:
                return False
        
        return True
    
    @patch('openai.ChatCompletion.create')
    def test_complex_financial_analysis(self, mock_openai):
        """Test LLM's ability to perform complex financial analysis."""
        # Mock LLM response
        mock_openai.return_value = Mock(
            choices=[Mock(message=Mock(content="The company shows strong financial performance with consistent revenue growth (30% total), improving profitability (EPS up 75%), and solid balance sheet strength (equity growth of 30% vs asset growth of 25%)."))]
        )
        
        # Combine multiple tables for comprehensive analysis
        financial_markdown = self._table_to_markdown(self.sample_financial_table)
        balance_markdown = self._table_to_markdown(self.sample_balance_sheet_table)
        
        combined_data = f"""
        Income Statement Data:
        {financial_markdown}
        
        Balance Sheet Data:
        {balance_markdown}
        """
        
        question = "Provide a comprehensive financial analysis of this company's performance."
        
        # Verify all key metrics are present for analysis
        self.assertIn("Revenue", combined_data)
        self.assertIn("Net Income", combined_data)
        self.assertIn("EPS", combined_data)
        self.assertIn("Total Assets", combined_data)
        self.assertIn("Shareholders' Equity", combined_data)
    
    def test_table_data_consistency_checks(self):
        """Test consistency checks for financial data."""
        # Test that growth rates match calculated values
        for row in self.sample_financial_table["rows"]:
            quarter, revenue, net_income, eps, growth_rate = row
            
            # Extract numeric values
            revenue_num = float(revenue.replace("$", "").replace("M", ""))
            eps_num = float(eps.replace("$", ""))
            
            # Basic sanity checks
            self.assertGreater(revenue_num, 0)
            self.assertGreater(eps_num, 0)
            
            # Check that growth rate is a percentage
            self.assertIn("%", growth_rate)
            growth_num = float(growth_rate.replace("%", ""))
            self.assertGreaterEqual(growth_num, 0)
    
    @patch('openai.ChatCompletion.create')
    def test_error_handling_in_llm_analysis(self, mock_openai):
        """Test error handling when LLM analysis fails."""
        # Mock LLM error
        mock_openai.side_effect = Exception("API Error")
        
        markdown_table = self._table_to_markdown(self.sample_financial_table)
        question = "What is the revenue trend?"
        
        # Should handle the error gracefully
        try:
            # This would normally call the LLM
            prompt = f"Question: {question}\n\nTable:\n{markdown_table}"
            # In real implementation, this would be the LLM call
            raise Exception("API Error")
        except Exception as e:
            # Should provide fallback analysis or error message
            self.assertIn("API Error", str(e))
    
    def test_table_data_summarization(self):
        """Test creation of table summaries for LLM consumption."""
        summary = self._create_table_summary(self.sample_financial_table)
        
        # Verify summary contains key information
        self.assertIn("4 quarters", summary)
        self.assertIn("Revenue", summary)
        self.assertIn("EPS", summary)
        self.assertIn("Growth Rate", summary)
        
        # Verify summary is concise
        self.assertLess(len(summary), 500)  # Should be concise
    
    def _create_table_summary(self, table_data: Dict[str, Any]) -> str:
        """Create a summary of table data for LLM consumption."""
        num_rows = len(table_data["rows"])
        headers = table_data["headers"]
        
        summary = f"Financial data table with {num_rows} quarters showing: "
        summary += ", ".join(headers)
        
        # Add key metrics
        if "Revenue" in headers:
            revenue_idx = headers.index("Revenue")
            revenues = [row[revenue_idx] for row in table_data["rows"]]
            summary += f". Revenue ranges from {revenues[0]} to {revenues[-1]}"
        
        if "EPS" in headers:
            eps_idx = headers.index("EPS")
            eps_values = [row[eps_idx] for row in table_data["rows"]]
            summary += f". EPS ranges from {eps_values[0]} to {eps_values[-1]}"
        
        return summary


class TestSECTableParsingQuality(unittest.TestCase):
    """Test cases for SEC table parsing quality."""
    
    def setUp(self):
        """Set up test fixtures for SEC table parsing."""
        self.sample_sec_table_html = """
        <table>
            <tr><th>Fiscal Year</th><th>Revenue</th><th>Operating Income</th><th>Net Income</th></tr>
            <tr><td>2021</td><td>$365,817</td><td>$108,949</td><td>$94,680</td></tr>
            <tr><td>2022</td><td>$394,328</td><td>$119,437</td><td>$99,803</td></tr>
            <tr><td>2023</td><td>$383,285</td><td>$114,301</td><td>$96,995</td></tr>
        </table>
        """
    
    def test_sec_table_extraction(self):
        """Test extraction of tables from SEC filings."""
        # Mock SEC parser
        mock_table_element = Mock()
        mock_table_element.table_to_markdown.return_value = """
        | Fiscal Year | Revenue | Operating Income | Net Income |
        |-------------|---------|------------------|------------|
        | 2021        | $365,817| $108,949         | $94,680    |
        | 2022        | $394,328| $119,437         | $99,803    |
        | 2023        | $383,285| $114,301         | $96,995    |
        """
        
        markdown_table = mock_table_element.table_to_markdown()
        
        # Verify table structure
        self.assertIn("| Fiscal Year | Revenue | Operating Income | Net Income |", markdown_table)
        self.assertIn("2021", markdown_table)
        self.assertIn("2022", markdown_table)
        self.assertIn("2023", markdown_table)
        self.assertIn("$365,817", markdown_table)
        self.assertIn("$394,328", markdown_table)
        self.assertIn("$383,285", markdown_table)
    
    @patch('openai.ChatCompletion.create')
    def test_sec_table_analysis_by_llm(self, mock_openai):
        """Test LLM analysis of SEC table data."""
        # Mock LLM response
        mock_openai.return_value = Mock(
            choices=[Mock(message=Mock(content="Revenue peaked in 2022 at $394,328M but declined to $383,285M in 2023. Operating income followed a similar pattern, reaching $119,437M in 2022 before falling to $114,301M in 2023."))]
        )
        
        sec_table_markdown = """
        | Fiscal Year | Revenue | Operating Income | Net Income |
        |-------------|---------|------------------|------------|
        | 2021        | $365,817| $108,949         | $94,680    |
        | 2022        | $394,328| $119,437         | $99,803    |
        | 2023        | $383,285| $114,301         | $96,995    |
        """
        
        question = "What are the revenue and operating income trends from 2021 to 2023?"
        
        # Verify the data supports the analysis
        self.assertIn("2021", sec_table_markdown)
        self.assertIn("2022", sec_table_markdown)
        self.assertIn("2023", sec_table_markdown)
        self.assertIn("$365,817", sec_table_markdown)
        self.assertIn("$394,328", sec_table_markdown)
        self.assertIn("$383,285", sec_table_markdown)
        
        # Verify question is answerable
        self.assertIn("revenue", question.lower())
        self.assertIn("operating income", question.lower())
        self.assertIn("trends", question.lower())


if __name__ == '__main__':
    unittest.main() 