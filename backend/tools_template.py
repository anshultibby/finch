"""
Template for adding tool calls to the Finch agent

This file shows how to integrate Robinhood API with tool calling.
Uncomment and modify as needed when ready to add portfolio functionality.
"""

# Uncomment to use:
# import robin_stocks.robinhood as rh
# import os

# Tool definitions for Anthropic Claude
PORTFOLIO_TOOLS = [
    {
        "name": "get_portfolio",
        "description": "Get the user's current portfolio holdings including stocks, quantities, and current values",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_stock_quote",
        "description": "Get real-time quote data for a stock symbol including current price, change, and volume",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "The stock ticker symbol (e.g., 'AAPL', 'TSLA')"
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_portfolio_performance",
        "description": "Get portfolio performance metrics including total value, gains/losses, and returns",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["day", "week", "month", "3month", "year", "all"],
                    "description": "Time period for performance calculation"
                }
            },
            "required": ["period"]
        }
    },
    {
        "name": "search_stocks",
        "description": "Search for stocks by company name or ticker symbol",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Company name or partial ticker to search for"
                }
            },
            "required": ["query"]
        }
    },
]


class PortfolioTools:
    """Handler for portfolio-related tool calls"""
    
    def __init__(self):
        # Uncomment to initialize Robinhood connection
        # self.login()
        pass
    
    def login(self):
        """Login to Robinhood"""
        # username = os.getenv("ROBINHOOD_USERNAME")
        # password = os.getenv("ROBINHOOD_PASSWORD")
        # rh.login(username, password)
        pass
    
    def get_portfolio(self):
        """Get current portfolio holdings"""
        # holdings = rh.build_holdings()
        # return {
        #     "success": True,
        #     "holdings": holdings
        # }
        return {
            "success": False,
            "message": "Portfolio tools not yet configured"
        }
    
    def get_stock_quote(self, symbol: str):
        """Get stock quote"""
        # quote = rh.get_latest_price(symbol)[0]
        # fundamentals = rh.get_fundamentals(symbol)[0]
        # return {
        #     "success": True,
        #     "symbol": symbol,
        #     "price": quote,
        #     "fundamentals": fundamentals
        # }
        return {
            "success": False,
            "message": "Stock quote tool not yet configured"
        }
    
    def get_portfolio_performance(self, period: str):
        """Get portfolio performance"""
        # profile = rh.load_portfolio_profile()
        # historicals = rh.get_historical_portfolio(interval='day', span=period)
        # return {
        #     "success": True,
        #     "period": period,
        #     "data": historicals
        # }
        return {
            "success": False,
            "message": "Performance tool not yet configured"
        }
    
    def search_stocks(self, query: str):
        """Search for stocks"""
        # results = rh.get_instruments_by_symbols(query)
        # return {
        #     "success": True,
        #     "results": results
        # }
        return {
            "success": False,
            "message": "Search tool not yet configured"
        }
    
    def execute_tool(self, tool_name: str, tool_input: dict):
        """Execute a tool by name"""
        tool_map = {
            "get_portfolio": self.get_portfolio,
            "get_stock_quote": self.get_stock_quote,
            "get_portfolio_performance": self.get_portfolio_performance,
            "search_stocks": self.search_stocks,
        }
        
        if tool_name in tool_map:
            return tool_map[tool_name](**tool_input)
        else:
            return {"error": f"Unknown tool: {tool_name}"}


# To integrate with agent.py:
"""
1. Import this module in agent.py:
   from tools_template import PORTFOLIO_TOOLS, PortfolioTools

2. Initialize tools in ChatAgent.__init__:
   self.tools = PortfolioTools()

3. Add tools to Claude API call:
   response = self.client.messages.create(
       model=self.model,
       max_tokens=2048,
       system=self.system_prompt,
       messages=messages,
       tools=PORTFOLIO_TOOLS  # Add this
   )

4. Handle tool calls in the response:
   if response.stop_reason == "tool_use":
       for content in response.content:
           if content.type == "tool_use":
               result = self.tools.execute_tool(
                   content.name,
                   content.input
               )
               # Continue conversation with tool result
"""

