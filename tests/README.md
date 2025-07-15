# QuantBot Test Suite

This directory contains comprehensive test cases for the QuantBot financial analysis system. The tests cover SEC parsing accuracy, table parsing quality, and Alphavantage Tool functionality for both single and multiple ticker scenarios.

## Test Structure

### 1. SEC Parsing Tests (`test_sec_parsing.py`)
Tests the accuracy and reliability of SEC filing parsing:

- **SEC Tool Initialization**: Verifies proper tool setup and configuration
- **Basic Functionality**: Tests core SEC parsing with mocked dependencies
- **Cache Functionality**: Ensures proper handling of cached SEC filings
- **Error Handling**: Tests graceful handling of invalid symbols and API errors
- **Section Extraction**: Validates extraction of specific SEC sections (Risk Factors, Management Discussion)
- **Table Parsing Quality**: Tests the quality of table extraction from SEC documents

### 2. Alphavantage Tools Tests (`test_alphavantage_tools.py`)
Comprehensive tests for all Alphavantage API tools:

#### FetchStockSummaryTool Tests:
- **Single Ticker Scenarios**: Tests fetching data for individual stocks
- **Multiple Ticker Scenarios**: Tests batch processing of multiple stocks
- **Error Handling**: Tests API rate limits, invalid symbols, and network errors
- **Data Format Validation**: Ensures proper data structure and types
- **Partial Failure Handling**: Tests behavior when some tickers fail

#### NewsSentimentTool Tests:
- **Single Ticker News**: Tests news sentiment analysis for individual stocks
- **Multiple Ticker News**: Tests batch news analysis across multiple stocks
- **Time Parameter Handling**: Tests date range filtering
- **Response Parsing**: Validates news sentiment data extraction

#### EarningsCallTranscriptTool Tests:
- **Transcript Fetching**: Tests earnings call transcript retrieval
- **Quarter Parameter Handling**: Tests different fiscal quarter formats
- **Error Handling**: Tests missing transcripts and API errors

#### Integration Tests:
- **Full Analysis Workflow**: Tests complete analysis using multiple tools
- **Data Consistency**: Ensures consistency across different API endpoints

### 3. LLM Table Integration Tests (`test_llm_table_integration.py`)
Tests the integration between parsed tables and LLM question answering:

- **Table Data Extraction**: Tests conversion of tables to LLM-friendly formats
- **Revenue Trend Analysis**: Tests LLM's ability to analyze revenue trends
- **EPS Growth Analysis**: Tests earnings per share trend analysis
- **Balance Sheet Analysis**: Tests financial statement analysis
- **Data Validation**: Tests table structure validation before LLM processing
- **Error Handling**: Tests graceful handling of LLM API failures
- **SEC Table Analysis**: Tests LLM analysis of SEC filing tables

## Running the Tests

### Prerequisites
```bash
# Install test dependencies
uv pip install pytest pytest-cov pytest-mock

# Set up environment variables for testing
export ALPHA_VANTAGE_API_KEY="your_test_key"
export OPENAI_API_KEY="your_test_key"
```

### Running All Tests
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src/sp_stock_agent --cov-report=html

# Run with verbose output
pytest tests/ -v
```

### Running Specific Test Categories
```bash
# Run only SEC parsing tests
pytest tests/test_sec_parsing.py

# Run only Alphavantage tool tests
pytest tests/test_alphavantage_tools.py

# Run only LLM integration tests
pytest tests/test_llm_table_integration.py

# Run by markers
pytest tests/ -m unit      # Unit tests
pytest tests/ -m integration  # Integration tests
pytest tests/ -m slow      # Slow-running tests
```

### Running Individual Tests
```bash
# Run specific test method
pytest tests/test_alphavantage_tools.py::TestFetchStockSummaryTool::test_single_ticker_fetch_success

# Run tests matching a pattern
pytest tests/ -k "single_ticker"
```

## Test Data and Fixtures

The test suite uses comprehensive fixtures defined in `conftest.py`:

- **sample_stock_data**: Mock stock price data
- **sample_news_data**: Mock news sentiment data
- **sample_sec_table_data**: Mock SEC filing table data
- **sample_financial_table**: Mock financial performance data
- **mock_env_vars**: Environment variable mocking
- **temp_cache_dir**: Temporary directory for cache testing
- **mock_api_responses**: Mock API responses
- **mock_llm_response**: Mock LLM responses

## Test Coverage Areas

### SEC Parsing Accuracy
- ✅ Tool initialization and configuration
- ✅ HTML parsing and element extraction
- ✅ Section identification and extraction
- ✅ Table parsing and markdown conversion
- ✅ Cache management and file handling
- ✅ Error handling for invalid inputs
- ✅ Data structure validation

### Table Parsing Quality
- ✅ Table structure validation
- ✅ Data type consistency
- ✅ Markdown format conversion
- ✅ Financial data accuracy
- ✅ Growth rate calculations
- ✅ Data completeness checks

### Alphavantage Tool Functionality

#### Single Ticker Tests:
- ✅ API endpoint configuration
- ✅ Request parameter validation
- ✅ Response parsing and formatting
- ✅ Data type conversion
- ✅ Error message handling
- ✅ Rate limit handling

#### Multiple Ticker Tests:
- ✅ Batch processing logic
- ✅ Partial failure handling
- ✅ Data aggregation
- ✅ Memory efficiency
- ✅ Progress tracking
- ✅ Result consistency

### LLM Integration
- ✅ Table data preparation for LLM
- ✅ Question formulation
- ✅ Response parsing
- ✅ Financial analysis accuracy
- ✅ Error handling and fallbacks
- ✅ Data validation before LLM calls

## Mocking Strategy

The tests use comprehensive mocking to avoid external API calls:

1. **API Calls**: All HTTP requests are mocked using `unittest.mock.patch`
2. **Environment Variables**: API keys are mocked for testing
3. **File System**: Cache files and temporary directories are mocked
4. **LLM Calls**: OpenAI API calls are mocked with realistic responses
5. **External Dependencies**: SEC parser and other external libraries are mocked

## Continuous Integration

The test suite is designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions configuration
- name: Run Tests
  run: |
    pytest tests/ --cov=src/sp_stock_agent --cov-report=xml
    pytest tests/ --cov=src/sp_stock_agent --cov-report=html
```

## Performance Considerations

- **Unit Tests**: Fast execution (< 1 second each)
- **Integration Tests**: Moderate execution time (1-5 seconds each)
- **Slow Tests**: LLM integration tests (5-10 seconds each)

Use markers to run appropriate test categories:
```bash
pytest tests/ -m "not slow"  # Skip slow tests
pytest tests/ -m unit        # Run only fast unit tests
```

## Adding New Tests

When adding new tests:

1. **Follow Naming Convention**: `test_<functionality>_<scenario>`
2. **Use Appropriate Markers**: Mark tests as `unit`, `integration`, or `slow`
3. **Add Fixtures**: Create reusable fixtures in `conftest.py`
4. **Mock External Dependencies**: Avoid real API calls in tests
5. **Test Error Cases**: Include error handling and edge cases
6. **Document Test Purpose**: Add clear docstrings explaining test objectives

## Troubleshooting

### Common Issues:

1. **Import Errors**: Ensure `src/sp_stock_agent` is in Python path
2. **Missing Dependencies**: Install test dependencies with `uv pip install pytest`
3. **Environment Variables**: Set required API keys for integration tests
4. **Mock Issues**: Check that all external calls are properly mocked

### Debug Mode:
```bash
# Run tests with debug output
pytest tests/ -v -s --tb=long

# Run specific test with debug
pytest tests/test_alphavantage_tools.py::TestFetchStockSummaryTool::test_single_ticker_fetch_success -v -s
```

## Test Results Interpretation

- **Passing Tests**: All functionality working as expected
- **Failing Tests**: Indicates bugs or API changes that need attention
- **Slow Tests**: May indicate performance issues or inefficient mocking
- **Coverage Reports**: Identify untested code paths

The test suite provides comprehensive coverage of QuantBot's core functionality, ensuring reliable and accurate financial analysis capabilities. 