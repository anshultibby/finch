"""
Create Strategy - Tool for LLM to create new trading strategies

This allows the LLM to generate strategies by creating:
1. entry.py - Entry signal logic
2. exit.py - Exit signal logic  
3. config.json - Configuration with hard priors
"""
from typing import Dict, Any


def create_strategy(
    name: str,
    thesis: str,
    platform: str,
    execution_frequency: int,
    total_capital: float,
    capital_per_trade: float,
    max_positions: int,
    entry_code: str,
    exit_code: str,
    entry_description: str,
    exit_description: str,
    parameters: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Create a new trading strategy
    
    Args:
        name: Strategy name (e.g., "Polymarket Copy Trader")
        thesis: Why this will make money (plain English)
        platform: "polymarket", "kalshi", or "alpaca"
        execution_frequency: Check for signals every N seconds
        total_capital: Total USD allocated to strategy
        capital_per_trade: USD per single trade
        max_positions: Max concurrent positions
        entry_code: Python code for entry.py (must define: async def check_entry(ctx))
        exit_code: Python code for exit.py (must define: async def check_exit(ctx, position))
        entry_description: Human-readable entry condition
        exit_description: Human-readable exit condition
        parameters: Optional strategy-specific parameters
        
    Returns:
        Dict with:
        - file_contents: Dict of filename -> code
        - validation: Any validation errors
        
    Example:
        result = create_strategy(
            name="Polymarket Copy Trader",
            thesis="Copy trades from proven successful traders",
            platform="polymarket",
            execution_frequency=60,
            total_capital=5000,
            capital_per_trade=100,
            max_positions=5,
            entry_code='''
async def check_entry(ctx):
    poly = await ctx.polymarket
    signals = []
    
    tracked_traders = ["0x742d35Cc..."]
    for trader in tracked_traders:
        trades = await poly.get_trade_history(maker_address=trader, limit=10)
        # Logic to detect new trades...
        
    return signals
''',
            exit_code='''
async def check_exit(ctx, position):
    pnl_pct = position.unrealized_pnl / position.size
    
    if pnl_pct < -0.10:  # Stop loss
        return {"position_id": position.position_id, "reason": "Stop loss"}
    if pnl_pct > 0.20:  # Take profit
        return {"position_id": position.position_id, "reason": "Take profit"}
    
    return None
''',
            entry_description="When tracked traders make a new trade",
            exit_description="Stop loss at -10%, take profit at +20%"
        )
    """
    import json
    
    # Validate required fields
    errors = []
    
    if platform not in ["polymarket", "kalshi", "alpaca"]:
        errors.append(f"Invalid platform: {platform}")
    
    if execution_frequency < 10:
        errors.append("execution_frequency must be >= 10 seconds")
    
    if capital_per_trade > total_capital:
        errors.append("capital_per_trade cannot exceed total_capital")
    
    if "async def check_entry(ctx)" not in entry_code:
        errors.append("entry_code must define: async def check_entry(ctx)")
    
    if "async def check_exit(ctx, position)" not in exit_code:
        errors.append("exit_code must define: async def check_exit(ctx, position)")
    
    if errors:
        return {
            "success": False,
            "errors": errors
        }
    
    # Generate config.json
    config = {
        "name": name,
        "thesis": thesis,
        "platform": platform,
        "execution_frequency": execution_frequency,
        "capital": {
            "total_capital": total_capital,
            "capital_per_trade": capital_per_trade,
            "max_positions": max_positions,
            "max_position_size": capital_per_trade * 2,  # Default to 2x per trade
            "max_daily_loss": total_capital * 0.10,  # Default 10% of capital
            "sizing_method": "fixed"
        },
        "entry_script": "entry.py",
        "exit_script": "exit.py",
        "entry_description": entry_description,
        "exit_description": exit_description,
        "parameters": parameters or {}
    }
    
    # Return file contents for LLM to save as ChatFiles
    return {
        "success": True,
        "files": {
            "entry.py": entry_code,
            "exit.py": exit_code,
            "config.json": json.dumps(config, indent=2)
        },
        "config": config,
        "message": f"Strategy '{name}' created. Save these 3 files as ChatFiles and deploy."
    }


# Example usage for LLM
USAGE_EXAMPLE = """
To create a Polymarket copy trading strategy:

from servers.strategies.create_strategy import create_strategy

result = create_strategy(
    name="Copy Top Traders",
    thesis="Successful traders have edge, copy their moves",
    platform="polymarket",
    execution_frequency=60,
    total_capital=5000,
    capital_per_trade=100,
    max_positions=5,
    entry_code='''
async def check_entry(ctx):
    from servers.strategies import EntrySignal
    
    poly = await ctx.polymarket
    signals = []
    
    # Get tracked traders from parameters
    tracked_traders = ctx.get_param('tracked_traders', [])
    processed_trades = ctx.load_state('processed_trades', set())
    
    for trader in tracked_traders:
        result = await poly.get_trade_history(maker_address=trader, limit=20)
        
        for trade in result.get('trades', []):
            if trade['id'] in processed_trades:
                continue
            
            processed_trades.add(trade['id'])
            
            if trade['side'] == 'BUY':
                signals.append({
                    'market_id': trade['token_id'],
                    'market_name': trade.get('market_slug', 'Unknown'),
                    'side': 'yes',
                    'reason': f"Copy trade from {trader[:10]}...",
                    'confidence': 0.8,
                    'metadata': {'original_trade': trade}
                })
    
    ctx.save_state('processed_trades', processed_trades)
    return signals
''',
    exit_code='''
async def check_exit(ctx, position):
    # Calculate P&L percentage
    pnl_pct = position.unrealized_pnl / (position.size * position.entry_price)
    
    # Stop loss at -10%
    if pnl_pct < -0.10:
        return {
            'position_id': position.position_id,
            'reason': f'Stop loss: {pnl_pct:.1%}',
            'metadata': {'exit_type': 'stop_loss'}
        }
    
    # Take profit at +20%
    if pnl_pct > 0.20:
        return {
            'position_id': position.position_id,
            'reason': f'Take profit: {pnl_pct:.1%}',
            'metadata': {'exit_type': 'take_profit'}
        }
    
    return None
''',
    entry_description="When tracked traders make a new BUY trade",
    exit_description="Stop loss -10%, take profit +20%",
    parameters={
        'tracked_traders': ['0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb'],
        'wallet_address': 'YOUR_WALLET'
    }
)

# Result contains 3 files to save:
# result['files']['entry.py']
# result['files']['exit.py']  
# result['files']['config.json']
"""
