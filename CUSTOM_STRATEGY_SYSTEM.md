# Custom Strategy System Architecture

## Overview
A flexible, LLM-powered system that allows users to create, backtest, and track custom trading strategies using natural language. The system interprets strategy ideas, determines required data, executes backtests, and monitors ongoing performance.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INPUT                                │
│  "Buy stocks when insiders are buying and RSI is oversold"      │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                   STRATEGY PARSER (LLM)                          │
│  - Interprets natural language                                   │
│  - Identifies required data sources (FMP, Reddit, etc.)          │
│  - Determines indicators to calculate (RSI, MA, etc.)            │
│  - Defines entry/exit conditions                                 │
│  - Sets risk parameters                                          │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                  STRUCTURED STRATEGY DEFINITION                  │
│  {                                                               │
│    "name": "Insider + RSI Oversold",                            │
│    "timeframe": "short_term",                                   │
│    "data_requirements": [                                        │
│      {"source": "fmp", "type": "insider_trading"},              │
│      {"source": "fmp", "type": "price_history", "period": 60},  │
│      {"source": "calculated", "type": "rsi", "period": 14}      │
│    ],                                                            │
│    "entry_conditions": [...],                                    │
│    "exit_conditions": [...],                                     │
│    "risk_parameters": {...}                                      │
│  }                                                               │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ├─────────────────┬─────────────────────────┐
                       ▼                 ▼                         ▼
              ┌────────────────┐  ┌─────────────┐       ┌─────────────────┐
              │   BACKTESTING  │  │ LIVE SIGNAL │       │   PERFORMANCE   │
              │     ENGINE     │  │  GENERATION │       │    TRACKING     │
              └────────────────┘  └─────────────┘       └─────────────────┘
                       │                 │                         │
                       ▼                 ▼                         ▼
              ┌────────────────────────────────────────────────────┐
              │          RESULTS & PERFORMANCE METRICS              │
              │  - Win rate, profit factor, Sharpe ratio            │
              │  - Individual trade logs                            │
              │  - Strategy comparison                              │
              └────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Strategy Definition Model (Pydantic)

```python
class DataRequirement(BaseModel):
    source: Literal["fmp", "reddit", "calculated", "user_portfolio"]
    data_type: str  # e.g., "insider_trading", "price_history", "rsi"
    parameters: Dict[str, Any] = {}  # e.g., {"period": 14, "ticker": "$SYMBOL"}

class Condition(BaseModel):
    field: str  # e.g., "rsi", "insider_buy_amount", "price_change_pct"
    operator: Literal["gt", "lt", "gte", "lte", "eq", "between", "in"]
    value: Union[float, int, List[Any]]
    logic: Literal["AND", "OR"] = "AND"

class RiskParameters(BaseModel):
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    max_hold_days: Optional[int] = None
    position_size_pct: float = 5.0  # % of portfolio
    
class TradingStrategy(BaseModel):
    id: Optional[str] = None
    user_id: str
    name: str
    description: str
    natural_language_input: str  # Original user input
    timeframe: Literal["short_term", "medium_term", "long_term"]
    
    # Data requirements
    data_requirements: List[DataRequirement]
    
    # Entry logic
    entry_conditions: List[Condition]
    entry_logic: str = "AND"  # How to combine conditions
    
    # Exit logic
    exit_conditions: List[Condition]
    exit_logic: str = "OR"
    
    # Risk management
    risk_parameters: RiskParameters
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    
class StrategySignal(BaseModel):
    """A trade signal generated by a strategy"""
    strategy_id: str
    ticker: str
    signal_type: Literal["entry", "exit"]
    generated_at: datetime
    price_at_signal: float
    confidence_score: float  # 0-100
    reasoning: str  # Why this signal was generated
    data_snapshot: Dict[str, Any]  # All data used for decision

class StrategyBacktest(BaseModel):
    """Results from backtesting a strategy"""
    strategy_id: str
    backtest_id: str
    start_date: date
    end_date: date
    
    # Performance metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    total_return_pct: float
    total_return_dollars: float
    
    avg_win_pct: float
    avg_loss_pct: float
    profit_factor: float  # avg_win / avg_loss
    
    max_drawdown_pct: float
    sharpe_ratio: Optional[float]
    
    # Detailed trades
    trades: List[Dict[str, Any]]
    
    # Time series data for charts
    equity_curve: List[Dict[str, Any]]
    
class StrategyPerformance(BaseModel):
    """Live tracking of strategy performance"""
    strategy_id: str
    user_id: str
    
    # Live signals tracked
    signals_generated: int
    signals_acted_on: int
    
    # If user took the trades
    actual_trades: int
    actual_wins: int
    actual_losses: int
    actual_return_pct: float
    
    # Hypothetical (if they took all signals)
    hypothetical_trades: int
    hypothetical_return_pct: float
    
    last_signal_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
```

---

### 2. Strategy Parser Service (LLM-Based)

**Purpose:** Convert natural language strategy ideas into structured definitions

**LLM Prompt Template:**
```python
STRATEGY_PARSER_PROMPT = """You are a trading strategy architect. Your job is to convert user's natural language trading ideas into structured, executable strategy definitions.

User's Strategy Idea:
{user_input}

Your task:
1. Understand the strategy logic
2. Identify all data sources needed
3. Define precise entry and exit conditions
4. Set appropriate risk parameters
5. Determine the timeframe

Available Data Sources:
- FMP (Financial Modeling Prep): price_history, insider_trading, financial_statements, analyst_ratings, key_metrics, financial_ratios, etc.
- Reddit: ticker_sentiment, trending_stocks, mention_volume
- Calculated Indicators: rsi, macd, moving_average, bollinger_bands, volume_profile
- User Portfolio: holdings, transaction_history, performance_metrics

Output a JSON object matching this structure:
{schema}

Guidelines:
- Be specific about data requirements (e.g., "60 days of price history" not "price data")
- Define measurable conditions (e.g., "rsi < 30" not "oversold")
- Set realistic risk parameters based on strategy timeframe
- Short-term: 7% stop, 15% target, max 30 days
- Medium-term: 10% stop, 25% target, max 90 days
- Long-term: 15% stop, 50% target, max 180 days
- Explain reasoning in plain language

Be precise and executable. Think like a quantitative trader.
"""
```

**Implementation:**
```python
class StrategyParserService:
    def __init__(self, llm_client):
        self.llm = llm_client
        
    async def parse_strategy(
        self, 
        user_id: str,
        natural_language_input: str,
        user_context: Optional[Dict] = None  # Their trading history/preferences
    ) -> TradingStrategy:
        """
        Parse natural language strategy into structured definition
        
        Args:
            user_id: User creating the strategy
            natural_language_input: Their strategy description
            user_context: Optional context about their trading style
            
        Returns:
            Structured TradingStrategy object
        """
        # Build prompt with user input
        prompt = STRATEGY_PARSER_PROMPT.format(
            user_input=natural_language_input,
            schema=TradingStrategy.schema_json(indent=2),
            user_context=json.dumps(user_context) if user_context else ""
        )
        
        # Get LLM to parse strategy
        response = await self.llm.generate(prompt, response_format="json")
        
        # Validate and create strategy object
        strategy_dict = json.loads(response)
        strategy_dict["user_id"] = user_id
        strategy_dict["natural_language_input"] = natural_language_input
        strategy = TradingStrategy(**strategy_dict)
        
        return strategy
    
    async def refine_strategy(
        self,
        strategy: TradingStrategy,
        refinement_request: str
    ) -> TradingStrategy:
        """Allow user to iteratively refine their strategy"""
        # Implementation for iterative refinement
        pass
```

---

### 3. Backtesting Engine

**Purpose:** Test strategies on historical data to validate before live use

```python
class BacktestEngine:
    def __init__(self, data_service, fmp_client):
        self.data_service = data_service
        self.fmp = fmp_client
        
    async def run_backtest(
        self,
        strategy: TradingStrategy,
        start_date: date,
        end_date: date,
        initial_capital: float = 100000,
        universe: List[str] = None  # Tickers to test on
    ) -> StrategyBacktest:
        """
        Backtest a strategy on historical data
        
        Steps:
        1. Get universe of stocks (default: S&P 500)
        2. For each day in date range:
           - Fetch required data for all stocks
           - Evaluate entry conditions
           - Track open positions
           - Evaluate exit conditions
           - Record trades
        3. Calculate performance metrics
        4. Return backtest results
        """
        if universe is None:
            universe = await self._get_sp500_tickers()
        
        # Initialize tracking
        positions = {}  # {ticker: {entry_date, entry_price, shares}}
        trades = []
        cash = initial_capital
        equity_curve = []
        
        # Iterate through each trading day
        current_date = start_date
        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue
            
            # Get data for all stocks
            market_data = await self._fetch_market_data(
                universe, 
                current_date, 
                strategy.data_requirements
            )
            
            # Check exit conditions for existing positions
            for ticker, position in list(positions.items()):
                if ticker in market_data:
                    should_exit = self._evaluate_conditions(
                        strategy.exit_conditions,
                        market_data[ticker],
                        strategy.exit_logic
                    )
                    
                    # Also check risk parameters
                    days_held = (current_date - position['entry_date']).days
                    pnl_pct = (market_data[ticker]['price'] / position['entry_price'] - 1) * 100
                    
                    if should_exit or \
                       (strategy.risk_parameters.stop_loss_pct and pnl_pct <= -strategy.risk_parameters.stop_loss_pct) or \
                       (strategy.risk_parameters.take_profit_pct and pnl_pct >= strategy.risk_parameters.take_profit_pct) or \
                       (strategy.risk_parameters.max_hold_days and days_held >= strategy.risk_parameters.max_hold_days):
                        
                        # Exit position
                        exit_price = market_data[ticker]['price']
                        exit_value = position['shares'] * exit_price
                        pnl = exit_value - position['cost_basis']
                        
                        trades.append({
                            'ticker': ticker,
                            'entry_date': position['entry_date'],
                            'entry_price': position['entry_price'],
                            'exit_date': current_date,
                            'exit_price': exit_price,
                            'shares': position['shares'],
                            'pnl': pnl,
                            'pnl_pct': pnl_pct,
                            'days_held': days_held,
                            'exit_reason': 'signal' if should_exit else 'risk_management'
                        })
                        
                        cash += exit_value
                        del positions[ticker]
            
            # Check entry conditions for new positions
            for ticker in universe:
                if ticker not in positions and ticker in market_data:
                    should_enter = self._evaluate_conditions(
                        strategy.entry_conditions,
                        market_data[ticker],
                        strategy.entry_logic
                    )
                    
                    if should_enter and cash > 0:
                        # Calculate position size
                        position_value = initial_capital * (strategy.risk_parameters.position_size_pct / 100)
                        shares = int(position_value / market_data[ticker]['price'])
                        cost = shares * market_data[ticker]['price']
                        
                        if cost <= cash:
                            positions[ticker] = {
                                'entry_date': current_date,
                                'entry_price': market_data[ticker]['price'],
                                'shares': shares,
                                'cost_basis': cost
                            }
                            cash -= cost
            
            # Track equity curve
            total_position_value = sum(
                positions[t]['shares'] * market_data.get(t, {}).get('price', positions[t]['entry_price'])
                for t in positions
                if t in market_data
            )
            total_equity = cash + total_position_value
            
            equity_curve.append({
                'date': current_date,
                'equity': total_equity,
                'cash': cash,
                'positions_value': total_position_value
            })
            
            current_date += timedelta(days=1)
        
        # Close any remaining positions
        for ticker, position in positions.items():
            # Use last known price
            trades.append({
                'ticker': ticker,
                'entry_date': position['entry_date'],
                'entry_price': position['entry_price'],
                'exit_date': end_date,
                'exit_price': position['entry_price'],  # Simplified
                'shares': position['shares'],
                'pnl': 0,
                'pnl_pct': 0,
                'days_held': (end_date - position['entry_date']).days,
                'exit_reason': 'backtest_end'
            })
        
        # Calculate metrics
        metrics = self._calculate_metrics(trades, equity_curve, initial_capital)
        
        return StrategyBacktest(
            strategy_id=strategy.id,
            backtest_id=str(uuid.uuid4()),
            start_date=start_date,
            end_date=end_date,
            trades=trades,
            equity_curve=equity_curve,
            **metrics
        )
    
    def _evaluate_conditions(
        self,
        conditions: List[Condition],
        data: Dict[str, Any],
        logic: str
    ) -> bool:
        """Evaluate if conditions are met"""
        results = []
        
        for condition in conditions:
            field_value = data.get(condition.field)
            if field_value is None:
                results.append(False)
                continue
            
            if condition.operator == "gt":
                results.append(field_value > condition.value)
            elif condition.operator == "lt":
                results.append(field_value < condition.value)
            elif condition.operator == "gte":
                results.append(field_value >= condition.value)
            elif condition.operator == "lte":
                results.append(field_value <= condition.value)
            elif condition.operator == "eq":
                results.append(field_value == condition.value)
            elif condition.operator == "between":
                results.append(condition.value[0] <= field_value <= condition.value[1])
            elif condition.operator == "in":
                results.append(field_value in condition.value)
        
        if logic == "AND":
            return all(results)
        else:  # OR
            return any(results)
    
    def _calculate_metrics(self, trades, equity_curve, initial_capital):
        """Calculate strategy performance metrics"""
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_return_pct': 0,
                'total_return_dollars': 0,
                'avg_win_pct': 0,
                'avg_loss_pct': 0,
                'profit_factor': 0,
                'max_drawdown_pct': 0,
                'sharpe_ratio': None
            }
        
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] < 0]
        
        final_equity = equity_curve[-1]['equity']
        
        # Calculate max drawdown
        peak = initial_capital
        max_dd = 0
        for point in equity_curve:
            if point['equity'] > peak:
                peak = point['equity']
            dd = (peak - point['equity']) / peak * 100
            max_dd = max(max_dd, dd)
        
        # Calculate Sharpe ratio (simplified daily returns)
        returns = []
        for i in range(1, len(equity_curve)):
            daily_return = (equity_curve[i]['equity'] / equity_curve[i-1]['equity']) - 1
            returns.append(daily_return)
        
        if returns:
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        else:
            sharpe = None
        
        return {
            'total_trades': len(trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': len(wins) / len(trades) * 100 if trades else 0,
            'total_return_pct': (final_equity / initial_capital - 1) * 100,
            'total_return_dollars': final_equity - initial_capital,
            'avg_win_pct': np.mean([t['pnl_pct'] for t in wins]) if wins else 0,
            'avg_loss_pct': np.mean([t['pnl_pct'] for t in losses]) if losses else 0,
            'profit_factor': abs(sum(t['pnl'] for t in wins) / sum(t['pnl'] for t in losses)) if losses else float('inf'),
            'max_drawdown_pct': max_dd,
            'sharpe_ratio': sharpe
        }
```

---

### 4. Live Signal Generation

```python
class SignalGenerator:
    def __init__(self, data_service, fmp_client, reddit_client):
        self.data_service = data_service
        self.fmp = fmp_client
        self.reddit = reddit_client
        
    async def generate_signals(
        self,
        strategy: TradingStrategy,
        universe: List[str] = None
    ) -> List[StrategySignal]:
        """
        Generate current trade signals based on strategy
        
        Returns list of entry/exit signals for current market conditions
        """
        if universe is None:
            universe = await self._get_sp500_tickers()
        
        signals = []
        
        # Fetch current data for all tickers
        market_data = await self._fetch_current_data(
            universe,
            strategy.data_requirements
        )
        
        # Evaluate entry conditions
        for ticker, data in market_data.items():
            should_enter = self._evaluate_conditions(
                strategy.entry_conditions,
                data,
                strategy.entry_logic
            )
            
            if should_enter:
                # Calculate confidence score based on how strongly conditions are met
                confidence = self._calculate_confidence(strategy.entry_conditions, data)
                
                # Generate reasoning
                reasoning = self._generate_reasoning(
                    strategy.entry_conditions,
                    data,
                    "entry"
                )
                
                signals.append(StrategySignal(
                    strategy_id=strategy.id,
                    ticker=ticker,
                    signal_type="entry",
                    generated_at=datetime.utcnow(),
                    price_at_signal=data.get('price', 0),
                    confidence_score=confidence,
                    reasoning=reasoning,
                    data_snapshot=data
                ))
        
        return signals
    
    def _generate_reasoning(
        self,
        conditions: List[Condition],
        data: Dict[str, Any],
        signal_type: str
    ) -> str:
        """Generate human-readable explanation of why signal was triggered"""
        explanations = []
        
        for condition in conditions:
            field_value = data.get(condition.field)
            explanations.append(
                f"{condition.field} is {field_value} ({condition.operator} {condition.value})"
            )
        
        return f"{signal_type.upper()} signal: " + ", ".join(explanations)
```

---

### 5. Performance Tracking

```python
class StrategyPerformanceTracker:
    def __init__(self, db_session):
        self.db = db_session
        
    async def track_signal_outcome(
        self,
        signal: StrategySignal,
        user_acted: bool,
        outcome: Optional[Dict] = None  # If closed, track actual result
    ):
        """
        Track whether user acted on signal and the outcome
        
        This builds a history of strategy performance in real market
        """
        # Store signal
        await self.db.save_signal(signal)
        
        # Update strategy performance metrics
        if user_acted and outcome:
            await self._update_actual_performance(signal.strategy_id, outcome)
        
        # Always track hypothetical performance
        await self._update_hypothetical_performance(signal.strategy_id, signal)
    
    async def get_strategy_comparison(
        self,
        user_id: str,
        timeframe: Optional[str] = None
    ) -> List[Dict]:
        """
        Compare all user's strategies side-by-side
        
        Returns leaderboard of strategies by performance
        """
        strategies = await self.db.get_user_strategies(user_id)
        
        comparison = []
        for strategy in strategies:
            perf = await self.db.get_strategy_performance(strategy.id)
            
            comparison.append({
                'strategy_name': strategy.name,
                'timeframe': strategy.timeframe,
                'signals_generated': perf.signals_generated,
                'win_rate': (perf.actual_wins / perf.actual_trades * 100) if perf.actual_trades > 0 else None,
                'actual_return_pct': perf.actual_return_pct,
                'hypothetical_return_pct': perf.hypothetical_return_pct,
                'last_signal': perf.last_signal_date
            })
        
        # Sort by actual return (or hypothetical if no actual trades)
        comparison.sort(
            key=lambda x: x['actual_return_pct'] if x['actual_return_pct'] else x['hypothetical_return_pct'],
            reverse=True
        )
        
        return comparison
```

---

## Database Schema

```python
# New migration: 012_create_strategies_tables.py

def upgrade():
    # Strategies table
    op.create_table(
        'trading_strategies',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('natural_language_input', sa.Text, nullable=False),
        sa.Column('strategy_definition', sa.JSON, nullable=False),  # Full TradingStrategy as JSON
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['snaptrade_users.user_id']),
    )
    
    # Strategy backtests table
    op.create_table(
        'strategy_backtests',
        sa.Column('backtest_id', sa.String(36), primary_key=True),
        sa.Column('strategy_id', sa.String(36), nullable=False),
        sa.Column('start_date', sa.Date, nullable=False),
        sa.Column('end_date', sa.Date, nullable=False),
        sa.Column('backtest_results', sa.JSON, nullable=False),  # Full StrategyBacktest as JSON
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(['strategy_id'], ['trading_strategies.id']),
    )
    
    # Strategy signals table (live signals generated)
    op.create_table(
        'strategy_signals',
        sa.Column('signal_id', sa.String(36), primary_key=True),
        sa.Column('strategy_id', sa.String(36), nullable=False),
        sa.Column('ticker', sa.String(10), nullable=False),
        sa.Column('signal_type', sa.String(10), nullable=False),  # entry/exit
        sa.Column('generated_at', sa.DateTime, nullable=False),
        sa.Column('price_at_signal', sa.Numeric(precision=10, scale=2)),
        sa.Column('confidence_score', sa.Float),
        sa.Column('reasoning', sa.Text),
        sa.Column('data_snapshot', sa.JSON),
        sa.Column('user_acted', sa.Boolean, default=False),
        sa.Column('outcome', sa.JSON),  # If user took trade, track result
        sa.ForeignKeyConstraint(['strategy_id'], ['trading_strategies.id']),
    )
    
    # Strategy performance tracking
    op.create_table(
        'strategy_performance',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('strategy_id', sa.String(36), nullable=False, unique=True),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('signals_generated', sa.Integer, default=0),
        sa.Column('signals_acted_on', sa.Integer, default=0),
        sa.Column('actual_trades', sa.Integer, default=0),
        sa.Column('actual_wins', sa.Integer, default=0),
        sa.Column('actual_losses', sa.Integer, default=0),
        sa.Column('actual_return_pct', sa.Float, default=0),
        sa.Column('hypothetical_trades', sa.Integer, default=0),
        sa.Column('hypothetical_return_pct', sa.Float, default=0),
        sa.Column('last_signal_date', sa.DateTime),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(['strategy_id'], ['trading_strategies.id']),
        sa.ForeignKeyConstraint(['user_id'], ['snaptrade_users.user_id']),
    )
    
    # Indexes
    op.create_index('idx_strategies_user_id', 'trading_strategies', ['user_id'])
    op.create_index('idx_signals_strategy_id', 'strategy_signals', ['strategy_id'])
    op.create_index('idx_signals_generated_at', 'strategy_signals', ['generated_at'])
```

---

## Agent Tools

```python
# New tools to add to definitions.py

STRATEGY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_trading_strategy",
            "description": "Create a custom trading strategy from natural language description. The system will parse the strategy, determine required data, and create a structured, backtest-ready strategy definition.",
            "parameters": {
                "type": "object",
                "properties": {
                    "strategy_description": {
                        "type": "string",
                        "description": "Natural language description of the trading strategy. Be specific about entry conditions, exit conditions, and risk management. Example: 'Buy stocks when 3+ insiders buy more than $500K total in the last 30 days AND the stock is above its 50-day moving average. Sell when the stock drops below the 50-day MA or hits a 12% stop loss.'"
                    },
                    "strategy_name": {
                        "type": "string",
                        "description": "Short, descriptive name for the strategy"
                    }
                },
                "required": ["strategy_description", "strategy_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "backtest_strategy",
            "description": "Backtest a trading strategy on historical data to see how it would have performed. Returns detailed metrics including win rate, total return, profit factor, max drawdown, and individual trades.",
            "parameters": {
                "type": "object",
                "properties": {
                    "strategy_id": {
                        "type": "string",
                        "description": "ID of the strategy to backtest"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date for backtest in YYYY-MM-DD format"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date for backtest in YYYY-MM-DD format"
                    },
                    "initial_capital": {
                        "type": "number",
                        "description": "Starting capital for backtest. Defaults to $100,000",
                        "default": 100000
                    }
                },
                "required": ["strategy_id", "start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_strategy_signals",
            "description": "Get current trade signals generated by a strategy based on today's market data. Returns entry/exit signals with confidence scores and detailed reasoning.",
            "parameters": {
                "type": "object",
                "properties": {
                    "strategy_id": {
                        "type": "string",
                        "description": "ID of the strategy to generate signals for"
                    },
                    "min_confidence": {
                        "type": "number",
                        "description": "Minimum confidence score (0-100) to return. Defaults to 70",
                        "default": 70
                    }
                },
                "required": ["strategy_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_strategies",
            "description": "Compare performance of all user's strategies side-by-side. Shows which strategies are generating the best signals and returns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timeframe": {
                        "type": "string",
                        "enum": ["7d", "30d", "90d", "1y", "all"],
                        "description": "Timeframe for comparison. Defaults to 'all'",
                        "default": "all"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "refine_strategy",
            "description": "Modify an existing strategy based on new requirements or performance feedback. Use this to iteratively improve strategies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "strategy_id": {
                        "type": "string",
                        "description": "ID of the strategy to refine"
                    },
                    "refinement_description": {
                        "type": "string",
                        "description": "Natural language description of how to modify the strategy. Example: 'Add a condition that the stock must have volume above 1M shares' or 'Tighten the stop loss to 8%'"
                    }
                },
                "required": ["strategy_id", "refinement_description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_user_strategies",
            "description": "Get all trading strategies created by the user with their basic info and status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "active_only": {
                        "type": "boolean",
                        "description": "If true, only return active strategies. Defaults to true",
                        "default": True
                    }
                }
            }
        }
    }
]
```

---

## Example User Workflows

### Workflow 1: Create and Backtest Strategy

**User:** "Create a strategy: buy when insiders are buying and RSI is oversold"

**Agent:**
1. Calls `create_trading_strategy` with the description
2. System parses strategy, identifies data needs (insider trades, RSI)
3. Returns structured strategy
4. Agent explains the strategy back to user
5. Agent proactively calls `backtest_strategy` for last 2 years
6. Presents backtest results with metrics and chart

**User sees:**
```
✅ Created Strategy: "Insider + RSI Oversold"

Strategy Details:
- Entry: 3+ insider buys (>$500K total) in 30 days AND RSI < 30
- Exit: RSI > 70 OR 12% stop loss OR 60 days max hold
- Position size: 5% of portfolio

Backtest Results (2022-01-01 to 2024-11-30):
📊 Total Return: +34.2% ($34,200 on $100K)
✅ Win Rate: 62% (23 wins / 37 total trades)
💰 Profit Factor: 2.1 (avg win $2,100 / avg loss $1,000)
📉 Max Drawdown: -8.4%
⚡ Sharpe Ratio: 1.8

Best Trade: NVDA (+$4,200, +42%, 28 days)
Worst Trade: AMD (-$1,800, -12%, 8 days)

[Equity Curve Chart]

This strategy beat buy-and-hold S&P 500 (+18% vs +22%) but with better risk-adjusted returns.
Want to see current signals from this strategy?
```

---

### Workflow 2: Get Live Signals

**User:** "Show me signals for my Insider RSI strategy"

**Agent:**
1. Calls `get_strategy_signals` for that strategy
2. Gets 3 current entry signals
3. Formats and presents with details

**User sees:**
```
🎯 3 Current Entry Signals for "Insider + RSI Oversold"

1. **CRWD** - Confidence: 87/100 ⭐⭐⭐⭐
   - Current Price: $242.50
   - Entry Trigger: 5 insider buys ($1.2M total) in last 18 days, RSI at 28.3
   - Target: $272 (+12%)
   - Stop: $212 (-12%)
   - Similar to your past NVDA trade that made +$4,200

2. **PLTR** - Confidence: 78/100 ⭐⭐⭐
   - Current Price: $38.20
   - Entry Trigger: 3 C-suite buys ($850K total), RSI at 31.2
   - Target: $43 (+13%)
   - Stop: $33.60 (-12%)

3. **TSLA** - Confidence: 71/100 ⭐⭐⭐
   - Current Price: $235.00
   - Entry Trigger: 4 insider buys ($680K), RSI at 29.8
   - Target: $263 (+12%)
   - Stop: $207 (-12%)

Total capital needed: $15,000 (15% of portfolio for all 3 trades)
Expected value: +$1,800 based on 62% historical win rate

Want me to track these and alert you on any changes?
```

---

### Workflow 3: Compare Strategies

**User:** "Which of my strategies is performing best?"

**Agent:**
1. Calls `compare_strategies`
2. Formats leaderboard

**User sees:**
```
📊 Your Strategy Performance Leaderboard (Last 90 Days)

Rank | Strategy Name           | Signals | Win Rate | Return  | Status
-----|------------------------|---------|----------|---------|--------
 1   | Insider + RSI Oversold |   12    |   67%    | +18.2%  | 🟢 Active
 2   | MA Golden Cross        |    8    |   75%    | +14.5%  | 🟢 Active
 3   | Reddit Momentum        |   23    |   52%    | +8.1%   | 🟢 Active
 4   | Earnings Surprise      |    6    |   50%    | +2.3%   | 🟡 Paused

💡 Insight: Your "Insider + RSI" strategy is generating the best risk-adjusted returns.
It's also similar to your personal trading style (you have 68% win rate on value plays).

The "Reddit Momentum" strategy is generating lots of signals but lower win rate - 
consider tightening entry criteria to improve quality over quantity.
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- ✅ Pydantic models for strategies
- ✅ Database migration
- ✅ Strategy parser service (LLM-based)
- ✅ Basic CRUD operations

### Phase 2: Backtesting (Week 2)
- ✅ Backtest engine
- ✅ Data fetching for historical periods
- ✅ Metrics calculation
- ✅ Equity curve generation

### Phase 3: Live Signals (Week 3)
- ✅ Signal generator
- ✅ Daily batch job to scan market
- ✅ Signal storage and notification
- ✅ Performance tracking

### Phase 4: Agent Integration (Week 4)
- ✅ Add tools to definitions.py
- ✅ Update agent prompts
- ✅ Test user workflows
- ✅ UI for strategy management

---

## Future Enhancements

1. **Strategy Marketplace:**
   - Users can share successful strategies
   - See what strategies other users are running
   - Copy/clone high-performing strategies

2. **Auto-Optimization:**
   - Use genetic algorithms to optimize strategy parameters
   - A/B test strategy variations
   - Automatically adjust based on market regime

3. **Paper Trading:**
   - Automatically execute strategies in paper account
   - Track real-time performance without real money
   - Build confidence before going live

4. **Live Execution:**
   - Auto-execute trades based on signals (with user approval)
   - Integration with brokerage APIs
   - Risk limits and kill switches

5. **Advanced Analytics:**
   - Monte Carlo simulation
   - Walk-forward analysis
   - Out-of-sample testing
   - Regime-based performance analysis

