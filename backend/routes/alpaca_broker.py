"""
Alpaca Broker API — programmatic account opening.
Execute Router — SnapTrade swap execution.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import httpx

from core.config import Config
from core.database import get_async_db
from auth.dependencies import get_current_user_id
import logging

logger = logging.getLogger(__name__)

# ── Alpaca Broker API router ────────────────────────────────────────────────

router = APIRouter(prefix="/alpaca/broker", tags=["alpaca-broker"])

def _alpaca_broker_base() -> str:
    if Config.ALPACA_BROKER_SANDBOX:
        return "https://broker-api.sandbox.alpaca.markets"
    return "https://broker-api.alpaca.markets"

# Cache the bearer token so we don't request a new one per API call
_token_cache: dict = {"token": None, "expires_at": 0}

async def _get_broker_token() -> str:
    """Exchange client credentials for a bearer token (cached)."""
    import time
    now = time.time()
    if _token_cache["token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["token"]

    auth_base = "https://authx.sandbox.alpaca.markets" if Config.ALPACA_BROKER_SANDBOX else "https://authx.alpaca.markets"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{auth_base}/v1/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": Config.ALPACA_BROKER_CLIENT_ID or "",
                "client_secret": Config.ALPACA_BROKER_CLIENT_SECRET or "",
            },
        )
        if resp.status_code != 200:
            logger.error(f"Alpaca token exchange failed: {resp.status_code} {resp.text}")
            raise HTTPException(status_code=503, detail="Failed to authenticate with Alpaca")
        data = resp.json()
        _token_cache["token"] = data["access_token"]
        _token_cache["expires_at"] = now + data.get("expires_in", 3600)
        return _token_cache["token"]

async def _alpaca_broker_headers() -> dict:
    token = await _get_broker_token()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

async def _seed_sandbox_funds(alpaca_account_id: str, amount: float = 10000.0):
    """Sandbox only: seed account with test funds via ACH relationship + transfer."""
    if not Config.ALPACA_BROKER_SANDBOX:
        return
    try:
        headers = await _alpaca_broker_headers()
        base = _alpaca_broker_base()
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Create ACH relationship with dummy bank info (sandbox only)
            ach = await client.post(
                f"{base}/v1/accounts/{alpaca_account_id}/ach_relationships",
                json={
                    "account_owner_name": "Test User",
                    "bank_account_type": "CHECKING",
                    "bank_account_number": "123456789",
                    "bank_routing_number": "121000358",
                    "nickname": "Test Bank",
                },
                headers=headers,
            )
            if ach.status_code not in (200, 201):
                logger.warning(f"Failed to create ACH relationship: {ach.status_code} {ach.text}")
                return
            relationship_id = ach.json().get("id")
            if not relationship_id:
                return

            # Create transfer (deposit)
            transfer = await client.post(
                f"{base}/v1/accounts/{alpaca_account_id}/transfers",
                json={
                    "transfer_type": "ach",
                    "relationship_id": relationship_id,
                    "amount": str(amount),
                    "direction": "INCOMING",
                },
                headers=headers,
            )
            if transfer.status_code in (200, 201):
                logger.info(f"Seeded sandbox account {alpaca_account_id} with ${amount:,.0f}")
            else:
                logger.warning(f"Failed to seed sandbox funds: {transfer.status_code} {transfer.text}")
    except Exception as e:
        logger.warning(f"Error seeding sandbox funds: {e}")

# ── Schemas ─────────────────────────────────────────────────────────────────

class ContactInfo(BaseModel):
    email_address: str
    phone_number: str
    street_address: list[str]
    city: str
    state: str
    postal_code: str
    country: str = "USA"

class IdentityInfo(BaseModel):
    given_name: str
    family_name: str
    date_of_birth: str  # YYYY-MM-DD
    tax_id: str         # SSN
    tax_id_type: str = "USA_SSN"
    country_of_citizenship: str = "USA"
    country_of_tax_residence: str = "USA"
    funding_source: list[str]
    employment_status: Optional[str] = None

class DisclosuresInfo(BaseModel):
    is_control_person: bool = False
    is_affiliated_exchange_or_finra: bool = False
    is_politically_exposed: bool = False
    immediate_family_exposed: bool = False

class CreateAlpacaAccountRequest(BaseModel):
    user_id: str
    contact: ContactInfo
    identity: IdentityInfo
    disclosures: DisclosuresInfo

# ── Routes ──────────────────────────────────────────────────────────────────

@router.post("/accounts")
async def create_alpaca_account(
    req: CreateAlpacaAccountRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Create a new Alpaca brokerage account for a user via Broker API."""
    from models.brokerage import AlpacaBrokerAccount

    if not Config.ALPACA_BROKER_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Alpaca Broker API not configured")

    # Check if user already has an account in progress
    existing = await db.execute(
        select(AlpacaBrokerAccount).where(AlpacaBrokerAccount.user_id == req.user_id)
    )
    existing_account = existing.scalar_one_or_none()
    if existing_account and existing_account.status not in ("PENDING", "REJECTED"):
        return {
            "success": True,
            "already_exists": True,
            "status": existing_account.status,
            "alpaca_account_id": existing_account.alpaca_account_id,
        }

    # Get client IP for agreements
    client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "0.0.0.0")
    client_ip = client_ip.split(",")[0].strip()
    signed_at = datetime.now(timezone.utc).isoformat()

    payload = {
        "contact": req.contact.model_dump(),
        "identity": req.identity.model_dump(exclude={"tax_id"}),  # rebuild below with SSN
        "disclosures": req.disclosures.model_dump(),
        "agreements": [
            {"agreement": "customer_agreement", "signed_at": signed_at, "ip_address": client_ip},
            {"agreement": "account_agreement", "signed_at": signed_at, "ip_address": client_ip},
            {"agreement": "margin_agreement", "signed_at": signed_at, "ip_address": client_ip},
        ],
    }
    # Include SSN directly (not excluded from identity)
    payload["identity"] = req.identity.model_dump()

    try:
        headers = await _alpaca_broker_headers()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{_alpaca_broker_base()}/v1/accounts",
                json=payload,
                headers=headers,
            )
            data = response.json()

        if response.status_code not in (200, 201):
            logger.error(f"Alpaca Broker API error: {response.status_code} {data}")
            raise HTTPException(status_code=400, detail=data.get("message", "Account creation failed"))

        alpaca_account_id = data.get("id")
        status = data.get("status", "SUBMITTED")

        # Store in DB (don't store SSN in kyc_snapshot)
        safe_snapshot = {
            "contact": req.contact.model_dump(exclude={"phone_number"}),
            "identity": req.identity.model_dump(exclude={"tax_id"}),
            "disclosures": req.disclosures.model_dump(),
        }
        if existing_account:
            existing_account.alpaca_account_id = alpaca_account_id
            existing_account.status = status
            existing_account.kyc_snapshot = safe_snapshot
        else:
            db.add(AlpacaBrokerAccount(
                user_id=req.user_id,
                alpaca_account_id=alpaca_account_id,
                status=status,
                kyc_snapshot=safe_snapshot,
            ))
        await db.commit()

        # Sandbox: seed account with $10k test funds
        if Config.ALPACA_BROKER_SANDBOX and alpaca_account_id:
            asyncio.ensure_future(_seed_sandbox_funds(alpaca_account_id))

        return {"success": True, "alpaca_account_id": alpaca_account_id, "status": status}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating Alpaca account: {e}")
        raise HTTPException(status_code=500, detail="Failed to create account")


@router.get("/accounts/{user_id}")
async def get_alpaca_account_status(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Get status of user's Alpaca Broker account, refreshing from API if needed."""
    from models.brokerage import AlpacaBrokerAccount

    result = await db.execute(
        select(AlpacaBrokerAccount).where(AlpacaBrokerAccount.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        return {"exists": False}

    # Poll Alpaca for latest status if not in a terminal state
    terminal_statuses = {"ACTIVE", "REJECTED", "ACCOUNT_CLOSED"}
    if account.alpaca_account_id and account.status not in terminal_statuses and Config.ALPACA_BROKER_CLIENT_ID:
        try:
            headers = await _alpaca_broker_headers()
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{_alpaca_broker_base()}/v1/accounts/{account.alpaca_account_id}",
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    new_status = data.get("status", account.status)
                    reason = data.get("action_required_reason") if new_status == "ACTION_REQUIRED" else None
                    if new_status != account.status:
                        old_status = account.status
                        account.status = new_status
                        account.action_required_reason = reason
                        await db.commit()
        except Exception as e:
            logger.warning(f"Could not refresh Alpaca account status: {e}")

    return {
        "exists": True,
        "alpaca_account_id": account.alpaca_account_id,
        "status": account.status,
        "action_required_reason": account.action_required_reason,
        "created_at": account.created_at.isoformat() if account.created_at else None,
    }


@router.get("/accounts/{user_id}/portfolio")
async def get_alpaca_portfolio(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Fetch portfolio overview (account details + positions) from Alpaca Broker API."""
    from models.brokerage import AlpacaBrokerAccount

    result = await db.execute(
        select(AlpacaBrokerAccount).where(AlpacaBrokerAccount.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="No Alpaca account found")
    if account.status != "ACTIVE":
        raise HTTPException(status_code=400, detail=f"Account not active (status: {account.status})")

    headers = await _alpaca_broker_headers()
    base = _alpaca_broker_base()
    acct_id = account.alpaca_account_id

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            acct_resp, pos_resp = await asyncio.gather(
                client.get(f"{base}/v1/trading/accounts/{acct_id}/account", headers=headers),
                client.get(f"{base}/v1/trading/accounts/{acct_id}/positions", headers=headers),
            )
    except Exception as e:
        logger.error(f"Failed to fetch Alpaca portfolio: {e}")
        raise HTTPException(status_code=502, detail="Failed to connect to Alpaca")

    if acct_resp.status_code != 200:
        logger.error(f"Alpaca account fetch failed: {acct_resp.status_code} {acct_resp.text}")
        raise HTTPException(status_code=502, detail="Failed to fetch account details from Alpaca")

    acct_data = acct_resp.json()
    positions = pos_resp.json() if pos_resp.status_code == 200 else []

    return {
        "success": True,
        "account": {
            "equity": acct_data.get("equity"),
            "cash": acct_data.get("cash"),
            "buying_power": acct_data.get("buying_power"),
            "portfolio_value": acct_data.get("portfolio_value", acct_data.get("equity")),
            "long_market_value": acct_data.get("long_market_value"),
            "short_market_value": acct_data.get("short_market_value"),
            "last_equity": acct_data.get("last_equity"),
            "currency": acct_data.get("currency", "USD"),
            "status": acct_data.get("status"),
            "account_number": acct_data.get("account_number"),
        },
        "positions": [
            {
                "symbol": p.get("symbol"),
                "qty": p.get("qty"),
                "side": p.get("side"),
                "market_value": p.get("market_value"),
                "cost_basis": p.get("cost_basis"),
                "avg_entry_price": p.get("avg_entry_price"),
                "current_price": p.get("current_price"),
                "unrealized_pl": p.get("unrealized_pl"),
                "unrealized_plpc": p.get("unrealized_plpc"),
                "change_today": p.get("change_today"),
            }
            for p in positions
        ],
        "position_count": len(positions),
    }


# ── Order management ───────────────────────────────────────────────────────

class PlaceOrderRequest(BaseModel):
    user_id: str
    symbol: str
    side: str          # "buy" or "sell"
    qty: Optional[float] = None       # shares (mutually exclusive with notional)
    notional: Optional[float] = None  # dollar amount
    order_type: str = "market"        # market, limit, stop, stop_limit
    time_in_force: str = "day"        # day, gtc, ioc, fok
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None


async def _get_alpaca_account_id(user_id: str, db: AsyncSession) -> str:
    """Look up the user's active Alpaca account ID or raise 404/400."""
    from models.brokerage import AlpacaBrokerAccount
    result = await db.execute(
        select(AlpacaBrokerAccount).where(AlpacaBrokerAccount.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="No Alpaca account found")
    if account.status != "ACTIVE":
        raise HTTPException(status_code=400, detail=f"Account not active (status: {account.status})")
    return account.alpaca_account_id


@router.post("/accounts/{user_id}/orders")
async def place_order(
    user_id: str,
    req: PlaceOrderRequest,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Place a buy or sell order on the user's Alpaca account."""
    acct_id = await _get_alpaca_account_id(user_id, db)
    headers = await _alpaca_broker_headers()

    order_body: dict = {
        "symbol": req.symbol.upper(),
        "side": req.side.lower(),
        "type": req.order_type.lower(),
        "time_in_force": req.time_in_force.lower(),
    }
    if req.qty is not None:
        order_body["qty"] = str(req.qty)
    elif req.notional is not None:
        order_body["notional"] = str(req.notional)
    else:
        raise HTTPException(status_code=400, detail="Either qty or notional is required")
    if req.limit_price is not None:
        order_body["limit_price"] = str(req.limit_price)
    if req.stop_price is not None:
        order_body["stop_price"] = str(req.stop_price)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{_alpaca_broker_base()}/v1/trading/accounts/{acct_id}/orders",
            json=order_body,
            headers=headers,
        )

    data = resp.json()
    if resp.status_code not in (200, 201):
        logger.error(f"Alpaca order failed: {resp.status_code} {data}")
        raise HTTPException(status_code=400, detail=data.get("message", "Order failed"))

    return {
        "success": True,
        "order": {
            "id": data.get("id"),
            "symbol": data.get("symbol"),
            "side": data.get("side"),
            "qty": data.get("qty"),
            "notional": data.get("notional"),
            "type": data.get("type"),
            "time_in_force": data.get("time_in_force"),
            "status": data.get("status"),
            "filled_qty": data.get("filled_qty"),
            "filled_avg_price": data.get("filled_avg_price"),
            "created_at": data.get("created_at"),
        },
    }


@router.get("/accounts/{user_id}/orders")
async def list_orders(
    user_id: str,
    status: str = "all",  # open, closed, all
    limit: int = 50,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """List orders for the user's Alpaca account."""
    acct_id = await _get_alpaca_account_id(user_id, db)
    headers = await _alpaca_broker_headers()

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{_alpaca_broker_base()}/v1/trading/accounts/{acct_id}/orders",
            params={"status": status, "limit": limit, "direction": "desc"},
            headers=headers,
        )

    if resp.status_code != 200:
        return []

    return [
        {
            "id": o.get("id"),
            "symbol": o.get("symbol"),
            "side": o.get("side"),
            "qty": o.get("qty"),
            "notional": o.get("notional"),
            "type": o.get("type"),
            "time_in_force": o.get("time_in_force"),
            "status": o.get("status"),
            "filled_qty": o.get("filled_qty"),
            "filled_avg_price": o.get("filled_avg_price"),
            "limit_price": o.get("limit_price"),
            "stop_price": o.get("stop_price"),
            "created_at": o.get("created_at"),
            "filled_at": o.get("filled_at"),
        }
        for o in resp.json()
    ]


@router.delete("/accounts/{user_id}/orders/{order_id}")
async def cancel_order(
    user_id: str,
    order_id: str,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Cancel an open order."""
    acct_id = await _get_alpaca_account_id(user_id, db)
    headers = await _alpaca_broker_headers()

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.delete(
            f"{_alpaca_broker_base()}/v1/trading/accounts/{acct_id}/orders/{order_id}",
            headers=headers,
        )

    if resp.status_code not in (200, 204):
        raise HTTPException(status_code=400, detail="Failed to cancel order")

    return {"success": True}


@router.delete("/accounts/{user_id}/positions/{symbol}")
async def close_position(
    user_id: str,
    symbol: str,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Close (sell all) a position by symbol."""
    acct_id = await _get_alpaca_account_id(user_id, db)
    headers = await _alpaca_broker_headers()

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.delete(
            f"{_alpaca_broker_base()}/v1/trading/accounts/{acct_id}/positions/{symbol.upper()}",
            headers=headers,
        )

    data = resp.json() if resp.status_code in (200, 201) else {}
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=400, detail=data.get("message", "Failed to close position"))

    return {"success": True, "order": data}


class ExecuteBrokerSwapRequest(BaseModel):
    user_id: str
    alpaca_account_id: str
    sell_symbol: str
    sell_qty: float
    buy_symbol: str
    buy_notional: float

@router.post("/orders/swap")
async def execute_broker_swap(
    req: ExecuteBrokerSwapRequest,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Execute a TLH swap via Alpaca Broker API (for Finch-managed accounts)."""
    from models.brokerage import AlpacaBrokerAccount

    result = await db.execute(
        select(AlpacaBrokerAccount).where(
            AlpacaBrokerAccount.user_id == req.user_id,
            AlpacaBrokerAccount.alpaca_account_id == req.alpaca_account_id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.status != "ACTIVE":
        raise HTTPException(status_code=400, detail=f"Account not active (status: {account.status})")

    headers = await _alpaca_broker_headers()
    order_url = f"{_alpaca_broker_base()}/v1/trading/accounts/{req.alpaca_account_id}/orders"

    async with httpx.AsyncClient(timeout=30.0) as client:
        sell_resp = await client.post(order_url, json={
            "symbol": req.sell_symbol,
            "qty": str(req.sell_qty),
            "side": "sell",
            "type": "market",
            "time_in_force": "day",
        }, headers=headers)
        if sell_resp.status_code not in (200, 201):
            raise HTTPException(status_code=400, detail=f"Sell order failed: {sell_resp.json().get('message', 'unknown')}")
        sell_order = sell_resp.json()

        buy_resp = await client.post(order_url, json={
            "symbol": req.buy_symbol,
            "notional": str(req.buy_notional),
            "side": "buy",
            "type": "market",
            "time_in_force": "day",
        }, headers=headers)
        if buy_resp.status_code not in (200, 201):
            raise HTTPException(status_code=207, detail=f"Sell placed but buy failed: {buy_resp.json().get('message', 'unknown')}")
        buy_order = buy_resp.json()

    return {
        "success": True,
        "sell_order": sell_order,
        "buy_order": buy_order,
        "message": f"Sold {req.sell_qty} {req.sell_symbol}, bought ${req.buy_notional:,.0f} of {req.buy_symbol}",
    }


# ── Execute Swap router (SnapTrade) ─────────────────────────────────────────

execute_router = APIRouter(prefix="/execute", tags=["execute"])

class ExecuteSwapRequest(BaseModel):
    user_id: str
    account_id: str       # SnapTrade account ID
    sell_symbol: str      # ticker e.g. "NVDA"
    sell_qty: float
    buy_symbol: str       # ticker e.g. "AMD"
    buy_notional: float   # dollar amount to buy

@execute_router.post("/swap")
async def execute_swap(
    req: ExecuteSwapRequest,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Execute a TLH swap via SnapTrade (sell + buy market orders)."""
    from skills.snaptrade.scripts.reference.search_symbols import search_symbols
    from skills.snaptrade.scripts.trading.place_order import place_order

    # 1. Find sell symbol universal ID
    sell_search = await asyncio.to_thread(search_symbols, req.user_id, req.account_id, req.sell_symbol)
    if not sell_search.get("success") or not sell_search.get("symbols"):
        raise HTTPException(status_code=400, detail=f"Could not find symbol {req.sell_symbol} in this account")

    # Find best match (exact ticker match preferred)
    def find_symbol_id(symbols: list, ticker: str) -> Optional[str]:
        for s in symbols:
            sym = s.get("symbol") or s
            t = (sym.get("symbol") or "").upper()
            if t == ticker.upper():
                return sym.get("id")
        # Fall back to first result
        first = symbols[0]
        sym = first.get("symbol") or first
        return sym.get("id")

    sell_symbol_id = find_symbol_id(sell_search["symbols"], req.sell_symbol)
    if not sell_symbol_id:
        raise HTTPException(status_code=400, detail=f"No exact match for {req.sell_symbol}")

    # 2. Find buy symbol universal ID
    buy_search = await asyncio.to_thread(search_symbols, req.user_id, req.account_id, req.buy_symbol)
    if not buy_search.get("success") or not buy_search.get("symbols"):
        raise HTTPException(status_code=400, detail=f"Could not find symbol {req.buy_symbol} in this account")

    buy_symbol_id = find_symbol_id(buy_search["symbols"], req.buy_symbol)
    if not buy_symbol_id:
        raise HTTPException(status_code=400, detail=f"No exact match for {req.buy_symbol}")

    # 3. Place sell order (market, day, exact quantity)
    sell_result = await asyncio.to_thread(
        place_order, req.user_id, req.account_id, "SELL", sell_symbol_id, "Market", "Day", req.sell_qty
    )
    if not sell_result.get("success"):
        raise HTTPException(status_code=400, detail=f"Sell order failed: {sell_result.get('error', 'unknown error')}")

    # 4. Place buy order (market, day, notional value)
    buy_result = await asyncio.to_thread(
        place_order, req.user_id, req.account_id, "BUY", buy_symbol_id, "Market", "Day",
        notional_value=req.buy_notional
    )
    if not buy_result.get("success"):
        # Sell already went through — surface the error but note sell happened
        raise HTTPException(
            status_code=207,
            detail=f"Sell order placed but buy order failed: {buy_result.get('error', 'unknown error')}. Check your account."
        )

    return {
        "success": True,
        "sell_order": sell_result.get("order"),
        "buy_order": buy_result.get("order"),
        "message": f"Sold {req.sell_qty} {req.sell_symbol}, bought ${req.buy_notional:,.0f} of {req.buy_symbol}",
    }
