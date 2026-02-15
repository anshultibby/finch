"""
Polymarket Wallet - Position and P&L Tracking

Monitor wallet positions and performance.
"""
from .._client import call_dome_api
from ..models import (
    GetWalletInfoInput, GetWalletInfoOutput,
    GetPositionsInput, GetPositionsOutput,
    GetWalletPnLInput, GetWalletPnLOutput,
    GetWalletActivityInput, GetWalletActivityOutput,
    GetWalletTradesInput, GetWalletTradesOutput
)


def get_wallet_info(input: GetWalletInfoInput) -> GetWalletInfoOutput:
    """
    Get wallet address mapping (EOA <-> Proxy).
    
    Automatically determines if the provided wallet_address is an EOA or proxy
    by trying both with the API.
    """
    from .._client import DomeAPIError
    
    # Try as proxy first (most common for trading wallets)
    try:
        result = call_dome_api("/polymarket/wallet", {"proxy": input.wallet_address})
        return GetWalletInfoOutput(**result)
    except DomeAPIError:
        pass
    
    # Try as EOA
    try:
        result = call_dome_api("/polymarket/wallet", {"eoa": input.wallet_address})
        return GetWalletInfoOutput(**result)
    except DomeAPIError:
        pass
    
    # If both failed, raise informative error
    raise DomeAPIError(f"Could not find wallet info for address {input.wallet_address}. Address may be invalid or not used on Polymarket.")


def get_positions(input: GetPositionsInput) -> GetPositionsOutput:
    """
    Get all positions for a wallet on Polymarket.
    """
    endpoint = f"/polymarket/positions/wallet/{input.wallet_address}"
    params = input.model_dump(exclude={"wallet_address"}, exclude_none=True)
    result = call_dome_api(endpoint, params)
    return GetPositionsOutput(**result)


def get_wallet_pnl(input: GetWalletPnLInput) -> GetWalletPnLOutput:
    """
    Get profit and loss history for a wallet on Polymarket.
    
    NOTE: This returns REALIZED P&L only (from sells/redeems), not unrealized.
    """
    endpoint = f"/polymarket/wallet/pnl/{input.wallet_address}"
    params = input.model_dump(exclude={"wallet_address"}, exclude_none=True)
    result = call_dome_api(endpoint, params)
    return GetWalletPnLOutput(**result)


def get_wallet_activity(input: GetWalletActivityInput) -> GetWalletActivityOutput:
    """
    Get on-chain activity (SPLITS, MERGES, REDEEMS) for a wallet.
    
    NOTE: Returns SPLITS, MERGES, and REDEEMS only - NOT BUY/SELL trades.
    For BUY/SELL trades, use get_wallet_trades() or trading.get_orders().
    """
    params = input.model_dump(exclude_none=True)
    params["user"] = params.pop("wallet_address")
    result = call_dome_api("/polymarket/activity", params)
    return GetWalletActivityOutput(**result)


def get_wallet_trades(input: GetWalletTradesInput) -> GetWalletTradesOutput:
    """
    Get actual BUY/SELL trade executions for a wallet.
    
    This returns real trade execution data with prices, shares, and timestamps.
    Use this for copy trading, trade analysis, and performance tracking.
    """
    params = input.model_dump(exclude_none=True)
    params["user"] = params.pop("wallet_address")
    result = call_dome_api("/polymarket/orders", params)
    return GetWalletTradesOutput(**result)
