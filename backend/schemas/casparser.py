from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class CASParserInitiateRequest(BaseModel):
    pan: str
    bo_id: str   # 16-digit CDSL beneficiary owner ID
    dob: str     # YYYY-MM-DD

    @field_validator('pan')
    @classmethod
    def pan_upper(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator('bo_id')
    @classmethod
    def bo_id_digits(cls, v: str) -> str:
        v = v.strip().replace('-', '').replace(' ', '')
        if len(v) != 16 or not v.isdigit():
            raise ValueError('bo_id must be exactly 16 digits')
        return v


class CASParserVerifyRequest(BaseModel):
    otp: str
    session_id: str
    # Passed back from the initiate step so we can encrypt + store them
    pan: str
    bo_id: str
    dob: str

    @field_validator('pan')
    @classmethod
    def pan_upper(cls, v: str) -> str:
        return v.strip().upper()


class CASParserHolding(BaseModel):
    isin: str
    name: str
    quantity: float
    face_value: Optional[float] = None


class CASParserDematAccount(BaseModel):
    dp_name: str
    dp_id: str
    client_id: str
    holdings: List[CASParserHolding]


class CASParserStatusResponse(BaseModel):
    is_connected: bool
    investor_name: Optional[str] = None
    pan_last4: Optional[str] = None
    holdings_fetched_at: Optional[datetime] = None
    total_holdings: Optional[int] = None


class CASParserPortfolioResponse(BaseModel):
    is_connected: bool
    investor_name: Optional[str] = None
    accounts: List[CASParserDematAccount] = []
    holdings_fetched_at: Optional[datetime] = None
    total_holdings: int = 0
