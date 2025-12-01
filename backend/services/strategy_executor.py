"""
Strategy Executor Service - Execute rule-based strategies using LLM
"""
from typing import Dict, Any, List
from models.strategy_v2 import TradingStrategyV2, StrategyRule, StrategyDecision
from services.data_fetcher import DataFetcherService
from modules.agent.llm_handler import LLMHandler
from modules.agent.llm_config import LLMConfig
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class StrategyExecutor:
    """Execute rule-based trading strategies using LLM decision-making"""
    
    def __init__(self):
        self.data_fetcher = DataFetcherService()
        self.llm_handler = LLMHandler()
    
    async def execute_strategy(
        self,
        strategy: TradingStrategyV2,
        ticker: str
    ) -> StrategyDecision:
        """
        Execute a strategy on a ticker
        
        Args:
            strategy: The strategy to execute
            ticker: Stock ticker symbol
            
        Returns:
            StrategyDecision with action, confidence, and reasoning
        """
        logger.info(f"Executing strategy '{strategy.name}' on {ticker}")
        
        # Sort rules by order
        sorted_rules = sorted(strategy.rules, key=lambda r: r.order)
        
        # Execute each rule
        rule_results = []
        all_data = {}
        context = {"ticker": ticker, "strategy_name": strategy.name}
        
        for rule in sorted_rules:
            result = await self._execute_rule(rule, ticker, all_data, context)
            rule_results.append(result)
            
            # If rule says to SKIP this stock, stop execution
            if result.get("action") == "SKIP":
                logger.info(f"Rule {rule.order} returned SKIP for {ticker}")
                break
        
        # Aggregate results into final decision
        decision = await self._aggregate_decision(
            strategy=strategy,
            ticker=ticker,
            rule_results=rule_results,
            all_data=all_data
        )
        
        return decision
    
    async def _execute_rule(
        self,
        rule: StrategyRule,
        ticker: str,
        all_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single rule using LLM"""
        
        logger.info(f"Executing rule #{rule.order}: {rule.description}")
        
        # Fetch data for this rule
        rule_data = {}
        for data_source in rule.data_sources:
            key = f"{data_source.type}_{data_source.endpoint}"
            data = await self.data_fetcher.fetch_data(data_source, ticker)
            rule_data[key] = data
            all_data[key] = data
        
        # Build LLM prompt
        prompt = self._build_rule_prompt(rule, ticker, rule_data, context)
        
        # Get LLM decision
        try:
            llm_config = LLMConfig.from_config()
            response = await self.llm_handler.completion(
                messages=[{"role": "user", "content": prompt}],
                model=llm_config.model,
                response_format={"type": "json_object"}
            )
            
            response_text = response.choices[0].message.content
            result = json.loads(response_text)
            
            # Add metadata
            result["rule_order"] = rule.order
            result["rule_description"] = rule.description
            result["rule_weight"] = rule.weight
            
            logger.info(f"Rule {rule.order} result: {result.get('action', 'UNKNOWN')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing rule {rule.order}: {str(e)}")
            return {
                "rule_order": rule.order,
                "rule_description": rule.description,
                "action": "ERROR",
                "signal": "NEUTRAL",
                "signal_value": 0.5,
                "reasoning": f"Error executing rule: {str(e)}",
                "confidence": 0
            }
    
    def _build_rule_prompt(
        self,
        rule: StrategyRule,
        ticker: str,
        rule_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Build LLM prompt for a rule"""
        
        return f"""You are executing rule #{rule.order} of a trading strategy.

Ticker: {ticker}
Strategy: {context.get('strategy_name', 'Unknown')}

RULE DESCRIPTION:
{rule.description}

DECISION LOGIC:
{rule.decision_logic}

AVAILABLE DATA:
{json.dumps(rule_data, indent=2, default=str)}

Based on the decision logic and available data, provide your decision.

Respond with ONLY a JSON object in this exact format:
{{
    "action": "CONTINUE" | "SKIP" | "BUY" | "SELL" | "HOLD",
    "signal": "BULLISH" | "BEARISH" | "NEUTRAL",
    "signal_value": <number 0-1, where 0=very bearish, 0.5=neutral, 1=very bullish>,
    "reasoning": "<brief explanation of your decision>",
    "confidence": <number 0-100>
}}

Rules:
- Use "SKIP" to stop evaluating this ticker (e.g., if it doesn't meet basic criteria)
- Use "CONTINUE" to move to the next rule
- Use "BUY"/"SELL"/"HOLD" only in final decision rules
- signal_value should reflect the strength of the signal (0=bearish, 1=bullish)
- confidence should reflect how certain you are (0-100)

Your JSON response:"""
    
    async def _aggregate_decision(
        self,
        strategy: TradingStrategyV2,
        ticker: str,
        rule_results: List[Dict[str, Any]],
        all_data: Dict[str, Any]
    ) -> StrategyDecision:
        """Aggregate rule results into final decision using LLM"""
        
        # Check if any rule returned SKIP
        if any(r.get("action") == "SKIP" for r in rule_results):
            return StrategyDecision(
                strategy_id=strategy.id,
                ticker=ticker,
                action="SKIP",
                confidence=100,
                reasoning="Strategy criteria not met - ticker skipped",
                rule_results=rule_results,
                data_snapshot=all_data,
                current_price=await self._get_current_price(ticker)
            )
        
        # Calculate weighted average signal
        total_weight = sum(r.get("rule_weight", 0) for r in rule_results)
        if total_weight == 0:
            weighted_signal = 0.5
        else:
            weighted_signal = sum(
                r.get("signal_value", 0.5) * r.get("rule_weight", 0)
                for r in rule_results
            ) / total_weight
        
        # Determine action based on weighted signal
        if weighted_signal >= 0.7:
            action = "BUY"
        elif weighted_signal <= 0.3:
            action = "SELL"
        elif weighted_signal >= 0.55:
            action = "HOLD"
        else:
            action = "SKIP"
        
        # Calculate confidence (average of rule confidences)
        avg_confidence = sum(r.get("confidence", 50) for r in rule_results) / len(rule_results) if rule_results else 50
        
        # Build reasoning
        reasoning = self._build_reasoning(rule_results, weighted_signal, action)
        
        current_price = await self._get_current_price(ticker)
        
        return StrategyDecision(
            strategy_id=strategy.id,
            ticker=ticker,
            action=action,
            confidence=round(avg_confidence, 1),
            reasoning=reasoning,
            rule_results=rule_results,
            data_snapshot=all_data,
            current_price=current_price
        )
    
    def _build_reasoning(
        self,
        rule_results: List[Dict[str, Any]],
        weighted_signal: float,
        action: str
    ) -> str:
        """Build human-readable reasoning from rule results"""
        
        lines = ["Strategy Execution Summary:", ""]
        
        for result in rule_results:
            order = result.get("rule_order", "?")
            desc = result.get("rule_description", "Unknown")
            signal = result.get("signal", "NEUTRAL")
            reasoning = result.get("reasoning", "No reasoning provided")
            
            icon = "✓" if signal == "BULLISH" else "✗" if signal == "BEARISH" else "○"
            lines.append(f"{icon} Rule {order} ({desc}): {signal}")
            lines.append(f"   {reasoning}")
            lines.append("")
        
        lines.append(f"Weighted Signal Score: {weighted_signal:.2f}")
        lines.append(f"Final Decision: {action}")
        
        return "\n".join(lines)
    
    async def _get_current_price(self, ticker: str) -> float:
        """Get current price for ticker"""
        try:
            quote = await self.data_fetcher.fmp_client.get_quote(ticker)
            if quote and len(quote) > 0:
                return quote[0].get("price", 0.0)
        except Exception as e:
            logger.error(f"Error getting price for {ticker}: {str(e)}")
        
        return 0.0

