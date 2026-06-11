"""
Risk management — the only edge you fully control, enforced as code.

Most day traders lose for behavioral reasons (overtrading, averaging down,
revenge trading). An agent has no emotions to manage — but only if the gates
live in code AND their state survives between runs. That's why RiskBudget is
rebuilt from the persistent journal (from_journal), not constructed blank:
a fresh automation run inherits today's losses, streaks, and trade count.

Order of operations before ANY entry:
    budget = RiskBudget.from_journal(equity)      # today's state, from disk
    gate = budget.can_trade(account_value=..., open_risk_dollars=...)
    if gate["ok"]: plan = plan_trade(...)         # exact shares/stop/target
"""
from dataclasses import dataclass
from typing import Optional, Literal


def position_size(equity: float, risk_pct: float, entry: float, stop: float,
                  max_leverage: float = 4.0, max_weight: float = 0.25) -> dict:
    """
    Shares so a stop-out loses exactly risk_pct of equity:
        shares = (equity × risk_pct) / |entry − stop|
    capped by notional ≤ equity×max_leverage AND ≤ equity×max_weight (the
    equal-weight cap from the ORB research — default ¼ of equity per name).

    shares == 0 is a real outcome (price too high / stop too tight for the
    budget) — check `reason` and skip the trade rather than rounding up.
    """
    per_share_risk = abs(entry - stop)
    if per_share_risk <= 0 or equity <= 0 or risk_pct <= 0:
        return {"shares": 0, "dollars_at_risk": 0.0, "notional": 0.0, "leverage": 0.0,
                "capped": False, "reason": "invalid inputs / zero stop distance"}
    raw = (equity * risk_pct) / per_share_risk
    cap = min(equity * max_leverage, equity * max_weight) / entry
    shares = int(min(raw, cap))
    notional = shares * entry
    return {
        "shares": shares,
        "dollars_at_risk": round(shares * per_share_risk, 2),
        "notional": round(notional, 2),
        "leverage": round(notional / equity, 2),
        "capped": raw > cap,
        "reason": ("ok" if shares > 0 else
                   "rounds to 0 shares — risk budget too small for this price/stop; skip"),
    }


def plan_trade(equity: float, entry: float, stop: float,
               side: Literal["long", "short"] = "long",
               risk_pct: float = 0.01, rr: float = 10.0,
               max_leverage: float = 4.0, max_weight: float = 0.25) -> dict:
    """
    Complete risk-defined plan: shares, target at `rr` R-multiples, dollar P&L
    at stop vs target. rr=10 matches the Zarattini ORB payoff profile (the EOD
    exit usually fires first); use rr=2 for a conventional day trade.
    """
    sizing = position_size(equity, risk_pct, entry, stop, max_leverage, max_weight)
    r = abs(entry - stop)
    target = entry + rr * r if side == "long" else entry - rr * r
    return {
        "side": side, "entry": round(entry, 4), "stop": round(stop, 4),
        "target": round(target, 4), "r_per_share": round(r, 4), "rr": rr,
        **sizing,
        "profit_at_target": round(sizing["shares"] * rr * r, 2),
        "loss_at_stop": round(-sizing["shares"] * r, 2),
    }


@dataclass
class RiskBudget:
    """
    The day's circuit breaker. ALWAYS construct via from_journal() in
    automations — a blank RiskBudget() forgets every previous run's losses.
    """
    starting_equity: float
    max_daily_loss_pct: float = 0.03      # hard stop for the day
    max_consecutive_losses: int = 3       # tilt guard
    max_trades: int = 10                  # over-trading guard
    risk_pct_per_trade: float = 0.01

    realized_pnl: float = 0.0
    trades_taken: int = 0
    consecutive_losses: int = 0
    day_trades_5d: int = 0

    @classmethod
    def from_journal(cls, starting_equity: float, **overrides) -> "RiskBudget":
        """Rebuild today's state from the persistent journal — this is what
        makes the −3% day stop and the 3-loss streak survive stateless runs."""
        from .clock import session
        from .journal import today_summary, day_trades_past_5_sessions
        today = session()["date"]
        t = today_summary(today)
        return cls(starting_equity=starting_equity,
                   realized_pnl=t["realized_pnl"],
                   trades_taken=t["closed_trades"],
                   consecutive_losses=t["consecutive_losses"],
                   day_trades_5d=day_trades_past_5_sessions(today),
                   **overrides)

    def register(self, pnl: float) -> None:
        """Record a closed trade in THIS run (the journal covers prior runs)."""
        self.realized_pnl += pnl
        self.trades_taken += 1
        self.consecutive_losses = self.consecutive_losses + 1 if pnl < 0 else 0

    def can_trade(self, account_value: Optional[float] = None,
                  open_risk_dollars: float = 0.0) -> dict:
        """
        Gate before every NEW entry.
          account_value     — live equity; enables the PDT check (<$25k → ≤3
                              day trades per 5 sessions).
          open_risk_dollars — Σ shares×|last−stop| across open positions, so an
                              open trade bleeding toward its stop counts against
                              the daily limit BEFORE it's realized.
        """
        loss_limit = -self.starting_equity * self.max_daily_loss_pct
        effective = self.realized_pnl - max(open_risk_dollars, 0.0)
        if self.realized_pnl <= loss_limit:
            return {"ok": False, "reason": f"daily loss limit hit ({self.realized_pnl:.2f} ≤ {loss_limit:.2f})"}
        if effective <= loss_limit:
            return {"ok": False, "reason": (f"realized {self.realized_pnl:.2f} + open risk "
                                            f"{open_risk_dollars:.2f} would breach the daily limit")}
        if self.consecutive_losses >= self.max_consecutive_losses:
            return {"ok": False, "reason": f"{self.consecutive_losses} losses in a row — done for the day"}
        if self.trades_taken >= self.max_trades:
            return {"ok": False, "reason": f"max {self.max_trades} trades reached"}
        if account_value is not None and account_value < 25_000 and self.day_trades_5d >= 3:
            return {"ok": False, "reason": (f"PDT: {self.day_trades_5d} day trades in 5 sessions "
                                            f"with equity < $25k — no more round trips")}
        return {"ok": True, "reason": "within risk budget"}

    def dollars_to_risk(self) -> float:
        return self.starting_equity * self.risk_pct_per_trade

    def summary(self) -> dict:
        return {
            "realized_pnl": round(self.realized_pnl, 2),
            "trades_taken": self.trades_taken,
            "consecutive_losses": self.consecutive_losses,
            "day_trades_5d": self.day_trades_5d,
            "can_trade": self.can_trade(),
            "pnl_pct": round(100 * self.realized_pnl / self.starting_equity, 2)
                       if self.starting_equity else 0.0,
        }
