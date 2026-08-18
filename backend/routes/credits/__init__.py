"""
Credits API routes.

Split by responsibility; `router` keeps the original /credits prefix so the
public URL surface is unchanged.
"""
from fastapi import APIRouter

from . import balance, billing, promos, webhooks

router = APIRouter(prefix="/credits", tags=["credits"])
router.include_router(balance.router)
router.include_router(billing.router)
router.include_router(promos.router)
router.include_router(webhooks.router)

__all__ = ["router"]
