from crewai import Agent, Crew, Task, Process
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

from .tools import Sec10KTool, EarningsCallTranscriptTool, ChunkedSEC10KTool, NewsScraperTool, NewsSentimentTool, FetchStockSummaryTool
from .llms import gpt_4_1
@CrewBase
class SpStockAgent():
    """SpStockAgent crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    def __init__(self):
        pass

    @agent
    def stock_data_collector(self) -> Agent:
        return Agent(
            config=self.agents_config["stock_data_collector"],
            tools=[FetchStockSummaryTool(), EarningsCallTranscriptTool(), Sec10KTool(), ChunkedSEC10KTool()],
            # llm=self.llm,
        )
    
    @task
    def stock_data_collector_task(self) -> Task:
        return Task(
            config=self.tasks_config["stock_data_collector_task"],
            agent=self.stock_data_collector()
        )
    

    @agent
    def news_analysis(self) -> Agent:
        return Agent(
            config=self.agents_config["news_analysis"],
            tools=[NewsSentimentTool(), NewsScraperTool()]
        )

    @task
    def news_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config["news_analysis_task"],
            agent=self.news_analysis(),
            output_file="data/generated/news_analysis.md",
        )
    

    @agent 
    def final_decision(self) -> Agent:
        return Agent(
            #This line calls the agent of final decision
            config=self.agents_config["final_decision"],           
            tools=[],
            # llm=self.llm,
			verbose=True,
			max_iter=4,
			allow_delegation=True
        )

    @task 
    def final_decision_task(self) -> Task:
        return Task(
            config=self.tasks_config['final_decision_task'],
            output_file='data/generated/financial_repord.md',      
            agent=self.final_decision()
        )


    # Initializing the crew and then calling it in main
    @crew
    def crew(self) -> Crew:

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.hierarchical,
            verbose=True,
            manager_llm=gpt_4_1,
            memory=True
        )
