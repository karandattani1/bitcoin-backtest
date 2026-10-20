"""Simulating option legs on daily (end-of-day) bars.

Daily bars only give open/high/low/close per contract, so intraday paths are approximated:
- entry "at the open" uses the contract's first traded price of the day;
- a stop-loss is hit if the day's high (short leg) or low (long leg) reaches the stop level, and it fills at
  the stop level plus slippage;
- if a long leg could have hit both its stop and its target on the same day, the stop is assumed (conservative);
- "exit at 15:15" uses the day's close.
All prices are per unit; P&L is converted to rupees for one current NIFTY lot.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..costs import DEFAULT_COSTS, NIFTY_LOT, CostModel


@dataclass
class Fill:
    entry: float
    exit: float
    side: str            # "sell" or "buy" at entry
    exit_reason: str
    costs_rs: float

    @property
    def pnl_pts(self) -> float:
        return (self.entry - self.exit) if self.side == "sell" else (self.exit - self.entry)


def intraday_leg(row, side: str, sl_pct: float | None = None, tp_pct: float | None = None,
                 expiry_day: bool = False, costs: CostModel = DEFAULT_COSTS, lot: int = NIFTY_LOT) -> Fill:
    slip = costs.slip(expiry_day)
    o, h, l, c = float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"])
    if side == "sell":
        entry = max(o - slip, 0.05)
        if sl_pct is not None and h >= o * (1 + sl_pct):
            exit_px, reason = o * (1 + sl_pct) + slip, "stop"
        else:
            exit_px, reason = c + slip, "close"
        cost = costs.option_order(entry, lot, "sell") + costs.option_order(exit_px, lot, "buy")
    else:
        entry = o + slip
        stop_hit = sl_pct is not None and l <= o * (1 - sl_pct)
        tgt_hit = tp_pct is not None and h >= o * (1 + tp_pct)
        if stop_hit:
            exit_px, reason = max(o * (1 - sl_pct) - slip, 0.05), "stop"
        elif tgt_hit:
            exit_px, reason = o * (1 + tp_pct) - slip, "target"
        else:
            exit_px, reason = max(c - slip, 0.05), "close"
        cost = costs.option_order(entry, lot, "buy") + costs.option_order(exit_px, lot, "sell")
    return Fill(entry, exit_px, side, reason, cost)


def overnight_leg(row_today, row_next, side: str, costs: CostModel = DEFAULT_COSTS, lot: int = NIFTY_LOT) -> Fill:
    """Enter at today's close, exit at the next day's open."""
    slip = costs.slip(False)
    if side == "sell":
        entry, exit_px = max(float(row_today["close"]) - slip, 0.05), float(row_next["open"]) + slip
        cost = costs.option_order(entry, lot, "sell") + costs.option_order(exit_px, lot, "buy")
    else:
        entry, exit_px = float(row_today["close"]) + slip, max(float(row_next["open"]) - slip, 0.05)
        cost = costs.option_order(entry, lot, "buy") + costs.option_order(exit_px, lot, "sell")
    return Fill(entry, exit_px, side, "next_open", cost)


def intrinsic(strike: float, opt_type: str, spot: float) -> float:
    return max(spot - strike, 0.0) if opt_type == "CE" else max(strike - spot, 0.0)


@dataclass
class TradeLog:
    strategy: str
    capital: float
    rows: list = field(default_factory=list)

    def add(self, entry_date, exit_date, fills: list[Fill], detail: str) -> None:
        pts = sum(f.pnl_pts for f in fills)
        costs_rs = sum(f.costs_rs for f in fills)
        self.rows.append({
            "strategy": self.strategy, "entry_date": entry_date, "exit_date": exit_date, "detail": detail,
            "pnl_pts": pts, "costs_rs": costs_rs, "pnl_rs": pts * NIFTY_LOT - costs_rs,
            "exits": ",".join(f.exit_reason for f in fills),
        })

    def frame(self) -> pd.DataFrame:
        cols = ["strategy", "entry_date", "exit_date", "detail", "pnl_pts", "costs_rs", "pnl_rs", "exits"]
        return pd.DataFrame(self.rows, columns=cols)


def between(row_a, field_a: str, row_b, field_b: str, side: str, costs: CostModel = DEFAULT_COSTS,
            lot: int = NIFTY_LOT, reason: str = "hold") -> Fill:
    """Enter at row_a[field_a] and exit at row_b[field_b] (e.g. close -> next close)."""
    slip = costs.slip(False)
    a, b = float(row_a[field_a]), float(row_b[field_b])
    if side == "sell":
        entry, exit_px = max(a - slip, 0.05), b + slip
        cost = costs.option_order(entry, lot, "sell") + costs.option_order(exit_px, lot, "buy")
    else:
        entry, exit_px = a + slip, max(b - slip, 0.05)
        cost = costs.option_order(entry, lot, "buy") + costs.option_order(exit_px, lot, "sell")
    return Fill(entry, exit_px, side, reason, cost)
