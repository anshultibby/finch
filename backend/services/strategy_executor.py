"""
Strategy Executor - Execute screening and management rules

Clean separation:
- Screening rules: Run on candidates → BUY/SKIP
- Management rules: Run on positions → BUY/HOLD/SELL

Controlled Parallelization (to prevent API overload):
- Candidates: max 3 concurrent (reduced from 10)
- Positions: max 5 concurrent (reduced from 20)
- Data sources: max 2 concurrent per rule (prevents API hammering)
- Rate limiting: 100ms delay between API calls
"""
from typing import Dict, Any, List, Optional
from models.strategy_v2 import (
    TradingStrategyV2, StrategyRule, StrategyDecision, StrategyPosition, RuleDecisionResponse
)
from services.data_fetcher import DataFetcherService
from modules.agent.llm_handler import LLMHandler
from modules.agent.llm_config import LLMConfig
import json
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


def strip_markdown_code_fences(text: str) -> str:
    """
    Strip markdown code fences from text if present.
    Handles formats like:
    - ```json\n{...}\n```
    - ```\n{...}\n```
    """
    text = text.strip()
    
    # Check if starts with markdown code fence
    if text.startswith("```"):
        # Find the first newline (end of opening fence)
        first_newline = text.find("\n")
        if first_newline != -1:
            # Remove opening fence
            text = text[first_newline + 1:]
        
        # Check if ends with closing fence
        if text.endswith("```"):
            # Remove closing fence
            text = text[:-3]
        
        text = text.strip()
    
    return text


class StrategyExecutor:
    """Execute rule-based trading strategies"""
    
    def __init__(self, max_concurrent_candidates: int = 3, max_concurrent_positions: int = 5):
        self.data_fetcher = DataFetcherService()
        self.llm_handler = LLMHandler()
        self.max_concurrent_candidates = max_concurrent_candidates
        self.max_concurrent_positions = max_concurrent_positions
        # Limit data source fetching to prevent API overload
        self.max_concurrent_data_sources = 2
    
    async def screen_candidate(
        self,
        strategy: TradingStrategyV2,
        ticker: str
    ) -> StrategyDecision:
        """
        Run screening rules on a candidate stock
        
        Returns decision: BUY or SKIP
        """
        logger.info(f"Screening {ticker} with strategy '{strategy.name}'")
        
        return await self._execute_rules(
            rules=strategy.screening_rules,
            strategy_name=strategy.name,
            strategy_id=strategy.id,
            ticker=ticker,
            position=None,
            mode="screening"
        )
    
    async def screen_candidates_parallel(
        self,
        strategy: TradingStrategyV2,
        tickers: List[str]
    ) -> List[StrategyDecision]:
        """
        Screen multiple candidates in parallel with concurrency limit
        
        Returns list of decisions for all candidates
        """
        logger.info(f"Screening {len(tickers)} candidates (max {self.max_concurrent_candidates} concurrent) for strategy '{strategy.name}'")
        
        # Use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent_candidates)
        
        async def screen_with_semaphore(ticker: str):
            async with semaphore:
                try:
                    result = await self.screen_candidate(strategy, ticker)
                    logger.debug(f"✓ Screened {ticker}: {result.action}")
                    return result
                except Exception as e:
                    logger.error(f"✗ Error screening {ticker}: {str(e)}")
                    raise
        
        # Create tasks for all candidates
        tasks = [screen_with_semaphore(ticker) for ticker in tickers]
        
        # Execute all with concurrency control
        decisions = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log errors
        valid_decisions = []
        error_count = 0
        for ticker, result in zip(tickers, decisions):
            if isinstance(result, Exception):
                error_count += 1
                logger.error(f"Failed to screen {ticker}: {result}")
            else:
                valid_decisions.append(result)
        
        logger.info(f"Screening complete: {len(valid_decisions)} successful, {error_count} failed")
        return valid_decisions
    
    async def manage_position(
        self,
        strategy: TradingStrategyV2,
        position: StrategyPosition
    ) -> StrategyDecision:
        """
        Run management rules on a held position
        
        Returns decision: BUY (add more), HOLD, or SELL
        """
        logger.info(f"Managing position {position.ticker} for strategy '{strategy.name}'")
        
        return await self._execute_rules(
            rules=strategy.management_rules if strategy.management_rules else strategy.screening_rules,
            strategy_name=strategy.name,
            strategy_id=strategy.id,
            ticker=position.ticker,
            position=position,
            mode="management"
        )
    
    async def manage_positions_parallel(
        self,
        strategy: TradingStrategyV2,
        positions: List[StrategyPosition]
    ) -> List[StrategyDecision]:
        """
        Manage multiple positions in parallel with concurrency limit
        
        Returns list of decisions for all positions
        """
        logger.info(f"Managing {len(positions)} positions (max {self.max_concurrent_positions} concurrent) for strategy '{strategy.name}'")
        
        # Use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent_positions)
        
        async def manage_with_semaphore(position: StrategyPosition):
            async with semaphore:
                try:
                    result = await self.manage_position(strategy, position)
                    logger.debug(f"✓ Managed {position.ticker}: {result.action}")
                    return result
                except Exception as e:
                    logger.error(f"✗ Error managing {position.ticker}: {str(e)}")
                    raise
        
        # Create tasks for all positions
        tasks = [manage_with_semaphore(position) for position in positions]
        
        # Execute all with concurrency control
        decisions = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and log errors
        valid_decisions = []
        error_count = 0
        for position, result in zip(positions, decisions):
            if isinstance(result, Exception):
                error_count += 1
                logger.error(f"Failed to manage {position.ticker}: {result}")
            else:
                valid_decisions.append(result)
        
        logger.info(f"Position management complete: {len(valid_decisions)} successful, {error_count} failed")
        return valid_decisions
    
    async def _execute_rules(
        self,
        rules: List[StrategyRule],
        strategy_name: str,
        strategy_id: str,
        ticker: str,
        position: Optional[StrategyPosition],
        mode: str  # "screening" or "management"
    ) -> StrategyDecision:
        """Execute rules and aggregate into decision"""
        
        # Sort rules by order
        sorted_rules = sorted(rules, key=lambda r: r.order)
        
        # Build context
        context = {
            "ticker": ticker,
            "strategy_name": strategy_name,
            "mode": mode,
            "position": position.model_dump() if position else None
        }
        
        # Execute each rule
        rule_results = []
        all_data = {}
        
        for rule in sorted_rules:
            result = await self._execute_rule(rule, ticker, all_data, context)
            rule_results.append(result)
            
            # If rule says SKIP, stop execution
            if result.get("action") == "SKIP":
                break
        
        # Aggregate results
        decision = self._aggregate_decision(
            strategy_id=strategy_id,
            ticker=ticker,
            rule_results=rule_results,
            all_data=all_data,
            position=position,
            mode=mode
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
        
        # Fetch data for this rule - CONTROLLED PARALLEL DATA FETCHING
        rule_data = {}
        
        # Determine which data sources need fetching
        fetch_tasks = []
        fetch_keys = []
        for data_source in rule.data_sources:
            key = f"{data_source.type}_{data_source.endpoint}"
            if key not in all_data:  # Cache data
                fetch_tasks.append(data_source)
                fetch_keys.append(key)
            else:
                rule_data[key] = all_data[key]
        
        # Fetch data sources with limited parallelism to prevent API overload
        if fetch_tasks:
            semaphore = asyncio.Semaphore(self.max_concurrent_data_sources)
            
            async def fetch_with_semaphore(ds, ticker):
                async with semaphore:
                    return await self.data_fetcher.fetch_data(ds, ticker)
            
            # Fetch with concurrency control
            fetched_data = await asyncio.gather(
                *[fetch_with_semaphore(ds, ticker) for ds in fetch_tasks],
                return_exceptions=True
            )
            
            for key, data in zip(fetch_keys, fetched_data):
                if isinstance(data, Exception):
                    logger.error(f"Error fetching {key}: {data}")
                    all_data[key] = None
                else:
                    all_data[key] = data
                rule_data[key] = all_data[key]
        
        # Build LLM prompt
        prompt = self._build_rule_prompt(rule, ticker, rule_data, context)
        
        # Get LLM decision
        try:
            llm_config = LLMConfig.from_config()
            
            # Build kwargs for LLM call with structured JSON output
            llm_kwargs = {
                "messages": [{"role": "user", "content": prompt}],
                "model": llm_config.model
            }
            
            # Only add response_format for OpenAI models
            # Anthropic/Claude doesn't support response_format natively, and litellm's
            # conversion to tool schema can cause validation errors with nested models
            if llm_config.model.startswith(("gpt-", "o1-", "o3-")):
                llm_kwargs["response_format"] = {"type": "json_object"}
            
            response = await self.llm_handler.acompletion(**llm_kwargs)
            
            response_text = response.choices[0].message.content
            cleaned_text = ""  # Initialize for error handling
            
            # Log the raw response for debugging
            logger.info(f"LLM response for rule #{rule.order}: {response_text[:200]}...")
            
            # Strip markdown code fences if present (Claude often wraps JSON in ```json...```)
            cleaned_text = strip_markdown_code_fences(response_text)
            
            # Parse JSON response
            result_dict = json.loads(cleaned_text)
            
            # Validate with Pydantic model
            rule_response = RuleDecisionResponse(**result_dict)
            
            # Convert to dict and add metadata
            result = rule_response.model_dump()
            result["rule_order"] = rule.order
            result["rule_description"] = rule.description
            result["rule_weight"] = rule.weight
            
            logger.info(f"✅ Rule #{rule.order}: {rule_response.action} ({rule_response.signal})")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response for rule {rule.order}: {str(e)}")
            logger.error(f"Original response: {response_text}")
            logger.error(f"Cleaned response: {cleaned_text}")
            return {
                "rule_order": rule.order,
                "rule_description": rule.description,
                "action": "ERROR",
                "signal": "NEUTRAL",
                "signal_value": 0.5,
                "reasoning": f"Invalid JSON response: {str(e)}",
                "confidence": 0
            }
        except Exception as e:
            import traceback
            logger.error(f"Error executing rule {rule.order}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "rule_order": rule.order,
                "rule_description": rule.description,
                "action": "ERROR",
                "signal": "NEUTRAL",
                "signal_value": 0.5,
                "reasoning": f"Error: {str(e)}",
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
        
        mode = context["mode"]
        position = context.get("position")
        
        if mode == "screening":
            mode_context = f"""
MODE: SCREENING
You are evaluating {ticker} as a potential BUY candidate.
We don't own this stock yet.

Your decision should be:
- CONTINUE: Move to next rule
- SKIP: Don't buy this stock (stop evaluation)
- BUY: Only if this is the final rule and all signals are good
"""
        else:  # management
            pos = position
            mode_context = f"""
MODE: POSITION MANAGEMENT
We currently own {pos['shares']} shares of {ticker}:
- Entry price: ${pos['entry_price']:.2f}
- Current price: ${pos['current_price']:.2f}
- P&L: {pos['pnl_pct']:.1f}%
- Days held: {pos['days_held']}

Your decision should be:
- SELL: Exit this position
- HOLD: Keep current position  
- BUY: Add more shares (if still bullish)
"""
        
        return f"""You are executing rule #{rule.order} of a trading strategy.

Ticker: {ticker}
Strategy: {context['strategy_name']}
{mode_context}

RULE DESCRIPTION:
{rule.description}

DECISION LOGIC:
{rule.decision_logic}

AVAILABLE DATA:
{json.dumps(rule_data, indent=2, default=str)}

Based on the decision logic and available data, respond with a JSON object:
{{
    "action": "CONTINUE" | "SKIP" | "BUY" | "SELL" | "HOLD",
    "signal": "BULLISH" | "BEARISH" | "NEUTRAL",
    "signal_value": <0-1, where 0=bearish, 0.5=neutral, 1=bullish>,
    "reasoning": "<brief explanation>",
    "confidence": <0-100>
}}"""
    
    def _aggregate_decision(
        self,
        strategy_id: str,
        ticker: str,
        rule_results: List[Dict[str, Any]],
        all_data: Dict[str, Any],
        position: Optional[StrategyPosition],
        mode: str
    ) -> StrategyDecision:
        """Aggregate rule results into final decision"""
        
        # Check for SKIP
        if any(r.get("action") == "SKIP" for r in rule_results):
            return StrategyDecision(
                strategy_id=strategy_id,
                ticker=ticker,
                action="SKIP",
                confidence=100,
                reasoning="Strategy criteria not met",
                rule_results=rule_results,
                data_snapshot=all_data,
                current_price=0.0,
                position_data=position.model_dump() if position else None
            )
        
        # Calculate weighted signal
        total_weight = sum(r.get("rule_weight", 0) for r in rule_results)
        if total_weight == 0:
            weighted_signal = 0.5
        else:
            weighted_signal = sum(
                r.get("signal_value", 0.5) * r.get("rule_weight", 0)
                for r in rule_results
            ) / total_weight
        
        # Determine action based on mode and signal
        if mode == "screening":
            # Screening: BUY if bullish enough
            action = "BUY" if weighted_signal >= 0.7 else "SKIP"
        else:
            # Management: BUY/HOLD/SELL based on signal
            if weighted_signal >= 0.75:
                action = "BUY"  # Very bullish, add more
            elif weighted_signal >= 0.4:
                action = "HOLD"  # Neutral to bullish
            else:
                action = "SELL"  # Bearish
        
        # Calculate confidence
        avg_confidence = sum(r.get("confidence", 50) for r in rule_results) / len(rule_results) if rule_results else 50
        
        # Build reasoning
        reasoning = self._build_reasoning(rule_results, weighted_signal, action, mode)
        
        # Get current price
        current_price = position.current_price if position else all_data.get("current_price", 0.0)
        
        return StrategyDecision(
            strategy_id=strategy_id,
            ticker=ticker,
            action=action,
            confidence=round(avg_confidence, 1),
            reasoning=reasoning,
            rule_results=rule_results,
            data_snapshot=all_data,
            current_price=current_price,
            position_data=position.model_dump() if position else None
        )
    
    def _build_reasoning(
        self,
        rule_results: List[Dict[str, Any]],
        weighted_signal: float,
        action: str,
        mode: str
    ) -> str:
        """Build human-readable reasoning"""
        
        lines = [f"{'Screening' if mode == 'screening' else 'Position Management'} Analysis:", ""]
        
        for result in rule_results:
            order = result.get("rule_order", "?")
            desc = result.get("rule_description", "Unknown")
            signal = result.get("signal", "NEUTRAL")
            reasoning = result.get("reasoning", "")
            
            icon = "✓" if signal == "BULLISH" else "✗" if signal == "BEARISH" else "○"
            lines.append(f"{icon} Rule {order}: {desc}")
            lines.append(f"   {signal} - {reasoning}")
            lines.append("")
        
        lines.append(f"Weighted Signal: {weighted_signal:.2f}")
        lines.append(f"**Decision: {action}**")
        
        return "\n".join(lines)
