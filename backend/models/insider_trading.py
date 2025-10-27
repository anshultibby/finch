"""
Financial Modeling Prep API Pydantic models for insider trading data
Including Senate, House, and corporate insider trades
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
import pandas as pd


class SenateTrade(BaseModel):
    """Senate trading disclosure data"""
    first_name: str = Field(description="Senator's first name", alias="firstName")
    last_name: str = Field(description="Senator's last name", alias="lastName")
    office: Optional[str] = Field(None, description="Senate office")
    link: Optional[str] = Field(None, description="Link to disclosure")
    disclosure_date: Optional[str] = Field(None, description="Date disclosure was received", alias="disclosureDate")
    transaction_date: Optional[str] = Field(None, description="Date of transaction", alias="transactionDate")
    owner: Optional[str] = Field(None, description="Owner of the asset (self, spouse, etc)")
    asset_description: Optional[str] = Field(None, description="Description of asset traded", alias="assetDescription")
    asset_type: Optional[str] = Field(None, description="Type of asset", alias="assetType")
    type: Optional[str] = Field(None, description="Transaction type (Purchase, Sale, etc)")
    amount: Optional[str] = Field(None, description="Transaction amount range")
    comment: Optional[str] = Field(None, description="Additional comments")
    symbol: Optional[str] = Field(None, description="Stock ticker symbol if available")
    district: Optional[str] = Field(None, description="State/district code")
    
    class Config:
        populate_by_name = True  # Allow both field name and alias
    
    def to_df_row(self) -> dict:
        """
        Convert to dictionary suitable for DataFrame row
        """
        senator_name = f"{self.first_name} {self.last_name}"
        return {
            "date": self.transaction_date or self.disclosure_date,
            "senator": senator_name[:25],
            "type": self.type or "Unknown",
            "symbol": self.symbol or "N/A",
            "amount": self.amount or "N/A",
            "owner": self.owner or "N/A"
        }
    
    @classmethod
    def list_to_df(cls, trades: List['SenateTrade']) -> pd.DataFrame:
        """Convert list of SenateTrade objects to pandas DataFrame"""
        return pd.DataFrame([t.to_df_row() for t in trades])


class HouseTrade(BaseModel):
    """House trading disclosure data"""
    first_name: Optional[str] = Field(None, description="Representative's first name", alias="firstName")
    last_name: Optional[str] = Field(None, description="Representative's last name", alias="lastName")
    office: Optional[str] = Field(None, description="Representative office")
    disclosure_year: Optional[str] = Field(None, description="Year of disclosure", alias="disclosureYear")
    disclosure_date: Optional[str] = Field(None, description="Date of disclosure", alias="disclosureDate")
    transaction_date: Optional[str] = Field(None, description="Date of transaction", alias="transactionDate")
    owner: Optional[str] = Field(None, description="Owner of the asset")
    symbol: Optional[str] = Field(None, description="Stock ticker symbol")
    asset_description: Optional[str] = Field(None, description="Description of asset", alias="assetDescription")
    asset_type: Optional[str] = Field(None, description="Type of asset", alias="assetType")
    type: Optional[str] = Field(None, description="Transaction type")
    amount: Optional[str] = Field(None, description="Transaction amount range")
    comment: Optional[str] = Field(None, description="Additional comments")
    district: Optional[str] = Field(None, description="Congressional district")
    link: Optional[str] = Field(None, description="Link to disclosure")
    capital_gains_over_200_usd: Optional[bool] = Field(None, description="Capital gains over $200", alias="capitalGainsOver200USD")
    
    class Config:
        populate_by_name = True  # Allow both field name and alias
    
    def to_df_row(self) -> dict:
        """
        Convert to dictionary suitable for DataFrame row
        """
        rep_name = f"{self.first_name or ''} {self.last_name or ''}".strip() or self.office or "Unknown"
        return {
            "date": self.transaction_date or self.disclosure_date,
            "representative": rep_name[:25],
            "type": self.type or "Unknown",
            "symbol": self.symbol or "N/A",
            "amount": self.amount or "N/A",
            "owner": self.owner or "N/A"
        }
    
    @classmethod
    def list_to_df(cls, trades: List['HouseTrade']) -> pd.DataFrame:
        """Convert list of HouseTrade objects to pandas DataFrame"""
        return pd.DataFrame([t.to_df_row() for t in trades])


class InsiderTrade(BaseModel):
    """Corporate insider trading data"""
    symbol: str = Field(description="Stock ticker symbol")
    filing_date: Optional[str] = Field(None, description="SEC filing date", alias="filingDate")
    transaction_date: Optional[str] = Field(None, description="Transaction date", alias="transactionDate")
    reporting_cik: Optional[str] = Field(None, description="CIK of reporting person", alias="reportingCik")
    transaction_type: Optional[str] = Field(None, description="Type of transaction", alias="transactionType")
    securities_owned: Optional[float] = Field(None, description="Securities owned after transaction", alias="securitiesOwned")
    company_cik: Optional[str] = Field(None, description="Company CIK", alias="companyCik")
    reporting_name: Optional[str] = Field(None, description="Name of insider", alias="reportingName")
    type_of_owner: Optional[str] = Field(None, description="Type of owner (director, officer, etc)", alias="typeOfOwner")
    acquisition_or_disposition: Optional[str] = Field(None, description="A for acquisition, D for disposition", alias="acquisitionOrDisposition")
    form_type: Optional[str] = Field(None, description="SEC form type (3, 4, 5)", alias="formType")
    securities_transacted: Optional[float] = Field(None, description="Number of securities transacted", alias="securitiesTransacted")
    price: Optional[float] = Field(None, description="Transaction price per share")
    security_name: Optional[str] = Field(None, description="Name of security", alias="securityName")
    link: Optional[str] = Field(None, description="Link to SEC filing", alias="url")
    direct_or_indirect: Optional[str] = Field(None, description="D for direct, I for indirect ownership", alias="directOrIndirect")
    
    class Config:
        populate_by_name = True  # Allow both field name and alias
    
    def to_df_row(self) -> dict:
        """
        Convert to dictionary suitable for DataFrame row
        """
        return {
            "date": self.transaction_date or self.filing_date,
            "insider": (self.reporting_name or "Unknown")[:25],
            "position": (self.type_of_owner or "N/A")[:20],
            "type": self.transaction_type or "Unknown",
            "shares": self.securities_transacted,
            "price": self.price
        }
    
    @classmethod
    def list_to_df(cls, trades: List['InsiderTrade']) -> pd.DataFrame:
        """Convert list of InsiderTrade objects to pandas DataFrame"""
        return pd.DataFrame([t.to_df_row() for t in trades])


class CongressionalActivity(BaseModel):
    """Aggregated congressional trading activity for a ticker"""
    ticker: str
    recent_trades: List[dict]
    total_purchases: int
    total_sales: int
    notable_traders: List[str]
    date_range: str


class InsiderTradingStatistics(BaseModel):
    """Quarterly aggregated insider trading statistics for a symbol"""
    symbol: str = Field(description="Stock ticker symbol")
    cik: str = Field(description="Company CIK number")
    year: int = Field(description="Year")
    quarter: int = Field(description="Quarter (1-4)")
    acquired_transactions: int = Field(description="Number of acquisition transactions", alias="acquiredTransactions")
    disposed_transactions: int = Field(description="Number of disposal transactions", alias="disposedTransactions")
    acquired_disposed_ratio: float = Field(description="Ratio of acquired to disposed transactions", alias="acquiredDisposedRatio")
    total_acquired: float = Field(description="Total shares acquired", alias="totalAcquired")
    total_disposed: float = Field(description="Total shares disposed", alias="totalDisposed")
    average_acquired: float = Field(description="Average shares per acquisition", alias="averageAcquired")
    average_disposed: float = Field(description="Average shares per disposal", alias="averageDisposed")
    total_purchases: int = Field(description="Total purchase transactions", alias="totalPurchases")
    total_sales: int = Field(description="Total sale transactions", alias="totalSales")
    
    class Config:
        populate_by_name = True
    
    def to_df_row(self) -> dict:
        """Convert to dictionary suitable for DataFrame row"""
        return {
            "quarter": f"Q{self.quarter} {self.year}",
            "buys": self.acquired_transactions,
            "sells": self.disposed_transactions,
            "buy_sell_ratio": round(self.acquired_disposed_ratio, 2),
            "shares_bought": f"{self.total_acquired:,.0f}",
            "shares_sold": f"{self.total_disposed:,.0f}",
            "purchases": self.total_purchases,
            "sales": self.total_sales
        }
    
    @classmethod
    def list_to_df(cls, statistics: List['InsiderTradingStatistics']) -> pd.DataFrame:
        """Convert list of InsiderTradingStatistics objects to pandas DataFrame"""
        return pd.DataFrame([s.to_df_row() for s in statistics])


class InsiderTradingResponse(BaseModel):
    """Generic response for insider trading data"""
    success: bool
    data_type: Literal["senate", "house", "insider", "mixed"]
    trades: List[dict]
    total_count: int
    message: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data_type": "senate",
                "trades": [],
                "total_count": 25,
                "message": "Found 25 recent Senate trades",
                "timestamp": "2025-10-27T12:00:00Z"
            }
        }

