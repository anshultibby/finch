"""
Finch Strategy Runner — executes a single strategy tick inside the E2B sandbox.

Usage (called by the backend executor via sbx.commands.run):
    python /home/user/strategy_runner.py <strategy_id>

Environment variables (injected by the backend before every run):
    FINCH_STRATEGY_ID    — strategy UUID
    FINCH_DRY_RUN        — "true" | "false"
    FINCH_MAX_ORDER_USD  — optional float
    FINCH_MAX_DAILY_USD  — optional float
    FINCH_PLATFORM       — "kalshi" | "alpaca"
    FINCH_USER_ID        — user UUID (informational)
    FINCH_EXECUTION_ID   — execution UUID (informational)

    Platform credentials (e.g. KALSHI_API_KEY_ID, KALSHI_PRIVATE_KEY) are
    also injected by the backend and consumed by the skill clients.

Strategy files are uploaded to:
    /home/user/strategies/<strategy_id>/strategy.py
    /home/user/strategies/<strategy_id>/config.json

The runner writes a single JSON blob to stdout on exit:
    {
        "status": "success" | "error",
        "summary": "...",
        "actions": [...],
        "logs": [...],
        "error": "..." | null
    }

All other output (from print, skill libraries, etc.) goes to stderr.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Strategy files live here
STRATEGIES_DIR = Path("/home/user/strategies")
SKILLS_DIR = Path("/home/user/skills")

# Ensure skills are importable
if SKILLS_DIR.exists() and str(SKILLS_DIR) not in sys.path:
    sys.path.insert(0, str(SKILLS_DIR))


# ---------------------------------------------------------------------------
# Pydantic-free signal models (keep runner self-contained, no extra deps)
# ---------------------------------------------------------------------------

@dataclass
class EntrySignal:
    market_id: str
    side: str        # 'yes' / 'no' / 'buy' / 'sell'
    reason: str
    confidence: float = 1.0
    size_usd: Optional[float] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ExitSignal:
    position_id: str
    reason: str
    metadata: dict = field(default_factory=dict)


@dataclass
class Position:
    position_id: str
    market_id: str
    market_name: str
    side: str
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    entry_time: str
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# StrategyRunner decorator host
# ---------------------------------------------------------------------------

class _StrategyHost:
    """
    Provides the @strategy.on_entry / @strategy.on_exit decorators.
    strategy.py imports this via `from finch import strategy`.
    """

    def __init__(self):
        self._entry_fn = None
        self._exit_fn = None

    def on_entry(self, fn):
        self._entry_fn = fn
        return fn

    def on_exit(self, fn):
        self._exit_fn = fn
        return fn

    async def run_entry(self, ctx) -> list[EntrySignal]:
        if self._entry_fn is None:
            return []
        result = await self._entry_fn(ctx)
        signals = []
        for s in (result or []):
            if isinstance(s, EntrySignal):
                signals.append(s)
            elif isinstance(s, dict):
                signals.append(EntrySignal(**s))
        return signals

    async def run_exit(self, ctx, position: Position) -> Optional[ExitSignal]:
        if self._exit_fn is None:
            return None
        result = await self._exit_fn(ctx, position)
        if result is None:
            return None
        if isinstance(result, ExitSignal):
            return result
        if isinstance(result, dict):
            return ExitSignal(**result)
        return None


# ---------------------------------------------------------------------------
# Context object injected as `ctx` in strategy code
# ---------------------------------------------------------------------------

class StrategyContext:
    """
    Injected into check_entry / check_exit as `ctx`.

    Provides:
        ctx.kalshi        — KalshiContextWrapper (dry_run aware, risk limited)
        ctx.alpaca        — AlpacaContextWrapper (dry_run aware, risk limited)
        ctx.log(msg)      — structured log
        ctx.dry_run       — bool
        ctx.strategy_id   — str
        ctx.user_id       — str
        ctx.execution_id  — str
    """

    def __init__(
        self,
        strategy_id: str,
        user_id: str,
        execution_id: str,
        dry_run: bool,
        platform: str,
        max_order_usd: Optional[float],
        max_daily_usd: Optional[float],
    ):
        self.strategy_id = strategy_id
        self.user_id = user_id
        self.execution_id = execution_id
        self.dry_run = dry_run
        self.platform = platform
        self._max_order_usd = max_order_usd
        self._max_daily_usd = max_daily_usd
        self._total_spent_usd = 0.0
        self._logs: list[str] = []
        self._actions: list[dict] = []

    def log(self, message: str) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        entry = f"[{ts}] {message}"
        self._logs.append(entry)
        print(entry, file=sys.stderr)

    def _check_order_limit(self, amount_usd: float) -> bool:
        if self._max_order_usd and amount_usd > self._max_order_usd:
            self.log(f"BLOCKED: ${amount_usd:.2f} exceeds max_order_usd ${self._max_order_usd:.2f}")
            return False
        if self._max_daily_usd:
            projected = self._total_spent_usd + amount_usd
            if projected > self._max_daily_usd:
                self.log(f"BLOCKED: would exceed max_daily_usd ${self._max_daily_usd:.2f}")
                return False
        return True

    def _record_action(self, action_type: str, details: dict, amount_usd: float = 0.0) -> None:
        self._total_spent_usd += amount_usd
        self._actions.append({
            "type": action_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dry_run": self.dry_run,
            "details": details,
        })

    @property
    def kalshi(self) -> "KalshiContextWrapper":
        return KalshiContextWrapper(self)

    @property
    def alpaca(self) -> "AlpacaContextWrapper":
        return AlpacaContextWrapper(self)


class KalshiContextWrapper:
    """
    Wraps the kalshi skill library to enforce dry_run and risk limits.
    Delegates to /home/user/skills/kalshi_trading/scripts/kalshi.py
    (sync functions that manage their own event loops internally).
    """

    def __init__(self, ctx: StrategyContext):
        self._ctx = ctx
        # Lazy import the skill
        try:
            from kalshi_trading.scripts import kalshi as _kalshi
            self._lib = _kalshi
        except ImportError:
            self._lib = None

    def _require_lib(self):
        if self._lib is None:
            raise ImportError(
                "kalshi_trading skill not found. Enable the Kalshi Trading skill in Settings."
            )

    # --- Read-only ---

    def get_balance(self) -> dict:
        self._require_lib()
        return self._lib.get_balance()

    def get_positions(self, **kwargs) -> dict:
        self._require_lib()
        return self._lib.get_positions(**kwargs)

    def get_events(self, **kwargs) -> dict:
        self._require_lib()
        return self._lib.get_events(**kwargs)

    def get_event(self, event_ticker: str) -> dict:
        self._require_lib()
        return self._lib.get_event(event_ticker)

    def get_market(self, ticker: str) -> dict:
        self._require_lib()
        return self._lib.get_market(ticker)

    def get_orders(self, **kwargs) -> dict:
        self._require_lib()
        return self._lib.get_orders(**kwargs)

    # --- Write operations (respect dry_run + risk limits) ---

    def create_order(
        self,
        ticker: str,
        side: str,
        action: str,
        count: int,
        order_type: str = "market",
        price: Optional[int] = None,
    ) -> dict:
        self._require_lib()
        estimated_price = price if price else 50
        estimated_cost_usd = (count * estimated_price) / 100

        if not self._ctx._check_order_limit(estimated_cost_usd):
            return {"error": "Order blocked by risk limits", "blocked": True}

        order_details = {
            "ticker": ticker,
            "side": side,
            "action": action,
            "count": count,
            "order_type": order_type,
            "price": price,
            "estimated_cost_usd": estimated_cost_usd,
        }

        if self._ctx.dry_run:
            self._ctx.log(f"[DRY RUN] Would place Kalshi order: {order_details}")
            self._ctx._record_action("kalshi_order", order_details, estimated_cost_usd)
            return {"dry_run": True, "would_execute": order_details}

        result = self._lib.create_order(
            ticker=ticker,
            side=side,
            action=action,
            count=count,
            order_type=order_type,
            price=price,
        )
        self._ctx._record_action("kalshi_order", {**order_details, "result": result}, estimated_cost_usd)
        return result

    def cancel_order(self, order_id: str) -> dict:
        self._require_lib()
        if self._ctx.dry_run:
            self._ctx._record_action("kalshi_cancel", {"order_id": order_id})
            return {"dry_run": True, "would_cancel": order_id}
        result = self._lib.cancel_order(order_id)
        self._ctx._record_action("kalshi_cancel", {"order_id": order_id, "result": result})
        return result


class AlpacaContextWrapper:
    """Alpaca context wrapper — placeholder until Alpaca skill is implemented."""

    def __init__(self, ctx: StrategyContext):
        self._ctx = ctx

    def __getattr__(self, name: str):
        raise NotImplementedError(
            "Alpaca trading is not yet implemented in the sandbox runner. "
            "Use Kalshi or check back later."
        )


# ---------------------------------------------------------------------------
# finch module shim — strategy.py does `from finch import strategy, ...`
# ---------------------------------------------------------------------------

def _build_finch_module(host: _StrategyHost) -> Any:
    """Build a fake 'finch' module that exposes strategy + signal types."""
    import types
    mod = types.ModuleType("finch")
    mod.strategy = host
    mod.EntrySignal = EntrySignal
    mod.ExitSignal = ExitSignal
    mod.Position = Position
    sys.modules["finch"] = mod
    return mod


# ---------------------------------------------------------------------------
# Load open positions from the platform
# ---------------------------------------------------------------------------

def _load_open_positions(ctx: StrategyContext) -> list[Position]:
    """Load open positions from the configured platform."""
    try:
        if ctx.platform == "kalshi":
            from kalshi_trading.scripts import kalshi as _kalshi
            result = _kalshi.get_positions()
            if "error" in result:
                ctx.log(f"Could not load positions: {result['error']}")
                return []
            positions = []
            for p in result.get("positions", result.get("market_positions", [])):
                positions.append(Position(
                    position_id=p.get("market_id", p.get("ticker", "")),
                    market_id=p.get("market_id", p.get("ticker", "")),
                    market_name=p.get("market_title", p.get("title", "")),
                    side="yes" if p.get("position", 0) > 0 else "no",
                    size=abs(float(p.get("position", 0))),
                    entry_price=float(p.get("average_price", 50)) / 100,
                    current_price=float(p.get("last_price", 50)) / 100,
                    unrealized_pnl=float(p.get("resting_orders_count", 0)),
                    entry_time="",
                    metadata=p,
                ))
            return positions
    except Exception as e:
        ctx.log(f"Error loading positions: {e}")
    return []


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

async def run_strategy_tick(
    strategy_dir: Path,
    ctx: StrategyContext,
    host: _StrategyHost,
) -> dict:
    strategy_file = strategy_dir / "strategy.py"
    if not strategy_file.exists():
        raise FileNotFoundError(f"strategy.py not found in {strategy_dir}")

    # Execute strategy.py — registers @strategy.on_entry / @strategy.on_exit
    code = strategy_file.read_text()
    exec(compile(code, str(strategy_file), "exec"), {"__name__": "__strategy__"})

    ctx.log("Checking exits on open positions...")
    positions = _load_open_positions(ctx)
    ctx.log(f"Found {len(positions)} open position(s)")

    for position in positions:
        try:
            exit_signal = await host.run_exit(ctx, position)
            if exit_signal:
                ctx.log(f"Exit signal for {position.market_id}: {exit_signal.reason}")
                if ctx.platform == "kalshi":
                    ctx.kalshi.create_order(
                        ticker=position.market_id,
                        side="no" if position.side == "yes" else "yes",
                        action="sell",
                        count=int(position.size),
                    )
        except Exception as e:
            ctx.log(f"Error checking exit for {position.market_id}: {e}")

    ctx.log("Checking for entry signals...")
    try:
        entry_signals = await host.run_entry(ctx)
        ctx.log(f"Got {len(entry_signals)} entry signal(s)")
        for signal in entry_signals:
            ctx.log(f"Entry signal: {signal.market_id} {signal.side} — {signal.reason}")
            # Execution is handled by strategy code itself via ctx.kalshi / ctx.alpaca
    except Exception as e:
        ctx.log(f"Error in entry check: {e}")
        raise

    actions = ctx._actions
    summary_parts = []
    kalshi_orders = [a for a in actions if a["type"] == "kalshi_order"]
    if kalshi_orders:
        summary_parts.append(f"{len(kalshi_orders)} Kalshi order(s)")
    if not summary_parts:
        summary_parts.append("No trades executed")

    prefix = "[DRY RUN] " if ctx.dry_run else ""
    return {
        "status": "success",
        "summary": prefix + ", ".join(summary_parts),
        "actions": actions,
        "logs": ctx._logs,
        "error": None,
    }


def main():
    strategy_id = os.getenv("FINCH_STRATEGY_ID") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not strategy_id:
        print(json.dumps({"status": "error", "error": "FINCH_STRATEGY_ID not set", "logs": [], "actions": []}))
        sys.exit(1)

    dry_run = os.getenv("FINCH_DRY_RUN", "true").lower() == "true"
    platform = os.getenv("FINCH_PLATFORM", "kalshi")
    max_order_usd = float(os.getenv("FINCH_MAX_ORDER_USD", "0") or 0) or None
    max_daily_usd = float(os.getenv("FINCH_MAX_DAILY_USD", "0") or 0) or None
    user_id = os.getenv("FINCH_USER_ID", "")
    execution_id = os.getenv("FINCH_EXECUTION_ID", "")

    strategy_dir = STRATEGIES_DIR / strategy_id

    host = _StrategyHost()
    _build_finch_module(host)

    ctx = StrategyContext(
        strategy_id=strategy_id,
        user_id=user_id,
        execution_id=execution_id,
        dry_run=dry_run,
        platform=platform,
        max_order_usd=max_order_usd,
        max_daily_usd=max_daily_usd,
    )

    try:
        result = asyncio.run(run_strategy_tick(strategy_dir, ctx, host))
    except Exception as e:
        tb = traceback.format_exc()
        ctx.log(f"Fatal error: {e}\n{tb}")
        result = {
            "status": "error",
            "summary": f"Strategy failed: {e}",
            "actions": ctx._actions,
            "logs": ctx._logs,
            "error": str(e),
        }

    # Single JSON blob to stdout — backend parses this
    print(json.dumps(result))


if __name__ == "__main__":
    main()
