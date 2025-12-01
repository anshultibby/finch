# Finch Design Philosophy

## Core Identity
**Finch is NOT a general-purpose agent.** We are a **financial analysis assistant** focused on helping users make better investment decisions using real market data.

## Inspiration from Manus
We learned UX patterns from Manus, not architecture:
1. **Progress messages persist in chat** - Users see the work being done
2. **Chat-scoped artifacts** - Strategies and files belong to specific conversations
3. **Clean task flow** - Each chat is a focused financial analysis session

## Our Domain: Finance
**Tools we provide:**
- FMP financial data APIs (fundamentals, technicals, news, earnings, insider trading)
- Portfolio analysis and performance tracking
- Trading strategy creation using natural language
- Strategy backtesting and paper trading
- Market data visualization
- SnapTrade integration for brokerage connections
- **Python code execution for financial analysis** (like Manus, but finance-focused):
  * Data processing with pandas/numpy
  * Custom financial calculations
  * Analysis workflows with FMP data
  * Technical indicator computation

**Tools we DON'T provide:**
- Browser automation
- Shell/terminal access
- General file operations
- Web scraping
- General-purpose code execution
- Deployment tools

## User Flow
1. User asks a financial question or gives a trading idea
2. Agent uses **financial tools** to gather data
3. Progress updates shown as persistent messages (like Manus)
4. Results delivered as:
   - Chat messages with analysis
   - Saved resources (charts, tables, reports)
   - Executable trading strategies

## Chat Organization (like Manus tasks)
Each chat represents a **financial analysis session**:
- "Analyze NVDA earnings impact"
- "Create momentum strategy for tech stocks"
- "Review my portfolio performance"

Within each chat:
- Generated files (charts, CSV exports)
- Created strategies
- Research notes
- All scoped to that specific analysis

## Key Difference from Manus
**Manus**: General agent → Can do anything with any tool  
**Finch**: Specialized agent → Focused on finance, uses curated financial data APIs

This focus makes us better at what we do.

