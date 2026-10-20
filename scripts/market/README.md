# Market data for the backtester

Run this on your own PC. NSE and Yahoo block cloud servers.

```
pip install -r scripts/market/requirements.txt
python scripts/market/fetch_market_data.py                 # 2020-01-01 to today
```

| Part | Source | Used by | Time |
|---|---|---|---|
| `index` | Yahoo `^NSEI`, `^INDIAVIX` | everything (spot, VIX, ATR, gaps, kurtosis) | seconds |
| `events` | built-in list (Budgets, 2024 election results) | A4, A8 | – |
| `equities` | Nifty 200 list from NSE, prices from Yahoo | E1–E3 | ~2 min |
| `fo` | NSE daily F&O bhavcopy | A, B, C (options) and S6 futures build-up | ~20–30 min for 2020–2025, resumable |

- Add RBI policy dates to `data/market/events.csv` (`date,event`) if you want them filtered as well.
- If the NSE downloads return nothing, NSE is rate-limiting or blocking you. Raise `--sleep`, try later, or try another network. Months already downloaded are cached in `data/market/raw_fo/`.

## 1-minute data (needed for D1–D3)

There is no free, complete source. Options:
- **Your broker's historical API**, e.g. Zerodha Kite Connect historical candles or Dhan's intraday historical data. Both need an API subscription.
- **Public datasets on GitHub and IEEE DataPort** cover older years only (e.g. 2017–2020, or 2015–2022).

Whatever the source, save it as `data/market/index_minute_NIFTY.csv.gz` with columns `datetime,open,high,low,close[,volume]`,
with timestamps in IST. NIFTY futures minute data with volume is better than the index: D2 then uses a real VWAP.

## Intraday option data (needed for A2, A3, B3, C1)

These four strategies need 1-minute option prices. Dhan offers an "expired options data" API (ATM-relative strikes, NSE/BSE index options),
and paid vendors sell full option-chain history. Once there's a source, the strategies can be added in `backtest/strategies/`.
