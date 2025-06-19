from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

from sp_stock_agent.tools.alpha_vantage_api_tool import StockDataTool
from sp_stock_agent.tools.sec_10k_tool import SEC10KSummaryTool


#All of these imports are for the ones before the Class start 
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from langchain_openai import ChatOpenAI

agent_llm = ChatOpenAI(temperature=0, model='gpt-3.5-turbo')


env_path = Path(__file__).resolve().parents[2] / '.env'
load_dotenv(dotenv_path=env_path)

openai_api_key = os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    raise ValueError("OPENAI_API_KEY is not set in your environment or .env file.")

llm = ChatOpenAI(
    temperature=0,
    model="gpt-3.5-turbo",
    openai_api_key=openai_api_key
)

@CrewBase
class SpStockAgent():
    """SpStockAgent crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    
    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools

    def __init__(self):
        self.llm = agent_llm    #Ollama(model=os.environ['MODEL'])lama(model=os.environ['MODEL'])

    
    @agent 
    def final_decision(self) -> Agent:
        return Agent(
            #This line calls the agent of final decision
            config=self.agents_config["final_decision"],
            
            tools=[StockDataTool(), SEC10KSummaryTool()],  # Pass an instance of your tool

            llm=self.llm,
			verbose=True,
			max_iter=4,
			allow_delegation=True
        )



    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task


    @task 
    def final_decision_task(self) -> Task:
        return Task(
            config=self.tasks_config['final_decision_task'],
            output_file='financial_repord.md',      
            agent=self.final_decision()         # This is needed to link the task and the agents
            
        )


    # Initializing the crew and then calling it in main
    @crew
    def crew(self) -> Crew:

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.hierarchical,
            verbose=True,
            manager_llm=llm,
            memory=True
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
