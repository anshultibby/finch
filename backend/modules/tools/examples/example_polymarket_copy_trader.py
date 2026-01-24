"""
Example: Polymarket Copy Trading Strategy

This is what the AI would generate when user says:
"Create a bot to copy this Polymarket trader: 0x742d35Cc..."

The AI creates TWO files:
1. strategy.py (this file) - Implements BaseStrategy
2. config.json - Configuration with hard priors
"""

from servers.strategies import BaseStrategy, EntrySignal, ExitSignal, Position
from typing import Optional


class PolymarketCopyTrader(BaseStrategy):
    """
    Copies trades from specified Polymarket traders
    
    Entry: When tracked trader makes a new trade
    Exit: Stop loss at -10%, take profit at +20%
    Platform: Polymarket
    Polling: Every 60 seconds
    """
    
    def __init__(self, config):
        super().__init__(config)
        # State to track which trades we've already seen
        self.processed_trades = set()
    
    async def should_enter(self, ctx) -> list[EntrySignal]:
        """
        Check if tracked traders made new trades
        
        Returns list of entry signals (one per new trade to copy)
        """
        poly = await ctx.polymarket
        signals = []
        
        # Get tracked traders from config
        tracked_traders = self.get_param('tracked_traders', [])
        copy_percentage = self.get_param('copy_percentage', 0.5)
        min_trade_size = self.get_param('min_trade_size', 10)
        
        ctx.log(f"🔍 Checking {len(tracked_traders)} traders...")
        
        for trader_wallet in tracked_traders:
            # Get their recent trades
            result = await poly.get_trade_history(
                maker_address=trader_wallet,
                limit=20
            )
            
            if 'error' in result:
                ctx.log(f"⚠️ Error fetching trades: {result['error']}")
                continue
            
            trades = result.get('trades', [])
            
            for trade in trades:
                trade_id = trade['id']
                
                # Skip if already processed
                if trade_id in self.processed_trades:
                    continue
                
                # Mark as processed
                self.processed_trades.add(trade_id)
                
                # Only copy BUY trades
                if trade['side'] != 'BUY':
                    continue
                
                # Calculate our copy size
                their_size_usd = trade['size'] * trade['price']
                our_size_usd = their_size_usd * copy_percentage
                
                # Check minimum
                if our_size_usd < min_trade_size:
                    continue
                
                # Create entry signal
                signals.append(EntrySignal(
                    market_id=trade['token_id'],
                    market_name=trade.get('market_slug', 'Unknown'),
                    side='yes',  # Polymarket uses yes/no
                    reason=f"Copy trade from {trader_wallet[:10]}... (${their_size_usd:.2f})",
                    confidence=0.8,  # Could calculate based on trader's win rate
                    metadata={
                        'original_trade': trade,
                        'trader_wallet': trader_wallet,
                        'copy_size_usd': our_size_usd
                    }
                ))
        
        if signals:
            ctx.log(f"✅ Found {len(signals)} new trades to copy")
        
        return signals
    
    async def should_exit(self, ctx, position: Position) -> Optional[ExitSignal]:
        """
        Check if we should exit a position
        
        Exit conditions:
        - Stop loss: -10%
        - Take profit: +20%
        """
        # Calculate P&L percentage
        pnl_pct = position.unrealized_pnl / (position.size * position.entry_price)
        
        # Stop loss at -10%
        if pnl_pct < -0.10:
            return ExitSignal(
                position_id=position.position_id,
                reason=f"Stop loss triggered: {pnl_pct:.1%}",
                metadata={'exit_type': 'stop_loss', 'pnl_pct': pnl_pct}
            )
        
        # Take profit at +20%
        if pnl_pct > 0.20:
            return ExitSignal(
                position_id=position.position_id,
                reason=f"Take profit triggered: {pnl_pct:.1%}",
                metadata={'exit_type': 'take_profit', 'pnl_pct': pnl_pct}
            )
        
        # No exit signal
        return None
    
    async def execute_entry(self, ctx, signal: EntrySignal):
        """Execute entry trade"""
        poly = await ctx.polymarket
        
        # Get size from signal metadata
        size_usd = signal.metadata.get('copy_size_usd', 50)
        
        # Apply risk limits
        max_order = self.config.risk_limits.get('max_order_usd', 100)
        size_usd = min(size_usd, max_order)
        
        ctx.log(f"💰 Entering {signal.market_name}: ${size_usd}")
        
        # Place order
        result = await poly.create_order(
            token_id=signal.market_id,
            side='BUY',
            amount=size_usd,
            price=None  # Market order
        )
        
        return result
    
    async def execute_exit(self, ctx, position: Position, signal: ExitSignal):
        """Execute exit trade"""
        poly = await ctx.polymarket
        
        ctx.log(f"📤 Exiting {position.market_name}: {signal.reason}")
        
        # Sell entire position
        result = await poly.create_order(
            token_id=position.position_id,
            side='SELL',
            amount=position.size,
            price=None  # Market order
        )
        
        return result


# ============================================================================
# config.json (AI would generate this as separate file)
# ============================================================================

CONFIG_JSON = """
{
  "name": "Polymarket Copy Trader",
  "description": "Automatically copies trades from top Polymarket traders",
  "platform": "polymarket",
  "polling_interval": 60,
  "risk_limits": {
    "max_order_usd": 100,
    "max_daily_usd": 500,
    "max_position_usd": 200,
    "allowed_services": ["polymarket"]
  },
  "parameters": {
    "tracked_traders": [
      "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
    ],
    "copy_percentage": 0.5,
    "min_trade_size": 10,
    "wallet_address": "YOUR_WALLET_ADDRESS"
  }
}
"""
