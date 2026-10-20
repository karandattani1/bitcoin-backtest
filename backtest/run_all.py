"""Run every strategy in research/strategy-rulebook.md that the available data supports.

    python -m backtest.run_all                       # data from data/market, report to research/backtest-results.md
    python -m backtest.run_all --data <dir> --out <report.md> --start 2020-01-01

Strategies whose data is missing are listed as skipped with the reason; strategies that cannot be tested on
end-of-day data are listed with what they need.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from . import signals
from .data import MARKET, ROOT, Market
from .metrics import summarize_fixed_capital, summarize_returns
from .strategies import equity, intraday, options_eod

REGIME_START = pd.Timestamp("2025-09-01")  # NIFTY weekly expiry moved to Tuesday; single weekly per exchange

NAMES = {
    "A1": "9:20 short straddle", "A2": "Combined-premium straddle", "A3": "Re-entry straddle",
    "A4": "VRP-filtered straddle", "A5": "Expiry iron fly", "A6": "Delta strangle / iron condor",
    "A7": "OI-wall expiry strangle", "A8": "Rangetrap overnight straddle", "A9": "Kurtosis straddle",
    "B1": "Skew mean-reversion spread", "B2": "Curvature credit spread", "B3": "Expiry delta-rotation spread",
    "B4": "OI-wall bias spread", "C1": "SkewHunter-style buy", "C2": "Fixed 1:3 option buy (C3 entries)",
    "C3": "Gap-and-flow continuation", "D1": "Opening range breakout", "D2": "VWAP + build-up trend",
    "D3": "EMA/Supertrend", "E1": "Momentum rotation", "E2": "Momentum + regime filter", "E3": "RSI(2) mean reversion",
    "E4": "Quality + momentum",
}

NEEDS_INTRADAY_OPTIONS = {
    "A2": "combined-premium stop needs both legs' prices at the same moment (1-minute option data)",
    "A3": "re-entries after stops need 1-minute option data",
    "B3": "30-minute re-scoring of flow, VWAP and skew needs intraday option-chain data",
    "C1": "intraday flow/skew/VWAP alignment needs intraday option-chain data",
}
NEEDS_OTHER = {"E4": "needs point-in-time fundamentals (ROE, debt/equity, earnings history) for the universe"}


def _period_slice(trades: pd.DataFrame, start) -> pd.DataFrame:
    return trades[trades["exit_date"] >= start] if len(trades) else trades


def run(data_dir: Path, start: str | None = None) -> tuple[pd.DataFrame, dict, list]:
    m = Market.load(data_dir)
    if m.index is None:
        raise SystemExit(f"No index data in {data_dir}. Run scripts/market/fetch_market_data.py first.")
    if start:
        cut = pd.Timestamp(start)
        m.index = m.index[m.index.index >= cut - pd.Timedelta(days=400)]  # keep warm-up history for signals
    sig = signals.build(m)
    results, trades_out, skipped = [], {}, []

    if m.options is not None:
        for code, (fn, capital) in options_eod.STRATEGIES.items():
            tr = fn(m, sig)
            if start:
                tr = tr[tr["entry_date"] >= pd.Timestamp(start)]
            cal = m.trading_days()
            cal = cal[cal >= (pd.Timestamp(start) if start else cal[0])]
            row = {"code": code, "name": NAMES[code], **summarize_fixed_capital(tr, cal, capital)}
            recent = _period_slice(tr, REGIME_START)
            rc = cal[cal >= REGIME_START]
            if len(rc) > 20:
                rec = summarize_fixed_capital(recent, rc, capital)
                row["since_sep25_trades"], row["since_sep25_annual_pct"] = rec["trades"], rec["annual_return_pct"]
            results.append(row)
            trades_out[code] = tr
    else:
        skipped += [(c, "no NIFTY option EOD data (options_eod_NIFTY.csv.gz)") for c in options_eod.STRATEGIES]

    if m.minute is not None:
        for code, (fn, capital) in intraday.STRATEGIES.items():
            tr = fn(m, sig)
            cal = pd.DatetimeIndex(sorted(m.minute.index.normalize().unique()))
            if start:
                tr = tr[tr["entry_date"] >= pd.Timestamp(start)] if len(tr) else tr
                cal = cal[cal >= pd.Timestamp(start)]
            results.append({"code": code, "name": NAMES[code], **summarize_fixed_capital(tr, cal, capital)})
            trades_out[code] = tr
    else:
        skipped += [(c, "no 1-minute NIFTY data (index_minute_NIFTY.csv.gz)") for c in intraday.STRATEGIES]

    if m.equities is not None:
        for code, fn in equity.STRATEGIES.items():
            rets = fn(m, sig)
            if start:
                rets = rets[rets.index >= pd.Timestamp(start)]
            rets = rets.iloc[260:] if not start else rets  # skip the 12-month warm-up when no start is given
            row = {"code": code, "name": NAMES.get(code, code), **summarize_returns(rets)}
            recent = rets[rets.index >= REGIME_START]
            if len(recent) > 20:
                row["since_sep25_annual_pct"] = summarize_returns(recent)["annual_return_pct"]
            results.append(row)
            trades_out[code] = rets.rename("daily_return").to_frame()
    else:
        skipped += [(c, "no equity data (equities_daily.csv.gz)") for c in ("E1", "E2", "E3")]

    skipped += list(NEEDS_INTRADAY_OPTIONS.items()) + list(NEEDS_OTHER.items())
    return pd.DataFrame(results), trades_out, skipped


def _fmt(v, nd=1):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "–"
    if isinstance(v, (int, np.integer)) or nd == "int":
        return f"{int(v):,}"
    return f"{v:,.{nd}f}"


def write_report(res: pd.DataFrame, skipped: list, out: Path, data_dir: Path, note: str = "") -> None:
    lines = ["# Backtest results", ""]
    if note:
        lines += [note, ""]
    lines += [f"Data: `{data_dir}`. Costs: 2026 schedule (STT 0.15% on option premium sold), plus slippage. "
              "Option/futures P&L is for **one current NIFTY lot (65)** over the whole history, against a fixed capital "
              "base (no compounding). Equity strategies compound.", ""]
    opt = res[res["code"].str[0].isin(list("ABCD"))] if len(res) else res
    if len(opt):
        lines += ["## Options and futures (A–D)", "",
                  "| Code | Strategy | Trades | Win % | Avg win ₹ | Avg loss ₹ | Total P&L ₹ | Costs ₹ | Return %/yr | Max DD % | Calmar | Sharpe | Worst day ₹ | Top-5-day share % | Since Sep-25 %/yr |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in opt.iterrows():
            lines.append("| " + " | ".join([r["code"], r["name"], _fmt(r["trades"], "int"), _fmt(r["win_rate_pct"]),
                         _fmt(r["avg_win_rs"], 0), _fmt(r["avg_loss_rs"], 0), _fmt(r["total_pnl_rs"], 0),
                         _fmt(r.get("costs_rs"), 0), _fmt(r["annual_return_pct"]), _fmt(r["max_drawdown_pct"]),
                         _fmt(r["calmar"], 2), _fmt(r["sharpe"], 2), _fmt(r["worst_day_rs"], 0),
                         _fmt(r["top5_days_share_pct"]), _fmt(r.get("since_sep25_annual_pct"))]) + " |")
        lines.append("")
    eq = res[res["code"].str[0] == "E"] if len(res) else res
    if len(eq):
        lines += ["## Equity (E)", "", "| Code | Strategy | CAGR % | Max DD % | Calmar | Sharpe | Worst day % | Since Sep-25 %/yr |",
                  "|---|---|---|---|---|---|---|---|"]
        for _, r in eq.iterrows():
            lines.append("| " + " | ".join([r["code"], r["name"], _fmt(r["annual_return_pct"]), _fmt(r["max_drawdown_pct"]),
                         _fmt(r["calmar"], 2), _fmt(r["sharpe"], 2), _fmt(r["worst_day_pct"], 2),
                         _fmt(r.get("since_sep25_annual_pct"))]) + " |")
        lines.append("")
    if skipped:
        lines += ["## Not tested", "", "| Code | Strategy | Why |", "|---|---|---|"]
        lines += [f"| {c} | {NAMES.get(c, c)} | {why} |" for c, why in skipped]
        lines.append("")
    lines += ["## How daily bars approximate the rules", "",
              "- Entries \"at 9:20\" use each option's first traded price of the day; exits \"at 15:15\" use the close.",
              "- Stops trigger when the day's high (short legs) or low (long legs) reaches the stop level and fill there plus slippage. If a long option could have hit both stop and target, the stop is assumed.",
              "- Signals for open entries use the previous day's close (no look-ahead). Overnight and close-to-close strategies use the same day's close for a ~15:10 decision.",
              "- Per-strategy deviations from the rulebook are in each function's docstring in `backtest/strategies/`.",
              "- Capital per lot used for % figures: naked selling ₹2.5L, defined-risk ₹1L, spreads ₹75k, option buying ₹50k, futures ₹2L.",
              "- Equity universe is today's Nifty 200 list, which adds survivorship bias.", ""]
    out.write_text("\n".join(lines))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", default=str(MARKET))
    p.add_argument("--out", default=str(ROOT / "research" / "backtest-results.md"))
    p.add_argument("--trades-dir", default=str(ROOT / "data" / "results"))
    p.add_argument("--start", default=None)
    p.add_argument("--note", default="")
    args = p.parse_args()
    res, trades, skipped = run(Path(args.data), args.start)
    tdir = Path(args.trades_dir)
    tdir.mkdir(parents=True, exist_ok=True)
    for code, tr in trades.items():
        tr.to_csv(tdir / f"{code.split()[0]}.csv")
    res.to_csv(tdir / "summary.csv", index=False)
    write_report(res, skipped, Path(args.out), Path(args.data), args.note)
    with pd.option_context("display.width", 200, "display.max_columns", 30):
        cols = [c for c in ["code", "trades", "win_rate_pct", "total_pnl_rs", "annual_return_pct", "max_drawdown_pct", "calmar"] if c in res]
        print(res[cols].round(2).to_string(index=False))
    print(f"\nreport: {args.out}")


if __name__ == "__main__":
    main()
