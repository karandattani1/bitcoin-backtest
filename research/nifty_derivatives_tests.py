"""Realized-volatility facts that decide whether NIFTY option-selling / buying ideas can work.

No option prices are available offline, so this measures the *realized* side only:
  A. how daily variance splits between the overnight gap and the trading session
  B. expiry-day behaviour (monthly = last Thursday; weekly Thursdays from Feb 2019) vs other days
  C. tail frequency: how often the day's move exceeds k x its forecast sigma
  D. forecastability of tomorrow's range (the core of "choosing days" to sell premium)
  E. weekend: does Monday's gap carry ~3 days of variance, or ~1?

Data: external/marketcalls__data/NIFTY_daily_data.csv (NIFTY price index, 1995-11..2024-01).
Run:  python3 research/nifty_derivatives_tests.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "external" / "marketcalls__data" / "NIFTY_daily_data.csv"
START = "2012-01-01"  # modern microstructure: pre-open session, rolling settlement, weeklies later


def load() -> pd.DataFrame:
    df = pd.read_csv(CSV, parse_dates=["date"]).set_index("date").sort_index()
    df = df.loc["1995-11-03":, ["open", "high", "low", "close"]]
    df = df[df.index.dayofweek < 5]  # drop special weekend sessions (budget Saturdays, Muhurat)
    df["prev_close"] = df.close.shift(1)
    df["gap"] = np.log(df.open / df.prev_close)
    df["session"] = np.log(df.close / df.open)
    df["cc"] = np.log(df.close / df.prev_close)
    df["range"] = np.log(df.high / df.low)
    # Parkinson intraday variance estimate from the high-low range
    df["pk_var"] = df["range"] ** 2 / (4 * np.log(2))
    return df.loc[START:].dropna()


def monthly_expiry_flags(idx: pd.DatetimeIndex) -> pd.Series:
    """Last Thursday of each month; if that Thursday is not a trading day, the previous trading day."""
    s = pd.Series(False, index=idx)
    for period, days in pd.Series(idx, index=idx).groupby(idx.to_period("M")):
        month_end = period.to_timestamp(how="end").normalize()
        last_thu = month_end - pd.Timedelta(days=(month_end.dayofweek - 3) % 7)
        candidates = days[days <= last_thu]
        if len(candidates):
            s.loc[candidates.iloc[-1]] = True
    return s


def main() -> None:
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", None)
    df = load()
    print(f"NIFTY {df.index[0].date()} .. {df.index[-1].date()}, {len(df)} sessions\n")

    print("=" * 78, "\nA. Where does NIFTY's daily variance come from?")
    v_gap, v_ses, v_cc = df.gap.var(), df.session.var(), df.cc.var()
    print(f"  overnight gap variance share : {100 * v_gap / (v_gap + v_ses):5.1f}%")
    print(f"  session variance share       : {100 * v_ses / (v_gap + v_ses):5.1f}%")
    print(f"  corr(gap, session)           : {df.gap.corr(df.session):+.3f}   (negative = session partly reverses the gap)")
    print(f"  ann. vol close-close {100 * np.sqrt(252 * v_cc):.1f}%, gap-only {100 * np.sqrt(252 * v_gap):.1f}%, "
          f"session-only {100 * np.sqrt(252 * v_ses):.1f}%")
    by_year = df.groupby(df.index.year).apply(lambda g: 100 * g.gap.var() / (g.gap.var() + g.session.var()))
    print("  gap share by year:", " ".join(f"{y}:{v:.0f}%" for y, v in by_year.items()))

    print("\n" + "=" * 78, "\nB. Expiry days vs other days (session |open->close| and high-low range, bps)")
    thu = df.index.dayofweek == 3
    mexp = monthly_expiry_flags(df.index).values
    wexp = thu & (df.index >= "2019-02-11") & ~mexp
    groups = {
        "monthly expiry": mexp,
        "weekly expiry Thu (2019+)": wexp,
        "Thu before weeklies (non-exp)": thu & (df.index < "2019-02-11") & ~mexp,
        "Mon-Wed, Fri": ~thu,
    }
    rows = {}
    for name, m in groups.items():
        g = df[m]
        rows[name] = {
            "n": len(g),
            "|session| bps": 1e4 * g.session.abs().mean(),
            "range bps": 1e4 * g.range.mean(),
            "|gap| bps": 1e4 * g.gap.abs().mean(),
            "close in last-hour-ish middle%": np.nan,
        }
    out = pd.DataFrame(rows).T.drop(columns="close in last-hour-ish middle%")
    print(out.round(1))
    # same-period comparison for the weekly era only
    era = df.index >= "2019-02-11"
    e = df[era]
    e_thu = e.index.dayofweek == 3
    print(f"\n  Weekly era only (2019-02..2024-01): Thu range {1e4 * e[e_thu].range.mean():.0f} bps vs "
          f"other days {1e4 * e[~e_thu].range.mean():.0f} bps; "
          f"Thu |session| {1e4 * e[e_thu].session.abs().mean():.0f} vs {1e4 * e[~e_thu].session.abs().mean():.0f} bps")

    print("\n" + "=" * 78, "\nC. Tail frequency: close-to-close move vs forecast sigma (EWMA, lambda=0.94, known at prior close)")
    ewma_var = df.cc.pow(2).ewm(alpha=0.06, adjust=False).mean().shift(1)
    z = df.cc / np.sqrt(ewma_var)
    z = z.dropna().iloc[60:]
    normal = {1: 31.7, 2: 4.55, 3: 0.27, 4: 0.0063}
    for k in (1, 2, 3, 4):
        obs = 100 * (z.abs() > k).mean()
        print(f"  |move| > {k} sigma : {obs:5.2f}% of days   (normal would be {normal[k]:.2f}%)  "
              f"-> about {obs / 100 * 252:.1f} days/yr")
    gap_z = (df.gap / np.sqrt(ewma_var)).dropna().iloc[60:]
    print(f"  gap alone > 2 sigma: {100 * (gap_z.abs() > 2).mean():.2f}% of days  (unhedgeable for anyone holding overnight)")

    print("\n" + "=" * 78, "\nD. Can we forecast tomorrow's range? (the whole 'pick your days' premise)")
    r = df.range
    feats = pd.DataFrame({
        "r_1": r.shift(1),
        "r_5": r.rolling(5).mean().shift(1),
        "r_22": r.rolling(22).mean().shift(1),
        "absgap_today": df.gap.abs(),  # known at 09:15 today, before an intraday seller enters
    })
    data = pd.concat([r.rename("y"), feats], axis=1).dropna()
    split = "2019-01-01"
    tr, te = data.loc[:split], data.loc[split:]
    for cols, label in [(["r_1", "r_5", "r_22"], "HAR (prior days only)"),
                        (["r_1", "r_5", "r_22", "absgap_today"], "HAR + today's opening gap")]:
        X = np.column_stack([np.ones(len(tr)), tr[cols].values])
        beta, *_ = np.linalg.lstsq(X, tr.y.values, rcond=None)
        pred = np.column_stack([np.ones(len(te)), te[cols].values]) @ beta
        ss_res = ((te.y - pred) ** 2).sum()
        ss_tot = ((te.y - te.y.mean()) ** 2).sum()
        print(f"  {label:28s} out-of-sample R^2 (2019-2024): {1 - ss_res / ss_tot:.2f}")
    q = pd.qcut(pd.Series(np.column_stack([np.ones(len(te)), te[['r_1', 'r_5', 'r_22', 'absgap_today']].values]) @ beta,
                          index=te.index), 5, labels=False)
    realized_by_q = (1e4 * te.y.groupby(q).mean()).round(0)
    print("  realized range by forecast quintile (bps, low->high):", realized_by_q.tolist())

    print("\n" + "=" * 78, "\nE. Weekend: overnight gap variance by weekday (Monday gap spans the weekend)")
    gv = df.groupby(df.index.dayofweek).gap.var()
    base = gv.drop(0).mean()
    for d, name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri"]):
        print(f"  {name} gap variance = {gv[d] / base:4.2f} x a normal weeknight")
    print("  (an option priced on calendar days charges ~3 nights of decay for the weekend)")

    print("\n" + "=" * 78, "\nF. Scheduled events: move on the day vs the EWMA sigma known the night before")
    events = {
        "Budget": ["2012-03-16", "2013-02-28", "2014-07-10", "2015-02-28", "2016-02-29", "2017-02-01",
                   "2018-02-01", "2019-07-05", "2020-02-01", "2021-02-01", "2022-02-01", "2023-02-01"],
        "Election result": ["2014-05-16", "2019-05-23"],
    }
    full = pd.read_csv(CSV, parse_dates=["date"]).set_index("date").sort_index().loc[START:]
    cc_all = np.log(full.close / full.close.shift(1))
    sig_all = np.sqrt(cc_all.pow(2).ewm(alpha=0.06, adjust=False).mean().shift(1))
    for kind, dates in events.items():
        zs = []
        for d in dates:
            d = pd.Timestamp(d)
            if d in cc_all.index and not np.isnan(sig_all.loc[d]):
                zs.append(abs(cc_all.loc[d]) / sig_all.loc[d])
                print(f"  {kind:15s} {d.date()}  move {100 * cc_all.loc[d]:+5.2f}%  = {zs[-1]:.1f} sigma")
        print(f"  -> {kind}: median |move| {np.median(zs):.1f} sigma, mean {np.mean(zs):.1f} sigma (n={len(zs)})")


if __name__ == "__main__":
    main()
