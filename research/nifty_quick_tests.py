"""Quick, honest sanity tests of index-level ideas on NIFTY daily data.

Data: external/marketcalls__data/NIFTY_daily_data.csv (run scripts/fetch_repos.sh first).
It is the NIFTY *price* index (no dividends), 1990-2024; real OHLC starts 1995-11.

Every test reports in-sample (1996-2011) and out-of-sample (2012-2024) separately.
Signals are computed at the close of day t and applied from day t+1, and trading
costs of COST_BPS per side (index futures ballpark) are charged on every position change.
Treat any single result as a hypothesis: several tests are run here, so some will look good by luck.

Run:  python3 research/nifty_quick_tests.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "external" / "marketcalls__data" / "NIFTY_daily_data.csv"
COST_BPS = 5.0
CASH_RATE = 0.06  # rough Indian T-bill / liquid-fund yield earned while out of the market
SPLITS = {"IS 1996-2011": ("1996-01-01", "2011-12-31"), "OOS 2012-2024": ("2012-01-01", "2024-12-31")}


def load() -> pd.DataFrame:
    df = pd.read_csv(CSV, parse_dates=["date"]).set_index("date").sort_index()
    return df.loc["1995-11-03":, ["open", "high", "low", "close"]]


def stats(ret: pd.Series) -> dict:
    ret = ret.dropna()
    eq = (1 + ret).cumprod()
    years = len(ret) / 252
    cagr = eq.iloc[-1] ** (1 / years) - 1
    vol = ret.std() * np.sqrt(252)
    dd = (eq / eq.cummax() - 1).min()
    return {"CAGR%": 100 * cagr, "Vol%": 100 * vol, "Sharpe": ret.mean() / ret.std() * np.sqrt(252), "MaxDD%": 100 * dd}


def strat_returns(close: pd.Series, pos: pd.Series, cash_rate: float = 0.0) -> pd.Series:
    """pos is decided at close t; earns return t+1; costs charged on changes."""
    ret = close.pct_change()
    held = pos.shift(1).fillna(0)
    cost = held.diff().abs().fillna(0) * COST_BPS / 1e4
    return held * ret + (1 - held) * cash_rate / 252 - cost


def by_split(series_fn) -> pd.DataFrame:
    rows = {}
    for name, (a, b) in SPLITS.items():
        rows[name] = series_fn(a, b)
    return pd.DataFrame(rows).T.round(2)


def main() -> None:
    df = load()
    c = df.close
    ret = c.pct_change()
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", None)

    print("=" * 70, "\nA. Trend filter: long NIFTY only when close > 200-day SMA (else cash, 0%)")
    sma = c.rolling(200).mean()
    for label, pos in {
        "buy&hold": pd.Series(1.0, index=c.index),
        "close>SMA200": (c > sma).astype(float),
        "close>SMA50": (c > c.rolling(50).mean()).astype(float),
    }.items():
        trades = pos.diff().abs().sum() / 2
        print(f"\n{label}  (round trips over full period: {trades:.0f})")
        sr = strat_returns(c, pos)
        print(by_split(lambda a, b: stats(sr.loc[a:b])))
        if label != "buy&hold":
            sr_cash = strat_returns(c, pos, CASH_RATE)
            print(f"  ...earning {CASH_RATE:.0%} on cash while out:")
            print(by_split(lambda a, b: stats(sr_cash.loc[a:b])))

    print("\n" + "=" * 70, "\nB. Day-of-week mean close-to-close return (bps) and t-stat")
    for name, (a, b) in SPLITS.items():
        r = ret.loc[a:b]
        g = r.groupby(r.index.dayofweek)
        out = pd.DataFrame({"mean_bps": g.mean() * 1e4, "t": g.mean() / (g.std() / np.sqrt(g.count())), "n": g.count()})
        out.index = [["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][i] for i in out.index]
        print(f"\n{name}\n{out.round(2)}")

    print("\n" + "=" * 70, "\nC. Overnight (prev close -> open) vs intraday (open -> close), annualised %")
    overnight = df.open / c.shift(1) - 1
    intraday = c / df.open - 1
    print(by_split(lambda a, b: {
        "overnight_ann%": 100 * overnight.loc[a:b].mean() * 252,
        "intraday_ann%": 100 * intraday.loc[a:b].mean() * 252,
        "overnight_hit%": 100 * (overnight.loc[a:b] > 0).mean(),
        "intraday_hit%": 100 * (intraday.loc[a:b] > 0).mean(),
    }))

    print("\n" + "=" * 70, "\nD. After a big down day (< -2%): forward returns (bps) vs unconditional")
    fwd1 = ret.shift(-1)
    fwd5 = c.shift(-5) / c - 1
    big_down = ret < -0.02
    print(by_split(lambda a, b: {
        "n_events": big_down.loc[a:b].sum(),
        "next1d_bps": 1e4 * fwd1.loc[a:b][big_down.loc[a:b]].mean(),
        "next5d_bps": 1e4 * fwd5.loc[a:b][big_down.loc[a:b]].mean(),
        "uncond1d_bps": 1e4 * fwd1.loc[a:b].mean(),
        "uncond5d_bps": 1e4 * fwd5.loc[a:b].mean(),
    }))

    print("\n" + "=" * 70, "\nE. Turn of month: last trading day + first 3 days vs the rest (mean bps/day)")
    month = c.index.to_period("M")
    pos_in_month = pd.Series(range(len(c)), index=c.index).groupby(month).rank().astype(int)
    days_in_month = pd.Series(1, index=c.index).groupby(month).transform("sum")
    tom = (pos_in_month <= 3) | (pos_in_month == days_in_month)
    print(by_split(lambda a, b: {
        "TOM_bps": 1e4 * ret.loc[a:b][tom.loc[a:b]].mean(),
        "rest_bps": 1e4 * ret.loc[a:b][~tom.loc[a:b]].mean(),
        "TOM_share_of_days%": 100 * tom.loc[a:b].mean(),
    }))

    print("\n" + "=" * 70, "\nF. Volatility regime: 20d realised vol vs its trailing 1y median -> next 20d return")
    rv = ret.rolling(20).std() * np.sqrt(252)
    high_vol = rv > rv.rolling(252).median()
    fwd20 = c.shift(-20) / c - 1
    trend_up = c > sma
    print(by_split(lambda a, b: {
        "fwd20_highvol_bps": 1e4 * fwd20.loc[a:b][high_vol.loc[a:b]].mean(),
        "fwd20_lowvol_bps": 1e4 * fwd20.loc[a:b][~high_vol.loc[a:b]].mean(),
        "fwd20_up&calm_bps": 1e4 * fwd20.loc[a:b][(trend_up & ~high_vol).loc[a:b]].mean(),
        "fwd20_down&wild_bps": 1e4 * fwd20.loc[a:b][(~trend_up & high_vol).loc[a:b]].mean(),
    }))


if __name__ == "__main__":
    main()
