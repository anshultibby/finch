"""Shared core for the passive-monitoring passes.

The portfolio digest, nightly ledger review, market monitor and move explainer
all "inspect portfolio/watchlist + news → emit a signal." They used to each
carry their own copy of the quote fetch, holdings parser, SPY backdrop, LLM
narration wrapper, TTL cache and ledger/notify plumbing. Those primitives live
here now; the pass modules are thin adapters over them.

- inputs  — symbol/holdings gathering + FMP batch quotes
- narrate — the single-completion narration wrapper (model policy + thinking off)
- cache   — in-memory TTL cache with single-flight locking
- sink    — emit_signal(): one write to the ledger (+ optional push)
"""
