"""E-series: positional equity strategies on daily adjusted closes (cash segment, delivery costs).

Universe = the current Nifty 200 list. Using today's constituents for the whole history adds survivorship
bias (stocks that fell out of the index are missing), which flatters every E strategy somewhat.
"""
import numpy as np
import pandas as pd

from ..costs import DEFAULT_COSTS
from ..data import Market

CASH_RATE = 0.065  # liquid fund yield while in cash


def _month_ends(idx: pd.DatetimeIndex) -> set:
    s = pd.Series(idx, index=idx)
    return set(s.groupby([idx.year, idx.month]).max())


def _run_portfolio(px: pd.DataFrame, target_fn) -> pd.Series:
    """Daily returns of a portfolio rebalanced at month ends to target_fn(date, current_weights) -> weights.
    Weights drift with prices between rebalances; costs are charged on the traded fraction."""
    rets = px.pct_change(fill_method=None).fillna(0.0)
    rebal = _month_ends(px.index)
    w = pd.Series(0.0, index=px.columns)
    out = []
    buy_c, sell_c = DEFAULT_COSTS.equity_rate("buy"), DEFAULT_COSTS.equity_rate("sell")
    for d in px.index:
        cash_w = max(1.0 - w.sum(), 0.0)
        r = float((w * rets.loc[d]).sum()) + cash_w * CASH_RATE / 252
        w = w * (1 + rets.loc[d]) / (1 + r)  # weights drift with prices
        if d in rebal:
            new = target_fn(d, w).reindex(px.columns, fill_value=0.0)
            trade = new - w
            cost = float(trade.clip(lower=0).sum() * buy_c + (-trade.clip(upper=0)).sum() * sell_c)
            r -= cost
            w = new
        out.append(r)
    return pd.Series(out, index=px.index)


def _momentum_score(px: pd.DataFrame, d) -> pd.Series:
    hist = px.loc[:d]
    if len(hist) < 260:
        return pd.Series(dtype=float)
    r6 = hist.iloc[-1] / hist.iloc[-127] - 1
    r12 = hist.iloc[-1] / hist.iloc[-253] - 1
    vol = hist.pct_change(fill_method=None).iloc[-252:].std() * np.sqrt(252)
    a, b = r6 / vol, r12 / vol
    z = lambda s: (s - s.mean()) / s.std()
    score = (z(a) + z(b)) / 2
    return score.dropna()


def e1_momentum(m: Market, sig: pd.DataFrame, top: int = 25, buffer: int = 40, regime: bool = False) -> pd.Series:
    """E1: rank by the average z-score of 6M and 12M return / 12M volatility; hold the top 25 equal-weight,
    keep a holding while it stays in the top 40; rebalance monthly. E2 adds the regime filter."""
    px = m.equities
    nifty = m.index["close"].reindex(px.index).ffill() if m.index is not None else None
    dma = nifty.rolling(200).mean() if nifty is not None else None

    def target(d, w):
        if regime:
            hist = px.loc[:d].iloc[-200:]
            breadth = (px.loc[d] > hist.mean()).mean()
            if nifty is None or not (nifty.loc[d] > dma.loc[d] and breadth > 0.5):
                return pd.Series(dtype=float)
        score = _momentum_score(px, d)
        if score.empty:
            return pd.Series(dtype=float)
        ranked = score.sort_values(ascending=False)
        keep = [s for s in w[w > 0].index if s in ranked.index[:buffer]]
        picks = keep + [s for s in ranked.index if s not in keep][: max(top - len(keep), 0)]
        picks = picks[:top]
        return pd.Series(1.0 / len(picks), index=picks)

    return _run_portfolio(px, target)


def e2_momentum_regime(m: Market, sig: pd.DataFrame) -> pd.Series:
    """E2: E1, but only invested when NIFTY > its 200-DMA and >50% of the universe is above its own 200-DMA
    (checked at each monthly rebalance); otherwise in a liquid fund."""
    return e1_momentum(m, sig, regime=True)


def e3_rsi2(m: Market, sig: pd.DataFrame, max_pos: int = 5, max_days: int = 10) -> pd.Series:
    """E3: Connors RSI(2): stock above its 200-DMA and RSI(2)<10 -> buy at the close (lowest RSI first, at most
    5 positions of 20%); sell at the close when it closes above its 5-DMA or after 10 days.
    Deviation: the rule's Nifty 100 universe is approximated by the full Nifty 200 list."""
    px = m.equities
    delta = px.diff()
    up, dn = delta.clip(lower=0), -delta.clip(upper=0)
    rs = up.ewm(alpha=0.5, adjust=False).mean() / dn.ewm(alpha=0.5, adjust=False).mean()
    rsi2 = 100 - 100 / (1 + rs)
    dma200, dma5 = px.rolling(200).mean(), px.rolling(5).mean()
    rets = px.pct_change(fill_method=None).fillna(0.0)
    held: dict = {}
    buy_c, sell_c = DEFAULT_COSTS.equity_rate("buy"), DEFAULT_COSTS.equity_rate("sell")
    out = []
    slot = 1.0 / max_pos
    for i, d in enumerate(px.index):
        r = sum(slot * rets.at[d, s] for s in held) + (max_pos - len(held)) * slot * CASH_RATE / 252
        for s in list(held):
            held[s] += 1
            if px.at[d, s] > dma5.at[d, s] or held[s] >= max_days:
                del held[s]
                r -= slot * sell_c
        if i >= 200:
            cand = rsi2.loc[d][(rsi2.loc[d] < 10) & (px.loc[d] > dma200.loc[d])].sort_values()
            for s in cand.index:
                if len(held) >= max_pos:
                    break
                if s not in held:
                    held[s] = 0
                    r -= slot * buy_c
        out.append(r)
    return pd.Series(out, index=px.index)


def benchmark_equal_weight(m: Market, sig: pd.DataFrame) -> pd.Series:
    px = m.equities
    return _run_portfolio(px, lambda d, w: pd.Series(1.0 / px.loc[d].notna().sum(), index=px.columns[px.loc[d].notna()]))


STRATEGIES = {"E1": e1_momentum, "E2": e2_momentum_regime, "E3": e3_rsi2, "E-bench (equal weight)": benchmark_equal_weight}
