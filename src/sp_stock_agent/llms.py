"""
This module centralizes the configuration of various Language Learning Models (LLMs)
used throughout the application. It provides pre-configured instances of LLMs
from different providers like OpenAI, Google, Mistral, and local Ollama models.

This setup allows for easy swapping of LLMs and keeps the model configuration
separate from the agent and task definitions.

To use an LLM from this module, simply import the desired instance, for example:
`from sp_stock_agent.config.llms import gpt_4o`
"""

import os
from crewai import LLM

gpt_4_1 = LLM(
    model="openai/gpt-4.1",
    temperature=0.2
)
# --- Ollama Models ---
# Requires Ollama to be running locally.
# Download and run Ollama from https://ollama.com/
# To pull a model, run `ollama pull <model_name>` in your terminal.
# Example: `ollama pull llama3` or `ollama pull mistral`

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

try:
    from langchain_community.chat_models import Ollama
    # Check if Ollama is running, but don't fail if it's not.
    ollama_llama3 = Ollama(model="llama3", base_url=OLLAMA_BASE_URL)
    ollama_mistral = Ollama(model="mistral", base_url=OLLAMA_BASE_URL)
except Exception as e:
    print(f"Ollama models could not be initialized. Make sure Ollama is installed and instance at {OLLAMA_BASE_URL} is running. Error: {e}")
    ollama_llama3 = None
    ollama_mistral = None
