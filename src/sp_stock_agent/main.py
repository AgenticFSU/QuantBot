#!/usr/bin/env python
import json
import sys
import warnings
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field
from crewai.flow.flow import Flow, listen, start
from datetime import datetime
from sp_stock_agent.crew import SpStockAgent
from .tools import Sec10KTool, StockSelectorTool

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# Define our flow state model
class StockAnalysisState(BaseModel):
    raw_tickers: List[str] = Field(default_factory=list, description="Raw ticker input from user")
    validated_tickers: List[str] = Field(default_factory=list, description="Validated stock tickers")

class StockAnalysisFlow(Flow[StockAnalysisState]):
    """Flow for analyzing stock tickers using SP Stock Agent crew"""

    @start()
    def get_tickers(self):
        """
        Get the tickers for the stocks that I want to analyze.
        """
        print("\n==Enter the ticker of the stock you want to analyze. You can input 0 to 5 tickers. ==\n")
        ticker_input = input("Enter tickers | space-separated e.g. META NFLX CSCO INTC or leave blank for random: ")
        
        try:
            tickers = ticker_input.split() if ticker_input.strip() else []
            if len(tickers) > 5:
                warnings.warn("You entered more than 5 tickers. Only the first 5 will be used.", UserWarning)
                tickers = tickers[:5]
            
            self.state.raw_tickers = tickers
            
            print(f"Received tickers: {self.state.raw_tickers}")
            return self.state.raw_tickers
            
        except ValueError as e:
            print(f"Error: {e}")
            return None

    @listen(get_tickers)
    def validate_tickers(self, raw_tickers):
        """Validate the tickers against the available tickers list"""
        print("Validating Tickers...")
        
        try:
            # Load available tickers
            with open("tickers.json", "r") as f:
                available_tickers = set(json.load(f))
            
            validated = []
            for ticker in raw_tickers:
                ticker_upper = ticker.upper()
                if ticker_upper in available_tickers:
                    validated.append(ticker_upper)
                    print(f"✓ {ticker_upper} is valid")
                else:
                    warnings.warn(f"Invalid ticker: {ticker_upper}. Ticker removed", UserWarning)

            if (len(validated) == 0):
                print("No valid tickers provided, using random selection")
                validated = StockSelectorTool()._run()
            
            self.state.validated_tickers = validated
            print(f"Final tickers: {self.state.validated_tickers}")
            return self.state.validated_tickers
            
        except FileNotFoundError:
            warnings.warn("tickers.json file not found. Proceeding with provided tickers.", UserWarning)
            self.state.validated_tickers = [t.upper() for t in raw_tickers]
            return self.state.validated_tickers
    
    @listen(get_tickers)
    def get_10K_document(self, validated_tickers):
        for ticker in validated_tickers:
            _ = Sec10KTool()._run(ticker)

    @listen(validate_tickers)
    def run_crew_analysis(self, validated_tickers):
        """
        Run the crew analysis with the validated tickers.
        """
        print(f"Starting stock analysis for: {validated_tickers}")
        
        # Prepare inputs for the crew
        crew_inputs = {
            "tickers": validated_tickers,
            "current_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        try:
            # Run the crew with the validated tickers
            result = SpStockAgent().crew().kickoff(inputs=crew_inputs)
            print("Stock analysis completed successfully!")
            return result
            
        except Exception as e:
            raise Exception(f"An error occurred while running the crew: {e}")

def run():
    """Run the stock analysis flow"""
    print("Starting Stock Analysis Flow...")
    flow = StockAnalysisFlow()
    result = flow.kickoff()
    print("\n=== Stock Analysis Flow Complete ===")
    return result

def plot():
    """Generate a visualization of the flow"""
    flow = StockAnalysisFlow()
    flow.plot("stock_analysis_flow")
    print("Flow visualization saved to stock_analysis_flow.html")

def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        "topic": "Quantum Computing Companies Profitability",
        'current_year': str(datetime.now().year)
    }
    try:
        SpStockAgent().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay(task_id):
    """
    Replay the crew execution from a specific task.
    """
    try:
        SpStockAgent().crew().replay(task_id=task_id)
    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        "topic": "Quantum Computing Companies Profitability",
        "current_year": str(datetime.now().year)
    }
    
    try:
        SpStockAgent().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")

if __name__ == "__main__":
    run()
