"""
Strategy Parser Service - Converts natural language strategy descriptions into structured definitions
"""
import json
import logging
from typing import Dict, Any, Optional
from anthropic import Anthropic
from backend.models.strategy import TradingStrategy
from backend.config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)


STRATEGY_PARSER_PROMPT = """You are a trading strategy architect. Your job is to convert user's natural language trading ideas into structured, executable strategy definitions.

User's Strategy Idea:
{user_input}

{user_context}

Your task:
1. Understand the strategy logic
2. Identify all data sources needed
3. Define precise entry and exit conditions
4. Set appropriate risk parameters based on timeframe
5. Determine the timeframe (short_term: 1-4 weeks, medium_term: 1-3 months, long_term: 3+ months)

Available Data Sources:
- **FMP (Financial Modeling Prep)**: 
  * price_history (daily OHLCV data)
  * insider_trading (SEC Form 4 transactions)
  * financial_statements (income, balance sheet, cash flow)
  * analyst_ratings (analyst recommendations)
  * key_metrics (P/E, P/B, ROE, debt ratios, etc.)
  * financial_ratios (liquidity, profitability, leverage, efficiency)
  * financial_growth (revenue growth, earnings growth, etc.)
  * quote (real-time price and volume)
  
- **Reddit (Apewisdom)**: 
  * ticker_sentiment (sentiment scores for specific stocks)
  * trending_stocks (currently trending tickers)
  * mention_volume (number of mentions)
  
- **Calculated Indicators**: 
  * rsi (Relative Strength Index, period 14 typical)
  * macd (Moving Average Convergence Divergence)
  * moving_average (SMA or EMA, specify period)
  * bollinger_bands (price bands based on std dev)
  * volume_avg (average volume over period)
  * atr (Average True Range for volatility)
  
- **User Portfolio**: 
  * holdings (current positions)
  * transaction_history (past trades)
  * performance_metrics (win rate, profit factor, etc.)

Field Names You Can Use in Conditions:
From insider_trading: insider_buy_count, insider_sell_count, insider_buy_amount, insider_sell_amount
From price_history: price, volume, price_change_pct, high, low, close
From calculated: rsi, macd, macd_signal, sma_20, sma_50, sma_200, ema_12, ema_26, volume_avg_20
From key_metrics: pe_ratio, pb_ratio, roe, debt_to_equity, current_ratio
From reddit: mention_count, sentiment_score, sentiment_change_pct
From financial_growth: revenue_growth, earnings_growth, eps_growth

Risk Parameter Guidelines by Timeframe:
- **short_term** (1-4 weeks): stop_loss_pct: 7-10%, take_profit_pct: 12-20%, max_hold_days: 20-30
- **medium_term** (1-3 months): stop_loss_pct: 10-12%, take_profit_pct: 20-35%, max_hold_days: 60-90
- **long_term** (3+ months): stop_loss_pct: 12-15%, take_profit_pct: 40-100%, max_hold_days: 120-180

Output a JSON object matching this exact structure:
{{
  "name": "Short descriptive name",
  "description": "Detailed explanation of the strategy",
  "timeframe": "short_term|medium_term|long_term",
  "data_requirements": [
    {{
      "source": "fmp|reddit|calculated|user_portfolio",
      "data_type": "specific data type",
      "parameters": {{"key": "value"}}
    }}
  ],
  "entry_conditions": [
    {{
      "field": "field_name",
      "operator": "gt|lt|gte|lte|eq|between|in",
      "value": numeric_value_or_array,
      "description": "Plain English explanation"
    }}
  ],
  "entry_logic": "AND|OR",
  "exit_conditions": [
    {{
      "field": "field_name",
      "operator": "gt|lt|gte|lte|eq|between|in",
      "value": numeric_value_or_array,
      "description": "Plain English explanation"
    }}
  ],
  "exit_logic": "AND|OR",
  "risk_parameters": {{
    "stop_loss_pct": float,
    "take_profit_pct": float,
    "max_hold_days": int,
    "position_size_pct": 5.0,
    "max_positions": 5
  }},
  "stock_universe": null
}}

Important:
- Be SPECIFIC about data requirements (e.g., "60 days" not "some history")
- Define MEASURABLE conditions (e.g., "rsi < 30" not "oversold")
- Set REALISTIC risk parameters based on timeframe
- Use standard field names from the list above
- Combine multiple conditions logically (AND/OR)
- Explain each condition in plain English in the description field

Return ONLY the JSON object, no other text.
"""


class StrategyParserService:
    """Service to parse natural language strategy descriptions into structured definitions"""
    
    def __init__(self):
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
        
    async def parse_strategy(
        self,
        user_id: str,
        natural_language_input: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> TradingStrategy:
        """
        Parse natural language strategy into structured definition
        
        Args:
            user_id: User creating the strategy
            natural_language_input: Their strategy description
            user_context: Optional context about their trading style/history
            
        Returns:
            Structured TradingStrategy object
            
        Raises:
            ValueError: If strategy cannot be parsed or is invalid
        """
        try:
            # Build user context string if provided
            context_str = ""
            if user_context:
                context_str = f"\nUser's Trading Context:\n{json.dumps(user_context, indent=2)}\n"
            
            # Build prompt
            prompt = STRATEGY_PARSER_PROMPT.format(
                user_input=natural_language_input,
                user_context=context_str
            )
            
            # Call LLM to parse strategy
            logger.info(f"Parsing strategy for user {user_id}: {natural_language_input[:100]}...")
            
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Extract JSON from response
            response_text = response.content[0].text
            logger.debug(f"LLM response: {response_text}")
            
            # Parse JSON
            strategy_dict = json.loads(response_text)
            
            # Add required fields
            strategy_dict["user_id"] = user_id
            strategy_dict["natural_language_input"] = natural_language_input
            
            # Validate and create strategy object
            strategy = TradingStrategy(**strategy_dict)
            
            logger.info(f"Successfully parsed strategy: {strategy.name}")
            return strategy
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise ValueError(f"Could not parse strategy definition. Please try rephrasing your strategy description.")
        except Exception as e:
            logger.error(f"Error parsing strategy: {e}")
            raise ValueError(f"Error creating strategy: {str(e)}")
    
    async def refine_strategy(
        self,
        strategy: TradingStrategy,
        refinement_request: str
    ) -> TradingStrategy:
        """
        Refine an existing strategy based on user feedback
        
        Args:
            strategy: Existing strategy to refine
            refinement_request: Natural language description of changes
            
        Returns:
            Updated TradingStrategy object
        """
        refinement_prompt = f"""You have an existing trading strategy. The user wants to refine it.

Current Strategy:
{strategy.model_dump_json(indent=2)}

User's Refinement Request:
{refinement_request}

Output the UPDATED strategy definition as JSON. Keep everything the same except what the user asked to change.
Return ONLY the JSON object, no other text.
"""
        
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": refinement_prompt
                }]
            )
            
            response_text = response.content[0].text
            strategy_dict = json.loads(response_text)
            
            # Preserve original metadata
            strategy_dict["user_id"] = strategy.user_id
            strategy_dict["natural_language_input"] = strategy.natural_language_input
            strategy_dict["id"] = strategy.id
            strategy_dict["created_at"] = strategy.created_at
            
            refined_strategy = TradingStrategy(**strategy_dict)
            
            logger.info(f"Successfully refined strategy: {refined_strategy.name}")
            return refined_strategy
            
        except Exception as e:
            logger.error(f"Error refining strategy: {e}")
            raise ValueError(f"Error refining strategy: {str(e)}")
    
    def validate_strategy(self, strategy: TradingStrategy) -> Dict[str, Any]:
        """
        Validate a strategy definition and return validation results
        
        Returns:
            Dict with 'valid' (bool) and 'issues' (list) keys
        """
        issues = []
        
        # Check for required data
        if not strategy.data_requirements:
            issues.append("Strategy must specify data requirements")
        
        # Check for entry conditions
        if not strategy.entry_conditions:
            issues.append("Strategy must have at least one entry condition")
        
        # Check for exit conditions or risk parameters
        if not strategy.exit_conditions and not strategy.risk_parameters.stop_loss_pct:
            issues.append("Strategy must have exit conditions or stop loss")
        
        # Validate condition fields are reasonable
        for condition in strategy.entry_conditions + strategy.exit_conditions:
            if not condition.field:
                issues.append(f"Condition missing field name")
            if condition.value is None:
                issues.append(f"Condition '{condition.field}' missing value")
        
        # Check risk parameters are reasonable
        if strategy.risk_parameters.stop_loss_pct and strategy.risk_parameters.stop_loss_pct > 50:
            issues.append("Stop loss > 50% is unreasonably high")
        
        if strategy.risk_parameters.position_size_pct > 50:
            issues.append("Position size > 50% is unreasonably high")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }

