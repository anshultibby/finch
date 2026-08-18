"""
Tests for the credit system: pricing calculations, service methods, and edge cases.

Runs against a real PostgreSQL database (integration tests).
Uses the same async session infrastructure as the app.
"""
import pytest
import math
from unittest.mock import AsyncMock, MagicMock

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
        # prompt_tokens is the TOTAL input, so BOTH cache buckets come out of it
        # — each token is billed exactly once (see calculate_cost_usd).
        uncached = 100_000 - 80_000 - 5_000  # 15_000
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
        assert credits == 125

    def test_rounds_up(self):
        credits = usd_to_credits(0.001)
        assert credits == 1  # ceil(0.001 * 1.25 * 100) = ceil(0.125) = 1

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
        assert PREMIUM_MULTIPLIER == 1.25



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


# ---------------------------------------------------------------------------
# Daily-refresh accrual (_apply_refresh)
# ---------------------------------------------------------------------------

class TestApplyRefresh:
    """
    _apply_refresh does a read-modify-write with an absolute `credits = value`.
    It must (a) not lock or write on the common no-op path, (b) accrue whole
    days of daily credits when due, and (c) never let the free daily refresh
    push a balance past the plan cap -- the bug that once destroyed ~19k
    purchased credits.
    """

    @staticmethod
    def _user(credits, *, plan="free", days_since_refresh=0.0):
        from datetime import datetime, timezone, timedelta
        u = MagicMock()
        u.user_id = "u1"
        u.credits = credits
        u.plan = plan
        u.last_credit_refresh = datetime.now(timezone.utc) - timedelta(days=days_since_refresh)
        u.created_at = u.last_credit_refresh
        return u

    @pytest.mark.asyncio
    async def test_noop_path_takes_no_lock_and_no_write(self):
        from services.credits import CreditsService

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()  # would be a SELECT ... FOR UPDATE if locked
        user = self._user(500, days_since_refresh=0.3)  # < 1 day → nothing due

        balance = await CreditsService._apply_refresh(mock_db, user)

        assert balance == 500
        # Fast path must not hit the DB at all: no lock, no update, no txn row.
        mock_db.execute.assert_not_called()
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_accrues_whole_days_under_lock(self):
        from services.credits import CreditsService

        locked_user = self._user(200, plan="free", days_since_refresh=3.5)
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = locked_user

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=select_result)
        mock_db.flush = AsyncMock()

        balance = await CreditsService._apply_refresh(mock_db, locked_user)

        # 3 whole days × 100/day = 300 accrued → 200 + 300 = 500
        assert balance == 500
        txn = mock_db.add.call_args[0][0]
        assert txn.amount == 300
        assert txn.transaction_type == "daily_refresh"

    @pytest.mark.asyncio
    async def test_refresh_never_exceeds_cap_but_keeps_existing_surplus(self):
        from services.credits import CreditsService

        # Already above the free cap (1000) from a purchase; refresh adds nothing
        # and must not clamp the balance down.
        locked_user = self._user(4_000, plan="free", days_since_refresh=10)
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = locked_user

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=select_result)
        mock_db.flush = AsyncMock()

        balance = await CreditsService._apply_refresh(mock_db, locked_user)

        assert balance == 4_000          # surplus preserved
        mock_db.add.assert_not_called()  # nothing accrued, no transaction

    @pytest.mark.asyncio
    async def test_refresh_fills_only_up_to_cap(self):
        from services.credits import CreditsService

        # 950/1000 with 5 days due (would accrue 500) → capped to +50.
        locked_user = self._user(950, plan="free", days_since_refresh=5)
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = locked_user

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=select_result)
        mock_db.flush = AsyncMock()

        balance = await CreditsService._apply_refresh(mock_db, locked_user)

        assert balance == 1_000
        txn = mock_db.add.call_args[0][0]
        assert txn.amount == 50


