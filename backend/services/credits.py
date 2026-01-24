"""
Credits management service

Handles credit tracking, deduction, and transaction logging.
Uses actual token usage from LLM calls with 20% premium on costs.
"""
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from models.db import SnapTradeUser, CreditTransaction
from utils.logger import get_logger
import uuid

logger = get_logger(__name__)


# Pricing per million tokens (from llm_handler.py)
# Format: {model_prefix: {"input": price, "output": price, "cache_read": price, "cache_write": price}}
MODEL_PRICING = {
    # Claude 4 models
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75},
    "claude-opus-4-5": {"input": 15.0, "output": 75.0, "cache_read": 1.50, "cache_write": 18.75},
    "claude-sonnet-4": {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75},
    "claude-opus-4": {"input": 15.0, "output": 75.0, "cache_read": 1.50, "cache_write": 18.75},
    # Claude 3.5 models
    "claude-3-5-sonnet": {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.0, "cache_read": 0.08, "cache_write": 1.0},
    "claude-3-opus": {"input": 15.0, "output": 75.0, "cache_read": 1.50, "cache_write": 18.75},
    # OpenAI models
    "gpt-4o": {"input": 2.50, "output": 10.0, "cache_read": 1.25, "cache_write": 2.50},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "cache_read": 0.075, "cache_write": 0.15},
    "o1": {"input": 15.0, "output": 60.0, "cache_read": 7.50, "cache_write": 15.0},
    "o3-mini": {"input": 1.10, "output": 4.40, "cache_read": 0.55, "cache_write": 1.10},
    "gpt-5": {"input": 2.0, "output": 8.0, "cache_read": 1.0, "cache_write": 2.0},
    # Gemini models
    "gemini-2.0": {"input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_write": 0.0},  # Free tier
    "gemini-2.5": {"input": 1.25, "output": 5.0, "cache_read": 0.125, "cache_write": 1.5625},
    "gemini-3": {"input": 2.5, "output": 10.0, "cache_read": 0.25, "cache_write": 3.125},
}

# Credits conversion: 1000 credits = $1 USD
# This means 1 credit = $0.001 USD
CREDITS_PER_DOLLAR = 1000

# Premium multiplier (20% markup)
PREMIUM_MULTIPLIER = 1.2


def _get_model_pricing(model: str) -> Dict[str, float]:
    """Get pricing for a model by matching prefix."""
    model_lower = model.lower()
    for prefix, pricing in MODEL_PRICING.items():
        if prefix in model_lower:
            return pricing
    # Default fallback pricing (Claude Sonnet 4.5)
    return {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75}


def calculate_cost_usd(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0
) -> float:
    """
    Calculate the cost in USD for an LLM call based on token usage.
    
    Args:
        model: Model name (e.g., "claude-sonnet-4-5", "gpt-4o")
        prompt_tokens: Total prompt tokens
        completion_tokens: Completion tokens
        cache_read_tokens: Tokens read from cache (cheaper)
        cache_creation_tokens: Tokens written to cache (more expensive)
    
    Returns:
        Cost in USD
    """
    pricing = _get_model_pricing(model)
    
    # Calculate uncached input tokens
    uncached_input = prompt_tokens - cache_read_tokens
    
    # Calculate costs (pricing is per million tokens)
    input_cost = (uncached_input / 1_000_000) * pricing["input"]
    cache_read_cost = (cache_read_tokens / 1_000_000) * pricing["cache_read"]
    cache_write_cost = (cache_creation_tokens / 1_000_000) * pricing["cache_write"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    
    total_cost = input_cost + cache_read_cost + cache_write_cost + output_cost
    
    return total_cost


def usd_to_credits(usd_cost: float) -> int:
    """
    Convert USD cost to credits with 20% premium.
    
    Args:
        usd_cost: Cost in USD
    
    Returns:
        Credits to deduct (rounded up to nearest integer)
    """
    # Apply 20% premium
    cost_with_premium = usd_cost * PREMIUM_MULTIPLIER
    
    # Convert to credits (1000 credits = $1)
    credits = cost_with_premium * CREDITS_PER_DOLLAR
    
    # Round up to ensure we don't undercharge
    import math
    return math.ceil(credits)


def calculate_credits_for_llm_call(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0
) -> int:
    """
    Calculate credits to deduct for an LLM call (includes 20% premium).
    
    Args:
        model: Model name
        prompt_tokens: Total prompt tokens
        completion_tokens: Completion tokens
        cache_read_tokens: Tokens read from cache
        cache_creation_tokens: Tokens written to cache
    
    Returns:
        Credits to deduct
    """
    usd_cost = calculate_cost_usd(
        model,
        prompt_tokens,
        completion_tokens,
        cache_read_tokens,
        cache_creation_tokens
    )
    
    return usd_to_credits(usd_cost)


class CreditsService:
    """Service for managing user credits"""
    
    @staticmethod
    async def get_user_credits(db: AsyncSession, user_id: str) -> Optional[int]:
        """
        Get the current credit balance for a user.
        
        Args:
            db: Database session
            user_id: User ID
        
        Returns:
            Credit balance or None if user not found
        """
        result = await db.execute(
            select(SnapTradeUser.credits).where(SnapTradeUser.user_id == user_id)
        )
        row = result.first()
        return row[0] if row else None
    
    @staticmethod
    async def check_sufficient_credits(
        db: AsyncSession,
        user_id: str,
        required_credits: int
    ) -> bool:
        """
        Check if user has sufficient credits.
        
        Args:
            db: Database session
            user_id: User ID
            required_credits: Credits needed
        
        Returns:
            True if user has enough credits, False otherwise
        """
        current_credits = await CreditsService.get_user_credits(db, user_id)
        if current_credits is None:
            return False
        return current_credits >= required_credits
    
    @staticmethod
    async def deduct_credits(
        db: AsyncSession,
        user_id: str,
        credits: int,
        transaction_type: str,
        description: str,
        chat_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Deduct credits from user balance and log transaction.
        
        If user doesn't have enough credits, deducts whatever they have (down to 0).
        This ensures users pay for what they used, even if they can't afford the full amount.
        
        Args:
            db: Database session
            user_id: User ID
            credits: Amount to deduct (full cost)
            transaction_type: Type of transaction (e.g., 'llm_call', 'tool_call')
            description: Human-readable description
            chat_id: Optional chat ID
            tool_name: Optional tool name
            metadata: Optional metadata (model, tokens, etc.)
        
        Returns:
            True if successful (deducted at least some credits), False if user not found
        """
        # Get current balance
        result = await db.execute(
            select(SnapTradeUser).where(SnapTradeUser.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User {user_id} not found for credit deduction")
            return False
        
        # If they can't afford the full amount, deduct what they have (down to 0)
        # This prevents "free" responses when balance is low
        actual_deduction = min(credits, user.credits)
        
        if user.credits < credits:
            logger.warning(
                f"Partial deduction for user {user_id}: "
                f"needs {credits}, has {user.credits}, deducting {actual_deduction} (balance → 0)"
            )
        
        # Deduct credits and update lifetime usage
        new_balance = user.credits - actual_deduction
        await db.execute(
            update(SnapTradeUser)
            .where(SnapTradeUser.user_id == user_id)
            .values(
                credits=new_balance,
                total_credits_used=SnapTradeUser.total_credits_used + actual_deduction
            )
        )
        
        # Log transaction (record actual deduction, note if partial)
        transaction_desc = description
        if actual_deduction < credits:
            transaction_desc = f"{description} (partial: {actual_deduction}/{credits} credits)"
        
        transaction = CreditTransaction(
            id=uuid.uuid4(),
            user_id=user_id,
            amount=-actual_deduction,  # Negative for deduction
            balance_after=new_balance,
            transaction_type=transaction_type,
            description=transaction_desc,
            chat_id=chat_id,
            tool_name=tool_name,
            transaction_metadata=metadata
        )
        db.add(transaction)
        
        logger.info(
            f"Deducted {actual_deduction} credits from user {user_id}: "
            f"{user.credits} → {new_balance} ({description})"
        )
        
        return True
    
    @staticmethod
    async def add_credits(
        db: AsyncSession,
        user_id: str,
        credits: int,
        transaction_type: str = "admin_adjustment",
        description: str = "Credits added"
    ) -> bool:
        """
        Add credits to user balance and log transaction.
        
        Args:
            db: Database session
            user_id: User ID
            credits: Amount to add
            transaction_type: Type of transaction
            description: Human-readable description
        
        Returns:
            True if successful, False if user not found
        """
        # Get current balance
        result = await db.execute(
            select(SnapTradeUser).where(SnapTradeUser.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User {user_id} not found for credit addition")
            return False
        
        # Add credits
        new_balance = user.credits + credits
        await db.execute(
            update(SnapTradeUser)
            .where(SnapTradeUser.user_id == user_id)
            .values(credits=new_balance)
        )
        
        # Log transaction
        transaction = CreditTransaction(
            id=uuid.uuid4(),
            user_id=user_id,
            amount=credits,  # Positive for addition
            balance_after=new_balance,
            transaction_type=transaction_type,
            description=description,
            transaction_metadata=None
        )
        db.add(transaction)
        
        logger.info(
            f"Added {credits} credits to user {user_id}: "
            f"{user.credits} → {new_balance} ({description})"
        )
        
        return True
    
    @staticmethod
    async def get_transaction_history(
        db: AsyncSession,
        user_id: str,
        limit: int = 50
    ) -> list:
        """
        Get credit transaction history for a user.
        
        Args:
            db: Database session
            user_id: User ID
            limit: Maximum number of transactions to return
        
        Returns:
            List of transactions (most recent first)
        """
        result = await db.execute(
            select(CreditTransaction)
            .where(CreditTransaction.user_id == user_id)
            .order_by(CreditTransaction.created_at.desc())
            .limit(limit)
        )
        transactions = result.scalars().all()
        
        return [
            {
                "id": str(t.id),
                "amount": t.amount,
                "balance_after": t.balance_after,
                "transaction_type": t.transaction_type,
                "description": t.description,
                "chat_id": t.chat_id,
                "tool_name": t.tool_name,
                "metadata": t.transaction_metadata,
                "created_at": t.created_at.isoformat() if t.created_at else None
            }
            for t in transactions
        ]
