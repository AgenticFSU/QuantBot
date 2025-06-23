from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

from sp_stock_agent.tools.alpha_vantage_api_tool import StockDataTool
from sp_stock_agent.tools.sec_10k_tool import SEC10KSummaryTool

from .llms import gpt_4o, gpt_3_5_turbo, gpt_o4_mini

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
        self.llm = gpt_3_5_turbo
        
    
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
            output_file='data/generated/financial_repord.md',      
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
            manager_llm=gpt_3_5_turbo,
            memory=True
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
