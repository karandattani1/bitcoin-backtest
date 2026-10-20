"""Daily signal table (rulebook Part 2, S1-S10) computed from end-of-day data.

Every value in row `t` uses data up to and including the close of day `t`. Strategies that enter at the
open of day t must therefore read row t-1 (use `.shift(1)`); overnight strategies entering at the close
of day t read row t (a small look-ahead: 15:30 close data for a ~15:10 decision).
"""
import numpy as np
import pandas as pd

from . import black76
from .data import Market


def _z(s: pd.Series, n: int) -> pd.Series:
    return (s - s.rolling(n, min_periods=n // 2).mean()) / s.rolling(n, min_periods=n // 2).std()


def price_signals(m: Market) -> pd.DataFrame:
    """S1 (VIX-based), S2, S8, S9, S10 and trend helpers from index + VIX data."""
    ix = m.index.copy()
    out = pd.DataFrame(index=ix.index)
    out["spot"] = ix["close"]
    logret = np.log(ix["close"]).diff()
    out["rv10"] = 100 * logret.rolling(10).std() * np.sqrt(252)
    if m.vix is not None:
        vix = m.vix.reindex(ix.index).ffill()
        out["vix"] = vix
        out["ivp"] = 100 * vix.rolling(252, min_periods=120).apply(lambda w: (w[:-1] < w[-1]).mean(), raw=True)
        lo, hi = vix.rolling(252, min_periods=120).min(), vix.rolling(252, min_periods=120).max()
        out["ivr"] = 100 * (vix - lo) / (hi - lo)
        out["vrp_ratio"] = vix / out["rv10"]
    prev_close = ix["close"].shift(1)
    tr = pd.concat([ix["high"] - ix["low"], (ix["high"] - prev_close).abs(), (ix["low"] - prev_close).abs()], axis=1).max(axis=1)
    out["atr5"], out["atr14"], out["atr20"] = tr.rolling(5).mean(), tr.rolling(14).mean(), tr.rolling(20).mean()
    out["atr_ratio"] = out["atr5"] / out["atr20"]
    out["kurt20"] = logret.rolling(20).kurt()
    out["kurt20_p30"] = out["kurt20"].rolling(252, min_periods=120).quantile(0.30)
    out["inside_day"] = (ix["open"] <= ix["high"].shift(1)) & (ix["open"] >= ix["low"].shift(1))
    rng = ix["high"] - ix["low"]
    out["nr7"] = rng == rng.rolling(7).min()
    out["gap_pct"] = 100 * (ix["open"] / prev_close - 1)
    out["range_pct"] = 100 * rng / ix["open"]
    out["range_med20"] = out["range_pct"].rolling(20).median()
    out["ema20"] = ix["close"].ewm(span=20, adjust=False).mean()
    out["dma200"] = ix["close"].rolling(200).mean()
    days = out.index
    out["event_today"] = days.isin(list(m.events))
    out["event_tomorrow"] = pd.Series(out["event_today"].values, index=days).shift(-1, fill_value=False).values
    return out


def _chain_metrics(ch: pd.DataFrame, spot: float, date) -> dict:
    """S1 (ATM IV), S3 skew, S4 curvature, S5 OI structure, S7 flow for one expiry on one day."""
    t = (ch["expiry"].iloc[0] - date).days / 365.0
    if t <= 0 or len(ch) < 10:
        return {}
    ce = ch[ch.opt_type == "CE"].set_index("strike")
    pe = ch[ch.opt_type == "PE"].set_index("strike")
    common = ce.index.intersection(pe.index)
    if not len(common):
        return {}
    k_atm = common[np.argmin(np.abs(common - spot))]
    # forward from put-call parity at the ATM strike
    fwd = k_atm + (ce.loc[k_atm, "close"] - pe.loc[k_atm, "close"]) * np.exp(black76.RATE * t)
    otm = pd.concat([pe[pe.index < fwd].assign(is_call=False), ce[ce.index >= fwd].assign(is_call=True)])
    otm = otm[(otm.index > fwd * 0.93) & (otm.index < fwd * 1.07)]
    if len(otm) < 6:
        return {}
    k = otm.index.values.astype(float)
    iv = black76.implied_vol(otm["close"].values, fwd, k, t, otm["is_call"].values)
    d = black76.delta(fwd, k, t, np.nan_to_num(iv, nan=0.2), otm["is_call"].values)
    ok = np.isfinite(iv)
    res = {"fwd": fwd, "t": t}
    if ok.sum() >= 6:
        kk, ivv, dd, is_call = np.log(k[ok] / fwd), iv[ok], d[ok], otm["is_call"].values[ok]
        res["atm_iv"] = 100 * float(np.interp(0.0, kk, ivv))
        put_m, call_m = ~is_call, is_call
        if put_m.sum() >= 2 and call_m.sum() >= 2:
            p_order, c_order = np.argsort(dd[put_m]), np.argsort(dd[call_m])
            iv25p = float(np.interp(-0.25, dd[put_m][p_order], ivv[put_m][p_order]))
            iv25c = float(np.interp(0.25, dd[call_m][c_order], ivv[call_m][c_order]))
            res["rr25"] = 100 * (iv25p - iv25c)
            res["bf25"] = 100 * ((iv25p + iv25c) / 2 - res["atm_iv"] / 100)
            res["put_wing"] = 100 * iv25p - res["atm_iv"]
            res["call_wing"] = 100 * iv25c - res["atm_iv"]
        near = np.abs(kk) < 0.05
        if near.sum() >= 5:
            res["curv_c"] = float(np.polyfit(kk[near], ivv[near], 2)[0])
    # S5: OI structure within +-5% of the forward
    band = ch[(ch.strike > fwd * 0.95) & (ch.strike < fwd * 1.05)]
    put_oi, call_oi = band.loc[band.opt_type == "PE", "oi"].sum(), band.loc[band.opt_type == "CE", "oi"].sum()
    res["pcr_oi"] = put_oi / call_oi if call_oi > 0 else np.nan
    calls_above, puts_below = ce[ce.index > fwd], pe[pe.index < fwd]
    if len(calls_above) and len(puts_below):
        res["call_wall"] = float(calls_above["oi"].idxmax())
        res["put_wall"] = float(puts_below["oi"].idxmax())
        res["call_wall_new"] = float(calls_above["chg_oi"].idxmax())
        res["put_wall_new"] = float(puts_below["chg_oi"].idxmax())
    # S7: flow imbalance on the 3 OTM strikes each side; volume/OI on OTM calls
    c3, p3 = calls_above.sort_index().head(3), puts_below.sort_index().tail(3)
    if len(c3) and len(p3) and "signed_vol" in ch:
        cf, pf = c3["signed_vol"].sum(), p3["signed_vol"].sum()
        denom = abs(cf) + abs(pf)
        res["flow_imb"] = (cf - pf) / denom if denom > 0 else 0.0
        res["voloi_calls"] = c3["volume"].sum() / c3["oi"].sum() if c3["oi"].sum() > 0 else np.nan
    return res


def chain_signals(m: Market, spot: pd.Series) -> pd.DataFrame:
    opt = m.options.sort_values(["expiry", "strike", "opt_type", "date"]).copy()
    prev = opt.groupby(["expiry", "strike", "opt_type"])["close"].shift(1)
    opt["signed_vol"] = opt["volume"] * np.sign(opt["close"] - prev).fillna(0)
    m_by_date = {d: g for d, g in opt.groupby("date")}
    rows = {}
    for date, ch in m_by_date.items():
        if date not in spot.index:
            continue
        expiries = sorted(e for e in ch["expiry"].unique() if (e - date).days >= 1)
        if not expiries:
            continue
        front = ch[ch.expiry == expiries[0]]
        rows[date] = _chain_metrics(front, float(spot.loc[date]), date)
        rows[date]["front_expiry"] = expiries[0]
    out = pd.DataFrame.from_dict(rows, orient="index").sort_index()
    for col, n in (("rr25", 60), ("bf25", 60), ("curv_c", 60), ("put_wing", 60), ("call_wing", 60), ("voloi_calls", 60)):
        if col in out:
            out[f"{col}_z"] = _z(out[col], n)
    return out


def futures_signals(m: Market) -> pd.DataFrame:
    """S6 price-OI build-up on the front-month future (day over day, same contract only)."""
    f = m.futures
    same = f["expiry"] == f["expiry"].shift(1)
    dp = (f["close"] - f["close"].shift(1)).where(same)
    doi = (f["oi"] - f["oi"].shift(1)).where(same)
    label = np.select(
        [(dp > 0) & (doi > 0), (dp < 0) & (doi > 0), (dp > 0) & (doi < 0), (dp < 0) & (doi < 0)],
        ["long_buildup", "short_buildup", "short_covering", "long_unwinding"], default="none",
    )
    bias = np.select([np.isin(label, ["long_buildup", "short_covering"]), np.isin(label, ["short_buildup", "long_unwinding"])], [1, -1], 0)
    return pd.DataFrame({"buildup": label, "buildup_bias": bias}, index=f.index)


def build(m: Market) -> pd.DataFrame:
    sig = price_signals(m)
    if m.options is not None:
        sig = sig.join(chain_signals(m, sig["spot"]), how="left")
    if m.futures is not None:
        sig = sig.join(futures_signals(m), how="left")
    return sig
