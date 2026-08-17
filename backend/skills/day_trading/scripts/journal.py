"""
Trade journal — the agent's persistent state across stateless runs.

This module owns the hard facts — the trade ledger and today's plan:

    /home/user/store/day_trading/trades.jsonl   — append-only event ledger
    /home/user/store/day_trading/plan.md        — TODAY's plan (written nightly)

Everything narrative is filed through the `library` skill instead, one document
per subject, so it's findable and (for theses and tasks) visible to the user:

    stocks/{SYMBOL}/thesis.md   a view on a company   -> Analysis tab
    tasks/{slug}.md             work spanning runs    -> Tasks
    journal/{YYYY-MM}.md        what happened, dated
    playbooks/day-trading.md    the rules you operate by

`session_state()` is the one memory call a run should need. Everything past it
goes through the library's index → outline → section path, never a whole-file
read: this operation's diary once reached 40K tokens and was, by itself, ~38%
of a nightly run's input bill.

Events are linked by trade_id so one trade's lifecycle is unambiguous:

    planned → submitted → filled → closed
                        ↘ rejected | cancelled | expired | skipped

A position is OPEN iff its trade_id has a `filled` with no terminal event after
it. Rejecting a NEW plan on a symbol you already hold no longer touches the
held position (events on different trade_ids never interact).

This module is also the source of truth for the risk circuit breaker —
risk.RiskBudget.from_journal() rebuilds today's losses/trade count from here,
which is what makes the daily loss limit survive across automation runs.
"""
import os
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from .clock import now_et

JOURNAL_DIR = os.environ.get("DAY_TRADING_JOURNAL_DIR", "/home/user/store/day_trading")
TRADES_PATH = os.path.join(JOURNAL_DIR, "trades.jsonl")
PLAN_PATH = os.path.join(JOURNAL_DIR, "plan.md")

TERMINAL = {"closed", "rejected", "cancelled", "expired", "skipped"}


def _ensure_dir() -> None:
    os.makedirs(JOURNAL_DIR, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_trade(symbol: str, side: str, status: str, trade_id: Optional[str] = None,
              setup: str = "", entry: Optional[float] = None,
              stop: Optional[float] = None, target: Optional[float] = None,
              shares: Optional[float] = None, pnl: Optional[float] = None,
              note: str = "", **extra: Any) -> Dict[str, Any]:
    """
    Append one event. A NEW trade (status='planned') may omit trade_id — one is
    generated and returned; every LATER event for that trade MUST pass it back:

        t = log_trade("MU", "long", "planned", setup="orb", entry=82.1, stop=81.7,
                      target=86.1, shares=120, note="RVOL 3.1, earnings beat + raise")
        log_trade("MU", "long", "filled", trade_id=t["trade_id"])
        log_trade("MU", "long", "closed", trade_id=t["trade_id"], pnl=143.2,
                  note="scaled at 1:1, flattened 15:45")

    Timestamps are stamped automatically (UTC) with the ET date alongside.
    """
    _ensure_dir()
    symbol = symbol.upper()
    if trade_id is None:
        trade_id = f"{symbol}-{now_et().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"
    record = {
        "ts": _now_iso(),
        "date_et": now_et().date().isoformat(),
        "trade_id": trade_id,
        "symbol": symbol, "side": side, "status": status, "setup": setup,
        "entry": entry, "stop": stop, "target": target,
        "shares": shares, "pnl": pnl, "note": note,
        **extra,
    }
    with open(TRADES_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")
    return record


def read_trades(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """All events oldest-first (optionally just the last `limit`)."""
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


def _lifecycles() -> Dict[str, List[Dict[str, Any]]]:
    """Events grouped by trade_id (legacy rows without one group per symbol)."""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for r in read_trades():
        key = r.get("trade_id") or f"legacy-{r.get('symbol', '?')}"
        groups.setdefault(key, []).append(r)
    return groups


def _merged(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """One view of a trade: later non-null fields override earlier ones."""
    out: Dict[str, Any] = {}
    for e in events:
        out.update({k: v for k, v in e.items() if v is not None and v != ""})
    return out


def open_positions() -> Dict[str, Dict[str, Any]]:
    """
    Trades that are filled and not yet terminal, keyed by trade_id. Each value
    is the merged lifecycle (so entry/stop/target from `planned` survive into
    the `filled` view). "What am I holding — and what's the plan for it?"
    """
    out = {}
    for tid, events in _lifecycles().items():
        statuses = [e.get("status") for e in events]
        if "filled" in statuses and not (set(statuses) & TERMINAL):
            out[tid] = _merged(events)
    return out


def pending_orders() -> Dict[str, Dict[str, Any]]:
    """Planned/submitted trades with no fill and no terminal event — resting
    entry orders or approvals still in flight. Reconcile these against the
    broker's get_orders() every run; mark stale ones cancelled/expired."""
    out = {}
    for tid, events in _lifecycles().items():
        statuses = [e.get("status") for e in events]
        if "filled" not in statuses and not (set(statuses) & TERMINAL):
            out[tid] = _merged(events)
    return out


def realized_pnl(date_et: Optional[str] = None) -> float:
    """Realized P&L from closed trades — for ONE ET day if given (use
    session()['date']; the risk circuit breaker wants today's, not all-time)."""
    total = 0.0
    for r in read_trades():
        if r.get("status") == "closed" and r.get("pnl") is not None:
            if date_et and r.get("date_et") != date_et:
                continue
            total += float(r["pnl"])
    return round(total, 2)


def today_summary(date_et: str) -> Dict[str, Any]:
    """Today's closed trades in order — feeds RiskBudget.from_journal()."""
    closed = [r for r in read_trades()
              if r.get("status") == "closed" and r.get("date_et") == date_et]
    pnls = [float(r["pnl"]) for r in closed if r.get("pnl") is not None]
    consec = 0
    for p in reversed(pnls):
        if p < 0:
            consec += 1
        else:
            break
    return {"closed_trades": len(closed), "realized_pnl": round(sum(pnls), 2),
            "consecutive_losses": consec, "pnls": pnls}


def day_trades_past_5_sessions(today_et: str) -> int:
    """Round trips (fill + close, same ET day) over the last 5 distinct journal
    days — the PDT counter. Under $25k equity, ≤3 are allowed."""
    by_tid = _lifecycles()
    days = sorted({r.get("date_et") for r in read_trades() if r.get("date_et")})[-5:]
    n = 0
    for events in by_tid.values():
        dates = {e.get("date_et") for e in events if e.get("status") in ("filled", "closed")}
        statuses = {e.get("status") for e in events}
        if "filled" in statuses and "closed" in statuses and len(dates) == 1 \
                and dates and next(iter(dates)) in days:
            n += 1
    return n


def setup_stats() -> Dict[str, Dict[str, Any]]:
    """
    Per-setup scorecard from the agent's own history — the review loop's input.
    {"orb": {"n": 12, "wins": 3, "win_rate": 0.25, "total_pnl": 312.5,
             "avg_pnl": 26.0, "by_phase": {"opening": 9, "lunch": 3}}, ...}
    A setup that's negative after ~20 trades is a setup to retire (write that
    in strategy.md).
    """
    stats: Dict[str, Dict[str, Any]] = {}
    for tid, events in _lifecycles().items():
        m = _merged(events)
        if m.get("status") != "closed" or m.get("pnl") is None:
            continue
        s = stats.setdefault(m.get("setup") or "unknown",
                             {"n": 0, "wins": 0, "total_pnl": 0.0, "by_phase": {}})
        pnl = float(m["pnl"])
        s["n"] += 1
        s["wins"] += 1 if pnl > 0 else 0
        s["total_pnl"] = round(s["total_pnl"] + pnl, 2)
        phase = m.get("phase")
        if phase:
            s["by_phase"][phase] = s["by_phase"].get(phase, 0) + 1
    for s in stats.values():
        s["win_rate"] = round(s["wins"] / s["n"], 2) if s["n"] else None
        s["avg_pnl"] = round(s["total_pnl"] / s["n"], 2) if s["n"] else None
    return stats


# ── plan ─────────────────────────────────────────────────────────────────────

def write_plan(content: str, date_et: Optional[str] = None) -> str:
    """Overwrite plan.md with the plan for `date_et` (the nightly PLAN run's
    output: watchlist with catalyst notes, risk budget, focus/avoid list)."""
    _ensure_dir()
    date_et = date_et or now_et().date().isoformat()
    body = f"# Plan for {date_et}\n\n{content.strip()}\n"
    with open(PLAN_PATH, "w") as f:
        f.write(body)
    return body


def read_plan() -> Dict[str, str]:
    """{'date': 'YYYY-MM-DD', 'content': ...}. ALWAYS check date — a stale plan
    (date != today) means the nightly run failed; trade reduced or not at all."""
    if not os.path.exists(PLAN_PATH):
        return {"date": "", "content": ""}
    with open(PLAN_PATH) as f:
        text = f.read()
    first, _, rest = text.partition("\n")
    date = first.replace("# Plan for", "").strip() if first.startswith("# Plan for") else ""
    return {"date": date, "content": rest.strip()}


# ── the run's memory ─────────────────────────────────────────────────────────
#
# There is deliberately no day-trading notebook any more. A private diary that
# every run read whole was the single most expensive thing in the operation, and
# splitting it fixed more than cost: a thesis in a diary is invisible to the
# user and unfindable later. Its contents now live where they belong —
#
#   a view on a company   -> stocks/{SYMBOL}/thesis.md   (shows in Analysis)
#   work spanning runs    -> tasks/{slug}.md             (shows in Tasks)
#   what happened today   -> journal/{YYYY-MM}.md        (dated, self-bounding)
#   a rule you now follow -> playbooks/day-trading.md
#
# — all reached through the `library` skill, which reads sections rather than
# files. See skills/library/SKILL.md.

JOURNAL_DOC = "journal/{month}.md"


def journal_path(when=None) -> str:
    """This month's log document. Dated files need no rotation: next month is
    simply a new file, and the library indexes them all."""
    return JOURNAL_DOC.format(month=(when or now_et()).strftime("%Y-%m"))


def append_note(did: str, next_steps: str = "") -> str:
    """End-of-run entry in this month's log.

    `next_steps` is the standing message to the next run — session_state() hands
    it straight back, so it's the one channel that reliably survives. Anything
    that should outlive tomorrow belongs in a task file or the playbook instead.
    """
    from skills.library.scripts.notes import log
    body = did.strip()
    if next_steps:
        body += f"\n\n**Next:** {next_steps.strip()}"
    return log(journal_path(), now_et().isoformat(timespec="seconds"), body)


def last_note() -> Dict[str, str]:
    """The previous run's entry: {'title', 'body'}. Empty if this is the first
    run of the month — check the prior month only if you actually need to."""
    from skills.library.scripts.notes import latest
    entries = latest(journal_path(), 1)
    return entries[0] if entries else {"title": "", "body": ""}


def session_state(**_ignored) -> Dict[str, Any]:
    """
    One-call situational awareness — call this FIRST every run, and let it be
    the only memory read you make unless something specific is missing.

    Everything here is derived from the trade ledger and one log entry, so it
    stays around 1-2K tokens no matter how long the operation has been running.
    To go deeper, go through the library: `read("stocks/NVDA/thesis.md",
    "Invalidation")`, `find("dilution")`, `tasks(due_by=today)` — never a
    whole-file read.

    Extra keyword arguments are accepted and ignored, so a live agent calling
    an older signature doesn't crash mid-run.
    """
    from .clock import session
    from skills.library.scripts.notes import tasks as open_tasks
    sess = session()
    today = sess["date"]
    return {
        "session": sess,
        "open_positions": open_positions(),
        "pending_orders": pending_orders(),
        "today": today_summary(today),
        "day_trades_past_5_sessions": day_trades_past_5_sessions(today),
        "plan": read_plan(),
        "last_note": last_note(),
        "tasks_due": open_tasks(due_by=today),
    }
