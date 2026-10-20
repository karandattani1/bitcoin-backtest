"""Option strategies A, B and C from research/strategy-rulebook.md, approximated on daily bars.

See legs.py for how intraday behaviour is approximated. Where a rule can't be expressed on daily bars the
deviation is written in the strategy's docstring and in the results report.
"""
import numpy as np
import pandas as pd

from .. import black76
from ..costs import DEFAULT_COSTS, NIFTY_LOT
from ..data import Market
from .legs import Fill, TradeLog, between, intraday_leg, intrinsic

STRIKE_STEP = 50.0

# Capital assumed per lot, used only to turn rupee P&L into % returns and drawdowns.
CAPITAL = {"naked": 250_000, "defined": 100_000, "spread": 75_000, "buy": 50_000}


def _t_at_open(date, expiry) -> float:
    return max((expiry - date).days, 0) / 365.0 + 0.26 / 365.0  # ~6.25 trading hours left today


def _strike_for_delta(m: Market, date, expiry, opt_type, target, spot, vol, t) -> float | None:
    ks = m.strikes(date, expiry, opt_type)
    if not len(ks) or not np.isfinite(vol):
        return None
    fwd = spot * np.exp(black76.RATE * t)
    d = np.abs(black76.delta(fwd, ks, t, vol, opt_type == "CE"))
    return float(ks[np.argmin(np.abs(d - target))])


def _prev(sig: pd.DataFrame) -> pd.DataFrame:
    return sig.shift(1)


def _legs_open(m, date, expiry, legs, expiry_day, sl_pct=None):
    """legs: list of (side, strike, opt_type, sl). Returns fills or None if any contract is missing."""
    fills = []
    for side, k, typ, sl in legs:
        row = m.contract(date, expiry, k, typ)
        if row is None:
            return None
        fills.append(intraday_leg(row, side, sl_pct=sl if sl is not None else sl_pct, expiry_day=expiry_day))
    return fills


# ---------------------------------------------------------------------------------------------- A
def a1_straddle_920(m: Market, sig: pd.DataFrame, sl: float = 0.30, name: str = "A1") -> pd.DataFrame:
    """A1: sell ATM CE+PE of the nearest expiry at the open, 30% SL per leg, exit at the close."""
    log = TradeLog(name, CAPITAL["naked"])
    for d in m.trading_days():
        if d not in m.index.index:
            continue
        exp = m.front_expiry(d, 0)
        if exp is None:
            continue
        k = m.atm_strike(d, exp, m.index.at[d, "open"])
        fills = k and _legs_open(m, d, exp, [("sell", k, "CE", sl), ("sell", k, "PE", sl)], d == exp)
        if fills:
            log.add(d, d, fills, f"ATM {k:.0f} exp {exp.date()}")
    return log.frame()


def a4_vrp_filtered(m: Market, sig: pd.DataFrame) -> pd.DataFrame:
    """A4: trade only when IVP>=50, VRP ratio>=1.2 and RR25_z<1.5 (all from the previous close).
    Rich wings (BF25_z>1) -> 20-delta strangle; cheap wings (BF25_z<-1) -> iron fly; else ATM straddle.
    Deviation: the rule's combined 25% SL needs intraday data; a 30% per-leg SL is used on the short legs."""
    log = TradeLog("A4", CAPITAL["naked"])
    p = _prev(sig)
    for d in m.trading_days():
        if d not in p.index or d not in m.index.index:
            continue
        s = p.loc[d]
        if not (s.get("ivp", np.nan) >= 50 and s.get("vrp_ratio", np.nan) >= 1.2 and s.get("rr25_z", np.nan) < 1.5):
            continue
        if bool(sig.at[d, "event_today"]) if "event_today" in sig else False:
            continue
        exp = m.front_expiry(d, 0)
        if exp is None:
            continue
        spot = m.index.at[d, "open"]
        k = m.atm_strike(d, exp, spot)
        if k is None:
            continue
        bf = s.get("bf25_z", np.nan)
        if bf > 1:
            t, vol = _t_at_open(d, exp), s.get("atm_iv", np.nan) / 100
            kc = _strike_for_delta(m, d, exp, "CE", 0.20, spot, vol, t)
            kp = _strike_for_delta(m, d, exp, "PE", 0.20, spot, vol, t)
            legs, detail = [("sell", kc, "CE", 0.30), ("sell", kp, "PE", 0.30)], f"strangle {kp:.0f}/{kc:.0f}"
        elif bf < -1:
            ce, pe = m.contract(d, exp, k, "CE"), m.contract(d, exp, k, "PE")
            if ce is None or pe is None:
                continue
            width = max(STRIKE_STEP, round((ce["open"] + pe["open"]) / STRIKE_STEP) * STRIKE_STEP)
            kc, kp = m.nearest_strike(d, exp, "CE", k + width), m.nearest_strike(d, exp, "PE", k - width)
            legs = [("sell", k, "CE", None), ("sell", k, "PE", None), ("buy", kc, "CE", None), ("buy", kp, "PE", None)]
            detail = f"iron fly {k:.0f} wings {kp:.0f}/{kc:.0f}"
        else:
            legs, detail = [("sell", k, "CE", 0.30), ("sell", k, "PE", 0.30)], f"straddle {k:.0f}"
        fills = _legs_open(m, d, exp, legs, d == exp)
        if fills:
            log.add(d, d, fills, detail)
    return log.frame()


def a5_expiry_iron_fly(m: Market, sig: pd.DataFrame) -> pd.DataFrame:
    """A5: expiry day only. Sell ATM straddle at the open, buy wings at ATM +/- the combined premium.
    Deviation: the 50% target / 1x-credit SL are path-dependent; the position is held to the close."""
    log = TradeLog("A5", CAPITAL["defined"])
    for d in m.trading_days():
        exp = m.front_expiry(d, 0)
        if exp is None or exp != d or d not in m.index.index:
            continue
        k = m.atm_strike(d, exp, m.index.at[d, "open"])
        if k is None:
            continue
        ce, pe = m.contract(d, exp, k, "CE"), m.contract(d, exp, k, "PE")
        if ce is None or pe is None:
            continue
        width = max(STRIKE_STEP, round((ce["open"] + pe["open"]) / STRIKE_STEP) * STRIKE_STEP)
        kc, kp = m.nearest_strike(d, exp, "CE", k + width), m.nearest_strike(d, exp, "PE", k - width)
        fills = _legs_open(m, d, exp, [("sell", k, "CE", None), ("sell", k, "PE", None),
                                       ("buy", kc, "CE", None), ("buy", kp, "PE", None)], True)
        if fills:
            log.add(d, d, fills, f"fly {k:.0f} wings {kp:.0f}/{kc:.0f}")
    return log.frame()


def a6_delta_strangle(m: Market, sig: pd.DataFrame, wings: bool = True, name: str = "A6") -> pd.DataFrame:
    """A6: two sessions before each expiry, sell 20-delta CE+PE at the open (with 7-delta wings = iron condor).
    Checked at each close: exit if the loss reaches 1.5x the credit; otherwise settle at expiry.
    Deviation: the delta>0.40 adjustment needs intraday data and is not modelled."""
    log = TradeLog(name, CAPITAL["defined" if wings else "naked"])
    days = m.trading_days()
    pos = {d: i for i, d in enumerate(days)}
    p = _prev(sig)
    expiries = sorted({e for e in m.options["expiry"].unique() if e in pos})
    for exp in expiries:
        i = pos[exp] - 2
        if i < 1:
            continue
        d = days[i]
        if d not in m.index.index or d not in p.index:
            continue
        spot, t = m.index.at[d, "open"], _t_at_open(d, exp)
        vol = p.at[d, "atm_iv"] / 100 if "atm_iv" in p and np.isfinite(p.at[d, "atm_iv"]) else (p.at[d, "vix"] / 100 if "vix" in p else np.nan)
        kc, kp = (_strike_for_delta(m, d, exp, typ, 0.20, spot, vol, t) for typ in ("CE", "PE"))
        if kc is None or kp is None:
            continue
        legs = [("sell", kc, "CE"), ("sell", kp, "PE")]
        if wings:
            wc, wp = (_strike_for_delta(m, d, exp, typ, 0.07, spot, vol, t) for typ in ("CE", "PE"))
            if wc is None or wp is None or wc <= kc or wp >= kp:
                continue
            legs += [("buy", wc, "CE"), ("buy", wp, "PE")]
        entry_rows = [m.contract(d, exp, k, typ) for _, k, typ in legs]
        if any(r is None for r in entry_rows):
            continue
        slip = DEFAULT_COSTS.slip(False)
        entries = [(r["open"] - slip if side == "sell" else r["open"] + slip) for (side, _, _), r in zip(legs, entry_rows)]
        credit = sum(e if side == "sell" else -e for (side, _, _), e in zip(legs, entries))
        last = list(entries)
        exit_px, exit_day, reason = None, exp, "expiry"
        for j in range(i, pos[exp] + 1):
            day = days[j]
            rows = [m.contract(day, exp, k, typ) for _, k, typ in legs]
            last = [float(r["close"]) if r is not None else lp for r, lp in zip(rows, last)]
            if day == exp:
                break
            value = sum(px if side == "sell" else -px for (side, _, _), px in zip(legs, last))
            if credit - value <= -1.5 * credit:
                exit_px = [px + slip if side == "sell" else max(px - slip, 0.05) for (side, _, _), px in zip(legs, last)]
                exit_day, reason = day, "stop"
                break
        fills = []
        for leg_i, ((side, k, typ), e) in enumerate(zip(legs, entries)):
            entry_cost = DEFAULT_COSTS.option_order(e, NIFTY_LOT, side)
            if exit_px is not None:
                x = exit_px[leg_i]
                cost = entry_cost + DEFAULT_COSTS.option_order(x, NIFTY_LOT, "buy" if side == "sell" else "sell")
            else:  # cash-settled at expiry: intrinsic vs index close; exercise STT on long ITM legs
                x = intrinsic(k, typ, m.index.at[exp, "close"]) if exp in m.index.index else last[leg_i]
                cost = entry_cost + (DEFAULT_COSTS.opt_stt_sell * x * NIFTY_LOT if side == "buy" else 0.0)
            fills.append(Fill(e, x, side, reason, cost))
        log.add(d, exit_day, fills, f"{kp:.0f}P/{kc:.0f}C exp {exp.date()}")
    return log.frame()


def a7_oi_wall_strangle(m: Market, sig: pd.DataFrame) -> pd.DataFrame:
    """A7: expiry day. Sell CE at the call wall and PE at the put wall (from the previous close's OI) if each
    is >=0.5% from the open and trades >= Rs 8. Deviation: the 'wall shifts / spot breaks the wall' exits
    need intraday data; a 100% per-leg stop stands in for them."""
    log = TradeLog("A7", CAPITAL["naked"])
    p = _prev(sig)
    for d in m.trading_days():
        exp = m.front_expiry(d, 0)
        if exp is None or exp != d or d not in p.index or d not in m.index.index:
            continue
        s = p.loc[d]
        if s.get("front_expiry") != exp or not np.isfinite(s.get("call_wall", np.nan)):
            continue
        spot = m.index.at[d, "open"]
        kc, kp = s["call_wall"], s["put_wall"]
        if kc < spot * 1.005 or kp > spot * 0.995:
            continue
        rows = [m.contract(d, exp, kc, "CE"), m.contract(d, exp, kp, "PE")]
        if any(r is None or r["open"] < 8 for r in rows):
            continue
        fills = [intraday_leg(r, "sell", sl_pct=1.0, expiry_day=True) for r in rows]
        log.add(d, d, fills, f"walls {kp:.0f}/{kc:.0f}")
    return log.frame()


def a8_rangetrap_overnight(m: Market, sig: pd.DataFrame) -> pd.DataFrame:
    """A8: at the close, if ATR(5)/ATR(20)<0.8, today opened inside yesterday's range, all of the last 3 gaps
    were <0.5%, 20-day kurtosis <1 and tomorrow is not an event day: sell the ATM straddle of the nearest
    expiry at least 2 days out, buy back at the next open. Deviation: the US-VIX condition is not used."""
    log = TradeLog("A8", CAPITAL["naked"])
    days = m.trading_days()
    for i, d in enumerate(days[:-1]):
        if d not in sig.index:
            continue
        s = sig.loc[d]
        gaps_ok = sig["gap_pct"].abs().rolling(3).max().get(d, np.nan) < 0.5
        if not (s["atr_ratio"] < 0.8 and bool(s["inside_day"]) and gaps_ok and s["kurt20"] < 1.0 and not bool(s["event_tomorrow"])):
            continue
        exp = m.front_expiry(d, 2)
        nxt = days[i + 1]
        k = exp is not None and m.atm_strike(d, exp, s["spot"])
        if not k:
            continue
        rows = [(m.contract(d, exp, k, t), m.contract(nxt, exp, k, t)) for t in ("CE", "PE")]
        if any(a is None or b is None for a, b in rows):
            continue
        fills = [between(a, "close", b, "open", "sell", reason="next_open") for a, b in rows]
        log.add(d, nxt, fills, f"ATM {k:.0f} exp {exp.date()}")
    return log.frame()


def a9_kurtosis_straddle(m: Market, sig: pd.DataFrame) -> pd.DataFrame:
    """A9: sell the ATM straddle at the open only if yesterday's 20-day kurtosis was below its 1-year 30th
    percentile and yesterday's range was below its 20-day median. 20% per-leg SL, exit at the close.
    Deviation: the opening-15-minute range condition is replaced by the previous day's range."""
    log = TradeLog("A9", CAPITAL["naked"])
    p = _prev(sig)
    for d in m.trading_days():
        if d not in p.index or d not in m.index.index:
            continue
        s = p.loc[d]
        if not (s["kurt20"] < s["kurt20_p30"] and s["range_pct"] < s["range_med20"]):
            continue
        exp = m.front_expiry(d, 0)
        k = exp is not None and m.atm_strike(d, exp, m.index.at[d, "open"])
        fills = k and _legs_open(m, d, exp, [("sell", k, "CE", 0.20), ("sell", k, "PE", 0.20)], d == exp)
        if fills:
            log.add(d, d, fills, f"ATM {k:.0f}")
    return log.frame()


# ---------------------------------------------------------------------------------------------- B
def _spread_close_to_close(m, log, d, nxt, exp, short_k, long_k, typ, detail):
    rows = [(m.contract(d, exp, short_k, typ), m.contract(nxt, exp, short_k, typ)),
            (m.contract(d, exp, long_k, typ), m.contract(nxt, exp, long_k, typ))]
    if any(a is None or b is None for a, b in rows):
        return
    fills = [between(rows[0][0], "close", rows[0][1], "close", "sell"),
             between(rows[1][0], "close", rows[1][1], "close", "buy")]
    log.add(d, nxt, fills, detail)


def b1_skew_mean_reversion(m: Market, sig: pd.DataFrame) -> pd.DataFrame:
    """B1: at the close. Calls unusually bid (RR25_z<-1.5) after a stretched rally (close > EMA20 + ATR14)
    with heavy OTM call volume (vol/OI z>1) -> sell a 30-delta call spread (2 strikes wide). Mirror for puts
    (RR25_z>1.5, close < EMA20 - ATR14, PCR rising). Exit at the next close."""
    log = TradeLog("B1", CAPITAL["spread"])
    days = m.trading_days()
    for i, d in enumerate(days[:-1]):
        if d not in sig.index:
            continue
        s, nxt = sig.loc[d], days[i + 1]
        exp = m.front_expiry(d, 2)
        if exp is None or not np.isfinite(s.get("rr25_z", np.nan)):
            continue
        t, vol = max((exp - d).days, 1) / 365.0, s["atm_iv"] / 100
        pcr_rising = s["pcr_oi"] > sig["pcr_oi"].shift(1).get(d, np.nan)
        if s["rr25_z"] < -1.5 and s["spot"] > s["ema20"] + s["atr14"] and s.get("voloi_calls_z", 0) > 1:
            k = _strike_for_delta(m, d, exp, "CE", 0.30, s["spot"], vol, t)
            if k:
                _spread_close_to_close(m, log, d, nxt, exp, k, k + 2 * STRIKE_STEP, "CE", f"call spread {k:.0f}")
        elif s["rr25_z"] > 1.5 and s["spot"] < s["ema20"] - s["atr14"] and pcr_rising:
            k = _strike_for_delta(m, d, exp, "PE", 0.30, s["spot"], vol, t)
            if k:
                _spread_close_to_close(m, log, d, nxt, exp, k, k - 2 * STRIKE_STEP, "PE", f"put spread {k:.0f}")
    return log.frame()


def b2_curvature_spread(m: Market, sig: pd.DataFrame) -> pd.DataFrame:
    """B2: when smile curvature z>2, sell a 20-delta credit spread on the richer wing (higher wing z-score),
    at the close; exit at the next close."""
    log = TradeLog("B2", CAPITAL["spread"])
    days = m.trading_days()
    for i, d in enumerate(days[:-1]):
        if d not in sig.index:
            continue
        s, nxt = sig.loc[d], days[i + 1]
        if not s.get("curv_c_z", np.nan) > 2:
            continue
        exp = m.front_expiry(d, 2)
        if exp is None:
            continue
        t, vol = max((exp - d).days, 1) / 365.0, s["atm_iv"] / 100
        if s.get("put_wing_z", 0) >= s.get("call_wing_z", 0):
            k = _strike_for_delta(m, d, exp, "PE", 0.20, s["spot"], vol, t)
            if k:
                _spread_close_to_close(m, log, d, nxt, exp, k, k - 2 * STRIKE_STEP, "PE", f"put spread {k:.0f}")
        else:
            k = _strike_for_delta(m, d, exp, "CE", 0.20, s["spot"], vol, t)
            if k:
                _spread_close_to_close(m, log, d, nxt, exp, k, k + 2 * STRIKE_STEP, "CE", f"call spread {k:.0f}")
    return log.frame()


def b4_oi_wall_bias(m: Market, sig: pd.DataFrame) -> pd.DataFrame:
    """B4: from the previous close's fresh OI: if fresh put writing sits at least one strike closer to spot than
    fresh call writing and PCR>1.1, sell a put spread at that put strike (2 strikes wide). Mirror for calls
    (PCR<1/1.1). Entry at the open, exit at the close. Deviation: the intraday wall-break exit isn't modelled."""
    log = TradeLog("B4", CAPITAL["spread"])
    p = _prev(sig)
    for d in m.trading_days():
        if d not in p.index or d not in m.index.index:
            continue
        s = p.loc[d]
        exp = s.get("front_expiry")
        if not isinstance(exp, pd.Timestamp) or exp < d or not np.isfinite(s.get("put_wall_new", np.nan)):
            continue
        spot = m.index.at[d, "open"]
        dp, dc = spot - s["put_wall_new"], s["call_wall_new"] - spot
        if dp > 0 and dc > 0 and dp + STRIKE_STEP <= dc and s["pcr_oi"] > 1.1:
            k, typ, kl = s["put_wall_new"], "PE", s["put_wall_new"] - 2 * STRIKE_STEP
        elif dp > 0 and dc > 0 and dc + STRIKE_STEP <= dp and s["pcr_oi"] < 1 / 1.1:
            k, typ, kl = s["call_wall_new"], "CE", s["call_wall_new"] + 2 * STRIKE_STEP
        else:
            continue
        fills = _legs_open(m, d, exp, [("sell", k, typ, None), ("buy", kl, typ, None)], d == exp)
        if fills:
            log.add(d, d, fills, f"{typ} spread {k:.0f}")
    return log.frame()


# ---------------------------------------------------------------------------------------------- C
def c3_gap_and_flow(m: Market, sig: pd.DataFrame, target: float = 0.60, name: str = "C3") -> pd.DataFrame:
    """C3: gap >0.6% in the same direction as the previous day's option-flow imbalance -> buy the ATM option in
    the gap's direction at the open. SL -30% of premium, target +60% (2R), else exit at the close.
    C2 is the same entry with the fixed 1:3 exit (target +90%).
    Deviations: the first-15-minute candle confirmation needs intraday data; flow is the previous day's."""
    log = TradeLog(name, CAPITAL["buy"])
    p = _prev(sig)
    for d in m.trading_days():
        if d not in sig.index or d not in p.index:
            continue
        gap, flow = sig.at[d, "gap_pct"], p.at[d, "flow_imb"] if "flow_imb" in p else np.nan
        if not (abs(gap) > 0.6 and np.isfinite(flow) and np.sign(flow) == np.sign(gap)):
            continue
        exp = m.front_expiry(d, 0)
        k = exp is not None and m.atm_strike(d, exp, m.index.at[d, "open"])
        if not k:
            continue
        typ = "CE" if gap > 0 else "PE"
        row = m.contract(d, exp, k, typ)
        if row is None:
            continue
        log.add(d, d, [intraday_leg(row, "buy", sl_pct=0.30, tp_pct=target, expiry_day=d == exp)], f"{typ} {k:.0f}")
    return log.frame()


def c2_fixed_rr(m: Market, sig: pd.DataFrame) -> pd.DataFrame:
    return c3_gap_and_flow(m, sig, target=0.90, name="C2")


STRATEGIES = {
    "A1": (a1_straddle_920, CAPITAL["naked"]),
    "A4": (a4_vrp_filtered, CAPITAL["naked"]),
    "A5": (a5_expiry_iron_fly, CAPITAL["defined"]),
    "A6": (a6_delta_strangle, CAPITAL["defined"]),
    "A7": (a7_oi_wall_strangle, CAPITAL["naked"]),
    "A8": (a8_rangetrap_overnight, CAPITAL["naked"]),
    "A9": (a9_kurtosis_straddle, CAPITAL["naked"]),
    "B1": (b1_skew_mean_reversion, CAPITAL["spread"]),
    "B2": (b2_curvature_spread, CAPITAL["spread"]),
    "B4": (b4_oi_wall_bias, CAPITAL["spread"]),
    "C2": (c2_fixed_rr, CAPITAL["buy"]),
    "C3": (c3_gap_and_flow, CAPITAL["buy"]),
}
