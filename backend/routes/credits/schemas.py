"""
Credits API request/response models and shared constants.
"""
from pydantic import BaseModel
from typing import Optional


TOPUP_OPTIONS = {
    500: {"credits": 500, "label": "500 credits"},
    1000: {"credits": 1_050, "label": "1,050 credits"},
    2500: {"credits": 2_750, "label": "2,750 credits"},
}

class CreditBalanceResponse(BaseModel):
    user_id: str
    credits: int
    total_credits_used: int
    plan: str = "free"
    subscription_provider: Optional[str] = None  # stripe | apple
    subscription_status: Optional[str] = None
    cancel_at_period_end: bool = False
    current_period_end: Optional[str] = None

class AddCreditsRequest(BaseModel):
    """Request model for adding credits (admin only)"""
    user_id: str
    credits: int
    description: Optional[str] = "Credits added"

class CreditTransactionResponse(BaseModel):
    """Response model for a single credit transaction"""
    id: str
    amount: int
    balance_after: int
    transaction_type: str
    description: str
    chat_id: Optional[str]
    tool_name: Optional[str]
    metadata: Optional[dict]
    created_at: Optional[str]

class CreditRequestData(BaseModel):
    """Request model for credit request"""
    user_id: str
    user_email: str
    requested_credits: int
    reason: str
    current_balance: int
    total_used: int

class CheckoutRequest(BaseModel):
    user_id: str

class SetPlanRequest(BaseModel):
    user_id: str
    plan: str  # free | pro | admin

class PromoRequestBody(BaseModel):
    email: str
    message: str = ""

class TopupRequest(BaseModel):
    user_id: str
    amount_cents: int  # 500, 1000, or 2500

class SubscriptionActionRequest(BaseModel):
    user_id: str
    reason: Optional[str] = None

class RedeemCodeRequest(BaseModel):
    code: str
