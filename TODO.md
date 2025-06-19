# Also I can use a final decision task and agent, that after all the information given
# It decides in what of the S&P 500 should invest 



# PROBLEM: Whenever we load to much info into a json and feed it into the AI it says that there is too much input 
# PROBLEM: We can only use 100 api calls to AV tool 

# So whenever I want to ask a question like in which stock should I invest instead of giving them two jsons, one that contains # the financial report and then another one that contains the alpha vantage values we can integrate it in one json.

# Instead of calling multiple tools (e.g., Alpha Vantage and financial reports) separately and combining results later,
# we create a single JSON structure for each stock that contains all relevant information in one place.
# This way, whenever we want to analyze or make decisions (e.g., "Which stock should I invest in?"),
# we can work with a unified JSON per stock that includes both price data and financial metrics.





# would it not be a concern in the future that we pass to much information?
# I guess not becuase each of them will have their individuall statement 


# In the future, we can implement it also with claude Desktop, so it can be passed all this information to it.


# TODO IN THE FUTURE 

# Yes, that's correct!
# The output you received is a generic summary based only on daily price data (open, high, low, close, volume). For a comprehensive financial analysis of SPY (or any stock), you would typically need:

# Recent earnings reports (EPS, revenue, profit margins)
# Balance sheet data (assets, liabilities, equity)
# Cash flow statements
# Key financial ratios (P/E, P/B, ROE, etc.)
# Recent news and macroeconomic factors
# Analyst sentiment and consensus
# Industry/sector trends
# The daily OHLC data is useful for technical analysis and short-term trends,
# but for a full financial analysis, you need to supplement with the above data.

# What you can do next:
# Integrate additional API calls (e.g., Alpha Vantage's "EARNINGS", "BALANCE_SHEET", "INCOME_STATEMENT" endpoints).
# Add news and analyst sentiment sources.
# Pass this extra data to your agent for richer, more actionable analysis.
# Summary:
# Yes, to get a truly valuable financial analysis, you should feed your agent more detailed financial and fundamental data—not just price history.







# I think that jacobs script does not work because you need the @tool at the beginning, maybe one of the reasons why it does not
# give any decisions