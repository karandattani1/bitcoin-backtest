"""Download the free market data the backtester needs. Run on your own PC (NSE and Yahoo block cloud servers).

    pip install -r scripts/market/requirements.txt
    python scripts/market/fetch_market_data.py                     # everything from 2020-01-01
    python scripts/market/fetch_market_data.py --only index,equities
    python scripts/market/fetch_market_data.py --only fo --start 2023-01-01

Writes data/market/ (see backtest/data.py for the file formats):
  index_daily.csv            NIFTY 50 and India VIX daily OHLC (Yahoo: ^NSEI, ^INDIAVIX)
  equities_daily.csv.gz      daily prices of the current Nifty 200 constituents (Yahoo: SYMBOL.NS)
  options_eod_NIFTY.csv.gz   NIFTY index options from NSE's daily F&O bhavcopy (nearest 3 expiries, strikes within +-10%)
  futures_eod_NIFTY.csv.gz   NIFTY index futures from the same bhavcopy
  events.csv                 budget / election days (add RBI policy dates yourself)

The F&O download takes one request per trading day (~1,200 for 2020-2025) and resumes where it stopped:
finished months are cached in data/market/raw_fo/.

1-minute NIFTY data (needed for D1-D3) has no free source; see scripts/market/README.md.
"""
import argparse
import io
import sys
import time
import zipfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "market"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9", "Referer": "https://www.nseindia.com/",
}
UDIFF_FROM = date(2024, 7, 8)  # NSE switched the F&O bhavcopy to the UDiFF format around this date

EVENTS = [
    ("2020-02-01", "Union Budget"), ("2021-02-01", "Union Budget"), ("2022-02-01", "Union Budget"),
    ("2023-02-01", "Union Budget"), ("2024-02-01", "Interim Budget"), ("2024-06-04", "Lok Sabha election results"),
    ("2024-07-23", "Union Budget"), ("2025-02-01", "Union Budget"), ("2026-02-01", "Union Budget"),
]


# ------------------------------------------------------------------------------------------ Yahoo
def fetch_index(start: str) -> pd.DataFrame:
    import yfinance as yf
    frames = []
    for ticker, name in (("^NSEI", "NIFTY"), ("^INDIAVIX", "INDIAVIX")):
        df = yf.download(ticker, start=start, auto_adjust=False, progress=False, multi_level_index=False)
        if df.empty:
            raise SystemExit(f"Yahoo returned no data for {ticker}")
        df = df.rename(columns=str.lower)[["open", "high", "low", "close"]].reset_index()
        df.columns = ["date", "open", "high", "low", "close"]
        df.insert(1, "symbol", name)
        frames.append(df)
    out = pd.concat(frames)
    out.to_csv(OUT / "index_daily.csv", index=False)
    print(f"index_daily.csv: {len(out)} rows")
    return out


def nifty200_symbols(session: requests.Session, universe_file: str | None) -> list[str]:
    if universe_file:
        df = pd.read_csv(universe_file)
    else:
        df = None
        for url in ("https://nsearchives.nseindia.com/content/indices/ind_nifty200list.csv",
                    "https://www.niftyindices.com/IndexConstituent/ind_nifty200list.csv"):
            try:
                r = session.get(url, timeout=30)
                r.raise_for_status()
                df = pd.read_csv(io.StringIO(r.text))
                break
            except Exception as e:  # try the next source
                print(f"  could not get the Nifty 200 list from {url}: {e}")
        if df is None:
            raise SystemExit("Download ind_nifty200list.csv from niftyindices.com and pass --universe-file")
    col = next(c for c in df.columns if c.strip().lower() == "symbol")
    return sorted(df[col].astype(str).str.strip().unique())


def fetch_equities(start: str, symbols: list[str]) -> None:
    import yfinance as yf
    frames = []
    for i in range(0, len(symbols), 50):
        batch = [f"{s}.NS" for s in symbols[i:i + 50]]
        df = yf.download(batch, start=start, auto_adjust=False, progress=False, group_by="ticker", threads=True)
        for t in batch:
            if t not in df.columns.get_level_values(0):
                print(f"  no data: {t}")
                continue
            d = df[t].dropna(how="all").reset_index()
            d.columns = [str(c).lower().replace(" ", "_") for c in d.columns]
            d["symbol"] = t.removesuffix(".NS")
            frames.append(d[["date", "symbol", "open", "high", "low", "close", "adj_close", "volume"]])
        print(f"  equities {min(i + 50, len(symbols))}/{len(symbols)}")
    out = pd.concat(frames)
    out.to_csv(OUT / "equities_daily.csv.gz", index=False)
    print(f"equities_daily.csv.gz: {out['symbol'].nunique()} symbols, {len(out)} rows")


# ------------------------------------------------------------------------------------------ NSE bhavcopy
def _bhav_urls(d: date) -> list[str]:
    mon = d.strftime("%b").upper()
    old = f"https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{d:%Y}/{mon}/fo{d:%d}{mon}{d:%Y}bhav.csv.zip"
    new = f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{d:%Y%m%d}_F_0000.csv.zip"
    return [new, old] if d >= UDIFF_FROM else [old, new]


def _read_zip_csv(content: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        return pd.read_csv(z.open(name))


def normalise_bhavcopy(raw: pd.DataFrame, d: date) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (options, futures) for NIFTY in the backtester's format, from either bhavcopy format."""
    raw.columns = [c.strip() for c in raw.columns]
    if "INSTRUMENT" in raw.columns:  # old format
        r = raw[raw["SYMBOL"].str.strip() == "NIFTY"]
        common = pd.DataFrame({
            "date": pd.Timestamp(d), "expiry": pd.to_datetime(r["EXPIRY_DT"], format="%d-%b-%Y"),
            "open": r["OPEN"], "high": r["HIGH"], "low": r["LOW"], "close": r["CLOSE"], "settle": r["SETTLE_PR"],
            "volume": r["CONTRACTS"], "oi": r["OPEN_INT"], "chg_oi": r["CHG_IN_OI"],
        })
        is_opt, is_fut = r["INSTRUMENT"].str.strip() == "OPTIDX", r["INSTRUMENT"].str.strip() == "FUTIDX"
        common["strike"], common["opt_type"], common["underlying"] = r["STRIKE_PR"], r["OPTION_TYP"].str.strip(), float("nan")
    elif "FinInstrmTp" in raw.columns:  # UDiFF format
        r = raw[raw["TckrSymb"].astype(str).str.strip() == "NIFTY"]
        common = pd.DataFrame({
            "date": pd.Timestamp(d), "expiry": pd.to_datetime(r["XpryDt"]),
            "open": r["OpnPric"], "high": r["HghPric"], "low": r["LwPric"], "close": r["ClsPric"], "settle": r["SttlmPric"],
            "volume": r["TtlTradgVol"], "oi": r["OpnIntrst"], "chg_oi": r["ChngInOpnIntrst"],
        })
        is_opt, is_fut = r["FinInstrmTp"].str.strip() == "IDO", r["FinInstrmTp"].str.strip() == "IDF"
        common["strike"], common["opt_type"], common["underlying"] = r["StrkPric"], r["OptnTp"].astype(str).str.strip(), r["UndrlygPric"]
    else:
        raise ValueError(f"unknown bhavcopy format on {d}: columns {list(raw.columns)[:12]}")
    opts = common[is_opt.values][["date", "expiry", "strike", "opt_type", "open", "high", "low", "close", "settle",
                                  "volume", "oi", "chg_oi", "underlying"]]
    futs = common[is_fut.values][["date", "expiry", "open", "high", "low", "close", "oi", "chg_oi", "volume"]]
    return opts, futs


def trim_chain(opts: pd.DataFrame, spot: float | None, n_expiries: int = 3, band: float = 0.10) -> pd.DataFrame:
    exps = sorted(opts["expiry"].unique())[:n_expiries]
    opts = opts[opts["expiry"].isin(exps)]
    if spot:
        opts = opts[(opts["strike"] > spot * (1 - band)) & (opts["strike"] < spot * (1 + band))]
    return opts


def fetch_fo(start: str, end: str, session: requests.Session, sleep: float, spot: pd.Series | None) -> None:
    raw_dir = OUT / "raw_fo"
    raw_dir.mkdir(parents=True, exist_ok=True)
    d0, d1 = pd.Timestamp(start).date(), pd.Timestamp(end).date()
    months = pd.period_range(d0, d1, freq="M")
    current = pd.Period(date.today(), freq="M")
    for month in months:
        opt_path, fut_path = raw_dir / f"{month}_opt.csv.gz", raw_dir / f"{month}_fut.csv.gz"
        if opt_path.exists() and month != current:
            continue
        opt_frames, fut_frames, misses = [], [], 0
        day = max(month.start_time.date(), d0)
        last = min(month.end_time.date(), d1)
        while day <= last:
            if day.weekday() < 5:
                got = False
                for url in _bhav_urls(day):
                    try:
                        r = session.get(url, timeout=30)
                    except requests.RequestException as e:
                        print(f"  {day} network error: {e}")
                        continue
                    if r.status_code == 200 and r.content[:2] == b"PK":
                        o, f = normalise_bhavcopy(_read_zip_csv(r.content), day)
                        s = float(spot.get(pd.Timestamp(day), float("nan"))) if spot is not None else None
                        opt_frames.append(trim_chain(o, s if s == s else None))
                        fut_frames.append(f)
                        got = True
                        break
                misses += not got  # holidays have no file
                time.sleep(sleep)
            day += timedelta(days=1)
        if opt_frames:
            pd.concat(opt_frames).to_csv(opt_path, index=False)
            pd.concat(fut_frames).to_csv(fut_path, index=False)
        print(f"  {month}: {len(opt_frames)} trading days, {misses} weekdays without a file")
        if not opt_frames and misses > 15:
            print("  NSE returned nothing for a whole month: it may be blocking you. Try again later or from "
                  "another network.", file=sys.stderr)
    opts = pd.concat([pd.read_csv(p) for p in sorted(raw_dir.glob("*_opt.csv.gz"))])
    futs = pd.concat([pd.read_csv(p) for p in sorted(raw_dir.glob("*_fut.csv.gz"))])
    opts.to_csv(OUT / "options_eod_NIFTY.csv.gz", index=False)
    futs.to_csv(OUT / "futures_eod_NIFTY.csv.gz", index=False)
    print(f"options_eod_NIFTY.csv.gz: {len(opts)} rows; futures_eod_NIFTY.csv.gz: {len(futs)} rows")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", default="2020-01-01")
    p.add_argument("--end", default=str(date.today()))
    p.add_argument("--only", default="index,equities,fo,events", help="comma list of: index, equities, fo, events")
    p.add_argument("--universe-file", help="CSV with a Symbol column, instead of downloading the Nifty 200 list")
    p.add_argument("--sleep", type=float, default=0.7, help="pause between NSE requests (seconds)")
    args = p.parse_args()
    parts = set(args.only.split(","))
    OUT.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        session.get("https://www.nseindia.com", timeout=20)  # sets cookies some NSE endpoints expect
    except requests.RequestException:
        pass

    # the equity and signal history needs a year of warm-up before the first backtest date
    warm_start = str((pd.Timestamp(args.start) - pd.Timedelta(days=420)).date())
    spot = None
    if "index" in parts:
        idx = fetch_index(warm_start)
        spot = idx[idx.symbol == "NIFTY"].set_index("date")["close"]
    elif (OUT / "index_daily.csv").exists():
        idx = pd.read_csv(OUT / "index_daily.csv", parse_dates=["date"])
        spot = idx[idx.symbol == "NIFTY"].set_index("date")["close"]
    if "events" in parts:
        pd.DataFrame(EVENTS, columns=["date", "event"]).to_csv(OUT / "events.csv", index=False)
    if "equities" in parts:
        fetch_equities(warm_start, nifty200_symbols(session, args.universe_file))
    if "fo" in parts:
        fetch_fo(args.start, args.end, session, args.sleep, spot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
