from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

from sp_stock_agent.tools.alpha_vantage_api_tool import StockDataTool


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
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config['researcher'], # type: ignore[index]
            verbose=True
        )

    @agent
    def reporting_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['reporting_analyst'], # type: ignore[index]
            verbose=True
        )
    
    @agent 
    def financial_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["financial_analyst"],
            
            tools=[StockDataTool()],  # Pass an instance of your tool

            llm=self.llm,
			verbose=True,
			max_iter=4,
			allow_delegation=True

            # The parameter of get_daily... I put it in the main as that is how is passed
        )



    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def research_task(self) -> Task:
        return Task(
            config=self.tasks_config['research_task'], # type: ignore[index]
        )


    @task
    def reporting_task(self) -> Task:
        return Task(
            config=self.tasks_config['reporting_task'], # type: ignore[index]
            output_file='report.md'
        )

    @task 
    def financial_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['financial_analysis_task'],
            output_file='financial_repord.md',      
            agent=self.financial_analyst()           #I dont know if this is needed 
            
        )


    # @task
    # def market_prediction_task(self) -> Task:
    #     return Task(
    #         config=self.task_config['market_prediction_task'],
    #         ooutput_file='market_prediction_task.md',
    #         agent=agent            #I dont know if this is needed 
    #     )

    @crew
    def crew(self) -> Crew:
        """Creates the SpStockAgent crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.hierarchical,
            verbose=True,
            manager_llm=llm,
            memory=True
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
