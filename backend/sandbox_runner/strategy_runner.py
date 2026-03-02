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

strategy.py contract
--------------------
Define a single async function:

    async def run(ctx):
        # do whatever you want
        ctx.log("checking markets...")
        balance = ctx.kalshi.get_balance()
        ctx.kalshi.create_order(...)   # no-op in paper mode, risk-limited always

config.json contract
--------------------
    {
        "platform": "kalshi",
        "name": "...",
        "thesis": "...",
        "description": "...",
        "capital": { "total": 500, "per_trade": 50, "max_positions": 5 },
        "schedule": "0 * * * *",
        "schedule_description": "Every hour",
        "risk_limits": { "max_order_usd": 50, "max_daily_usd": 200 }
    }

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
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Strategy files live here
STRATEGIES_DIR = Path("/home/user/strategies")
SKILLS_DIR = Path("/home/user/skills")

# Ensure skills are importable
if SKILLS_DIR.exists() and str(SKILLS_DIR) not in sys.path:
    sys.path.insert(0, str(SKILLS_DIR))


# ---------------------------------------------------------------------------
# Context object — the only API exposed to strategy code
# ---------------------------------------------------------------------------

class StrategyContext:
    """
    Injected as `ctx` into the strategy's run() function.

    ctx.kalshi          — Kalshi client (dry_run aware, risk-limited)
    ctx.dry_run         — bool, True in paper mode
    ctx.log(msg)        — structured log visible in execution history
    ctx.strategy_id     — str
    ctx.user_id         — str
    ctx.execution_id    — str
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
        # Wrappers lazily created once per tick so risk tracking is shared
        self._kalshi_wrapper: Optional["KalshiClient"] = None
        self._alpaca_wrapper: Optional["AlpacaClient"] = None

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
                self.log(f"BLOCKED: would exceed max_daily_usd ${self._max_daily_usd:.2f} (spent ${self._total_spent_usd:.2f} so far)")
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
    def kalshi(self) -> "KalshiClient":
        if self._kalshi_wrapper is None:
            self._kalshi_wrapper = KalshiClient(self)
        return self._kalshi_wrapper

    @property
    def alpaca(self) -> "AlpacaClient":
        if self._alpaca_wrapper is None:
            self._alpaca_wrapper = AlpacaClient(self)
        return self._alpaca_wrapper


# ---------------------------------------------------------------------------
# Platform clients
# ---------------------------------------------------------------------------

class KalshiClient:
    """
    Thin proxy over the kalshi_trading skill that adds:
      1. dry_run enforcement on write operations (place_order, cancel_order)
      2. Risk limit checking (max_order_usd, max_daily_usd)
      3. Action recording for execution history
      4. ctx.log() on writes

    All other methods (get_balance, get_positions, get_events, get_market,
    get_markets, get_orderbook, get_orders, get_portfolio, get_event, ...)
    are forwarded directly to the skill via __getattr__.

    Strategy code can use the full kalshi skill API via ctx.kalshi.
    """

    # Methods that need risk/dry-run wrapping
    _WRITE_METHODS = {"place_order", "cancel_order"}

    def __init__(self, ctx: StrategyContext):
        self._ctx = ctx
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

    def __getattr__(self, name: str):
        """Forward any non-overridden method directly to the skill library."""
        self._require_lib()
        attr = getattr(self._lib, name, None)
        if attr is None:
            raise AttributeError(f"kalshi_trading has no attribute '{name}'")
        return attr

    def place_order(
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

        details = {
            "ticker": ticker, "side": side, "action": action,
            "count": count, "order_type": order_type, "price": price,
            "estimated_cost_usd": estimated_cost_usd,
        }

        if self._ctx.dry_run:
            self._ctx.log(f"[DRY RUN] Would place order: {details}")
            self._ctx._record_action("kalshi_order", details, estimated_cost_usd)
            return {"dry_run": True, "would_execute": details}

        result = self._lib.place_order(
            ticker=ticker, side=side, action=action,
            count=count, order_type=order_type, price=price,
        )
        self._ctx._record_action("kalshi_order", {**details, "result": result}, estimated_cost_usd)
        return result

    def cancel_order(self, order_id: str) -> dict:
        self._require_lib()
        if self._ctx.dry_run:
            self._ctx.log(f"[DRY RUN] Would cancel order {order_id}")
            self._ctx._record_action("kalshi_cancel", {"order_id": order_id})
            return {"dry_run": True, "would_cancel": order_id}
        result = self._lib.cancel_order(order_id)
        self._ctx._record_action("kalshi_cancel", {"order_id": order_id, "result": result})
        return result


class AlpacaClient:
    """Placeholder until Alpaca skill is implemented."""

    def __init__(self, ctx: StrategyContext):
        self._ctx = ctx

    def __getattr__(self, name: str):
        raise NotImplementedError(
            "Alpaca trading is not yet implemented. Use Kalshi or check back later."
        )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def run_strategy_tick(strategy_dir: Path, ctx: StrategyContext) -> dict:
    strategy_file = strategy_dir / "strategy.py"
    if not strategy_file.exists():
        raise FileNotFoundError(f"strategy.py not found in {strategy_dir}")

    code = strategy_file.read_text()

    # Execute strategy.py in an isolated namespace — it must define async def run(ctx)
    ns: dict = {}
    exec(compile(code, str(strategy_file), "exec"), ns)

    run_fn = ns.get("run")
    if run_fn is None:
        # Give a helpful hint if the common class-based mistake was made
        hint = ""
        if any(k for k in ns if not k.startswith("_") and k != "run"):
            top_level = [k for k in ns if not k.startswith("_")]
            hint = f" Found top-level names: {top_level}. strategy.py must only define `async def run(ctx)` — no classes, no other top-level objects."
        raise ValueError(f"strategy.py must define: async def run(ctx).{hint}")
    if not asyncio.iscoroutinefunction(run_fn):
        raise ValueError("run(ctx) must be an `async def` function — not a regular def.")

    await run_fn(ctx)

    # Build summary from recorded actions
    actions = ctx._actions
    order_count = sum(1 for a in actions if a["type"] == "kalshi_order")
    cancel_count = sum(1 for a in actions if a["type"] == "kalshi_cancel")

    parts = []
    if order_count:
        parts.append(f"{order_count} order(s)")
    if cancel_count:
        parts.append(f"{cancel_count} cancellation(s)")
    if not parts:
        parts.append("No trades executed")

    prefix = "[DRY RUN] " if ctx.dry_run else ""
    return {
        "status": "success",
        "summary": prefix + ", ".join(parts),
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
        result = asyncio.run(run_strategy_tick(STRATEGIES_DIR / strategy_id, ctx))
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

    print(json.dumps(result))


if __name__ == "__main__":
    main()
