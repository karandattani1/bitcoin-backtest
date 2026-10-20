"""Performance metrics from a trade list or a daily P&L / return series."""
import numpy as np
import pandas as pd

TRADING_DAYS = 252


def daily_pnl(trades: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.Series:
    """Rupee P&L booked on each exit date, on the full trading calendar (zeros on idle days)."""
    pnl = trades.groupby("exit_date")["pnl_rs"].sum() if len(trades) else pd.Series(dtype=float)
    return pnl.reindex(calendar, fill_value=0.0)


def summarize_fixed_capital(trades: pd.DataFrame, calendar: pd.DatetimeIndex, capital: float) -> dict:
    """Metrics for a strategy traded at a fixed size (1 lot) against a fixed capital base (no compounding)."""
    pnl = daily_pnl(trades, calendar)
    equity = capital + pnl.cumsum()
    years = max((calendar[-1] - calendar[0]).days / 365.25, 1e-9)
    total = equity.iloc[-1] / capital - 1
    dd = (equity / equity.cummax() - 1).min()
    base = summarize_trades(trades)
    ann_ret = total / years  # simple (non-compounded) annual return on capital
    rets = pnl / capital
    return {
        **base,
        "capital_rs": capital,
        "total_pnl_rs": float(pnl.sum()),
        "annual_return_pct": 100 * ann_ret,
        "max_drawdown_pct": 100 * dd,
        "calmar": ann_ret / abs(dd) if dd < 0 else np.nan,
        "sharpe": float(rets.mean() / rets.std() * np.sqrt(TRADING_DAYS)) if rets.std() > 0 else np.nan,
        "worst_day_rs": float(pnl.min()),
        "worst_week_rs": float(pnl.rolling(5).sum().min()),
        "top5_days_share_pct": 100 * float(pnl.nlargest(5).sum() / pnl.sum()) if pnl.sum() > 0 else np.nan,
    }


def summarize_trades(trades: pd.DataFrame) -> dict:
    if not len(trades):
        return {"trades": 0, "win_rate_pct": np.nan, "avg_win_rs": np.nan, "avg_loss_rs": np.nan}
    wins, losses = trades.loc[trades.pnl_rs > 0, "pnl_rs"], trades.loc[trades.pnl_rs <= 0, "pnl_rs"]
    return {
        "trades": int(len(trades)),
        "win_rate_pct": 100 * len(wins) / len(trades),
        "avg_win_rs": float(wins.mean()) if len(wins) else np.nan,
        "avg_loss_rs": float(losses.mean()) if len(losses) else np.nan,
        "costs_rs": float(trades["costs_rs"].sum()) if "costs_rs" in trades else np.nan,
    }


def summarize_returns(rets: pd.Series) -> dict:
    """Metrics for a compounding portfolio given daily returns."""
    rets = rets.dropna()
    equity = (1 + rets).cumprod()
    years = max((rets.index[-1] - rets.index[0]).days / 365.25, 1e-9)
    cagr = equity.iloc[-1] ** (1 / years) - 1
    dd = (equity / equity.cummax() - 1).min()
    return {
        "annual_return_pct": 100 * cagr,
        "max_drawdown_pct": 100 * dd,
        "calmar": cagr / abs(dd) if dd < 0 else np.nan,
        "sharpe": float(rets.mean() / rets.std() * np.sqrt(TRADING_DAYS)) if rets.std() > 0 else np.nan,
        "worst_day_pct": 100 * float(rets.min()),
    }
