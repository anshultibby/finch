"""
StrategyContext - Safe interface for strategy code to access services

This is what gets injected into every strategy execution.
It provides audited, rate-limited access to trading services.

Extensible design:
- Add new services by creating a client class and a property here
- All services are lazy-loaded (only initialized when accessed)
- All actions are logged for audit trail
"""
from typing import Any, Optional, Dict
from datetime import datetime, timezone
from dataclasses import dataclass, field
import logging
import json

from sqlalchemy.ext.asyncio import AsyncSession

from crud.user_api_keys import get_decrypted_credentials
from models.strategies import ExecutionAction, RiskLimits

logger = logging.getLogger(__name__)


@dataclass
class StrategyContext:
    """
    Context injected into strategy code execution
    
    Provides:
    - Lazy-loaded service clients (Kalshi, Alpaca, etc.)
    - Logging and action recording
    - File access for strategy bundle
    - Risk limit enforcement
    
    Usage in strategy code:
        async def strategy(ctx):
            kalshi = await ctx.kalshi
            markets = await kalshi.get_events()
            ctx.log(f"Found {len(markets)} events")
    """
    # Identity
    user_id: str
    strategy_id: str
    execution_id: str
    
    # Execution mode
    dry_run: bool = False
    
    # Database session (for loading credentials)
    _db: AsyncSession | None = None
    
    # Risk limits
    _risk_limits: RiskLimits | None = None
    
    # Strategy files (non-code files like config.json)
    _files: dict = field(default_factory=dict)
    
    # Logging and audit
    _logs: list = field(default_factory=list)
    _actions: list = field(default_factory=list)
    _total_spent_usd: float = 0.0
    
    # Lazy-loaded clients
    _kalshi_client: Any | None = None
    _alpaca_client: Any | None = None
    
    # ─────────────────────────────────────────────────────────────────────────
    # Logging
    # ─────────────────────────────────────────────────────────────────────────
    
    def log(self, message: str) -> None:
        """Log a message (visible in execution history)"""
        timestamp = datetime.now(timezone.utc).isoformat()
        log_entry = f"[{timestamp}] {message}"
        self._logs.append(log_entry)
        logger.info(f"[Strategy {self.strategy_id}] {message}")
    
    def record_action(
        self,
        action_type: str,
        details: dict,
        amount_usd: float | None = None
    ) -> None:
        """
        Record an action taken (for audit trail)
        
        Args:
            action_type: Type of action ('kalshi_order', 'alpaca_order', 'alert', etc.)
            details: Service-specific details
            amount_usd: USD amount if applicable (for risk tracking)
        """
        action = ExecutionAction(
            type=action_type,
            timestamp=datetime.now(timezone.utc),
            dry_run=self.dry_run,
            details=details
        )
        self._actions.append(action)
        
        if amount_usd:
            self._total_spent_usd += amount_usd
        
        mode = "[DRY RUN] " if self.dry_run else ""
        self.log(f"{mode}Action: {action_type} - {json.dumps(details)}")
    
    def get_logs(self) -> list[str]:
        """Get all logs"""
        return self._logs.copy()
    
    def get_actions(self) -> list[ExecutionAction]:
        """Get all actions"""
        return self._actions.copy()
    
    # ─────────────────────────────────────────────────────────────────────────
    # File access (for strategy bundle)
    # ─────────────────────────────────────────────────────────────────────────
    
    def read_file(self, filename: str) -> str:
        """Read a strategy file (config, data, etc.)"""
        if filename not in self._files:
            raise FileNotFoundError(f"No file '{filename}' in strategy bundle")
        return self._files[filename]
    
    def read_json(self, filename: str) -> dict:
        """Read and parse a JSON config file"""
        content = self.read_file(filename)
        return json.loads(content)
    
    def read_csv(self, filename: str) -> list[dict]:
        """Read a CSV file as list of dicts"""
        import csv
        from io import StringIO
        content = self.read_file(filename)
        reader = csv.DictReader(StringIO(content))
        return list(reader)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Risk limit checking
    # ─────────────────────────────────────────────────────────────────────────
    
    def check_order_limit(self, amount_usd: float) -> bool:
        """
        Check if an order is within risk limits
        
        Note: Daily limit tracking (_total_spent_usd) is per-execution only.
        For true daily limits across executions, we'd need to query today's
        executions from the database. This is a TODO for production.
        """
        if not self._risk_limits:
            return True
        
        # Check per-order limit
        if self._risk_limits.max_order_usd:
            if amount_usd > self._risk_limits.max_order_usd:
                self.log(f"⚠️ Order ${amount_usd:.2f} exceeds max_order_usd ${self._risk_limits.max_order_usd:.2f}")
                return False
        
        # Check daily limit (within this execution only - see note above)
        if self._risk_limits.max_daily_usd:
            projected = self._total_spent_usd + amount_usd
            if projected > self._risk_limits.max_daily_usd:
                self.log(f"⚠️ Order would exceed daily limit: ${projected:.2f} > ${self._risk_limits.max_daily_usd:.2f}")
                return False
        
        return True
    
    def check_service_allowed(self, service: str) -> bool:
        """Check if a service is allowed by risk limits"""
        if not self._risk_limits:
            return True
        if not self._risk_limits.allowed_services:
            return True
        return service in self._risk_limits.allowed_services
    
    # ─────────────────────────────────────────────────────────────────────────
    # Service clients (lazy-loaded)
    # ─────────────────────────────────────────────────────────────────────────
    
    @property
    async def kalshi(self):
        """
        Get Kalshi client (lazy-loaded)
        
        Usage:
            kalshi = await ctx.kalshi
            balance = await kalshi.get_balance()
        """
        if not self.check_service_allowed("kalshi"):
            raise PermissionError("Kalshi is not allowed for this strategy")
        
        if self._kalshi_client is None:
            if self._db is None:
                raise RuntimeError("Database session not available")
            
            creds = await get_decrypted_credentials(self._db, self.user_id, "kalshi")
            if not creds:
                raise ValueError("Kalshi credentials not configured. Please add your Kalshi API key in settings.")
            
            from modules.tools.clients.kalshi import KalshiClient
            self._kalshi_client = KalshiClient(
                api_key_id=creds["api_key_id"],
                private_key_pem=creds["private_key"]
            )
            self.log("Initialized Kalshi client")
        
        # Return wrapper that enforces dry_run and risk limits
        return KalshiContextWrapper(self._kalshi_client, self)
    
    @property
    async def alpaca(self):
        """
        Get Alpaca client (lazy-loaded)
        
        Usage:
            alpaca = await ctx.alpaca
            account = await alpaca.get_account()
        
        TODO: Implement when Alpaca integration is added
        """
        if not self.check_service_allowed("alpaca"):
            raise PermissionError("Alpaca is not allowed for this strategy")
        
        if self._alpaca_client is None:
            if self._db is None:
                raise RuntimeError("Database session not available")
            
            creds = await get_decrypted_credentials(self._db, self.user_id, "alpaca")
            if not creds:
                raise ValueError("Alpaca credentials not configured. Please add your Alpaca API key in settings.")
            
            # TODO: Import and initialize Alpaca client when implemented
            # from modules.tools.clients.alpaca import AlpacaClient
            # self._alpaca_client = AlpacaClient(...)
            raise NotImplementedError("Alpaca client not yet implemented")
        
        return AlpacaContextWrapper(self._alpaca_client, self)
    
    async def cleanup(self) -> None:
        """Cleanup resources (close clients)"""
        if self._kalshi_client:
            try:
                await self._kalshi_client.close()
            except Exception:
                pass
        if self._alpaca_client:
            try:
                await self._alpaca_client.close()
            except Exception:
                pass


class KalshiContextWrapper:
    """
    Wrapper around KalshiClient that:
    - Enforces dry_run mode
    - Checks risk limits before orders
    - Records all actions
    """
    
    def __init__(self, client, ctx: StrategyContext):
        self._client = client
        self._ctx = ctx
    
    # ─────────────────────────────────────────────────────────────────────────
    # Read-only operations (always allowed)
    # ─────────────────────────────────────────────────────────────────────────
    
    async def get_balance(self):
        """Get account balance"""
        result = await self._client.get_balance()
        self._ctx.log(f"Kalshi balance: ${result.get('balance', 0) / 100:.2f}")
        return result
    
    async def get_positions(self, limit: int = 100):
        """Get current positions"""
        return await self._client.get_positions(limit=limit)
    
    async def get_portfolio(self):
        """Get full portfolio"""
        return await self._client.get_portfolio()
    
    async def get_events(self, limit: int = 20, status: str = "open"):
        """Get events"""
        return await self._client.get_events(limit=limit, status=status)
    
    async def get_event(self, event_ticker: str):
        """Get single event"""
        return await self._client.get_event(event_ticker)
    
    async def get_market(self, ticker: str):
        """Get single market"""
        return await self._client.get_market(ticker)
    
    async def get_orders(self, ticker: str | None = None, status: str = "resting"):
        """Get orders"""
        return await self._client.get_orders(ticker=ticker, status=status)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Write operations (respect dry_run and risk limits)
    # ─────────────────────────────────────────────────────────────────────────
    
    async def create_order(
        self,
        ticker: str,
        side: str,
        action: str,
        count: int,
        type: str = "market",
        price: Optional[int] = None
    ):
        """
        Create an order (respects dry_run and risk limits)
        
        Args:
            ticker: Market ticker
            side: "yes" or "no"
            action: "buy" or "sell"
            count: Number of contracts
            type: "market" or "limit"
            price: Price in cents (for limit orders)
        """
        # Estimate cost (rough: count * price or count * 50 for market)
        estimated_price = price if price else 50  # Assume 50 cents for market orders
        estimated_cost_usd = (count * estimated_price) / 100
        
        # Check risk limits
        if not self._ctx.check_order_limit(estimated_cost_usd):
            return {
                "error": "Order exceeds risk limits",
                "blocked": True,
                "estimated_cost_usd": estimated_cost_usd
            }
        
        order_details = {
            "ticker": ticker,
            "side": side,
            "action": action,
            "count": count,
            "type": type,
            "price": price,
            "estimated_cost_usd": estimated_cost_usd
        }
        
        if self._ctx.dry_run:
            self._ctx.record_action("kalshi_order", order_details, estimated_cost_usd)
            return {
                "dry_run": True,
                "would_execute": order_details,
                "message": f"DRY RUN: Would {action} {count} {side} contracts on {ticker}"
            }
        
        # Execute real order
        result = await self._client.create_order(
            ticker=ticker,
            side=side,
            action=action,
            count=count,
            type=type,
            price=price
        )
        
        self._ctx.record_action("kalshi_order", {**order_details, "result": result}, estimated_cost_usd)
        return result
    
    async def cancel_order(self, order_id: str):
        """Cancel an order"""
        if self._ctx.dry_run:
            self._ctx.record_action("kalshi_cancel", {"order_id": order_id})
            return {"dry_run": True, "would_cancel": order_id}
        
        result = await self._client.cancel_order(order_id)
        self._ctx.record_action("kalshi_cancel", {"order_id": order_id, "result": result})
        return result


class AlpacaContextWrapper:
    """
    Wrapper around AlpacaClient (placeholder for future implementation)
    """
    
    def __init__(self, client, ctx: StrategyContext):
        self._client = client
        self._ctx = ctx
    
    # TODO: Implement when Alpaca integration is added
    # Will follow same pattern as KalshiContextWrapper:
    # - Read operations always allowed
    # - Write operations respect dry_run and risk limits
