"""D-series: intraday NIFTY strategies on 1-minute bars (index or futures).

Trades are sized at one NIFTY futures lot. If only index minute data is available it is used as a proxy for
futures prices (ignores the futures basis, which barely matters intraday).
"""
import numpy as np
import pandas as pd

from ..costs import DEFAULT_COSTS, NIFTY_LOT
from ..data import Market

CAPITAL_FUT = 200_000
EXIT_TIME = pd.Timedelta(hours=15, minutes=10)


def _trade(rows, entry_ts, exit_ts, direction, entry_px, exit_px, reason, name):
    slip = DEFAULT_COSTS.fut_slippage
    e = entry_px + slip * direction
    x = exit_px - slip * direction
    pts = (x - e) * direction
    side_in, side_out = ("buy", "sell") if direction > 0 else ("sell", "buy")
    costs = DEFAULT_COSTS.future_order(e, NIFTY_LOT, side_in) + DEFAULT_COSTS.future_order(x, NIFTY_LOT, side_out)
    rows.append({"strategy": name, "entry_date": entry_ts.normalize(), "exit_date": exit_ts.normalize(),
                 "detail": f"{'long' if direction > 0 else 'short'} {entry_ts.time()}", "pnl_pts": pts,
                 "costs_rs": costs, "pnl_rs": pts * NIFTY_LOT - costs, "exits": reason})


def _sessions(minute: pd.DataFrame):
    for day, g in minute.groupby(minute.index.normalize()):
        g = g.between_time("09:15", "15:29")
        if len(g) > 300:
            yield day, g


def _walk(g: pd.DataFrame, start_ts, direction, stop, target, exit_ts):
    """Follow 1-minute bars after start_ts; stop first if both hit in one bar. Returns (ts, price, reason)."""
    after = g[(g.index > start_ts) & (g.index <= exit_ts)]
    for ts, bar in after.iterrows():
        if direction > 0:
            if bar["low"] <= stop:
                return ts, stop, "stop"
            if target is not None and bar["high"] >= target:
                return ts, target, "target"
        else:
            if bar["high"] >= stop:
                return ts, stop, "stop"
            if target is not None and bar["low"] <= target:
                return ts, target, "target"
    last = after.iloc[-1] if len(after) else g.iloc[-1]
    return (after.index[-1] if len(after) else g.index[-1]), float(last["close"]), "time"


def d1_orb(m: Market, sig: pd.DataFrame) -> pd.DataFrame:
    """D1: 09:15-09:30 opening range; trade the first 5-minute close outside it. SL at the range midpoint,
    target 2x the range, exit 15:10. Filters: range narrower than its 20-day median, and (if futures data is
    available) the previous day's price-OI build-up agrees with the direction."""
    rows, or_hist = [], []
    bias = sig["buildup_bias"].shift(1) if "buildup_bias" in sig else None
    for day, g in _sessions(m.minute):
        orng = g.between_time("09:15", "09:29")
        hi, lo = orng["high"].max(), orng["low"].min()
        or_pct = (hi - lo) / orng["open"].iloc[0]
        med = np.median(or_hist[-20:]) if len(or_hist) >= 10 else np.nan
        or_hist.append(or_pct)
        if not (or_pct < med):
            continue
        five = g.between_time("09:30", "15:09").resample("5min", label="right", closed="right").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        brk = five[(five["close"] > hi) | (five["close"] < lo)]
        if not len(brk):
            continue
        ts, close = brk.index[0], brk["close"].iloc[0]
        direction = 1 if close > hi else -1
        if bias is not None and day in bias.index and bias.loc[day] not in (direction,):
            continue
        rng, mid = hi - lo, (hi + lo) / 2
        target = close + 2 * rng * direction
        xt, xp, reason = _walk(g, ts, direction, mid, target, day + EXIT_TIME)
        _trade(rows, ts, xt, direction, close, xp, reason, "D1")
    return pd.DataFrame(rows)


def _five(g):
    return g.resample("5min", label="right", closed="right").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()


def d2_vwap_buildup(m: Market, sig: pd.DataFrame) -> pd.DataFrame:
    """D2: long when price is above VWAP, the previous day's futures build-up was bullish and RR25 fell on the
    previous day (short: mirror). SL 0.3%, trail by the 5-minute EMA20, exit 15:10. One trade per day.
    Uses VWAP if the minute data has volume, otherwise a time-weighted average price."""
    rows = []
    prev_bias = sig["buildup_bias"].shift(1) if "buildup_bias" in sig else None
    rr_fall = (sig["rr25"].diff() < 0).shift(1) if "rr25" in sig else None
    for day, g in _sessions(m.minute):
        if prev_bias is None or day not in prev_bias.index or rr_fall is None:
            break
        b, fell = prev_bias.loc[day], rr_fall.loc[day]
        if b == 0 or pd.isna(fell):
            continue
        direction = 1 if (b > 0 and fell) else (-1 if (b < 0 and not fell) else 0)
        if not direction:
            continue
        tp = (g["high"] + g["low"] + g["close"]) / 3
        w = g["volume"] if "volume" in g and g["volume"].sum() > 0 else pd.Series(1.0, index=g.index)
        vwap = (tp * w).cumsum() / w.cumsum()
        five = _five(g.between_time("09:20", "15:09"))
        five["vwap"] = vwap.reindex(five.index, method="ffill")
        five["ema20"] = five["close"].ewm(span=20, adjust=False).mean()
        cond = (five["close"] > five["vwap"]) if direction > 0 else (five["close"] < five["vwap"])
        if not cond.any():
            continue
        ts = cond[cond].index[0]
        entry = five.loc[ts, "close"]
        stop = entry * (1 - 0.003 * direction)
        exit_ts, exit_px, reason = day + EXIT_TIME, None, "time"
        for t2, bar in five[five.index > ts].iterrows():
            if (direction > 0 and bar["low"] <= stop) or (direction < 0 and bar["high"] >= stop):
                exit_ts, exit_px, reason = t2, stop, "stop"
                break
            if (direction > 0 and bar["close"] < bar["ema20"]) or (direction < 0 and bar["close"] > bar["ema20"]):
                exit_ts, exit_px, reason = t2, bar["close"], "trail"
                break
        if exit_px is None:
            exit_px = float(g[g.index <= exit_ts]["close"].iloc[-1])
        _trade(rows, ts, exit_ts, direction, entry, exit_px, reason, "D2")
    return pd.DataFrame(rows)


def supertrend(df: pd.DataFrame, n: int = 10, mult: float = 3.0) -> pd.Series:
    hl2 = (df["high"] + df["low"]) / 2
    tr = pd.concat([df["high"] - df["low"], (df["high"] - df["close"].shift()).abs(),
                    (df["low"] - df["close"].shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / n, adjust=False).mean()
    upper, lower = (hl2 + mult * atr).values, (hl2 - mult * atr).values
    close = df["close"].values
    trend = np.ones(len(df))
    fu, fl = upper.copy(), lower.copy()
    for i in range(1, len(df)):
        fu[i] = upper[i] if (upper[i] < fu[i - 1] or close[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lower[i] if (lower[i] > fl[i - 1] or close[i - 1] < fl[i - 1]) else fl[i - 1]
        trend[i] = 1 if close[i] > fu[i - 1] else (-1 if close[i] < fl[i - 1] else trend[i - 1])
    return pd.Series(trend, index=df.index)


def d3_supertrend_ema(m: Market, sig: pd.DataFrame) -> pd.DataFrame:
    """D3: 5-minute Supertrend(10,3) flips, taken only when EMA9/EMA21 agree; exit on the opposite flip or 15:10."""
    five = _five(m.minute.between_time("09:15", "15:29"))
    five["st"] = supertrend(five)
    five["ema9"] = five["close"].ewm(span=9, adjust=False).mean()
    five["ema21"] = five["close"].ewm(span=21, adjust=False).mean()
    rows = []
    for day, g in five.groupby(five.index.normalize()):
        g = g[g.index <= day + EXIT_TIME]
        pos, entry, ets = 0, None, None
        prev_st = None
        for ts, bar in g.iterrows():
            if prev_st is not None and bar["st"] != prev_st:
                if pos:
                    _trade(rows, ets, ts, pos, entry, bar["close"], "flip", "D3")
                    pos = 0
                want = int(bar["st"])
                if (want > 0 and bar["ema9"] > bar["ema21"]) or (want < 0 and bar["ema9"] < bar["ema21"]):
                    pos, entry, ets = want, bar["close"], ts
            prev_st = bar["st"]
        if pos:
            _trade(rows, ets, g.index[-1], pos, entry, g["close"].iloc[-1], "time", "D3")
    return pd.DataFrame(rows)


STRATEGIES = {"D1": (d1_orb, CAPITAL_FUT), "D2": (d2_vwap_buildup, CAPITAL_FUT), "D3": (d3_supertrend_ema, CAPITAL_FUT)}
