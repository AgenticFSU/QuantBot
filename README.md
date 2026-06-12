# QuantBot - Automated Financial Intelligence System

QuantBot is an AI-powered stock analysis system built using the crewAI framework. It represents the future of automated financial information retrieval and analysis, where intelligent agents work collaboratively to gather, process, and synthesize complex market data into actionable investment insights.

## Vision

QuantBot is pioneering the next generation of financial analysis tools by creating an ecosystem of specialized AI agents that can:

- **Automate Information Retrieval**: Eliminate manual data gathering by automatically fetching real-time market data, news, SEC filings, and financial reports
- **Intelligent Data Synthesis**: Transform raw financial data into meaningful insights through multi-agent collaboration
- **Scalable Analysis**: Analyze multiple stocks simultaneously with consistent methodology
- **Adaptive Intelligence**: Continuously improve analysis quality through agent training and feedback loops
- **Democratize Financial Analysis**: Make institutional-grade analysis accessible to individual investors

Our goal is to build a comprehensive financial intelligence platform where AI agents can autonomously monitor markets, identify opportunities, and provide timely investment recommendations based on multiple data sources including real-time prices, fundamental analysis, news sentiment, and regulatory filings.

## Overview

This project utilizes multiple AI agents working together in a hierarchical structure to analyze stock data and make investment recommendations. Each agent specializes in different aspects of financial analysis, creating a robust decision-making framework that mimics the collaborative nature of professional investment teams.

## Key Features

- Multi-agent AI system for stock analysis
- Real-time stock data fetching via Alpha Vantage API
- 5-day OHLC (Open, High, Low, Close) analysis
- Investment recommendations based on recent price movements
- Support for multiple stock ticker analysis
- Modular architecture with configurable agents and tasks

## Prerequisites

- Python 3.12 or 3.13 (as specified in pyproject.toml)
- UV package manager
- Alpha Vantage API key (free tier available)
- OpenAI API key (for AI agents)

## Installation

1. **Install UV (if not already installed):**
   ```bash
   pip install uv
   ```

2. **Clone the repository:**
   ```bash
   git clone https://github.com/AgenticFSU/QuantBot.git
   cd QuantBot
   ```

3. **Create and activate a virtual environment:**
   ```bash
   uv venv
   source .venv/bin/activate  # On Linux/Mac
   # or
   .venv\Scripts\activate  # On Windows
   ```

4. **Install dependencies:**
   ```bash
   uv pip install -e .
   ```

   Or using crewAI CLI:
   ```bash
   crewai install
   ```

5. **macOS Additional Requirement:**
   
   If you're on macOS and encounter ONNX runtime errors, install the following:
   ```bash
   uv pip install onnxruntime==1.22.0
   ```
   
   This ensures compatibility with macOS system architecture.

## Configuration

1. **Create a `.env` file in the project root:**
   ```bash
   touch .env
   ```

2. **Add your API keys to the `.env` file:**
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key_here
   ```

   - Get your OpenAI API key from: https://platform.openai.com/api-keys
   - Get your free Alpha Vantage API key from: https://www.alphavantage.co/support/#api-key

## Usage

### Running the Stock Analysis

The main execution command:
```bash
uv run run_crew
```

Or using crewAI:
```bash
crewai run
```

By default, this analyzes AAPL, TSLA, MSFT, and META stocks and provides investment recommendations.

### Modifying Stock Tickers

To analyze different stocks, edit `src/sp_stock_agent/config/tasks.yaml`:
```yaml
final_decision_task:
  description: >
    Use your stock analysis tool to evaluate YOUR_TICKERS_HERE. Summarize the recent 5-day performance.
```

### Available Commands

- **Run analysis:** `uv run run_crew`
- **Train agents:** `uv run train <iterations> <filename>`
- **Replay execution:** `uv run replay <task_id>`
- **Test execution:** `uv run test <iterations> <eval_llm>`

## Project Structure

```
QuantBot/
├── src/sp_stock_agent/
│   ├── config/
│   │   ├── agents.yaml      # Agent definitions
│   │   └── tasks.yaml       # Task configurations
│   ├── tools/
│   │   ├── alpha_vantage_api_tool.py  # Stock data fetching
│   │   ├── news_scraper_tool.py       # News analysis
│   │   └── sec_10k_tool.py            # SEC filing analysis
│   ├── crew.py              # Crew orchestration
│   ├── main.py              # Entry points
│   └── llms.py              # LLM configurations
├── pyproject.toml           # Project dependencies
├── .env                     # API keys (create this)
└── README.md
```

## How It Works

1. **Financial Analyst Agent**: Analyzes individual stocks based on recent price movements and volume
2. **Investment Advisor Agent**: Aggregates insights from analysts and provides final recommendations
3. **Alpha Vantage Tool**: Fetches 5-day OHLC data for specified tickers
4. **Output**: Generates markdown-formatted investment recommendations

## API Limitations

- Alpha Vantage free tier: 25 API calls per day
- Rate limit: 75 calls per minute (handled by the tool)

## Output

The analysis results are saved to: `data/generated/financial_repord.md`

The output file contains:
- Stock performance summaries
- Price movement analysis
- Investment recommendations (Yes/No)
- Reasoning for each recommendation

## Troubleshooting

1. **API Key Issues**: Ensure your `.env` file contains valid API keys
2. **Rate Limiting**: If you hit API limits, wait before retrying
3. **Python Version**: Ensure you're using Python 3.12 or 3.13
4. **Dependencies**: Run `uv pip install -e .` to ensure all dependencies are installed

## Advanced Configuration

- Modify `agents.yaml` to change agent roles and behaviors
- Edit `tasks.yaml` to customize analysis parameters
- Adjust `crew.py` for custom logic and tool integration

## Support

For issues and questions:
- Check the crewAI documentation: https://docs.crewai.com
- Visit the GitHub repository for issue tracking
- Join the crewAI Discord community

## License

This project is licensed under the MIT License - see the LICENSE file for details.
