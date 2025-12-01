"""
Candidate Selector - Use LLM to intelligently select candidates

Instead of screening hundreds of stocks, use the LLM ONCE to:
1. Analyze the strategy
2. Use FMP screener API to find relevant stocks
3. Check news and market movers
4. Return exactly 10 candidates
"""
from typing import List, Dict, Any
from models.strategy_v2 import TradingStrategyV2
from modules.agent.llm_handler import LLMHandler
from modules.agent.llm_config import LLMConfig
from modules.tools.clients.fmp import FMPTools
import json
import logging

logger = logging.getLogger(__name__)


class CandidateSelector:
    """Select candidates using LLM + FMP screener"""
    
    def __init__(self):
        self.llm_handler = LLMHandler()
        self.fmp_tools = FMPTools()
    
    async def select_candidates(
        self,
        strategy: TradingStrategyV2,
        max_candidates: int = 10
    ) -> List[str]:
        """
        Use LLM to intelligently select candidates for screening
        
        Returns: List of ticker symbols (max 10)
        """
        logger.info(f"Selecting candidates for strategy '{strategy.name}'")
        
        # Step 1: If user specified custom tickers, use those
        if strategy.candidate_source.type in ["custom", "tickers"]:
            tickers = strategy.candidate_source.tickers or []
            logger.info(f"Using custom tickers: {tickers[:max_candidates]}")
            return tickers[:max_candidates]
        
        # Step 2: Use LLM to analyze strategy and select candidates
        try:
            # Get available data for LLM
            context_data = await self._gather_context_data(strategy)
            
            # Ask LLM to select candidates
            candidates = await self._llm_select_candidates(
                strategy=strategy,
                context_data=context_data,
                max_candidates=max_candidates
            )
            
            logger.info(f"LLM selected {len(candidates)} candidates: {candidates}")
            return candidates[:max_candidates]
            
        except Exception as e:
            logger.error(f"Error selecting candidates with LLM: {e}")
            # Fallback to simple universe selection
            return await self._fallback_selection(strategy, max_candidates)
    
    async def _gather_context_data(self, strategy: TradingStrategyV2) -> Dict[str, Any]:
        """Gather context data for LLM to use in selection"""
        context = {}
        
        try:
            # Get market movers
            gainers = await self.fmp_tools.get_fmp_data("biggest-gainers", {})
            losers = await self.fmp_tools.get_fmp_data("biggest-losers", {})
            actives = await self.fmp_tools.get_fmp_data("most-actives", {})
            
            context["market_movers"] = {
                "gainers": gainers[:5] if gainers else [],
                "losers": losers[:5] if losers else [],
                "most_active": actives[:5] if actives else []
            }
        except Exception as e:
            logger.warning(f"Could not fetch market movers: {e}")
            context["market_movers"] = None
        
        try:
            # Get sector performance
            sectors = await self.fmp_tools.get_fmp_data("sector-performance-snapshot", {})
            context["sector_performance"] = sectors[:10] if sectors else None
        except Exception as e:
            logger.warning(f"Could not fetch sector performance: {e}")
            context["sector_performance"] = None
        
        try:
            # Get latest market news (sample)
            news = await self.fmp_tools.get_fmp_data("news/stock-latest", {"limit": 10})
            context["recent_news"] = news[:10] if news else None
        except Exception as e:
            logger.warning(f"Could not fetch news: {e}")
            context["recent_news"] = None
        
        return context
    
    async def _llm_select_candidates(
        self,
        strategy: TradingStrategyV2,
        context_data: Dict[str, Any],
        max_candidates: int
    ) -> List[str]:
        """Use LLM to select candidates based on strategy and market context"""
        
        # Build prompt for LLM
        prompt = self._build_selection_prompt(strategy, context_data, max_candidates)
        
        # Get LLM response
        llm_config = LLMConfig.from_config()
        
        llm_kwargs = {
            "messages": [{"role": "user", "content": prompt}],
            "model": llm_config.model,
        }
        
        # Only add response_format for OpenAI models
        if llm_config.model.startswith(("gpt-", "o1-", "o3-")):
            llm_kwargs["response_format"] = {"type": "json_object"}
        
        response = await self.llm_handler.acompletion(**llm_kwargs)
        response_text = response.choices[0].message.content
        
        logger.info(f"LLM candidate selection response: {response_text[:500]}...")
        
        # Parse response
        result = self._extract_json(response_text)
        
        # Extract tickers and screener params
        tickers = []
        
        # If LLM suggested using screener
        if result.get("use_screener") and result.get("screener_params"):
            screener_params = result["screener_params"]
            logger.info(f"Using FMP screener with params: {screener_params}")
            
            try:
                # Call FMP screener
                screener_results = await self.fmp_tools.get_fmp_data(
                    "company-screener",
                    screener_params
                )
                
                if screener_results:
                    tickers = [r["symbol"] for r in screener_results[:max_candidates]]
                    logger.info(f"Screener returned {len(tickers)} tickers")
            except Exception as e:
                logger.error(f"Error calling FMP screener: {e}")
        
        # If we don't have enough tickers, add LLM's direct suggestions
        if len(tickers) < max_candidates and result.get("suggested_tickers"):
            remaining = max_candidates - len(tickers)
            suggested = result["suggested_tickers"][:remaining]
            tickers.extend(suggested)
            logger.info(f"Added {len(suggested)} LLM-suggested tickers")
        
        return tickers[:max_candidates]
    
    def _build_selection_prompt(
        self,
        strategy: TradingStrategyV2,
        context_data: Dict[str, Any],
        max_candidates: int
    ) -> str:
        """Build prompt for LLM to select candidates"""
        
        # Summarize strategy rules
        rule_summaries = []
        for i, rule in enumerate(strategy.screening_rules, 1):
            rule_summaries.append(f"Rule {i}: {rule.description}")
        
        return f"""You are a stock market analyst helping to select {max_candidates} candidate stocks for a trading strategy.

STRATEGY:
Name: {strategy.name}
Description: {strategy.description}

SCREENING RULES:
{chr(10).join(rule_summaries)}

CANDIDATE SOURCE: {strategy.candidate_source.type}
{f"Universe: {strategy.candidate_source.universe}" if strategy.candidate_source.universe else ""}
{f"Sector: {strategy.candidate_source.sector}" if strategy.candidate_source.sector else ""}

CURRENT MARKET CONTEXT:
{json.dumps(context_data, indent=2, default=str)}

YOUR TASK:
Based on the strategy description and rules, select {max_candidates} stocks that would be good candidates to screen.

You have two options:

Option 1: Use FMP Stock Screener
You can use the FMP company-screener API with these parameters:
- marketCapMoreThan, marketCapLowerThan (e.g., 1000000000 for $1B)
- sector (e.g., "Technology", "Healthcare", "Financial Services")
- industry (e.g., "Software", "Biotechnology")
- betaMoreThan, betaLowerThan (volatility measure)
- priceMoreThan, priceLowerThan
- volumeMoreThan, volumeLowerThan
- exchange (e.g., "NASDAQ", "NYSE")
- limit (max results, set to {max_candidates})

Option 2: Directly suggest tickers
Based on market movers, news, and your knowledge, suggest specific tickers.

RESPOND WITH JSON:
{{
    "use_screener": true/false,
    "screener_params": {{
        // If use_screener is true, provide parameters
        "sector": "Technology",
        "marketCapMoreThan": 1000000000,
        "limit": {max_candidates}
    }},
    "suggested_tickers": ["AAPL", "MSFT", ...],  // Direct suggestions (always provide as backup)
    "reasoning": "Brief explanation of why these candidates fit the strategy"
}}

Your JSON response:"""
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response"""
        import re
        
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try markdown code blocks
        patterns = [
            r'```json\s*\n(.*?)\n```',
            r'```\s*\n(.*?)\n```',
            r'\{.*\}'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1) if '```' in pattern else match.group(0))
                except json.JSONDecodeError:
                    continue
        
        raise ValueError(f"Could not parse JSON from response: {text[:200]}...")
    
    async def _fallback_selection(
        self,
        strategy: TradingStrategyV2,
        max_candidates: int
    ) -> List[str]:
        """Fallback selection if LLM fails"""
        logger.warning("Using fallback candidate selection")
        
        candidate_source = strategy.candidate_source
        
        # Simple hardcoded universes
        universes = {
            "sp500": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "JPM", "V"],
            "nasdaq100": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "NFLX", "ADBE", "CSCO"],
            "dow30": ["AAPL", "MSFT", "JPM", "V", "UNH", "JNJ", "WMT", "PG", "HD", "CVX"]
        }
        
        if candidate_source.type == "universe":
            return universes.get(candidate_source.universe or "sp500", [])[:max_candidates]
        elif candidate_source.type == "reddit_trending":
            return ["GME", "AMC", "PLTR", "TSLA", "NVDA"][:max_candidates]
        
        return universes["sp500"][:max_candidates]

