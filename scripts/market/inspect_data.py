"""Describe the market data files in a folder, so a converter to the backtester's format can be written.

    python scripts/market/inspect_data.py "D:/path/to/your/data"
    python scripts/market/inspect_data.py "D:/path/to/your/data" --out data/market/inventory.md

For every CSV / CSV.GZ / ZIP(CSV) / Parquet / Feather / Excel file (searched recursively) it writes the column
names and types, row count, date range and the first 5 rows. Only that summary is written, not the data.
Large folders: files that look alike (same columns) are grouped, and only one example per group is shown in full.
"""
import argparse
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

import pandas as pd

EXTS = {".csv", ".gz", ".zip", ".parquet", ".feather", ".xlsx", ".xls", ".txt"}


def read_any(path: Path, nrows: int | None = None) -> pd.DataFrame:
    suf = "".join(path.suffixes[-2:]).lower()
    if suf.endswith(".parquet"):
        df = pd.read_parquet(path)
        return df.head(nrows) if nrows else df
    if suf.endswith(".feather"):
        df = pd.read_feather(path)
        return df.head(nrows) if nrows else df
    if suf.endswith((".xlsx", ".xls")):
        return pd.read_excel(path, nrows=nrows)
    if suf.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            name = next(n for n in z.namelist() if n.lower().endswith((".csv", ".txt")))
            return pd.read_csv(z.open(name), nrows=nrows, sep=None, engine="python")
    return pd.read_csv(path, nrows=nrows, sep=None, engine="python")


def date_range(df: pd.DataFrame) -> str:
    for col in df.columns:
        name = str(col).lower()
        if any(k in name for k in ("date", "time", "timestamp", "dt")) or df[col].dtype.kind == "M":
            try:
                s = pd.to_datetime(df[col], errors="coerce", dayfirst=False)
            except Exception:
                continue
            if s.notna().mean() > 0.8:
                return f"{col}: {s.min()} → {s.max()} ({s.dt.normalize().nunique()} distinct days)"
    return "no date column recognised"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("folder")
    p.add_argument("--out", default="data/market/inventory.md")
    p.add_argument("--max-full-scan-mb", type=float, default=300, help="read whole files up to this size for row counts")
    args = p.parse_args()

    root = Path(args.folder)
    files = sorted(f for f in root.rglob("*") if f.is_file() and f.suffix.lower() in EXTS)
    if not files:
        print(f"No data files found under {root}", file=sys.stderr)
        return 1
    groups = defaultdict(list)
    errors = []
    for f in files:
        try:
            head = read_any(f, nrows=5)
        except Exception as e:
            errors.append(f"- `{f.relative_to(root)}`: {type(e).__name__}: {e}")
            continue
        groups[tuple(map(str, head.columns))].append((f, head))

    lines = [f"# Data inventory: `{root}`", "", f"{len(files)} files, {len(groups)} distinct layouts.", ""]
    for gi, (cols, items) in enumerate(groups.items(), 1):
        f, head = items[0]
        size_mb = f.stat().st_size / 1e6
        full = read_any(f) if size_mb <= args.max_full_scan_mb else None
        examples = ", ".join(f"`{x.relative_to(root)}`" for x, _ in items[:8]) + (" …" if len(items) > 8 else "")
        lines += [f"## Layout {gi}: {len(items)} file(s)", "", f"Examples: {examples}", "",
                  f"Example file `{f.name}`: {size_mb:.1f} MB"
                  + (f", {len(full):,} rows, {date_range(full)}" if full is not None else " (too large to scan fully)"), "",
                  "Columns: " + ", ".join(f"`{c}` ({head[c].dtype})" for c in head.columns), "", "```",
                  head.to_string(index=False, max_colwidth=30), "```", ""]
        if full is not None:
            for col in full.columns[:40]:
                if (full[col].dtype == object or pd.api.types.is_string_dtype(full[col])) and 1 < full[col].nunique() <= 25:
                    lines.append(f"- `{col}` values: {', '.join(map(str, sorted(full[col].dropna().unique())[:25]))}")
            lines.append("")
    if errors:
        lines += ["## Files that could not be read", ""] + errors + [""]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(files)} files, {len(groups)} layouts -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
