"""Momentum lookback study on Indian mutual funds (within-category ranking).

Usage: python backtest.py <panel_dir> <out_dir>
For each peer group, every month-end rank funds on trailing L-month return
(L = 3, 6, 12, 24 and 12-1 skip-month), buy the top quintile equal-weight and hold
H = 1, 3, 6, 12 months (Jegadeesh-Titman overlapping cohorts). Benchmark = equal-weight
average of all funds in the group. Reports annualised excess return, t-stat, IR, hit rate,
top-minus-bottom quintile spread, and rank IC.
"""
import os, sys, re
import numpy as np, pandas as pd

pdir, odir = sys.argv[1], sys.argv[2]
os.makedirs(odir, exist_ok=True)
panel = pd.read_pickle(os.path.join(pdir, "panel.pkl"))
meta = pd.read_csv(os.path.join(pdir, "meta.csv"), index_col="code")

RULES = [  # (regex on AMFI category, peer group, asset class)
    (r"Large & Mid Cap", "Large & Mid Cap", "Equity"), (r"Large Cap", "Large Cap", "Equity"),
    (r"Mid Cap", "Mid Cap", "Equity"), (r"Small Cap", "Small Cap", "Equity"),
    (r"Multi Cap", "Multi Cap", "Equity"), (r"Flexi Cap", "Flexi Cap", "Equity"),
    (r"Focused", "Focused", "Equity"), (r"Value|Contra", "Value/Contra", "Equity"),
    (r"ELSS", "ELSS", "Equity"), (r"Dividend Yield", "Dividend Yield", "Equity"),
    (r"^Equity.*(Sectoral|Thematic)", "Sectoral/Thematic", "Equity"),
    (r"^Growth$", "Equity (pre-2018, defunct)", "Equity"),
    (r"Index Funds - Equity|Other Scheme - Index Funds|Equity ETF|Other  ?ETFs|^Other ETFs", "Index Funds/ETFs (equity)", "Equity"),
    (r"Arbitrage", "Arbitrage", "Hybrid"), (r"Aggressive Hybrid|Balanced Hybrid|^Balanced$", "Aggressive/Balanced Hybrid", "Hybrid"),
    (r"Balanced Advantage|Dynamic Asset", "Balanced Advantage", "Hybrid"),
    (r"Conservative Hybrid", "Conservative Hybrid", "Hybrid"), (r"Equity Savings", "Equity Savings", "Hybrid"),
    (r"Multi Asset", "Multi Asset", "Hybrid"), (r"Retirement|Child", "Solution Oriented", "Hybrid"),
    (r"Overnight", "Overnight", "Debt"), (r"Liquid", "Liquid", "Debt"), (r"Money Market", "Money Market", "Debt"),
    (r"Ultra Short", "Ultra Short", "Debt"), (r"Low Duration", "Low Duration", "Debt"),
    (r"Short Duration|Short Term", "Short Duration", "Debt"), (r"Medium to Long|Medium Term|Medium Duration", "Medium Duration", "Debt"),
    (r"Long Duration|Long Term", "Long Duration", "Debt"), (r"Dynamic Bond|Dynamic Term", "Dynamic Bond", "Debt"),
    (r"Corporate Bond", "Corporate Bond", "Debt"), (r"Credit Risk", "Credit Risk", "Debt"),
    (r"Banking and PSU", "Banking & PSU", "Debt"), (r"Gilt", "Gilt", "Debt"), (r"Float", "Floater", "Debt"),
    (r"^Income$", "Income (pre-2018, defunct)", "Debt"),
    (r"Overseas|investing overseas", "FoF Overseas", "Other"), (r"Gold", "Gold", "Other"),
]
def classify(c):
    for rx, g, a in RULES:
        if re.search(rx, c):
            return g, a
    return None, None
meta[["group", "asset"]] = meta.amfi_category.apply(lambda c: pd.Series(classify(c)))
meta = meta.dropna(subset=["group"])
meta.to_csv(os.path.join(odir, "fund_groups.csv"))

ret = panel.pct_change(fill_method=None)
# data-error filter: absurd monthly moves
lim = meta.asset.map({"Equity": 0.6, "Hybrid": 0.3, "Debt": 0.25, "Other": 0.5})
ret = ret.where(ret.abs().le(lim.reindex(ret.columns).values))
ret = ret.loc["2006-06":]
logr = np.log1p(ret)

LOOKS = {"3m": (3, 0), "6m": (6, 0), "12m": (12, 0), "24m": (24, 0), "12-1m": (12, 1), "blend 3/6/12": ("blend", 0)}
HOLDS = [1, 3, 6, 12]
Q = 0.2

def signal(lr, L, skip):
    s = lr.shift(skip).rolling(L, min_periods=L).sum()  # requires full history (no gaps)
    return s

def run(cols, L, skip, H, minfunds=10):
    lr, r = logr[cols], ret[cols]
    if L == "blend":  # average percentile rank of 3m, 6m, 12m returns (needs all three)
        rs = [signal(lr, l, 0).rank(axis=1, pct=True) for l in (3, 6, 12)]
        sig = (rs[0] + rs[1] + rs[2]) / 3
    else:
        sig = signal(lr, L, skip)
    T = len(r)
    top = pd.DataFrame(False, index=r.index, columns=cols); bot = top.copy()
    valid = sig.notna() & r.shift(-1).notna()  # must exist next month to be investable
    n = valid.sum(axis=1)
    rk = sig.where(valid).rank(axis=1, pct=True)
    ok = n >= minfunds
    top = (rk > 1 - Q) & ok.values[:, None]
    bot = (rk <= Q) & ok.values[:, None]
    # JT overlapping: month m return = mean over cohorts k=1..H formed at m-k
    rv = r.values
    out = {"top": [], "bot": [], "all": [], "date": []}
    tv, bv, av = top.values, bot.values, (valid & ok.values[:, None]).values
    for m in range(1, T):
        legs = {"top": [], "bot": [], "all": []}
        for k in range(1, H + 1):
            f = m - k
            if f < 0:
                break
            for name, mask in (("top", tv), ("bot", bv), ("all", av)):
                sel = mask[f] & ~np.isnan(rv[m])
                if sel.sum() > 0:
                    legs[name].append(rv[m][sel].mean())
        if legs["top"] and legs["all"] and len(legs["top"]) == len(legs["all"]):
            for nme in legs:
                out[nme].append(np.mean(legs[nme]) if legs[nme] else np.nan)
            out["date"].append(r.index[m])
    d = pd.DataFrame(out).set_index("date")
    # retention: share of top-quintile names at formation f still top-quintile at f+H
    rets = []
    for f in range(T - H):
        a, b = tv[f], tv[f + H]
        if a.sum() and b.sum():
            rets.append((a & b).sum() / a.sum())
    d.attrs["retention"] = np.mean(rets) if rets else np.nan
    d.attrs["H"] = H
    # rank IC: spearman of signal vs next-H-month cumulative return
    fwd = lr[::-1].rolling(H, min_periods=H).sum()[::-1].shift(-1)
    ics = []
    for t in sig.index[ok.values]:
        a, b = sig.loc[t], fwd.loc[t]
        mk = a.notna() & b.notna()
        if mk.sum() >= minfunds:
            ics.append(a[mk].rank().corr(b[mk].rank()))
    return d, np.nanmean(ics) if ics else np.nan, n[ok].mean() if ok.any() else 0

def stats(d, ic, nf):
    ex = (d["top"] - d["all"]).dropna()
    sp = (d["top"] - d["bot"]).dropna()
    if len(ex) < 24:
        return None
    ann = ex.mean() * 12
    vol = ex.std() * np.sqrt(12)
    # Newey-West-ish t-stat (overlap): use lag 12
    e = ex - ex.mean(); T = len(e); g0 = (e**2).mean(); s = g0
    for l in range(1, 13):
        s += 2 * (1 - l / 13) * (e[l:].values * e[:-l].values).mean()
    t = ex.mean() / np.sqrt(s / T)
    cagr = lambda x: (1 + x).prod() ** (12 / len(x)) - 1
    return dict(months=len(ex), avg_funds=round(nf, 1), top_cagr=cagr(d["top"].loc[ex.index]),
                cat_cagr=cagr(d["all"].loc[ex.index]), excess_ann=ann, t_stat=t, info_ratio=ann / vol if vol > 0 else np.nan,
                hit_rate=(ex > 0).mean(), retention=d.attrs.get("retention"),
                exit_load_drag=0.0 if d.attrs.get("H", 1) >= 12 else 0.01 * (12 / d.attrs.get("H", 1)) * (1 - d.attrs.get("retention", 0)),
                top_minus_bottom_ann=sp.mean() * 12, rank_ic=ic)

results = []
universes = [(g, a, meta.index[meta.group == g].tolist()) for g, a in meta.groupby(["group", "asset"]).size().index]
# pooled broad universes (ranking across all funds of the asset class)
universes += [("ALL Equity (pooled)", "Equity", meta.index[meta.asset == "Equity"].tolist()),
              ("ALL Debt (pooled)", "Debt", meta.index[meta.asset == "Debt"].tolist()),
              ("ALL Hybrid (pooled)", "Hybrid", meta.index[meta.asset == "Hybrid"].tolist())]
periods = {"full": (None, None), "2007-2017": (None, "2017-12"), "2018-2026": ("2018-01", None)}
for g, a, cols in universes:
    cols = [c for c in cols if c in ret.columns]
    for ln, (L, skip) in LOOKS.items():
        for H in HOLDS:
            d, ic, nf = run(cols, L, skip, H)
            for pn, (s0, s1) in periods.items():
                dd = d.loc[s0:s1] if len(d) else d
                dd.attrs = d.attrs
                st = stats(dd, ic, nf) if len(dd) else None
                if st:
                    results.append(dict(group=g, asset=a, lookback=ln, hold_m=H, period=pn, **st))
    print("done", g, len(cols), flush=True)
res = pd.DataFrame(results)
res.to_csv(os.path.join(odir, "results.csv"), index=False)
print(res.shape)
