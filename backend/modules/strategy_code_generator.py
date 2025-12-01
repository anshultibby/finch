"""
Strategy Code Generator - LLM generates Python code for strategies

Instead of running LLM for every ticker evaluation, we:
1. Generate Python code once from user's strategy description
2. Validate and sandbox the code
3. Execute code directly (fast, deterministic, debuggable)
"""
from typing import Dict, Any, Optional
from modules.agent.llm_handler import LLMHandler
from modules.agent.llm_config import LLMConfig
from modules.code_sandbox import code_sandbox
import json
import logging

logger = logging.getLogger(__name__)


class StrategyCodeGenerator:
    """Generate executable Python code from strategy descriptions"""
    
    def __init__(self):
        self.llm_handler = LLMHandler()
    
    async def generate_screening_code(
        self,
        strategy_description: str,
        data_sources: list[str],
        example_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate screening function code
        
        Args:
            strategy_description: Natural language description of screening logic
            data_sources: List of FMP endpoints that will be available
            example_data: Sample data structure for reference
        
        Returns:
            {
                "success": bool,
                "code": str,  # Generated Python code
                "explanation": str,  # What the code does
                "error": str  # If generation failed
            }
        """
        prompt = self._build_screening_prompt(strategy_description, data_sources, example_data)
        
        try:
            llm_config = LLMConfig.from_config()
            response = await self.llm_handler.acompletion(
                messages=[{"role": "user", "content": prompt}],
                model=llm_config.model
            )
            
            response_text = response.choices[0].message.content
            
            # Extract code from markdown if wrapped
            code = self._extract_code_from_markdown(response_text)
            
            # Validate generated code
            validation = code_sandbox.test_strategy_code(code)
            
            if not validation["success"]:
                return {
                    "success": False,
                    "code": code,
                    "explanation": "",
                    "error": f"Generated code failed validation: {', '.join(validation['errors'])}"
                }
            
            # Extract explanation (text before first code block)
            explanation = self._extract_explanation(response_text)
            
            return {
                "success": True,
                "code": code,
                "explanation": explanation,
                "error": None
            }
        
        except Exception as e:
            logger.error(f"Error generating screening code: {str(e)}", exc_info=True)
            return {
                "success": False,
                "code": "",
                "explanation": "",
                "error": str(e)
            }
    
    async def generate_management_code(
        self,
        strategy_description: str,
        risk_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate position management function code
        
        Args:
            strategy_description: Natural language description of management logic
            risk_params: Risk parameters (stop_loss_pct, take_profit_pct, etc.)
        
        Returns:
            {
                "success": bool,
                "code": str,
                "explanation": str,
                "error": str
            }
        """
        prompt = self._build_management_prompt(strategy_description, risk_params)
        
        try:
            llm_config = LLMConfig.from_config()
            response = await self.llm_handler.acompletion(
                messages=[{"role": "user", "content": prompt}],
                model=llm_config.model
            )
            
            response_text = response.choices[0].message.content
            code = self._extract_code_from_markdown(response_text)
            
            # Validate
            validation = code_sandbox.test_strategy_code("", code)
            
            if not validation["management_valid"]:
                return {
                    "success": False,
                    "code": code,
                    "explanation": "",
                    "error": f"Generated code failed validation: {', '.join(validation['errors'])}"
                }
            
            explanation = self._extract_explanation(response_text)
            
            return {
                "success": True,
                "code": code,
                "explanation": explanation,
                "error": None
            }
        
        except Exception as e:
            logger.error(f"Error generating management code: {str(e)}", exc_info=True)
            return {
                "success": False,
                "code": "",
                "explanation": "",
                "error": str(e)
            }
    
    def _build_screening_prompt(
        self,
        strategy_description: str,
        data_sources: list[str],
        example_data: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for screening code generation"""
        
        data_context = ""
        if example_data:
            data_context = f"""
Example data structure that will be available:
```python
{json.dumps(example_data, indent=2, default=str)[:1000]}  # Truncated for brevity
```
"""
        
        return f"""Generate a Python function that screens stocks for a trading strategy.

STRATEGY DESCRIPTION:
{strategy_description}

AVAILABLE DATA SOURCES:
The function will receive a `data` dict with these FMP endpoints:
{', '.join(f'"{ds}"' for ds in data_sources)}

{data_context}

FUNCTION SIGNATURE:
```python
def screen(ticker: str, data: dict) -> dict:
    \"\"\"
    Screen a ticker for potential buy.
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")
        data: Dict with keys like "income-statement", "key-metrics", etc.
    
    Returns:
        {{
            "action": "BUY" | "SKIP",
            "signal": "BULLISH" | "BEARISH" | "NEUTRAL",
            "confidence": 0-100,
            "reason": "Brief explanation"
        }}
    \"\"\"
    # YOUR CODE HERE
```

REQUIREMENTS:
1. Return a dict with keys: action, signal, confidence, reason
2. Handle missing/incomplete data gracefully (return SKIP if insufficient data)
3. Use simple Python (no external imports except math, statistics, datetime)
4. Include comments explaining the logic
5. Be specific with thresholds (e.g., "revenue growth > 20%")

EXAMPLE:
```python
def screen(ticker: str, data: dict) -> dict:
    # Get income statement data
    income_stmt = data.get('income-statement', [])
    if not income_stmt or len(income_stmt) < 2:
        return {{"action": "SKIP", "signal": "NEUTRAL", "confidence": 0, "reason": "Insufficient data"}}
    
    # Calculate revenue growth
    current_revenue = income_stmt[0].get('revenue', 0)
    previous_revenue = income_stmt[1].get('revenue', 1)  # Avoid division by zero
    growth_pct = ((current_revenue - previous_revenue) / previous_revenue) * 100
    
    # Decision logic
    if growth_pct > 20:
        return {{"action": "BUY", "signal": "BULLISH", "confidence": 80, "reason": f"Strong revenue growth: {{growth_pct:.1f}}%"}}
    else:
        return {{"action": "SKIP", "signal": "NEUTRAL", "confidence": 60, "reason": f"Low growth: {{growth_pct:.1f}}%"}}
```

Generate the complete function with clear logic and error handling:"""
    
    def _build_management_prompt(
        self,
        strategy_description: str,
        risk_params: Dict[str, Any]
    ) -> str:
        """Build prompt for management code generation"""
        
        return f"""Generate a Python function that manages open positions for a trading strategy.

STRATEGY DESCRIPTION:
{strategy_description}

RISK PARAMETERS:
- Stop Loss: {risk_params.get('stop_loss_pct', 10)}%
- Take Profit: {risk_params.get('take_profit_pct', 25)}%
- Max Hold Days: {risk_params.get('max_hold_days', 'None')}

FUNCTION SIGNATURE:
```python
def manage(ticker: str, position: dict, data: dict) -> dict:
    \"\"\"
    Decide what to do with an open position.
    
    Args:
        ticker: Stock ticker symbol
        position: {{
            "shares": float,
            "entry_price": float,
            "current_price": float,
            "pnl_pct": float,  # Profit/loss percentage
            "days_held": int
        }}
        data: Dict with FMP data (same as screening)
    
    Returns:
        {{
            "action": "SELL" | "HOLD" | "BUY",  # BUY = add more shares
            "signal": "BULLISH" | "BEARISH" | "NEUTRAL",
            "confidence": 0-100,
            "reason": "Brief explanation"
        }}
    \"\"\"
    # YOUR CODE HERE
```

REQUIREMENTS:
1. Implement stop loss and take profit rules
2. Handle max hold days if specified
3. Can use data to make informed decisions (e.g., check if fundamentals deteriorated)
4. Return SELL, HOLD, or BUY (to add more shares)
5. Include clear reasoning

EXAMPLE:
```python
def manage(ticker: str, position: dict, data: dict) -> dict:
    pnl_pct = position['pnl_pct']
    days_held = position['days_held']
    
    # Take profit
    if pnl_pct >= 25:
        return {{"action": "SELL", "signal": "NEUTRAL", "confidence": 100, "reason": f"Take profit: {{pnl_pct:.1f}}%"}}
    
    # Stop loss
    if pnl_pct <= -10:
        return {{"action": "SELL", "signal": "BEARISH", "confidence": 100, "reason": f"Stop loss: {{pnl_pct:.1f}}%"}}
    
    # Max hold period
    if days_held >= 90:
        return {{"action": "SELL", "signal": "NEUTRAL", "confidence": 80, "reason": "Max hold period reached"}}
    
    # Default: hold
    return {{"action": "HOLD", "signal": "NEUTRAL", "confidence": 70, "reason": f"Within targets ({{pnl_pct:.1f}}%)"}}
```

Generate the complete function with the risk parameters incorporated:"""
    
    def _extract_code_from_markdown(self, text: str) -> str:
        """Extract code from markdown code block"""
        # Look for ```python ... ``` blocks
        if "```python" in text:
            start = text.find("```python") + len("```python")
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()
        
        # Look for plain ``` ... ``` blocks
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()
        
        # No code blocks, return as-is
        return text.strip()
    
    def _extract_explanation(self, text: str) -> str:
        """Extract explanation text (before first code block)"""
        if "```" in text:
            return text[:text.find("```")].strip()
        return ""


# Global instance
strategy_code_generator = StrategyCodeGenerator()

