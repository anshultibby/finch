"""
Tests for the credit system: pricing calculations, service methods, and edge cases.

Runs against a real PostgreSQL database (integration tests).
Uses the same async session infrastructure as the app.
"""
import pytest
import uuid
import math
from unittest.mock import AsyncMock, patch, MagicMock

from services.credits import (
    calculate_cost_usd,
    usd_to_credits,
    calculate_credits_for_llm_call,
    _get_model_pricing,
    CREDITS_PER_DOLLAR,
    PREMIUM_MULTIPLIER,
    MODEL_PRICING,
    DEFAULT_NEW_USER_CREDITS,
)


# ---------------------------------------------------------------------------
# Pure-function pricing tests (no DB needed)
# ---------------------------------------------------------------------------

class TestModelPricing:
    def test_exact_model_match(self):
        pricing = _get_model_pricing("claude-sonnet-4-6")
        assert pricing["input"] == 3.0
        assert pricing["output"] == 15.0

    def test_prefix_match_with_date_suffix(self):
        pricing = _get_model_pricing("claude-sonnet-4-5-20250101")
        assert pricing["input"] == 3.0

    def test_unknown_model_falls_back_to_sonnet(self):
        pricing = _get_model_pricing("some-unknown-model-xyz")
        assert pricing["input"] == 3.0
        assert pricing["output"] == 15.0

    def test_case_insensitive(self):
        pricing = _get_model_pricing("Claude-Sonnet-4-6")
        assert pricing["input"] == 3.0


class TestCostCalculation:
    def test_basic_cost(self):
        cost = calculate_cost_usd(
            model="claude-sonnet-4-5",
            prompt_tokens=100_000,
            completion_tokens=10_000,
        )
        expected = (100_000 / 1e6) * 3.0 + (10_000 / 1e6) * 15.0
        assert abs(cost - expected) < 1e-9

    def test_with_cache_tokens(self):
        cost = calculate_cost_usd(
            model="claude-sonnet-4-5",
            prompt_tokens=100_000,
            completion_tokens=10_000,
            cache_read_tokens=80_000,
            cache_creation_tokens=5_000,
        )
        uncached = 100_000 - 80_000  # 20_000
        expected = (
            (uncached / 1e6) * 3.0
            + (80_000 / 1e6) * 0.30
            + (5_000 / 1e6) * 3.75
            + (10_000 / 1e6) * 15.0
        )
        assert abs(cost - expected) < 1e-9

    def test_cache_read_exceeding_prompt_tokens_clamps_to_zero(self):
        """Regression: cache_read > prompt should not produce negative cost."""
        cost = calculate_cost_usd(
            model="claude-sonnet-4-5",
            prompt_tokens=50_000,
            completion_tokens=1_000,
            cache_read_tokens=60_000,
        )
        assert cost >= 0

    def test_zero_tokens(self):
        cost = calculate_cost_usd("claude-sonnet-4-5", 0, 0)
        assert cost == 0.0

    def test_opus_is_more_expensive(self):
        sonnet_cost = calculate_cost_usd("claude-sonnet-4-5", 100_000, 10_000)
        opus_cost = calculate_cost_usd("claude-opus-4-5", 100_000, 10_000)
        assert opus_cost > sonnet_cost

    def test_free_tier_gemini(self):
        cost = calculate_cost_usd("gemini-2.0-flash", 500_000, 50_000)
        assert cost == 0.0


class TestUsdToCredits:
    def test_basic_conversion(self):
        credits = usd_to_credits(1.0)
        assert credits == math.ceil(1.0 * PREMIUM_MULTIPLIER * CREDITS_PER_DOLLAR)
        assert credits == 120

    def test_rounds_up(self):
        credits = usd_to_credits(0.001)
        assert credits == 1  # ceil(0.001 * 1.2 * 100) = ceil(0.12) = 1

    def test_zero_cost(self):
        credits = usd_to_credits(0.0)
        assert credits == 0


class TestCalculateCreditsForLlmCall:
    def test_end_to_end(self):
        credits = calculate_credits_for_llm_call(
            model="claude-sonnet-4-5",
            prompt_tokens=100_000,
            completion_tokens=10_000,
        )
        usd = calculate_cost_usd("claude-sonnet-4-5", 100_000, 10_000)
        expected = math.ceil(usd * PREMIUM_MULTIPLIER * CREDITS_PER_DOLLAR)
        assert credits == expected

    def test_small_call_costs_at_least_one_credit(self):
        credits = calculate_credits_for_llm_call(
            model="claude-sonnet-4-5",
            prompt_tokens=100,
            completion_tokens=10,
        )
        assert credits >= 1


# ---------------------------------------------------------------------------
# Constants / configuration tests
# ---------------------------------------------------------------------------

class TestConstants:
    def test_default_new_user_credits_is_10_dollars(self):
        assert DEFAULT_NEW_USER_CREDITS == 1000

    def test_credits_per_dollar(self):
        assert CREDITS_PER_DOLLAR == 100

    def test_premium_multiplier(self):
        assert PREMIUM_MULTIPLIER == 1.2



# ---------------------------------------------------------------------------
# Service-layer tests (mock the DB session)
# ---------------------------------------------------------------------------

class TestCreditsServiceDeduct:
    @pytest.mark.asyncio
    async def test_deduct_full_amount(self):
        from services.credits import CreditsService

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = (900, 100)  # new_balance=900, deducted=100
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        success = await CreditsService.deduct_credits(
            db=mock_db,
            user_id="test-user",
            credits=100,
            transaction_type="chat_turn",
            description="Test deduction",
        )
        assert success is True
        assert mock_db.add.called

    @pytest.mark.asyncio
    async def test_deduct_user_not_found(self):
        from services.credits import CreditsService

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        success = await CreditsService.deduct_credits(
            db=mock_db,
            user_id="nonexistent",
            credits=100,
            transaction_type="chat_turn",
            description="Test",
        )
        assert success is False

    @pytest.mark.asyncio
    async def test_partial_deduction_logged(self):
        from services.credits import CreditsService

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = (0, 30)  # only had 30, wanted 100
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        success = await CreditsService.deduct_credits(
            db=mock_db,
            user_id="test-user",
            credits=100,
            transaction_type="chat_turn",
            description="Test deduction",
        )
        assert success is True
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.amount == -30
        assert "partial" in added_obj.description


class TestCreditsServiceAdd:
    @pytest.mark.asyncio
    async def test_add_credits(self):
        from services.credits import CreditsService

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = (600,)  # new balance after adding
        mock_db.execute = AsyncMock(return_value=mock_result)

        success = await CreditsService.add_credits(
            db=mock_db,
            user_id="test-user",
            credits=100,
            description="Bonus",
        )
        assert success is True
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.amount == 100
        assert added_obj.balance_after == 600

    @pytest.mark.asyncio
    async def test_add_user_not_found(self):
        from services.credits import CreditsService

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        success = await CreditsService.add_credits(
            db=mock_db,
            user_id="nonexistent",
            credits=100,
        )
        assert success is False


