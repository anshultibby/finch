"""
Unauthenticated provider webhooks (Stripe, RevenueCat).

These endpoints are NOT behind get_current_user_id -- they authenticate by
verifying a provider signature/secret in the handler. Keeping them in their
own module makes that trust boundary explicit.
"""
from utils.logger import get_logger
from fastapi import APIRouter, HTTPException, Request, Header
from core.database import get_db_session
from services.credits import CreditsService
from core.config import Config

logger = get_logger(__name__)

router = APIRouter()


@router.post("/webhook")
async def stripe_webhook(request: Request):
    import stripe

    if not Config.STRIPE_SECRET_KEY or not Config.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, Config.STRIPE_WEBHOOK_SECRET)
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    obj = event["data"]["object"]
    data = obj.to_dict() if hasattr(obj, 'to_dict') else obj

    from datetime import datetime, timezone

    async with get_db_session() as db:
        if event_type == "checkout.session.completed":
            user_id = data.get("client_reference_id")
            customer_id = data.get("customer")
            if not user_id:
                logger.warning("checkout.session.completed without client_reference_id")
                return {"status": "ignored"}

            if customer_id:
                await CreditsService.set_stripe_customer_id(db, user_id, customer_id)

            metadata = data.get("metadata") or {}
            topup_credits = metadata.get("topup_credits")

            if topup_credits:
                credits = int(topup_credits)
                await CreditsService.add_credits(
                    db, user_id, credits,
                    transaction_type="topup",
                    description=f"Credit top-up (+{credits:,} credits)",
                )
                logger.info(f"User {user_id} topped up {credits} credits")
            else:
                subscription_id = data.get("subscription")
                await CreditsService.set_user_plan(db, user_id, "pro")
                await CreditsService.set_subscription_info(
                    db, user_id, subscription_provider="stripe",
                )
                if subscription_id:
                    await CreditsService.set_subscription_info(
                        db, user_id,
                        stripe_subscription_id=subscription_id,
                        subscription_status="active",
                        cancel_at_period_end=False,
                    )
                await CreditsService.add_credits(
                    db, user_id, 1_000,
                    transaction_type="subscription",
                    description="Pro plan activation bonus (+1,000 credits)",
                )
                logger.info(f"User {user_id} upgraded to pro via Stripe")

        elif event_type == "customer.subscription.updated":
            customer_id = data.get("customer")
            if not customer_id:
                return {"status": "ignored"}
            user_id = await CreditsService.get_user_id_by_stripe_customer(db, customer_id)
            if user_id:
                cancel_at_period = data.get("cancel_at_period_end", False)
                status = data.get("status", "active")
                cancel_at_ts = data.get("cancel_at")
                period_end = datetime.fromtimestamp(cancel_at_ts, tz=timezone.utc) if cancel_at_ts else None
                await CreditsService.set_subscription_info(
                    db, user_id,
                    subscription_status=status,
                    cancel_at_period_end=cancel_at_period,
                    current_period_end=period_end,
                )
                logger.info(f"User {user_id} subscription updated: status={status} cancel_at_period_end={cancel_at_period}")

        elif event_type == "invoice.paid":
            # Monthly renewal: grant the recurring credits promised in the Pro plan UI.
            # billing_reason is "subscription_create" on the first invoice (already
            # granted via checkout.session.completed) and "subscription_cycle" on renewals.
            if data.get("billing_reason") == "subscription_cycle":
                customer_id = data.get("customer")
                user_id = (
                    await CreditsService.get_user_id_by_stripe_customer(db, customer_id)
                    if customer_id else None
                )
                if user_id:
                    await CreditsService.add_credits(
                        db, user_id, 1_000,
                        transaction_type="subscription",
                        description="Pro plan monthly credits (+1,000)",
                    )
                    logger.info(f"User {user_id} granted monthly Pro renewal credits")

        elif event_type == "customer.subscription.deleted":
            customer_id = data.get("customer")
            if not customer_id:
                return {"status": "ignored"}
            user_id = await CreditsService.get_user_id_by_stripe_customer(db, customer_id)
            if user_id:
                await CreditsService.set_user_plan(db, user_id, "free")
                await CreditsService.clear_subscription_info(db, user_id)
                logger.info(f"User {user_id} downgraded to free (subscription expired)")

    return {"status": "ok"}

@router.post("/revenuecat-webhook")
async def revenuecat_webhook(request: Request):
    """
    RevenueCat webhook for Apple In-App Purchase (iOS Pro subscription).

    RevenueCat validates the App Store receipt and POSTs lifecycle events here.
    We map `app_user_id` (which the iOS app sets to the Supabase user id via
    Purchases.logIn) onto UserAccount and mirror the Stripe grant logic so the
    `plan`/`credits` columns are the single source of truth across web + iOS.

    Auth: RevenueCat sends the dashboard-configured secret verbatim in the
    Authorization header — we compare it against REVENUECAT_WEBHOOK_AUTH.
    """
    import hmac

    if not Config.REVENUECAT_WEBHOOK_AUTH:
        raise HTTPException(status_code=500, detail="RevenueCat not configured")

    auth = request.headers.get("authorization", "")
    if not hmac.compare_digest(auth, Config.REVENUECAT_WEBHOOK_AUTH):
        raise HTTPException(status_code=401, detail="Invalid signature")

    body = await request.json()
    event = body.get("event") or {}
    event_type = event.get("type")
    user_id = event.get("app_user_id")

    # Anonymous RevenueCat ids ($RCAnonymousID:...) mean the purchase happened
    # before the app called logIn — we can't attribute it, so ack and move on.
    if not user_id or user_id.startswith("$RCAnonymousID"):
        logger.warning(f"RevenueCat {event_type} without a resolvable app_user_id; ignoring")
        return {"status": "ignored"}

    from datetime import datetime, timezone
    exp_ms = event.get("expiration_at_ms")
    period_end = (
        datetime.fromtimestamp(exp_ms / 1000, tz=timezone.utc) if exp_ms else None
    )

    APPLE_MONTHLY_CREDITS = 1_000  # match the Stripe Pro grant

    async with get_db_session() as db:
        if event_type in ("INITIAL_PURCHASE", "NON_RENEWING_PURCHASE"):
            current = await CreditsService.get_user_plan(db, user_id)
            if current == "pro":
                logger.warning(
                    f"User {user_id} bought Pro on Apple while already pro "
                    f"(prior provider may be Stripe) — switching provider to apple"
                )
            await CreditsService.set_user_plan(db, user_id, "pro")
            await CreditsService.set_subscription_info(
                db, user_id,
                subscription_provider="apple",
                subscription_status="active",
                cancel_at_period_end=False,
                current_period_end=period_end,
            )
            await CreditsService.add_credits(
                db, user_id, APPLE_MONTHLY_CREDITS,
                transaction_type="subscription",
                description=f"Pro plan activation bonus (+{APPLE_MONTHLY_CREDITS:,} credits)",
            )
            logger.info(f"User {user_id} upgraded to pro via Apple IAP")

        elif event_type == "RENEWAL":
            await CreditsService.set_user_plan(db, user_id, "pro")
            await CreditsService.set_subscription_info(
                db, user_id,
                subscription_provider="apple",
                subscription_status="active",
                cancel_at_period_end=False,
                current_period_end=period_end,
            )
            await CreditsService.add_credits(
                db, user_id, APPLE_MONTHLY_CREDITS,
                transaction_type="subscription",
                description=f"Pro plan monthly credits (+{APPLE_MONTHLY_CREDITS:,})",
            )
            logger.info(f"User {user_id} granted monthly Pro renewal credits (Apple)")

        elif event_type == "CANCELLATION":
            # Auto-renew turned off — keep Pro until the paid period actually ends
            # (EXPIRATION handles the downgrade), mirroring Stripe's cancel flow.
            await CreditsService.set_subscription_info(
                db, user_id,
                cancel_at_period_end=True,
                current_period_end=period_end,
            )
            logger.info(f"User {user_id} cancelled Apple Pro auto-renew")

        elif event_type == "UNCANCELLATION":
            await CreditsService.set_subscription_info(
                db, user_id,
                cancel_at_period_end=False,
                current_period_end=period_end,
            )
            logger.info(f"User {user_id} re-enabled Apple Pro auto-renew")

        elif event_type == "EXPIRATION":
            await CreditsService.set_user_plan(db, user_id, "free")
            await CreditsService.clear_subscription_info(db, user_id)
            logger.info(f"User {user_id} downgraded to free (Apple subscription expired)")

        # BILLING_ISSUE / PRODUCT_CHANGE / TEST etc. — acknowledged, no state change.

    return {"status": "ok"}
