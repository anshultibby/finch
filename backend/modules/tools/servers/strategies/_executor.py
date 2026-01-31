"""
Strategy Executor - Runs the strategy cycle (check signals, execute trades)

This is the main execution loop called by the scheduler:
1. Load open positions
2. Check exit signals for each position
3. Execute exits
4. Check entry signals
5. Execute entries
6. Log everything
"""
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from ._base import BaseStrategy, Position, EntrySignal, ExitSignal
from ._loader import get_strategy_loader
from modules.strategies.context import StrategyContext


async def execute_strategy_cycle(
    db: AsyncSession,
    strategy_db_record,  # Strategy ORM object
    ctx: StrategyContext
) -> Dict[str, Any]:
    """
    Execute one cycle of a strategy
    
    This is called by the scheduler at polling_interval.
    
    Args:
        db: Database session
        strategy_db_record: Strategy database record (has id, config, etc.)
        ctx: StrategyContext for this execution
        
    Returns:
        Dict with execution results for logging
    """
    start_time = datetime.now()
    
    try:
        # Load strategy class from files
        loader = get_strategy_loader()
        config = strategy_db_record.config or {}
        file_ids = config.get('file_ids', [])
        
        if not file_ids:
            raise ValueError("Strategy has no files")
        
        strategy: BaseStrategy = await loader.load_strategy(
            db=db,
            strategy_id=strategy_db_record.id,
            file_ids=file_ids
        )
        
        ctx.log(f"📋 Loaded strategy: {strategy.config.name}")
        ctx.log(f"⏱️ Platform: {strategy.config.platform}, Polling: {strategy.config.polling_interval}s")
        
        # Call on_start hook
        await strategy.on_start(ctx)
        
        # =====================================================================
        # Step 1: Load open positions
        # =====================================================================
        
        open_positions = await _load_open_positions(ctx, strategy)
        ctx.log(f"📊 Found {len(open_positions)} open positions")
        
        # =====================================================================
        # Step 2 & 3: Check exit signals and execute exits
        # =====================================================================
        
        exits_executed = []
        for position in open_positions:
            try:
                exit_signal = await strategy.should_exit(ctx, position)
                
                if exit_signal:
                    ctx.log(f"🚪 Exit signal: {position.market_name} - {exit_signal.reason}")
                    
                    # Execute exit
                    result = await strategy.execute_exit(ctx, position, exit_signal)
                    exits_executed.append({
                        'position': position.model_dump(),
                        'signal': exit_signal.model_dump(),
                        'result': result
                    })
                    
            except Exception as e:
                ctx.log(f"❌ Error checking exit for {position.market_name}: {e}")
                await strategy.on_error(ctx, e)
        
        # =====================================================================
        # Step 4 & 5: Check entry signals and execute entries
        # =====================================================================
        
        entries_executed = []
        
        # Check capital limits before entering new trades
        capital_config = strategy.config.capital
        current_deployed = sum(
            pos.size * pos.entry_price for pos in open_positions
        )
        available_capital = capital_config.total_capital - current_deployed
        
        ctx.log(f"💰 Capital: ${current_deployed:.2f} deployed / ${capital_config.total_capital:.2f} total")
        ctx.log(f"💰 Available: ${available_capital:.2f}, Max positions: {len(open_positions)}/{capital_config.max_positions}")
        
        # Check if we can enter new positions
        can_enter = (
            len(open_positions) < capital_config.max_positions and
            available_capital >= capital_config.capital_per_trade
        )
        
        if not can_enter:
            ctx.log("⏸️ Cannot enter new positions (capital or position limit)")
        
        try:
            entry_signals: List[EntrySignal] = await strategy.should_enter(ctx)
            ctx.log(f"🔍 Found {len(entry_signals)} entry signals")
            
            for signal in entry_signals:
                # Check if we still have capacity for this trade
                if not can_enter:
                    ctx.log(f"⏭️ Skipping {signal.market_name} - no capacity")
                    continue
                
                try:
                    ctx.log(f"🚪 Entry signal: {signal.market_name} - {signal.reason} (confidence: {signal.confidence:.0%})")
                    
                    # Calculate position size
                    position_size = _calculate_position_size(
                        capital_config,
                        signal.confidence,
                        available_capital
                    )
                    
                    ctx.log(f"💵 Position size: ${position_size:.2f}")
                    
                    # Execute entry with calculated size
                    result = await strategy.execute_entry(ctx, signal, position_size)
                    entries_executed.append({
                        'signal': signal.model_dump(),
                        'position_size': position_size,
                        'result': result
                    })
                    
                    # Update available capital
                    available_capital -= position_size
                    if available_capital < capital_config.capital_per_trade:
                        can_enter = False
                    
                except Exception as e:
                    ctx.log(f"❌ Error executing entry for {signal.market_name}: {e}")
                    await strategy.on_error(ctx, e)
                    
        except Exception as e:
            ctx.log(f"❌ Error checking entry signals: {e}")
            await strategy.on_error(ctx, e)
        
        # =====================================================================
        # Finish
        # =====================================================================
        
        await strategy.on_stop(ctx)
        
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        summary = f"Checked {len(open_positions)} positions, {len(entries_executed)} entries, {len(exits_executed)} exits"
        ctx.log(f"✅ Cycle complete: {summary} ({duration_ms:.0f}ms)")
        
        return {
            'success': True,
            'duration_ms': duration_ms,
            'summary': summary,
            'open_positions_checked': len(open_positions),
            'entry_signals': len(entry_signals) if entry_signals else 0,
            'entries_executed': len(entries_executed),
            'exits_executed': len(exits_executed),
            'entries': entries_executed,
            'exits': exits_executed,
        }
        
    except Exception as e:
        ctx.log(f"❌ Fatal error: {e}")
        return {
            'success': False,
            'error': str(e),
            'summary': f"Failed: {e}"
        }


async def _load_open_positions(
    ctx: StrategyContext,
    strategy: BaseStrategy
) -> List[Position]:
    """
    Load open positions for this strategy from the trading platform
    
    Returns list of Position objects
    """
    positions = []
    
    try:
        if strategy.config.platform == "polymarket":
            poly = await ctx.polymarket
            # Get user's wallet address from ctx or config
            wallet_address = strategy.get_param('wallet_address')
            if not wallet_address:
                ctx.log("⚠️ No wallet_address configured, skipping position check")
                return []
            
            wallet_data = await poly.get_wallet(wallet_address)
            if 'error' in wallet_data:
                ctx.log(f"⚠️ Error loading wallet: {wallet_data['error']}")
                return []
            
            for pos in wallet_data.get('positions', []):
                positions.append(Position(
                    position_id=pos.get('token_id', ''),
                    market_id=pos.get('condition_id', ''),
                    market_name=pos.get('market_slug', 'Unknown'),
                    side=pos.get('outcome', ''),
                    size=pos.get('size', 0),
                    entry_price=pos.get('average_price', 0),
                    current_price=pos.get('current_price', 0),
                    unrealized_pnl=pos.get('unrealized_pnl', 0),
                    entry_time=str(datetime.now()),  # TODO: Get actual time
                    metadata=pos
                ))
        
        elif strategy.config.platform == "kalshi":
            kalshi = await ctx.kalshi
            portfolio = await kalshi.get_portfolio()
            
            for pos in portfolio.get('market_positions', []):
                if pos.get('position', 0) != 0:
                    positions.append(Position(
                        position_id=pos.get('ticker', ''),
                        market_id=pos.get('ticker', ''),
                        market_name=pos.get('market_title', 'Unknown'),
                        side='yes' if pos.get('position', 0) > 0 else 'no',
                        size=abs(pos.get('position', 0)),
                        entry_price=pos.get('average_price', 0) / 100,  # Convert from cents
                        current_price=pos.get('last_price', 0) / 100,
                        unrealized_pnl=pos.get('unrealized_pnl', 0) / 100,
                        entry_time=str(datetime.now()),
                        metadata=pos
                    ))
        
        elif strategy.config.platform == "alpaca":
            # TODO: Implement Alpaca position loading
            ctx.log("⚠️ Alpaca position loading not yet implemented")
        
        else:
            ctx.log(f"⚠️ Unknown platform: {strategy.config.platform}")
    
    except Exception as e:
        ctx.log(f"⚠️ Error loading positions: {e}")
    
    return positions


def _calculate_position_size(
    capital: 'CapitalAllocation',
    confidence: float,
    available_capital: float
) -> float:
    """
    Calculate position size based on capital allocation method
    
    Args:
        capital: Capital allocation config
        confidence: Signal confidence (0-1)
        available_capital: How much capital is still available
        
    Returns:
        Position size in USD
    """
    if capital.sizing_method == "fixed":
        # Fixed size per trade
        size = capital.capital_per_trade
        
    elif capital.sizing_method == "percent_capital":
        # Percentage of total capital
        pct = capital.capital_per_trade / 100  # Treat as percentage
        size = capital.total_capital * pct
        
    elif capital.sizing_method == "kelly":
        # Kelly criterion: scale by confidence
        # Size = capital_per_trade * (2 * confidence - 1)
        # At 50% confidence: no position
        # At 75% confidence: 50% of max size
        # At 100% confidence: 100% of max size
        kelly_fraction = max(0, 2 * confidence - 1)
        size = capital.capital_per_trade * kelly_fraction
    
    else:
        size = capital.capital_per_trade
    
    # Apply limits
    size = min(size, capital.max_position_size)
    size = min(size, available_capital)
    
    return size
