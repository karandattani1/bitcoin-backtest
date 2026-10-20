"""Synthetic market data in the same file formats as fetch_market_data.py, for testing the backtester.

The numbers mean nothing about real markets: the point is to exercise every code path.

    python -m backtest.synthetic <out_dir> [--years 3] [--seed 1]
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from . import black76


def generate(out: Path, years: float = 3.0, seed: int = 1, minute_days: int = 120, n_stocks: int = 60) -> None:
    rng = np.random.default_rng(seed)
    out.mkdir(parents=True, exist_ok=True)
    days = pd.bdate_range("2022-01-03", periods=int(252 * years))
    n = len(days)
    # VIX: mean-reverting around 15; NIFTY: GBM with vol tied to VIX and occasional jumps
    vix = np.empty(n)
    vix[0] = 15
    for i in range(1, n):
        vix[i] = max(9, vix[i - 1] + 0.08 * (15 - vix[i - 1]) + rng.normal(0, 0.8))
    sigma = vix / 100 / np.sqrt(252) * 0.85  # realised a bit below implied: a volatility risk premium
    jumps = rng.choice([0, 1], n, p=[0.98, 0.02]) * rng.normal(0, 0.025, n)
    ret = rng.normal(0.0004, sigma) + jumps
    close = 17000 * np.exp(np.cumsum(ret))
    gap = rng.normal(0, sigma * 0.4)
    opn = np.r_[close[0], close[:-1]] * np.exp(gap)
    hi = np.maximum(opn, close) * np.exp(np.abs(rng.normal(0, sigma * 0.6)))
    lo = np.minimum(opn, close) * np.exp(-np.abs(rng.normal(0, sigma * 0.6)))
    idx = pd.DataFrame({"date": days, "symbol": "NIFTY", "open": opn, "high": hi, "low": lo, "close": close})
    vx = pd.DataFrame({"date": days, "symbol": "INDIAVIX", "open": vix, "high": vix, "low": vix, "close": vix})
    pd.concat([idx, vx]).to_csv(out / "index_daily.csv", index=False)

    # weekly expiries every Thursday (Tuesday from Sep 2024 in this fake world, to exercise the regime split)
    weekday = np.where(days >= pd.Timestamp("2024-09-01"), 1, 3)
    expiries = sorted({d + pd.Timedelta(days=int((wd - d.weekday()) % 7)) for d, wd in zip(days, weekday)})
    expiries = [e if e in set(days) else days[days < e][-1] for e in expiries if e <= days[-1]]
    rows = []
    for i, d in enumerate(days):
        live = [e for e in expiries if e >= d][:2]
        for e in live:
            t_open = max((e - d).days, 0) / 365 + 0.26 / 365
            t_close = max((e - d).days, 0) / 365 + 1e-5
            atm = round(close[i] / 50) * 50
            for k in np.arange(atm - 1500, atm + 1550, 50):
                for typ in ("CE", "PE"):
                    kk = np.log(k / close[i])
                    vol = vix[i] / 100 * (1 - 1.5 * kk + 8 * kk * kk)  # put skew + smile
                    is_call = typ == "CE"
                    p_open = black76.price(opn[i], k, t_open, vol, is_call)
                    p_close = black76.price(close[i], k, t_close, vol, is_call)
                    p_hi = black76.price(hi[i] if is_call else lo[i], k, t_open, vol, is_call)
                    p_lo = black76.price(lo[i] if is_call else hi[i], k, t_close, vol, is_call)
                    o, c = float(p_open), float(p_close)
                    h, l = max(o, c, float(p_hi)), min(o, c, float(p_lo))
                    if o < 0.5:
                        continue
                    dist = abs(k - close[i]) / close[i]
                    oi = rng.lognormal(12, 0.5) * np.exp(-dist * 40)
                    rows.append((d, e, float(k), typ, round(o, 2), round(h, 2), round(l, 2), round(c, 2), round(c, 2),
                                 int(oi * rng.uniform(0.5, 2)), int(oi), int(oi * rng.normal(0, 0.2)), close[i]))
    opt = pd.DataFrame(rows, columns=["date", "expiry", "strike", "opt_type", "open", "high", "low", "close", "settle",
                                      "volume", "oi", "chg_oi", "underlying"])
    opt.to_csv(out / "options_eod_NIFTY.csv.gz", index=False)

    month_exp = pd.Series(days).groupby([days.year, days.month]).max().values
    fut_exp = np.array([month_exp[month_exp >= d][0] if (month_exp >= d).any() else month_exp[-1] for d in days])
    foi = 1e7 * np.exp(np.cumsum(rng.normal(0, 0.03, n)))
    pd.DataFrame({"date": days, "expiry": fut_exp, "open": opn, "high": hi, "low": lo, "close": close * 1.002,
                  "oi": foi, "chg_oi": np.r_[0, np.diff(foi)], "volume": 1e5}).to_csv(out / "futures_eod_NIFTY.csv.gz", index=False)

    # stocks: one market factor + idiosyncratic noise + persistent drifts (so momentum has something to find)
    drift = rng.normal(0.0004, 0.0006, n_stocks)
    eq = []
    for j in range(n_stocks):
        r = 0.9 * ret + rng.normal(drift[j], 0.015, n) + rng.normal(0, 0.0005) * np.arange(n) / n
        p = 500 * np.exp(np.cumsum(r))
        eq.append(pd.DataFrame({"date": days, "symbol": f"STK{j:02d}", "open": p, "high": p, "low": p, "close": p,
                                "adj_close": p, "volume": 1e6}))
    pd.concat(eq).to_csv(out / "equities_daily.csv.gz", index=False)

    # 1-minute NIFTY bars for the last `minute_days` sessions, consistent with the daily open/close
    mrows = []
    for i in range(n - minute_days, n):
        ts = pd.date_range(days[i] + pd.Timedelta(hours=9, minutes=15), periods=375, freq="1min")
        steps = rng.normal(0, sigma[i] / np.sqrt(375), 375)
        path = opn[i] * np.exp(np.cumsum(steps))
        path *= np.exp(np.linspace(0, np.log(close[i] / path[-1]), 375))
        noise = np.abs(rng.normal(0, path * sigma[i] / np.sqrt(375) * 0.5))
        mrows.append(pd.DataFrame({"datetime": ts, "open": np.r_[opn[i], path[:-1]], "high": np.maximum(path, np.r_[opn[i], path[:-1]]) + noise,
                                   "low": np.minimum(path, np.r_[opn[i], path[:-1]]) - noise, "close": path}))
    pd.concat(mrows).to_csv(out / "index_minute_NIFTY.csv.gz", index=False)
    pd.DataFrame({"date": [days[100], days[300]], "event": ["fake budget", "fake policy"]}).to_csv(out / "events.csv", index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--years", type=float, default=3.0)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    generate(Path(a.out), a.years, a.seed)
