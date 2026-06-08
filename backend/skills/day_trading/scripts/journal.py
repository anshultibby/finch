"""
Trade journal — persistent continuity for the day-trading agent.

Day-trade automations are stateless: each run is a fresh agent. The journal is
how the agent remembers what it did last time. It lives in the persistent memory
store (NOT chat_files, which are per-chat), so every session/automation reads the
same history and can answer "where are we right now?" and "what have I learned?".

Layout (under the persistent store):
    /home/user/store/day_trading/trades.jsonl   — append-only structured trade events
    /home/user/store/day_trading/notebook.md    — the agent's running thoughts:
                                                   what it did + what to do next
    /home/user/store/day_trading/strategy.md    — the evolving rules (free-form)

Two complementary memories:
- trades.jsonl is the *ledger* (machine-readable: what was traded, P&L, open positions).
- notebook.md is the *diary* (human-readable: reasoning, observations, and a standing
  "next steps" the agent leaves for its future self).

Read both at session start with session_state(); append after every session so the
next run inherits the full picture.
"""
import os
import json
from typing import Optional, List, Dict, Any

# Overridable for tests; defaults to the persistent memory store in the sandbox.
JOURNAL_DIR = os.environ.get("DAY_TRADING_JOURNAL_DIR", "/home/user/store/day_trading")
TRADES_PATH = os.path.join(JOURNAL_DIR, "trades.jsonl")
NOTEBOOK_PATH = os.path.join(JOURNAL_DIR, "notebook.md")

# status lifecycle: planned -> approved -> filled -> closed   (or rejected/skipped)
OPEN_STATUSES = {"approved", "filled"}
CLOSED_STATUSES = {"closed", "rejected", "skipped"}


def _ensure_dir() -> None:
    os.makedirs(JOURNAL_DIR, exist_ok=True)


def log_trade(symbol: str, side: str, status: str, setup: str = "",
              entry: Optional[float] = None, stop: Optional[float] = None,
              target: Optional[float] = None, shares: Optional[float] = None,
              pnl: Optional[float] = None, note: str = "",
              ts: Optional[str] = None, **extra: Any) -> Dict[str, Any]:
    """
    Append one trade event to the journal. Call it at every decision point:
    when you plan, get approval, fill, and close a trade.

        log_trade("MU", "long", "filled", setup="orb", entry=82.1, stop=81.5,
                  target=88.1, shares=120, note="RVOL 3.1, broke 5-min high")
        log_trade("MU", "long", "closed", pnl=143.20, note="hit 1:1, trailed to EOD")

    `ts` defaults to the caller's clock if omitted (pass datetime.now().isoformat()
    from the sandbox). Returns the stored record.
    """
    _ensure_dir()
    record = {
        "ts": ts,
        "symbol": symbol.upper(),
        "side": side,
        "status": status,
        "setup": setup,
        "entry": entry, "stop": stop, "target": target,
        "shares": shares, "pnl": pnl, "note": note,
        **extra,
    }
    with open(TRADES_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")
    return record


def read_trades(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """All journal events oldest-first (optionally just the last `limit`)."""
    if not os.path.exists(TRADES_PATH):
        return []
    rows = []
    with open(TRADES_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows[-limit:] if limit else rows


def open_positions() -> Dict[str, Dict[str, Any]]:
    """
    Current open positions, by symbol — the latest entry event that hasn't been
    followed by a close. This is "what am I holding right now?".
    """
    state: Dict[str, Dict[str, Any]] = {}
    for r in read_trades():
        sym = r.get("symbol")
        if not sym:
            continue
        if r.get("status") in OPEN_STATUSES:
            state[sym] = r
        elif r.get("status") in CLOSED_STATUSES:
            state.pop(sym, None)
    return state


def realized_pnl(since_ts: Optional[str] = None) -> float:
    """Sum of realized P&L from closed trades (optionally only ts >= since_ts)."""
    total = 0.0
    for r in read_trades():
        if r.get("status") == "closed" and r.get("pnl") is not None:
            if since_ts and (r.get("ts") or "") < since_ts:
                continue
            total += float(r["pnl"])
    return round(total, 2)


def read_notebook() -> str:
    """The agent's running diary (markdown): what it did + what to do next."""
    if not os.path.exists(NOTEBOOK_PATH):
        return ""
    with open(NOTEBOOK_PATH) as f:
        return f.read()


def append_note(did: str, next_steps: str = "", ts: Optional[str] = None) -> str:
    """
    Append a dated entry to the notebook. Call at the END of a session.

        append_note(
            did="Took ORB long on MU at 82.1, scaled half at 1:1, trailed to EOD (+$143).",
            next_steps="Watch MU for a continuation tomorrow; NVDA still open, stop 119.",
            ts=datetime.now().isoformat(),
        )

    `next_steps` is the standing message to the agent's future self — STATUS reads it
    back next session. Returns the entry that was written.
    """
    _ensure_dir()
    header = f"## {ts}" if ts else "## (session)"
    entry = f"\n{header}\n\n**Did:** {did}\n"
    if next_steps:
        entry += f"\n**Next:** {next_steps}\n"
    new_file = not os.path.exists(NOTEBOOK_PATH)
    with open(NOTEBOOK_PATH, "a") as f:
        if new_file:
            f.write("# Day Trading Notebook\n_Running log of what I did and what to do next._\n")
        f.write(entry)
    return entry


def session_state(since_ts: Optional[str] = None, notebook_chars: int = 1500) -> Dict[str, Any]:
    """
    One-call snapshot for the start of a session: open positions, realized P&L,
    trade count, the last few events, AND the tail of the notebook (the agent's own
    recent thoughts + standing next-steps). Read this FIRST every run.
    """
    trades = read_trades()
    notebook = read_notebook()
    return {
        "open_positions": open_positions(),
        "realized_pnl": realized_pnl(since_ts),
        "total_events": len(trades),
        "recent": trades[-5:],
        "notebook_tail": notebook[-notebook_chars:] if notebook else "",
    }
