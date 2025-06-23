#!/usr/bin/env python
import sys
import warnings

from datetime import datetime

from sp_stock_agent.crew import SpStockAgent



warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def run():
    """
    Run the crew.
    """
    inputs = {
        # These are the inputs for the yaml files that can be added if we use a {}

         'ticker' : 'SPY',
         'symbol' : 'SPY'
    }
    
    try:
        SpStockAgent().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


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

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        SpStockAgent().crew().replay(task_id=sys.argv[1])

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
