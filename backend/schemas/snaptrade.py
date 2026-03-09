"""
SnapTrade-related Pydantic models
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
import pandas as pd


class SnapTradeConnectionRequest(BaseModel):
    """Request to initiate SnapTrade connection"""
    user_id: str
    redirect_uri: str  # Where to redirect after successful connection


class SnapTradeConnectionResponse(BaseModel):
    """Response with SnapTrade connection URL"""
    success: bool
    message: str
    redirect_uri: Optional[str] = None


class SnapTradeCallbackRequest(BaseModel):
    """Callback after successful connection"""
    user_id: str


class SnapTradeStatusResponse(BaseModel):
    """Response for connection status check"""
    success: bool
    message: str
    is_connected: bool
    account_count: Optional[int] = None
    brokerages: Optional[List[str]] = None


# SnapTrade API Response Models (for parsing their responses)

class SnapTradeSymbolInfo(BaseModel):
    """Symbol info from SnapTrade API (innermost level)"""
    id: Optional[str] = None
    symbol: str  # This is the actual ticker
    description: Optional[str] = None
    raw_symbol: Optional[str] = None
    
    class Config:
        extra = "allow"  # Ignore extra fields we don't need


class SnapTradeSymbolWrapper(BaseModel):
    """Middle wrapper level for symbol"""
    symbol: SnapTradeSymbolInfo  # Contains the actual symbol object
    id: Optional[str] = None
    
    class Config:
        extra = "allow"


class SnapTradePositionResponse(BaseModel):
    """Position response from SnapTrade API"""
    symbol: SnapTradeSymbolWrapper  # Only 2 levels deep!
    units: float
    price: float
    open_pnl: Optional[float] = None
    average_purchase_price: Optional[float] = None
    
    class Config:
        extra = "allow"
    
    def get_ticker(self) -> str:
        """Extract the actual ticker symbol"""
        return self.symbol.symbol.symbol  # symbol.symbol.symbol (not 4 levels)
    
    def get_value(self) -> float:
        """Calculate position value"""
        return self.units * self.price
    
    def to_position(self) -> 'Position':
        """Convert to clean Position model"""
        total_cost = None
        if self.average_purchase_price is not None:
            total_cost = self.units * self.average_purchase_price
        
        return Position(
            symbol=self.get_ticker(),
            quantity=self.units,
            price=self.price,
            value=self.get_value(),
            average_purchase_price=self.average_purchase_price,
            total_cost=total_cost
        )


class SnapTradeAccountMeta(BaseModel):
    """Account metadata"""
    type: Optional[str] = None
    brokerage_account_type: Optional[str] = None
    institution_name: Optional[str] = None
    
    class Config:
        extra = "allow"


class SnapTradeAccountBalance(BaseModel):
    """Account balance structure"""
    total: Optional[dict] = None
    
    class Config:
        extra = "allow"
    
    def get_amount(self) -> float:
        """Extract total amount"""
        if self.total and isinstance(self.total, dict):
            return float(self.total.get('amount', 0))
        return 0.0


class SnapTradeAccountResponse(BaseModel):
    """Account response from SnapTrade API"""
    id: str
    name: Optional[str] = "Unknown"
    number: Optional[str] = ""
    institution_name: Optional[str] = "Unknown"
    meta: Optional[SnapTradeAccountMeta] = None
    balance: Optional[SnapTradeAccountBalance] = None
    
    class Config:
        extra = "allow"
    
    def get_account_type(self) -> str:
        """Extract account type"""
        if self.meta and self.meta.brokerage_account_type:
            return self.meta.brokerage_account_type
        return "Unknown"
    
    def get_balance(self) -> float:
        """Extract balance amount"""
        if self.balance:
            return self.balance.get_amount()
        return 0.0
    
    def to_account(self, positions: List['Position'], total_value: float, status: Optional[str] = None) -> 'Account':
        """Convert to clean Account model"""
        return Account(
            id=self.id,
            name=self.name or 'Unknown',
            number=self.number or '',
            type=self.get_account_type(),
            institution=self.institution_name or 'Unknown',
            balance=self.get_balance(),
            positions=positions,
            total_value=total_value,
            position_count=len(positions),
            status=status
        )


# Portfolio data models (our cleaned-up versions)

class Position(BaseModel):
    """Individual position/holding"""
    symbol: str
    quantity: float
    price: float
    value: float
    average_purchase_price: Optional[float] = None
    total_cost: Optional[float] = None  # quantity * average_purchase_price
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "quantity": 10.0,
                "price": 150.50,
                "value": 1505.00,
                "average_purchase_price": 145.00,
                "total_cost": 1450.00
            }
        }


class Account(BaseModel):
    """Brokerage account with positions"""
    id: str
    name: str
    number: str
    type: str
    institution: str
    balance: float
    positions: List[Position] = []
    total_value: float = 0.0
    position_count: int = 0
    status: Optional[str] = None  # 'syncing', 'error', or None for success
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "abc123",
                "name": "Robinhood IRA",
                "number": "****1234",
                "type": "IRA Roth",
                "institution": "Robinhood",
                "balance": 10000.00,
                "positions": [
                    {
                        "symbol": "AAPL",
                        "quantity": 10.0,
                        "price": 150.50,
                        "value": 1505.00
                    }
                ],
                "total_value": 1505.00,
                "position_count": 1
            }
        }
    
    def positions_to_csv(self) -> str:
        """Convert positions to CSV string"""
        if not self.positions:
            return "symbol,quantity,price,value,avg_cost,total_cost,gain_loss,gain_loss_pct\n"
        
        df = pd.DataFrame([
            {
                'symbol': pos.symbol,
                'quantity': pos.quantity,
                'price': pos.price,
                'value': pos.value,
                'avg_cost': pos.average_purchase_price,
                'total_cost': pos.total_cost,
                'gain_loss': (pos.value - pos.total_cost) if pos.total_cost is not None else None,
                'gain_loss_pct': ((pos.value - pos.total_cost) / pos.total_cost * 100) if pos.total_cost and pos.total_cost > 0 else None
            }
            for pos in self.positions
        ])
        return df.to_csv(index=False, float_format='%.4f')


class AggregatedHolding(BaseModel):
    """Aggregated position across all accounts"""
    symbol: str
    quantity: float
    price: float  # Latest price
    value: float  # Total value across all accounts
    average_purchase_price: Optional[float] = None  # Weighted average cost basis
    total_cost: Optional[float] = None  # Total cost basis across all accounts
    unrealized_gain_loss: Optional[float] = None  # value - total_cost
    unrealized_gain_loss_percent: Optional[float] = None  # (value - total_cost) / total_cost * 100
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "quantity": 25.0,
                "price": 150.50,
                "value": 3762.50,
                "average_purchase_price": 145.00,
                "total_cost": 3625.00,
                "unrealized_gain_loss": 137.50,
                "unrealized_gain_loss_percent": 3.79
            }
        }
    
    def add_position(self, pos: 'Position'):
        """Add a position to this aggregated holding"""
        self.quantity += pos.quantity
        self.value += pos.value
        self.price = pos.price  # Use latest price
        
        # Aggregate cost basis (weighted average)
        if pos.total_cost is not None:
            if self.total_cost is None:
                self.total_cost = 0.0
            self.total_cost += pos.total_cost
            
            # Recalculate weighted average purchase price
            if self.quantity > 0:
                self.average_purchase_price = self.total_cost / self.quantity
                self.unrealized_gain_loss = self.value - self.total_cost
                if self.total_cost > 0:
                    self.unrealized_gain_loss_percent = (self.unrealized_gain_loss / self.total_cost) * 100


class Portfolio(BaseModel):
    """Complete portfolio with accounts and aggregated holdings"""
    success: bool
    accounts: List[Account]
    aggregated_holdings: dict[str, AggregatedHolding]
    total_value: float
    total_positions: int
    account_count: int
    message: str
    syncing: Optional[bool] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "accounts": [
                    {
                        "id": "abc123",
                        "name": "Robinhood IRA",
                        "number": "****1234",
                        "type": "IRA Roth",
                        "institution": "Robinhood",
                        "balance": 10000.00,
                        "positions": [{"symbol": "AAPL", "quantity": 10.0, "price": 150.50, "value": 1505.00}],
                        "total_value": 1505.00,
                        "position_count": 1
                    }
                ],
                "aggregated_holdings": {
                    "AAPL": {"symbol": "AAPL", "quantity": 25.0, "price": 150.50, "value": 3762.50}
                },
                "total_value": 3762.50,
                "total_positions": 1,
                "account_count": 2,
                "message": "Found 1 unique positions across 2 accounts"
            }
        }
    
    @classmethod
    def from_accounts(cls, accounts: List[Account], syncing_count: int = 0) -> 'Portfolio':
        """
        Create a Portfolio from a list of accounts, automatically aggregating holdings
        
        Args:
            accounts: List of Account objects
            syncing_count: Number of accounts still syncing
        
        Returns:
            Portfolio with aggregated holdings
        """
        aggregated_holdings: dict[str, AggregatedHolding] = {}
        total_value = 0.0
        
        # Aggregate all positions across all accounts
        for account in accounts:
            total_value += account.total_value
            
            for position in account.positions:
                if position.symbol in aggregated_holdings:
                    # Add to existing holding
                    aggregated_holdings[position.symbol].add_position(position)
                else:
                    # Create new aggregated holding
                    gain_loss = None
                    gain_loss_pct = None
                    if position.total_cost is not None:
                        gain_loss = position.value - position.total_cost
                        if position.total_cost > 0:
                            gain_loss_pct = (gain_loss / position.total_cost) * 100
                    
                    aggregated_holdings[position.symbol] = AggregatedHolding(
                        symbol=position.symbol,
                        quantity=position.quantity,
                        price=position.price,
                        value=position.value,
                        average_purchase_price=position.average_purchase_price,
                        total_cost=position.total_cost,
                        unrealized_gain_loss=gain_loss,
                        unrealized_gain_loss_percent=gain_loss_pct
                    )
        
        # Check if still syncing
        if syncing_count > 0 and len(aggregated_holdings) == 0:
            return cls(
                success=False,
                accounts=accounts,
                aggregated_holdings={},
                total_value=0.0,
                total_positions=0,
                account_count=len(accounts),
                message=f"SnapTrade is still syncing your data ({syncing_count} account{'s' if syncing_count > 1 else ''} syncing). This usually takes 1-2 minutes after first connection. Please try asking again in a moment!",
                syncing=True
            )
        
        # Return successful portfolio
        return cls(
            success=True,
            accounts=accounts,
            aggregated_holdings=aggregated_holdings,
            total_value=round(total_value, 2),
            total_positions=len(aggregated_holdings),
            account_count=len(accounts),
            message=f"Found {len(aggregated_holdings)} unique positions across {len(accounts)} accounts"
        )
    
    def aggregated_holdings_to_csv(self) -> str:
        """Convert aggregated holdings to CSV string, sorted by value descending"""
        if not self.aggregated_holdings:
            return "symbol,quantity,price,value,avg_cost,total_cost,gain_loss,gain_loss_pct\n"
        
        df = pd.DataFrame([
            {
                'symbol': holding.symbol,
                'quantity': holding.quantity,
                'price': holding.price,
                'value': holding.value,
                'avg_cost': holding.average_purchase_price,
                'total_cost': holding.total_cost,
                'gain_loss': holding.unrealized_gain_loss,
                'gain_loss_pct': holding.unrealized_gain_loss_percent
            }
            for holding in self.aggregated_holdings.values()
        ])
        df = df.sort_values('value', ascending=False)
        return df.to_csv(index=False, float_format='%.4f')
    
    def to_csv_format(self) -> Dict[str, Any]:
        """
        Convert portfolio to CSV format for LLM consumption.
        Returns ONLY summary info + aggregated CSV (not per-account details).
        This is much more efficient - the LLM gets all positions in one CSV.
        """
        result = {
            "success": self.success,
            "message": self.message,
            "total_value": self.total_value,
            "total_positions": self.total_positions,
            "account_count": self.account_count,
            "syncing": self.syncing,
            # Only send aggregated CSV - it contains all unique positions
            "holdings_csv": self.aggregated_holdings_to_csv()
        }
        
        return result

