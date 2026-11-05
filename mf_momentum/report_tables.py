"""Print markdown summary tables from results/results.csv."""
import pandas as pd, numpy as np
r = pd.read_csv("results/results.csv")
r["net"] = r.excess_ann - np.where(r.asset.isin(["Equity", "Hybrid"]), r.exit_load_drag, 0)
LB = ["3m", "6m", "12m", "24m", "12-1m", "blend 3/6/12"]
f = r[r.period == "full"]
order = ["Large Cap", "Large & Mid Cap", "Mid Cap", "Small Cap", "Multi Cap", "Flexi Cap", "Focused", "Value/Contra", "ELSS",
         "Sectoral/Thematic", "Index Funds/ETFs (equity)", "ALL Equity (pooled)",
         "Aggressive/Balanced Hybrid", "Balanced Advantage", "Conservative Hybrid", "Equity Savings", "Multi Asset", "Arbitrage", "ALL Hybrid (pooled)",
         "Liquid", "Money Market", "Ultra Short", "Low Duration", "Short Duration", "Medium Duration", "Dynamic Bond", "Corporate Bond",
         "Credit Risk", "Banking & PSU", "Gilt", "ALL Debt (pooled)", "FoF Overseas"]
for H, label, col in [(12, "Annual rebalance (H=12m), no exit load", "excess_ann"),
                      (3, "Quarterly rebalance (H=3m), gross", "excess_ann"),
                      (3, "Quarterly rebalance (H=3m), net of 1% exit load (equity/hybrid)", "net"),
                      (1, "Monthly rebalance (H=1m), gross", "excess_ann")]:
    x = f[f.hold_m == H]
    p = (x.pivot(index="group", columns="lookback", values=col)[LB] * 100).reindex(order)
    t = x.pivot(index="group", columns="lookback", values="t_stat")[LB].reindex(order)
    out = p.round(2).astype(str)
    if col == "excess_ann":
        out = out + " (" + t.round(1).astype(str) + ")"
    out["best"] = p.idxmax(axis=1)
    out["avg funds"] = x[x.lookback == "12m"].set_index("group").avg_funds.reindex(order)
    print(f"\n#### {label}: top-quintile excess vs category average, % p.a." + (" (t-stat)" if col == "excess_ann" else "") + "\n")
    print(out.to_markdown())
for p_ in ["2007-2017", "2018-2026"]:
    x = r[(r.period == p_) & (r.hold_m == 12)]
    p = (x.pivot(index="group", columns="lookback", values="excess_ann")[LB] * 100).reindex(order).dropna(how="all")
    p["best"] = p.idxmax(axis=1)
    print(f"\n#### Sub-period {p_}, H=12m: excess % p.a.\n")
    print(p.round(2).to_markdown())
x = f[f.hold_m == 12]
print("\n#### CAGR: top quintile vs category average, same eligible funds (H=12m, full period)\n")
rows = []
for g in ["ALL Equity (pooled)", "Large Cap", "Mid Cap", "Small Cap", "Flexi Cap", "Sectoral/Thematic", "Aggressive/Balanced Hybrid", "ALL Debt (pooled)"]:
    y = x[x.group == g].set_index("lookback")
    rows.append([g] + [f"{y.loc[l, 'top_cagr']*100:.1f}% vs {y.loc[l, 'cat_cagr']*100:.1f}%" for l in LB])
print(pd.DataFrame(rows, columns=["group"] + LB).to_markdown(index=False))
print("\n#### Average across peer groups (full period)\n")
eqhy = f[~f.group.str.startswith("ALL")]
agg = eqhy.groupby(["asset", "hold_m", "lookback"])[["excess_ann", "net", "t_stat", "rank_ic", "retention"]].mean().reset_index()
agg = agg[agg.asset != "Other"]
for c in ["excess_ann", "net"]:
    agg[c] = (agg[c] * 100).round(2)
print(agg.round(3).to_markdown(index=False))
