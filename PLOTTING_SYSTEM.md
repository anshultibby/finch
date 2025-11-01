# Plotting System - Agent Delegation Pattern

## Overview

The plotting system uses an **agent delegation pattern** where the main agent delegates visualization tasks to a specialized plotting sub-agent.

## Architecture

```
User → Main Agent → create_plot (delegation tool) → Plotting Agent → create_chart (plotting tool) → Plotly JSON → Frontend
```

### Components

1. **Low-level Tools** (`modules/plotting_tools.py`)
   - `create_chart` - Creates Plotly charts with trendlines
   - Pydantic models for type-safe parameters
   - Registered in PlottingAgent's tool registry

2. **Plotting Agent** (`modules/agent/plotting_agent.py`)
   - Inherits from `BaseAgent`
   - Has its own tool registry (only plotting tools)
   - System prompt gives it plotting expertise
   - **No custom methods** - uses base class `run_tool_loop()`

3. **Delegation Tool** (`modules/tool_definitions.py`)
   - `create_plot` - Main agent calls this
   - Builds messages and invokes plotting agent
   - Plotting agent automatically calls its tools via BaseAgent

4. **Frontend Rendering** (`components/ResourceViewer.tsx`)
   - Plotly.js integration
   - Interactive charts with zoom, pan, hover

## Installation

### Backend
```bash
cd backend
pip install -r requirements.txt
```

### Frontend
```bash
cd frontend
npm install
```

## Usage Examples

### Example 1: Simple Line Chart
```
User: "Plot AAPL stock prices: Jan=$150, Feb=$155, Mar=$160"

Main Agent calls create_plot with:
{
  "objective": "Create a line chart showing AAPL stock price trend",
  "data": {
    "months": ["Jan", "Feb", "Mar"],
    "prices": [150, 155, 160]
  }
}

Plotting Agent creates chart with linear trendline
```

### Example 2: Portfolio Comparison
```
User: "Compare my portfolio stocks as a bar chart"

Main Agent:
1. Calls get_portfolio() to get holdings
2. Calls create_plot with portfolio data
3. Plotting agent creates bar chart comparing positions
```

### Example 3: Trendline Analysis
```
User: "Show me senate trades over time with a polynomial trendline"

Main Agent:
1. Calls get_recent_senate_trades()
2. Calls create_plot with trades data
3. Plotting agent adds polynomial trendline for trend analysis
```

## Tool Parameters

### create_plot (Main Agent Tool)

```python
{
  "objective": str,  # What to visualize
  "data": dict       # Optional raw data
}
```

### create_chart (Plotting Agent Tool)

```python
{
  "data_series": [    # Multiple series supported
    {
      "name": str,
      "x": [values],
      "y": [values],
      "color": str    # Optional
    }
  ],
  "plot_type": "line" | "scatter" | "bar" | "area",
  "config": {
    "title": str,
    "x_label": str,
    "y_label": str,
    "width": int,
    "height": int,
    "theme": "light" | "dark" | "plotly" | "seaborn"
  },
  "trendline": {      # Optional
    "type": "linear" | "polynomial" | "exponential" | "moving_average",
    "degree": int,    # For polynomial
    "window": int     # For moving average
  }
}
```

## Features

✅ **Interactive Charts**
- Zoom, pan, hover
- Export as PNG
- Responsive design

✅ **Trendlines**
- Linear regression
- Polynomial fitting
- Exponential curves
- Moving averages

✅ **Chart Types**
- Line charts (time series)
- Scatter plots (correlation)
- Bar charts (comparison)
- Area charts (cumulative)

✅ **Multiple Series**
- Compare multiple datasets
- Color-coded legends
- Overlay support

## Why Agent Delegation?

1. **Separation of Concerns**
   - Main agent: Decides WHEN to plot
   - Plotting agent: Decides HOW to plot

2. **Specialized Expertise**
   - Plotting agent has domain knowledge
   - Optimal chart type selection
   - Smart data structuring

3. **Extensibility**
   - Easy to add more plotting tools
   - Can add data transformation tools
   - Independent evolution

4. **Clean Interface**
   - Main agent uses simple `create_plot` tool
   - Complexity hidden in plotting agent
   - User-friendly objective-based API

## Extending the System

### Add More Plotting Tools

```python
@tool(
    description="Transform data for optimal plotting",
    category="plotting"
)
async def transform_data(*, context: ToolContext, ...):
    # Data transformation logic
    pass

# Register in PlottingAgent
plotting_agent.tool_registry.register_function(transform_data)
```

### Add More Chart Types

Update `create_chart` tool to support:
- Heatmaps
- 3D plots
- Candlestick charts
- Sankey diagrams

### Improve Plotting Agent Prompts

Modify `plotting_agent.py` system prompt to:
- Detect outliers
- Suggest best practices
- Auto-scale axes
- Add annotations

## Testing

```python
# Test plotting agent directly
from modules.agent.plotting_agent import plotting_agent

result = await plotting_agent.create_plot(
    objective="Create a line chart with trendline",
    data={
        "x": [1, 2, 3, 4, 5],
        "y": [10, 12, 15, 11, 18]
    }
)

print(result)  # Contains plotly_json
```

## Troubleshooting

### Chart Not Rendering
- Check browser console for Plotly errors
- Verify `resource_type === 'plot'`
- Confirm `plotly_json` in resource data

### Trendline Issues
- Ensure x and y same length
- Check for NaN/null values
- Try different trendline types

### Agent Not Creating Chart
- Check plotting agent logs
- Verify data structure
- Ensure create_chart tool registered

## Performance

- Charts render client-side (no server load)
- Plotly JSON ~5-50KB typical
- Interactive without re-rendering
- Caches well for fast loading

## Future Enhancements

- [ ] Multi-panel plots (subplots)
- [ ] Real-time streaming plots
- [ ] Statistical annotations
- [ ] Custom color schemes
- [ ] Export to SVG/PDF
- [ ] 3D visualizations
- [ ] Animation support

