# Plotting System Update - Resources & Beautiful Styling

## Summary
Complete overhaul of the plotting system with two major improvements:
1. **Resource Communication**: Better communication that plots are saved as resources
2. **Beautiful Styling**: Minimal, modern, consistent styling across all plots

## Changes Made

### 1. Tool Descriptions Updated

#### `create_plot` tool (`backend/modules/tool_definitions.py`)
- **Before**: Description mentioned creating charts but didn't emphasize resources
- **After**: Description now clearly states "The plot will be saved as a RESOURCE that you can reference in your response. After calling this tool, you can tell the user about the plot that was created and mention they can view it in the resources sidebar."

#### `create_chart` tool (`backend/modules/plotting_tools.py`)
- **Before**: "Returns a Plotly chart that will be displayed to the user."
- **After**: "Returns a Plotly chart that will be saved as a resource and displayed to the user in the resources sidebar."

### 2. Return Values Enhanced

#### `create_plot` function
- Now adds `resource_type: "plot"` to the successful result
- Enhanced message to mention: "This plot has been saved as a resource and can be viewed in the resources sidebar."

#### `create_chart` function
- Now includes `resource_type: "plot"` in the return value for consistency

### 3. Agent Prompts Updated

#### PlottingAgent System Prompt (`backend/modules/agent/plotting_agent.py`)
- Updated opening line: "Your job is to create beautiful, informative visualizations that will be saved as resources for the user."
- Emphasized that plots are saved as RESOURCES in the resources sidebar
- Added note that titles and labels should describe what's being visualized (since they'll be shown in the sidebar)

## How This Helps

1. **ChatAgent Awareness**: The ChatAgent now knows from the tool description that calling `create_plot` will create a resource that can be referenced
2. **Clear Communication**: Tool results now explicitly mention resources, making it easier for the ChatAgent to inform users
3. **Consistent Metadata**: All plot results now include `resource_type: "plot"` for consistent handling
4. **Better UX**: Users are now informed that plots are saved and can be re-accessed via the resources sidebar

## Technical Flow

1. ChatAgent calls `create_plot(objective="...", data={...})`
2. `create_plot` delegates to PlottingAgent
3. PlottingAgent calls `create_chart` with structured data
4. `create_chart` returns result with `resource_type: "plot"`, `plotly_json`, `title`, etc.
5. `create_plot` enhances the message and returns to ChatAgent
6. ChatService creates a Resource in the database from the tool result
7. ChatAgent can now reference the plot in its response and tell the user about it

## Example Response Flow

**User**: "Plot my portfolio allocation"

**ChatAgent** (after calling create_plot):
```
I've created an interactive chart showing your portfolio allocation. The chart has been 
saved to your resources sidebar where you can view and interact with it anytime.

[The plot resource is automatically linked and displayed]
```

The plot is saved as a resource with:
- `resource_type`: "plot"
- `title`: "Portfolio Allocation"
- `data`: Contains the plotly_json for rendering
- Accessible via the resources sidebar

## Part 2: Beautiful, Minimal Styling

### Design Philosophy
Updated all plots to follow a **minimal but meaningful** design philosophy:
- Show ONLY what matters - no chart junk
- Clean, modern aesthetics with white space
- Consistent color palette across all visualizations
- Focus on data, not decoration

### Styling Changes

#### 1. Color Palette
Defined consistent colors for all plots:
- Primary: `#3B82F6` (blue)
- Success/Growth: `#10B981` (green)
- Warning: `#F59E0B` (amber)
- Danger/Loss: `#EF4444` (red)
- Secondary: `#6366F1` (indigo)
- Neutral: `#6B7280` (gray) for labels
- Trendlines: `#9CA3AF` (light gray)

#### 2. Typography
- Font: `Inter, system-ui, -apple-system, sans-serif`
- Title: 22px, weight 600, left-aligned
- Axis labels: 13px, subtle gray
- Tick labels: 11px

#### 3. Layout Improvements
- Default height reduced to 500px (cleaner aspect ratio)
- Better margins (60, 30, 80, 50)
- Left-aligned title for modern look
- Horizontal legend above plot
- Clean white background

#### 4. Trace Styling
**Line Charts**:
- Line width: 2.5px
- Marker size: 5px (smaller, minimal)
- No marker borders

**Scatter Plots**:
- Marker size: 8px
- 70% opacity for transparency
- No borders

**Bar Charts**:
- No bar borders
- 85% opacity for modern look

**Area Charts**:
- 20% opacity fill
- Clean line at 2px width

**Trendlines**:
- Dotted lines (not dashed) for subtlety
- Neutral gray color `#9CA3AF`
- 60% opacity
- Simplified names (e.g., "Linear Trend" not "AAPL - Linear Trendline")

#### 5. Axes & Grid
- Grid: OFF by default (minimal design)
- Subtle axis lines: `rgba(0, 0, 0, 0.1)`
- Y-axis zero line shown for orientation
- Clean tick styling

#### 6. PlottingAgent Instructions
Updated system prompt with extensive styling guidance:
- Keep titles concise (6-10 words)
- Use standard color palette
- Add trendlines ONLY when they add insight
- Choose simplest chart type
- Avoid visual clutter

### Code Changes

#### Modified Functions
Both `create_plot()` and `create_chart()` now have:
- Consistent beautiful styling
- Modern typography
- Minimal design defaults
- Proper color handling for all chart types

#### Configuration Defaults
- Theme: `"light"` (was `"plotly"`)
- Grid: `False` (was `True`)
- Height: `500` (was `600`)

## Files Modified

- `/Users/anshul/code/finch/backend/modules/tool_definitions.py` - Resource communication
- `/Users/anshul/code/finch/backend/modules/plotting_tools.py` - Styling implementation
- `/Users/anshul/code/finch/backend/modules/agent/plotting_agent.py` - Design philosophy & instructions

## New Documentation

- `/Users/anshul/code/finch/PLOTTING_STYLE_GUIDE.md` - Comprehensive style guide with examples

