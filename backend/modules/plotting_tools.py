"""
Plotting tools for creating interactive charts and visualizations

Uses Plotly for interactive charts that can be rendered in the frontend.
These are LOW-LEVEL tools used by the plotting agent.
"""
from typing import List, Optional, Dict, Any, Literal, Union, Tuple
from pydantic import BaseModel, Field
from modules.tools import tool, ToolContext

try:
    import plotly.graph_objects as go
    import plotly.express as px
    import numpy as np
except ImportError:
    # Will be handled gracefully in tools
    pass

from datetime import datetime


class DataPoint(BaseModel):
    """A single data point for plotting"""
    x: Union[float, str, int]
    y: Union[float, str, int]


class DataSeries(BaseModel):
    """A series of data points for plotting"""
    name: str = Field(description="Name/label for this data series")
    x: List[Union[float, str, int]] = Field(description="X-axis values")
    y: List[Union[float, int]] = Field(description="Y-axis values")
    color: Optional[str] = Field(None, description="Color for this series (e.g., 'blue', '#FF5733', 'rgb(255,0,0)')")
    
    def validate_lengths(self):
        """Ensure x and y have the same length"""
        if len(self.x) != len(self.y):
            raise ValueError(f"x and y must have same length (x={len(self.x)}, y={len(self.y)})")


class TrendlineConfig(BaseModel):
    """Configuration for trendlines"""
    type: Literal["linear", "polynomial", "exponential", "moving_average"] = Field(
        "linear",
        description="Type of trendline to fit"
    )
    degree: Optional[int] = Field(
        2,
        description="Degree for polynomial trendline (only used if type='polynomial')"
    )
    window: Optional[int] = Field(
        5,
        description="Window size for moving average (only used if type='moving_average')"
    )


class PlotConfig(BaseModel):
    """Configuration for plot appearance"""
    title: str = Field(description="Plot title")
    x_label: Optional[str] = Field(None, description="X-axis label")
    y_label: Optional[str] = Field(None, description="Y-axis label")
    width: Optional[int] = Field(800, description="Plot width in pixels")
    height: Optional[int] = Field(600, description="Plot height in pixels")
    show_legend: bool = Field(True, description="Whether to show legend")
    grid: bool = Field(True, description="Whether to show grid")
    theme: Literal["light", "dark", "plotly", "seaborn"] = Field(
        "plotly",
        description="Visual theme for the plot"
    )


class CreatePlotParams(BaseModel):
    """Parameters for creating a plot"""
    data_series: List[DataSeries] = Field(
        description="List of data series to plot. Each series is a line/scatter/bar on the chart."
    )
    plot_type: Literal["line", "scatter", "bar", "area"] = Field(
        "line",
        description="Type of chart to create"
    )
    config: PlotConfig = Field(description="Plot configuration (title, labels, theme, etc.)")
    trendline: Optional[TrendlineConfig] = Field(
        None,
        description="Optional trendline configuration. If provided, adds a trendline to the first data series."
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "data_series": [
                    {
                        "name": "AAPL",
                        "x": [1, 2, 3, 4, 5],
                        "y": [150, 155, 153, 160, 165],
                        "color": "blue"
                    }
                ],
                "plot_type": "line",
                "config": {
                    "title": "AAPL Stock Price Over Time",
                    "x_label": "Day",
                    "y_label": "Price ($)"
                },
                "trendline": {
                    "type": "linear"
                }
            }
        }


def calculate_trendline(
    x: List[Union[float, str, int]],
    y: List[Union[float, int]],
    trendline_config: TrendlineConfig
) -> Tuple[List[float], List[float]]:
    """
    Calculate trendline points based on configuration
    
    Returns:
        Tuple of (x_trend, y_trend) for plotting
    """
    # Convert x to numeric if needed
    x_numeric = []
    for val in x:
        if isinstance(val, (int, float)):
            x_numeric.append(float(val))
        else:
            # Try to parse string dates or use index
            try:
                dt = datetime.fromisoformat(str(val).replace('Z', '+00:00'))
                x_numeric.append(dt.timestamp())
            except:
                x_numeric.append(float(len(x_numeric)))
    
    x_arr = np.array(x_numeric)
    y_arr = np.array(y, dtype=float)
    
    if trendline_config.type == "linear":
        # Linear regression
        coeffs = np.polyfit(x_arr, y_arr, 1)
        y_trend = np.polyval(coeffs, x_arr)
        return x_arr.tolist(), y_trend.tolist()
    
    elif trendline_config.type == "polynomial":
        # Polynomial regression
        degree = trendline_config.degree or 2
        coeffs = np.polyfit(x_arr, y_arr, degree)
        y_trend = np.polyval(coeffs, x_arr)
        return x_arr.tolist(), y_trend.tolist()
    
    elif trendline_config.type == "exponential":
        # Exponential fit: y = a * exp(b * x)
        try:
            log_y = np.log(y_arr)
            coeffs = np.polyfit(x_arr, log_y, 1)
            y_trend = np.exp(coeffs[1]) * np.exp(coeffs[0] * x_arr)
            return x_arr.tolist(), y_trend.tolist()
        except:
            # Fall back to linear if exponential fails
            coeffs = np.polyfit(x_arr, y_arr, 1)
            y_trend = np.polyval(coeffs, x_arr)
            return x_arr.tolist(), y_trend.tolist()
    
    elif trendline_config.type == "moving_average":
        # Moving average
        window = trendline_config.window or 5
        y_trend = np.convolve(y_arr, np.ones(window)/window, mode='valid')
        # Adjust x to match the convolution output size
        x_trend = x_arr[window-1:].tolist()
        return x_trend, y_trend.tolist()
    
    return x_arr.tolist(), y_arr.tolist()


def create_plot(params: CreatePlotParams) -> Dict[str, Any]:
    """
    Create an interactive plot using Plotly
    
    Args:
        params: Plot parameters (data, type, config, trendline)
        
    Returns:
        Dict containing:
        - success: bool
        - plotly_json: Plotly figure as JSON (for frontend rendering)
        - message: Optional message
    """
    try:
        # Validate all data series
        for series in params.data_series:
            series.validate_lengths()
        
        # Create figure
        fig = go.Figure()
        
        # Add each data series
        for i, series in enumerate(params.data_series):
            # Determine trace type
            if params.plot_type == "line":
                trace = go.Scatter(
                    x=series.x,
                    y=series.y,
                    mode='lines+markers',
                    name=series.name,
                    line=dict(color=series.color) if series.color else None,
                    marker=dict(size=6)
                )
            elif params.plot_type == "scatter":
                trace = go.Scatter(
                    x=series.x,
                    y=series.y,
                    mode='markers',
                    name=series.name,
                    marker=dict(
                        size=10,
                        color=series.color if series.color else None
                    )
                )
            elif params.plot_type == "bar":
                trace = go.Bar(
                    x=series.x,
                    y=series.y,
                    name=series.name,
                    marker=dict(color=series.color) if series.color else None
                )
            elif params.plot_type == "area":
                trace = go.Scatter(
                    x=series.x,
                    y=series.y,
                    mode='lines',
                    name=series.name,
                    fill='tozeroy',
                    line=dict(color=series.color) if series.color else None
                )
            
            fig.add_trace(trace)
            
            # Add trendline to first series if requested
            if i == 0 and params.trendline:
                x_trend, y_trend = calculate_trendline(
                    series.x,
                    series.y,
                    params.trendline
                )
                
                trendline_name = f"{series.name} - {params.trendline.type.title()} Trendline"
                fig.add_trace(go.Scatter(
                    x=x_trend,
                    y=y_trend,
                    mode='lines',
                    name=trendline_name,
                    line=dict(dash='dash', width=2),
                    opacity=0.7
                ))
        
        # Update layout
        template_map = {
            "light": "plotly_white",
            "dark": "plotly_dark",
            "plotly": "plotly",
            "seaborn": "seaborn"
        }
        
        fig.update_layout(
            title=dict(
                text=params.config.title,
                font=dict(size=20, family="Arial, sans-serif")
            ),
            xaxis_title=params.config.x_label or "",
            yaxis_title=params.config.y_label or "",
            width=params.config.width,
            height=params.config.height,
            showlegend=params.config.show_legend,
            template=template_map.get(params.config.theme, "plotly"),
            hovermode='x unified',
            xaxis=dict(showgrid=params.config.grid),
            yaxis=dict(showgrid=params.config.grid)
        )
        
        # Convert to JSON for frontend
        plotly_json = fig.to_json()
        
        return {
            "success": True,
            "plot_type": "plotly",
            "plotly_json": plotly_json,
            "title": params.config.title,
            "message": f"Created {params.plot_type} chart with {len(params.data_series)} series"
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to create plot: {str(e)}"
        }


# ============================================================================
# TOOLS FOR PLOTTING AGENT (not directly callable by main agent)
# ============================================================================

@tool(
    description="Create an interactive line, scatter, bar, or area chart. You MUST structure the data properly with x and y arrays. Optionally add trendlines (linear, polynomial, exponential, moving average). Returns a Plotly chart that will be displayed to the user.",
    category="plotting",
    requires_auth=False
)
async def create_chart(
    *,
    context: ToolContext,
    data_series: List[Dict[str, Any]],
    plot_type: str = "line",
    config: Optional[Dict[str, Any]] = None,
    trendline: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create an interactive chart with optional trendlines
    
    Args:
        data_series: List of data series, each with name, x array, y array, and optional color
        plot_type: Type of chart (line, scatter, bar, area)
        config: Plot configuration with title, x_label, y_label, etc.
        trendline: Optional trendline config with type (linear, polynomial, etc.)
    """
    try:
        # Set default config if not provided
        if config is None:
            config = {"title": "Chart"}
        
        # Create figure directly from dicts
        fig = go.Figure()
        
        # Add each data series
        for i, series in enumerate(data_series):
            name = series.get("name", f"Series {i+1}")
            x = series.get("x", [])
            y = series.get("y", [])
            color = series.get("color")
            
            # Validate lengths
            if len(x) != len(y):
                return {
                    "success": False,
                    "message": f"Series '{name}': x and y arrays must have same length (x={len(x)}, y={len(y)})"
                }
            
            # Determine trace type
            if plot_type == "line":
                trace = go.Scatter(
                    x=x, y=y, mode='lines+markers', name=name,
                    line=dict(color=color) if color else None,
                    marker=dict(size=6)
                )
            elif plot_type == "scatter":
                trace = go.Scatter(
                    x=x, y=y, mode='markers', name=name,
                    marker=dict(size=10, color=color if color else None)
                )
            elif plot_type == "bar":
                trace = go.Bar(x=x, y=y, name=name, marker=dict(color=color) if color else None)
            elif plot_type == "area":
                trace = go.Scatter(
                    x=x, y=y, mode='lines', name=name, fill='tozeroy',
                    line=dict(color=color) if color else None
                )
            else:
                return {
                    "success": False,
                    "message": f"Invalid plot_type '{plot_type}'. Must be: line, scatter, bar, or area"
                }
            
            fig.add_trace(trace)
            
            # Add trendline to first series if requested
            if i == 0 and trendline:
                trendline_type = trendline.get("type", "linear")
                trendline_config = TrendlineConfig(
                    type=trendline_type,
                    degree=trendline.get("degree", 2),
                    window=trendline.get("window", 5)
                )
                x_trend, y_trend = calculate_trendline(x, y, trendline_config)
                
                fig.add_trace(go.Scatter(
                    x=x_trend, y=y_trend, mode='lines',
                    name=f"{name} - {trendline_type.title()} Trendline",
                    line=dict(dash='dash', width=2),
                    opacity=0.7
                ))
        
        # Update layout
        template_map = {"light": "plotly_white", "dark": "plotly_dark", "plotly": "plotly", "seaborn": "seaborn"}
        
        fig.update_layout(
            title=dict(text=config.get("title", "Chart"), font=dict(size=20, family="Arial, sans-serif")),
            xaxis_title=config.get("x_label", ""),
            yaxis_title=config.get("y_label", ""),
            width=config.get("width", 800),
            height=config.get("height", 600),
            showlegend=config.get("show_legend", True),
            template=template_map.get(config.get("theme", "plotly"), "plotly"),
            hovermode='x unified',
            xaxis=dict(showgrid=config.get("grid", True)),
            yaxis=dict(showgrid=config.get("grid", True))
        )
        
        # Convert to JSON for frontend
        plotly_json = fig.to_json()
        
        return {
            "success": True,
            "plot_type": "plotly",
            "plotly_json": plotly_json,
            "title": config.get("title", "Chart"),
            "message": f"Created {plot_type} chart with {len(data_series)} series"
        }
    
    except ImportError:
        return {
            "success": False,
            "message": "Plotly library not installed. Please install: pip install plotly numpy"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Chart creation failed: {str(e)}"
        }

