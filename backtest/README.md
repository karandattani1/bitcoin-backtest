# Backtester

Tests the strategies in [research/strategy-rulebook.md](../research/strategy-rulebook.md) on Indian market data.

```
pip install -r requirements.txt
python scripts/market/fetch_market_data.py          # on your PC: downloads data/market/
python -m backtest.run_all                          # writes research/backtest-results.md and data/results/*.csv
python -m backtest.run_all --start 2022-01-01       # a later start date
pytest -q tests                                     # mechanics tests
python -m backtest.synthetic /tmp/synth && python -m backtest.run_all --data /tmp/synth --out /tmp/r.md   # dry run on fake data
```

## Coverage

| Strategies | Data | How they're tested |
|---|---|---|
| A1, A4–A9, B1, B2, B4, C2, C3 | NSE F&O bhavcopy (daily OHLC + OI per option) + NIFTY/VIX | Daily-bar approximation (below) |
| D1–D3 | 1-minute NIFTY bars | Exact intraday rules |
| E1–E3 | Daily prices of Nifty 200 stocks | Exact rules (monthly / daily) |
| A2, A3, B3, C1 | 1-minute option prices | Not yet; need an intraday option data source |
| E4 | Point-in-time fundamentals | Not yet |

## How daily bars stand in for intraday rules

- **Timing.** Entry at 09:20 uses the option's first traded price of the day. Exit at 15:15 uses the day's close.
- **Stops.** A stop triggers if the day's high (short leg) or low (long leg) reaches it, and fills at the stop plus slippage.
  Two legs' stops can both trigger on the same day, which matches a V-shaped day.
- **Stop vs target.** If a long option could have hit both its stop and its target in one day, the stop is assumed.
- **Rules that can't be expressed on daily bars** are replaced, and each strategy's docstring says how:
  - combined-premium stops become per-leg stops;
  - the opening-15-minute range becomes the previous day's range;
  - intraday wall-break exits become a 100% per-leg stop.
- **No look-ahead.** Signals for an entry at the open come from the previous day's close.
  Overnight and close-to-close strategies use the same day's close for what would be a ~15:10 decision.

## Assumptions to keep in mind

- **Costs.** The 2026 schedule (STT 0.15% on option premium sold) is applied to the whole history, plus slippage of 0.5 point per option order (1 point on expiry day) and 1 point per futures order.
- **Position size.** One current NIFTY lot (65) for the whole period, against a fixed capital per lot:
  naked ₹2.5L, defined-risk ₹1L, spreads ₹75k, buying ₹50k, futures ₹2L.
  So returns in 2020, when NIFTY was ~12,000, are smaller in rupees than they'd be today.
- **Equity universe.** Today's Nifty 200 list is used for the whole history, which adds survivorship bias.
- **Expiry regimes.** Results are also reported from Sep 2025 onward (Tuesday NIFTY expiry, one weekly per exchange).
