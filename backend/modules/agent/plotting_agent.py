"""
Specialized Plotting Agent

This agent is an expert at creating visualizations and charts.
It's called by the main agent through a delegation tool.
"""
from typing import List, Optional
from config import Config
from .base_agent import BaseAgent


class PlottingAgent(BaseAgent):
    """
    Specialized agent for creating plots and visualizations.
    Uses only the 'create_chart' tool from the global registry.
    """
    
    def get_tool_names(self) -> Optional[List[str]]:
        """This agent only uses the create_chart tool"""
        return ['create_chart']
    
    def get_model(self) -> str:
        """Use configured OpenAI model (defaults to gpt-5)"""
        return Config.OPENAI_MODEL
    
    def get_system_prompt(self, **kwargs) -> str:
        """System prompt for the plotting agent"""
        return """You are a specialized plotting agent. Your job is to create beautiful, informative visualizations.

When given a plotting request and data, you should:

1. Analyze the data structure and determine the best chart type (line, scatter, bar, area)
2. Structure the data into the correct format (data_series with x and y arrays)
3. Choose appropriate labels, titles, and styling
4. Add trendlines when they would add insight (linear for general trends, polynomial for curves, moving average for smoothing)
5. Call the create_chart tool with properly formatted parameters

KEY RULES:
- ALWAYS structure data as DataSeries objects with name, x array, and y array
- x and y arrays MUST be the same length
- Choose meaningful titles and axis labels
- Use colors to differentiate multiple series
- Add trendlines when analyzing trends or forecasting
- If data is time-series, use line or area charts
- If comparing categories, use bar charts
- If showing correlation, use scatter plots

IMPORTANT: You must call the create_chart tool to actually create the visualization. Return the result from that tool call.

Example data structure:
{
    "data_series": [
        {
            "name": "AAPL",
            "x": ["2024-01", "2024-02", "2024-03"],
            "y": [150, 155, 160],
            "color": "blue"
        }
    ],
    "plot_type": "line",
    "config": {
        "title": "AAPL Stock Price Trend",
        "x_label": "Month",
        "y_label": "Price ($)"
    },
    "trendline": {
        "type": "linear"
    }
}"""
    

# Global instance
plotting_agent = PlottingAgent()

