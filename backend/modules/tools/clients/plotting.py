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
    height: Optional[int] = Field(500, description="Plot height in pixels")
    show_legend: bool = Field(True, description="Whether to show legend")
    grid: bool = Field(False, description="Whether to show grid (minimal design = no grid by default)")
    theme: Literal["light", "dark", "plotly", "seaborn"] = Field(
        "light",
        description="Visual theme for the plot (light recommended for clean look)"
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
        
        # Add each data series with minimal, beautiful styling
        for i, series in enumerate(params.data_series):
            # Determine trace type
            if params.plot_type == "line":
                trace = go.Scatter(
                    x=series.x,
                    y=series.y,
                    mode='lines+markers',
                    name=series.name,
                    line=dict(
                        color=series.color if series.color else None,
                        width=2.5  # Slightly thicker for visibility
                    ),
                    marker=dict(
                        size=5,  # Smaller markers for minimal look
                        color=series.color if series.color else None,
                        line=dict(width=0)  # No marker borders
                    )
                )
            elif params.plot_type == "scatter":
                trace = go.Scatter(
                    x=series.x,
                    y=series.y,
                    mode='markers',
                    name=series.name,
                    marker=dict(
                        size=8,  # Refined size
                        color=series.color if series.color else None,
                        opacity=0.7,  # Slight transparency
                        line=dict(width=0)  # No borders for clean look
                    )
                )
            elif params.plot_type == "bar":
                trace = go.Bar(
                    x=series.x,
                    y=series.y,
                    name=series.name,
                    marker=dict(
                        color=series.color if series.color else None,
                        line=dict(width=0),  # No bar borders
                        opacity=0.85  # Slight transparency for modern look
                    )
                )
            elif params.plot_type == "area":
                # Parse hex color to rgba for fill
                fill_color = None
                if series.color and series.color.startswith('#') and len(series.color) == 7:
                    r = int(series.color[1:3], 16)
                    g = int(series.color[3:5], 16)
                    b = int(series.color[5:7], 16)
                    fill_color = f"rgba({r}, {g}, {b}, 0.2)"
                
                trace = go.Scatter(
                    x=series.x,
                    y=series.y,
                    mode='lines',
                    name=series.name,
                    fill='tozeroy',
                    line=dict(
                        color=series.color if series.color else None,
                        width=2
                    ),
                    fillcolor=fill_color
                )
            
            fig.add_trace(trace)
            
            # Add trendline to first series if requested
            if i == 0 and params.trendline:
                x_trend, y_trend = calculate_trendline(
                    series.x,
                    series.y,
                    params.trendline
                )
                
                trendline_name = f"{params.trendline.type.title()} Trend"
                fig.add_trace(go.Scatter(
                    x=x_trend,
                    y=y_trend,
                    mode='lines',
                    name=trendline_name,
                    line=dict(
                        dash='dot',  # Dotted line for subtlety
                        width=2,
                        color='#9CA3AF'  # Neutral gray
                    ),
                    opacity=0.6,
                    showlegend=True
                ))
        
        # Update layout with beautiful, minimal styling
        template_map = {
            "light": "plotly_white",
            "dark": "plotly_dark",
            "plotly": "plotly_white",  # Default to white for cleaner look
            "seaborn": "seaborn"
        }
        
        fig.update_layout(
            # Title styling - clean and prominent
            title=dict(
                text=params.config.title,
                font=dict(
                    size=22,
                    family="Inter, system-ui, -apple-system, sans-serif",
                    color="#1F2937",
                    weight=600
                ),
                x=0.02,  # Left-align title for modern look
                xanchor='left',
                y=0.98,
                yanchor='top',
                pad=dict(b=10)
            ),
            # Axis labels - subtle but clear
            xaxis_title=dict(
                text=params.config.x_label or "",
                font=dict(size=13, family="Inter, system-ui, sans-serif", color="#6B7280")
            ),
            yaxis_title=dict(
                text=params.config.y_label or "",
                font=dict(size=13, family="Inter, system-ui, sans-serif", color="#6B7280")
            ),
            # Size
            width=params.config.width,
            height=params.config.height,
            # Legend - minimal and clean
            showlegend=params.config.show_legend,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=12, family="Inter, system-ui, sans-serif"),
                bgcolor="rgba(255, 255, 255, 0.8)",
                bordercolor="rgba(0, 0, 0, 0.1)",
                borderwidth=1
            ),
            # Theme
            template=template_map.get(params.config.theme, "plotly_white"),
            # Interaction
            hovermode='x unified',
            # Axes styling - minimal and clean
            xaxis=dict(
                showgrid=params.config.grid,
                gridcolor='rgba(0, 0, 0, 0.05)',
                showline=True,
                linewidth=1,
                linecolor='rgba(0, 0, 0, 0.1)',
                tickfont=dict(size=11, color="#6B7280"),
                zeroline=False
            ),
            yaxis=dict(
                showgrid=params.config.grid,
                gridcolor='rgba(0, 0, 0, 0.05)',
                showline=True,
                linewidth=1,
                linecolor='rgba(0, 0, 0, 0.1)',
                tickfont=dict(size=11, color="#6B7280"),
                zeroline=True,
                zerolinecolor='rgba(0, 0, 0, 0.1)',
                zerolinewidth=1
            ),
            # Margins - more breathing room
            margin=dict(l=60, r=30, t=80, b=50),
            # Paper and plot background
            paper_bgcolor='white',
            plot_bgcolor='white'
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

class CreateChartParams(BaseModel):
    """Parameters for creating a chart"""
    data_series: List[Dict[str, Any]] = Field(
        description="List of data series. Each series must have: name (str), x (array), y (array), and optional color (str)"
    )
    plot_type: str = Field(
        default="line",
        description="Type of chart: line, scatter, bar, or area"
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Plot configuration with title, x_label, y_label, width, height, etc."
    )
    trendline: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional trendline config with type (linear, polynomial, exponential, moving_average)"
    )


@tool(
    description="Create an interactive line, scatter, bar, or area chart. You MUST structure the data properly with x and y arrays. Optionally add trendlines (linear, polynomial, exponential, moving average). The chart will be automatically saved as a resource and displayed to the user in the resources sidebar. Returns the resource ID for future reference.",
    category="plotting",
    requires_auth=False
)
async def create_chart(
    *,
    context: ToolContext,
    params: CreateChartParams
) -> Dict[str, Any]:
    """
    Create an interactive chart with optional trendlines
    
    Args:
        context: Tool context with resource_manager
        params: Chart parameters including data_series, plot_type, config, and optional trendline
    
    Returns:
        Result with resource_id for the created chart
    """
    try:
        # Extract parameters
        data_series = params.data_series
        plot_type = params.plot_type
        config = params.config or {"title": "Chart"}
        trendline = params.trendline
        
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
            
            # Determine trace type with beautiful, minimal styling
            if plot_type == "line":
                trace = go.Scatter(
                    x=x, y=y, mode='lines+markers', name=name,
                    line=dict(
                        color=color if color else None,
                        width=2.5
                    ),
                    marker=dict(
                        size=5,
                        color=color if color else None,
                        line=dict(width=0)
                    )
                )
            elif plot_type == "scatter":
                trace = go.Scatter(
                    x=x, y=y, mode='markers', name=name,
                    marker=dict(
                        size=8,
                        color=color if color else None,
                        opacity=0.7,
                        line=dict(width=0)
                    )
                )
            elif plot_type == "bar":
                trace = go.Bar(
                    x=x, y=y, name=name,
                    marker=dict(
                        color=color if color else None,
                        line=dict(width=0),
                        opacity=0.85
                    )
                )
            elif plot_type == "area":
                # Parse hex color to rgba for fill
                fill_color = None
                if color and color.startswith('#') and len(color) == 7:
                    r = int(color[1:3], 16)
                    g = int(color[3:5], 16)
                    b = int(color[5:7], 16)
                    fill_color = f"rgba({r}, {g}, {b}, 0.2)"
                
                trace = go.Scatter(
                    x=x, y=y, mode='lines', name=name, fill='tozeroy',
                    line=dict(color=color if color else None, width=2),
                    fillcolor=fill_color
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
                    name=f"{trendline_type.title()} Trend",
                    line=dict(
                        dash='dot',
                        width=2,
                        color='#9CA3AF'
                    ),
                    opacity=0.6
                ))
        
        # Update layout with beautiful, minimal styling
        template_map = {"light": "plotly_white", "dark": "plotly_dark", "plotly": "plotly_white", "seaborn": "seaborn"}
        
        fig.update_layout(
            # Title styling - clean and prominent
            title=dict(
                text=config.get("title", "Chart"),
                font=dict(
                    size=22,
                    family="Inter, system-ui, -apple-system, sans-serif",
                    color="#1F2937",
                    weight=600
                ),
                x=0.02,
                xanchor='left',
                y=0.98,
                yanchor='top',
                pad=dict(b=10)
            ),
            # Axis labels - subtle but clear
            xaxis_title=dict(
                text=config.get("x_label", ""),
                font=dict(size=13, family="Inter, system-ui, sans-serif", color="#6B7280")
            ),
            yaxis_title=dict(
                text=config.get("y_label", ""),
                font=dict(size=13, family="Inter, system-ui, sans-serif", color="#6B7280")
            ),
            # Size
            width=config.get("width", 800),
            height=config.get("height", 500),
            # Legend - minimal and clean
            showlegend=config.get("show_legend", True),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=12, family="Inter, system-ui, sans-serif"),
                bgcolor="rgba(255, 255, 255, 0.8)",
                bordercolor="rgba(0, 0, 0, 0.1)",
                borderwidth=1
            ),
            # Theme
            template=template_map.get(config.get("theme", "light"), "plotly_white"),
            # Interaction
            hovermode='x unified',
            # Axes styling - minimal and clean
            xaxis=dict(
                showgrid=config.get("grid", False),
                gridcolor='rgba(0, 0, 0, 0.05)',
                showline=True,
                linewidth=1,
                linecolor='rgba(0, 0, 0, 0.1)',
                tickfont=dict(size=11, color="#6B7280"),
                zeroline=False
            ),
            yaxis=dict(
                showgrid=config.get("grid", False),
                gridcolor='rgba(0, 0, 0, 0.05)',
                showline=True,
                linewidth=1,
                linecolor='rgba(0, 0, 0, 0.1)',
                tickfont=dict(size=11, color="#6B7280"),
                zeroline=True,
                zerolinecolor='rgba(0, 0, 0, 0.1)',
                zerolinewidth=1
            ),
            # Margins - more breathing room
            margin=dict(l=60, r=30, t=80, b=50),
            # Paper and plot background
            paper_bgcolor='white',
            plot_bgcolor='white'
        )
        
        # Convert to JSON for frontend
        plotly_json = fig.to_json()
        
        # Create resource in database directly
        resource_id = None
        title = config.get("title", "Chart")
        
        # Check if we have chat_id and user_id to create resource
        print(f"🔍 Resource creation check - chat_id: {context.chat_id}, user_id: {context.user_id}", flush=True)
        
        if context.chat_id and context.user_id:
            from crud import resource as resource_crud
            from database import SessionLocal
            
            try:
                with SessionLocal() as db:
                    db_resource = resource_crud.create_resource(
                        db=db,
                        chat_id=context.chat_id,
                        user_id=context.user_id,
                        tool_name="create_chart",
                        resource_type="plot",
                        title=title,
                        data={
                            "plot_type": "plotly",
                            "plotly_json": plotly_json
                        },
                        resource_metadata={
                            "plot_type": plot_type,
                            "series_count": len(data_series),
                            "config": config
                        }
                    )
                    resource_id = db_resource.id
                    print(f"📊 Created chart resource in DB: {resource_id}", flush=True)
            except Exception as e:
                print(f"⚠️ Failed to create resource in DB: {e}", flush=True)
                import traceback
                print(f"⚠️ Traceback: {traceback.format_exc()}", flush=True)
        else:
            print(f"⚠️ Cannot create resource - missing chat_id or user_id in context", flush=True)
        
        return {
            "success": True,
            "resource_id": resource_id,
            "plot_type": "plotly",
            "resource_type": "plot",
            "plotly_json": plotly_json,
            "title": title,
            "message": f"Created {plot_type} chart with {len(data_series)} series" + (f". Resource ID: {resource_id}" if resource_id else "")
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


class PlotFromResourceParams(BaseModel):
    """Parameters for plotting data from an existing resource"""
    resource_id: str = Field(
        description="ID of the resource to plot. Must be a data resource (portfolio, trades, etc.)"
    )
    x_field: str = Field(
        description="Field name to use for x-axis (e.g., 'date', 'ticker', 'name')"
    )
    y_field: str = Field(
        description="Field name to use for y-axis (e.g., 'price', 'value', 'volume')"
    )
    plot_type: str = Field(
        default="bar",
        description="Type of chart: line, scatter, bar, or area"
    )
    title: Optional[str] = Field(
        None,
        description="Chart title (auto-generated if not provided)"
    )
    x_label: Optional[str] = Field(None, description="X-axis label")
    y_label: Optional[str] = Field(None, description="Y-axis label")
    group_by: Optional[str] = Field(
        None,
        description="Optional field to group data by (creates multiple series)"
    )
    limit: Optional[int] = Field(
        None,
        description="Limit number of data points to plot (useful for large datasets)"
    )


@tool(
    description="Create a chart from an existing resource by ID. Use this to visualize data from portfolio, trades, or other table resources. You can specify which fields to use for x and y axes, and optionally group data into multiple series. Returns a new chart resource.",
    category="plotting",
    requires_auth=False
)
async def plot_from_resource(
    *,
    context: ToolContext,
    params: PlotFromResourceParams
) -> Dict[str, Any]:
    """
    Create a chart from an existing resource
    
    Args:
        context: Tool context with resource_manager
        params: Parameters specifying which resource to plot and how
    
    Returns:
        Result with new chart resource_id
    """
    try:
        # Get the resource from database
        if not context.resource_manager:
            return {
                "success": False,
                "message": "Resource manager not available"
            }
        
        from database import SessionLocal
        
        resource_data = None
        with SessionLocal() as db:
            resource_data = context.resource_manager.get_resource(params.resource_id, db=db)
        
        if not resource_data:
            return {
                "success": False,
                "message": f"Resource not found: {params.resource_id}"
            }
        
        # Extract data array from resource
        data_array = None
        resource = resource_data["data"]  # Get the data field
        if isinstance(resource, dict):
            if "data" in resource and isinstance(resource["data"], list):
                data_array = resource["data"]
            elif isinstance(resource.get("holdings"), list):
                data_array = resource["holdings"]
            elif isinstance(resource.get("trades"), list):
                data_array = resource["trades"]
        elif isinstance(resource, list):
            data_array = resource
        
        if not data_array:
            return {
                "success": False,
                "message": f"Could not extract data array from resource {params.resource_id}"
            }
        
        # Limit data if requested
        if params.limit and len(data_array) > params.limit:
            data_array = data_array[:params.limit]
        
        # Extract fields for plotting
        if not params.group_by:
            # Single series
            x_values = []
            y_values = []
            
            for item in data_array:
                if isinstance(item, dict):
                    x_val = item.get(params.x_field)
                    y_val = item.get(params.y_field)
                    if x_val is not None and y_val is not None:
                        x_values.append(x_val)
                        y_values.append(float(y_val) if isinstance(y_val, (int, float, str)) else y_val)
            
            if not x_values:
                return {
                    "success": False,
                    "message": f"No data found for fields {params.x_field} and {params.y_field}"
                }
            
            # Create chart with single series
            chart_title = params.title or f"{resource_data['title']} - {params.y_field} by {params.x_field}"
            data_series = [{
                "name": params.y_field,
                "x": x_values,
                "y": y_values
            }]
        else:
            # Multiple series grouped by field
            groups = {}
            for item in data_array:
                if isinstance(item, dict):
                    group_val = item.get(params.group_by)
                    x_val = item.get(params.x_field)
                    y_val = item.get(params.y_field)
                    
                    if group_val is not None and x_val is not None and y_val is not None:
                        if group_val not in groups:
                            groups[group_val] = {"x": [], "y": []}
                        groups[group_val]["x"].append(x_val)
                        groups[group_val]["y"].append(float(y_val) if isinstance(y_val, (int, float, str)) else y_val)
            
            if not groups:
                return {
                    "success": False,
                    "message": f"No data found for fields {params.x_field}, {params.y_field}, and {params.group_by}"
                }
            
            # Create chart with multiple series
            chart_title = params.title or f"{resource_data['title']} - {params.y_field} by {params.x_field} (grouped by {params.group_by})"
            data_series = [
                {
                    "name": str(group_name),
                    "x": group_data["x"],
                    "y": group_data["y"]
                }
                for group_name, group_data in groups.items()
            ]
        
        # Create the chart using create_chart logic
        config = {
            "title": chart_title,
            "x_label": params.x_label or params.x_field,
            "y_label": params.y_label or params.y_field
        }
        
        # Use CreateChartParams to create the chart
        chart_params = CreateChartParams(
            data_series=data_series,
            plot_type=params.plot_type,
            config=config
        )
        
        # Call create_chart
        result = await create_chart(context=context, params=chart_params)
        
        if result.get("success"):
            result["message"] = f"Created chart from resource {params.resource_id}: {chart_title}"
            result["source_resource_id"] = params.resource_id
        
        return result
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to plot from resource: {str(e)}"
        }

