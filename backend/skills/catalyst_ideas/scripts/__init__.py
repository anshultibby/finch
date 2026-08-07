"""Catalyst idea generation — feeds, hygiene, a scanner registry, and starters."""
from . import feeds, registry, screen, starters
from .screen import CATALYST_TYPES, candidate, dedupe, is_litigation_spam, screen as apply_screen, surprise_pct
from .starters import scan_all

__all__ = [
    "feeds", "registry", "screen", "starters",
    "CATALYST_TYPES", "candidate", "dedupe", "is_litigation_spam",
    "apply_screen", "surprise_pct", "scan_all",
]
