"""
Risk management — the only part of day trading the evidence says you control.

Edges are fragile and most day traders lose (see SKILL.md citations). Survival
comes from fixed-fractional sizing, hard daily loss limits, and asymmetric
risk/reward — not from prediction. These helpers make those rules mechanical so
an automation can enforce them instead of relying on willpower.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Literal


def position_size(equity: float, risk_pct: float, entry: float, stop: float,
                  max_leverage: float = 4.0) -> dict:
    """
    Shares to trade so that being stopped out loses exactly `risk_pct` of equity.

        shares = (equity * risk_pct) / |entry - stop|

    Capped so notional <= equity * max_leverage (the research caps ORB at 4x).

    Args:
        equity: account value in dollars
        risk_pct: fraction of equity to risk, e.g. 0.01 for 1%
        entry, stop: prices; their distance is the per-share risk
        max_leverage: notional cap as a multiple of equity (default 4x)

    Returns dict with shares (int), dollars_at_risk, notional, leverage, and a
    `capped` flag if the leverage cap bound the size.
    """
    per_share_risk = abs(entry - stop)
    if per_share_risk <= 0 or equity <= 0 or risk_pct <= 0:
        return {"shares": 0, "dollars_at_risk": 0.0, "notional": 0.0,
                "leverage": 0.0, "capped": False, "reason": "invalid inputs / zero stop distance"}
    raw_shares = (equity * risk_pct) / per_share_risk
    max_shares_by_leverage = (equity * max_leverage) / entry
    capped = raw_shares > max_shares_by_leverage
    shares = int(min(raw_shares, max_shares_by_leverage))
    notional = shares * entry
    return {
        "shares": shares,
        "dollars_at_risk": round(shares * per_share_risk, 2),
        "notional": round(notional, 2),
        "leverage": round(notional / equity, 2) if equity else 0.0,
        "capped": capped,
    }


def plan_trade(equity: float, entry: float, stop: float,
               side: Literal["long", "short"] = "long",
               risk_pct: float = 0.01, rr: float = 10.0,
               max_leverage: float = 4.0) -> dict:
    """
    Build a complete, risk-defined trade plan in one call: shares, target at `rr`
    R-multiple, and the dollar P&L at stop vs target.

    `rr=10` matches the Zarattini ORB target (10R, let winners run to a big
    payoff that covers a low win rate). Use rr=2 for a conventional 2:1 day trade.
    For a short, stop is above entry and target below.
    """
    sizing = position_size(equity, risk_pct, entry, stop, max_leverage)
    r = abs(entry - stop)
    if side == "long":
        target = entry + rr * r
    else:
        target = entry - rr * r
    shares = sizing["shares"]
    return {
        "side": side,
        "entry": round(entry, 4),
        "stop": round(stop, 4),
        "target": round(target, 4),
        "r_per_share": round(r, 4),
        "rr": rr,
        **sizing,
        "profit_at_target": round(shares * rr * r, 2),
        "loss_at_stop": round(-shares * r, 2),
    }


@dataclass
class RiskBudget:
    """
    A day's circuit breaker. Construct at session start; call register(pnl) after
    each closed trade; check can_trade() before every new entry.

    Defaults reflect the consensus pro rules (SKILL.md): risk 1%/trade, stop the
    day at -3% OR after 3 losers in a row, cap at a few quality setups.
    """
    starting_equity: float
    max_daily_loss_pct: float = 0.03      # hard stop for the day
    max_consecutive_losses: int = 3       # tilt guard
    max_trades: int = 10                  # over-trading guard
    risk_pct_per_trade: float = 0.01

    realized_pnl: float = 0.0
    trades_taken: int = 0
    consecutive_losses: int = 0
    _closed: List[float] = field(default_factory=list)

    def register(self, pnl: float) -> None:
        """Record a closed-trade P&L (dollars)."""
        self.realized_pnl += pnl
        self.trades_taken += 1
        self._closed.append(pnl)
        self.consecutive_losses = self.consecutive_losses + 1 if pnl < 0 else 0

    def can_trade(self) -> dict:
        """Whether a new entry is allowed, with the blocking reason if not."""
        loss_limit = -self.starting_equity * self.max_daily_loss_pct
        if self.realized_pnl <= loss_limit:
            return {"ok": False, "reason": f"daily loss limit hit ({self.realized_pnl:.2f} <= {loss_limit:.2f})"}
        if self.consecutive_losses >= self.max_consecutive_losses:
            return {"ok": False, "reason": f"{self.consecutive_losses} losses in a row — stop for the day"}
        if self.trades_taken >= self.max_trades:
            return {"ok": False, "reason": f"max {self.max_trades} trades reached"}
        return {"ok": True, "reason": "within risk budget"}

    def dollars_to_risk(self) -> float:
        """The 1% (or configured) risk amount for the next trade, in dollars."""
        return self.starting_equity * self.risk_pct_per_trade

    def summary(self) -> dict:
        return {
            "realized_pnl": round(self.realized_pnl, 2),
            "trades_taken": self.trades_taken,
            "consecutive_losses": self.consecutive_losses,
            "can_trade": self.can_trade(),
            "pnl_pct": round(100 * self.realized_pnl / self.starting_equity, 2) if self.starting_equity else 0.0,
        }
