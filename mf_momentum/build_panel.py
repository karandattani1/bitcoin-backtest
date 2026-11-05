"""Parse AMFI daily NAV dumps (captn3m0/historical-mf-data) into a month-end NAV panel.

Usage: python build_panel.py <data_dir> <out_dir>
Keeps open-ended, Regular-plan, Growth-option schemes; tags each with its AMFI category.
"""
import os, re, sys, glob
import pandas as pd

data_dir, out_dir = sys.argv[1], sys.argv[2]
os.makedirs(out_dir, exist_ok=True)
cat_re = re.compile(r"^\s*(Open Ended|Close Ended|Interval Fund)[^(]*\(\s*(.*?)\s*\)\s*$")
rows, cats = [], {}
files = sorted(glob.glob(os.path.join(data_dir, "*", "*", "*.csv")))
for f in files:
    cur = None
    with open(f, encoding="utf-8", errors="ignore") as fh:
        header = fh.readline().strip().split(";")
        nav_i, date_i = header.index("Net Asset Value"), header.index("Date")
        name_i = 1
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if ";" not in line:
                m = cat_re.match(line)
                if m:
                    cur = (m.group(1), m.group(2))
                continue
            p = line.split(";")
            if len(p) <= max(nav_i, date_i) or cur is None or cur[0] != "Open Ended":
                continue
            try:
                nav = float(p[nav_i])
            except ValueError:
                continue
            if nav <= 0:
                continue
            rows.append((int(p[0]) if p[0].isdigit() else -1, p[date_i], nav))
            cats[int(p[0]) if p[0].isdigit() else -1] = (cur[1], p[name_i])
    print(f, len(rows), flush=True) if f.endswith("/01.csv") or len(rows) % 500000 < 3000 else None

df = pd.DataFrame(rows, columns=["code", "date", "nav"])
df = df[df.code > 0]
df["date"] = pd.to_datetime(df["date"], format="%d-%b-%Y", errors="coerce")
df = df.dropna().drop_duplicates(["code", "date"])
df["ym"] = df.date.dt.to_period("M")
# keep latest observation within each month, only if within last 10 days of month
df = df.sort_values("date").groupby(["code", "ym"]).tail(1)
df = df[df.date.dt.day >= df.date.dt.days_in_month - 10]
panel = df.pivot(index="ym", columns="code", values="nav").sort_index()

meta = pd.DataFrame([(k, v[0], v[1]) for k, v in cats.items()], columns=["code", "amfi_category", "name"]).set_index("code")
n = meta.name.str.lower()
keep = n.str.contains("growth") & ~n.str.contains("idcw|dividend|bonus|direct|payout|reinvest")
meta = meta[keep]
panel = panel[[c for c in panel.columns if c in meta.index]]
meta = meta.loc[panel.columns]
panel.to_pickle(os.path.join(out_dir, "panel.pkl"))
meta.to_csv(os.path.join(out_dir, "meta.csv"))
print(panel.shape, meta.amfi_category.value_counts().head(60).to_string())
