from crewai import Agent, Crew, Task, Process
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

from sp_stock_agent.tools.alpha_vantage_api_tool import FetchStockSummaryTool
from sp_stock_agent.tools.av_news_api_tool import NewsSentimentTool
# from sp_stock_agent.tools.serp_news_scraper import NewsSentimentTool as SerpNewsScraperTool
from sp_stock_agent.tools.av_earnings_transcript_api_tool import EarningsCallTranscriptTool
from sp_stock_agent.tools.sec_10k_tool import Sec10KTool
from sp_stock_agent.tools.serp_news_scraper import NewsScraperTool
from sp_stock_agent.tools.stock_selector import StockSelectorTool
from sp_stock_agent.tools.web_scraper_tool import WebScraperTool

from .tools import Sec10KTool, EarningsCallTranscriptTool, Chunked10KTool, NewsScraperTool, NewsSentimentTool, FetchStockSummaryTool
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
            tools=[FetchStockSummaryTool(), EarningsCallTranscriptTool(), Sec10KTool(), Chunked10KTool()],
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
<<<<<<< HEAD
=======
    
    @agent
    def web_analysis(self) -> Agent:
        return Agent(
            config=self.agents_config["web_analysis"],
            tools=[WebScraperTool()]
        )

    @task
    def web_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config["web_analysis_task"],
            agent=self.web_analysis(),
            output_file="data/generated/web_analysis.md",
        )
    
>>>>>>> bd7715325c54cb18a5f3b2481e79bec156807a23

    #@agent
    #def web_analysis(self) -> Agent:
    #    return Agent(
    #        config=self.agents_config["web_analysis"],
    #        tools=[WebScraperTool()]
    #    )

    #@task
    #def web_analysis_task(self) -> Task:
    #    return Task(
    #        config=self.tasks_config["web_analysis_task"],
    #        agent=self.web_analysis(),
    #        output_file="data/generated/web_analysis.md",
    #    )
    
    @agent 
    def research_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["research_analyst"]
        )
    
    @task 
    def research_analyst_task(self) -> Task:
        return Task(
            config=self.tasks_config["research_analyst_task"],
            output_file='data/generated/research_report.md',      
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
