# Prompt for Claude Code on the PC (paste everything below this line)

You are working in my trading research repo on my PC, where my market data lives. Your job has two phases. **Do phase 1 completely before starting phase 2.**

## Ground rules
- Research only. **Never place, modify or cancel orders.** Do not call any broker order endpoint, and do not log in to a broker unless I explicitly ask in this session. Read-only data access only.
- **Never fabricate data.** If something a strategy needs is missing, mark that strategy `BLOCKED` and say exactly what is missing. Do not generate fake prices. The one exception is the clearly labelled synthetic fallback in Part C of the spec.
- The spec is **pre-registered**. Do not change any condition, threshold or parameter grid. If you believe something in it is wrong or impossible with my data, write that in `results/SPEC_ISSUES.md`, explain why, and ask me before deviating. Every configuration you run gets a line in `results/TRIALS.md`.
- The test window is run **once** per strategy, after the configuration is chosen on validation.
- Keep everything reproducible: the config lives in `config/`, code in `bt/`, results in `results/`. Commit to a new git branch `research/fno-specs-v1`, in small commits.

## Phase 1 — Save the specifications
1. `git pull` the branch `claude/trading-backtesting-research-o6g9m0` from `karandattani1/bitcoin-backtest` if this repo has that remote. If `docs/STRATEGY_SPECS.md` already exists there with the same content as below, keep it. Otherwise create it.
2. Save the spec below **verbatim** to `docs/STRATEGY_SPECS.md`.
3. Also write a machine-readable copy at `config/strategies.yaml`, with one entry per strategy S01–S13 containing: id, name, priority, data_codes, diagnostic id, entry/exit rules as structured fields, the parameter grid, controls, and kill criteria. Write `config/costs.yaml` with the A3 cost defaults.
4. Commit with the message "Save pre-registered F&O strategy specs v1", then show me a short summary: the 13 strategies, their priorities, and the number of grid configs per strategy.

## Phase 2 — Test everything
Follow **Part C** of the spec exactly. Concretely:

**Step 1 — Data inventory (stop and report after this step).**
- Find my data. Search likely locations: this repo, folders named data/history/market/duckdb/parquet, and DuckDB/SQLite/Parquet/CSV files. Ask me for the path if you can't find it.
- For each dataset report: instrument(s), timeframe, date range, columns (OI? bid/ask?), number of expiries/contracts, gaps, and timezone.
- Map the data to the codes `IDX1m IDXd VIX1m VIXd OPT1m OPTd FUT1m BFO STKOPT CAL PART BAN`.
- Write `results/DATA_INVENTORY.md` with a table of each strategy S01–S13 against READY / PARTIAL / BLOCKED.
- **Show me this table and wait for my confirmation** before continuing. I may point you to extra data.

**Step 2 — Harness with tests.** Build a small Python package in `bt/` (pandas/numpy, plus duckdb or polars if my data is in DuckDB or Parquet). It needs:
- data loaders: a unified minute-bar and option-chain API by (underlying, expiry, strike, type)
- an expiry list and DTE taken from the data
- a lot-size-by-date lookup
- a Black-76 pricer, IV solver and Greeks
- the synthetic forward via put-call parity
- the cost model per A3
- fills, slippage and adverse-extreme stops per A2
- margin via `marginism` if SPAN files exist, otherwise the A9 approximation
- the HAR range forecast with walk-forward refits per A5
- splits per A6
- controls per A7
- metrics per A8, including the deflated Sharpe and block bootstrap

Write pytest unit tests for at least:
- the ₹141.83 cost example
- the Black-76 price→IV→price round-trip
- a no-look-ahead guard
- the expiry/DTE derivation on a known expiry
- lot size by date
- a hand-computed P&L on one iron-fly trade

Run the tests and show me they pass.

**Step 3 — Diagnostics.** Run D-01…D-10, S12 and S13 on **train+validation only**. Write `results/DIAGNOSTICS.md` with each diagnostic's numbers and a PASS/FAIL against the spec's criterion. Strategies with a failed premise are not backtested.

**Step 4 — Backtests.** For each strategy whose diagnostic passed, in priority order:
1. Run the full pre-registered grid on train→validation.
2. Pick the best config on **validation net return on margin**.
3. Run it **once** on test.
4. Run the required controls.
5. Write `results/Sxx/` with summary.json, trades.csv, daily_pnl.csv, report.md and charts.
6. Append to `TRIALS.md`.

Also run the slippage sensitivity at 0.15/0.30/0.60% for the chosen config.

**Step 5 — Summary.** Write `results/SUMMARY.md` per Part C, step 6. Then give me a plain-language verdict covering:
- which strategies passed, failed or were blocked, and why
- the 2–3 most promising next steps
- any data I should acquire to unblock strategies

Be blunt. "No edge" is a valid and useful result.

Work through these steps autonomously, apart from the stop after Step 1. If a run will take more than about 20 minutes, tell me the estimate first. Keep me posted with one short line per completed step.

---

## The specification (save verbatim as docs/STRATEGY_SPECS.md)

# Strategy Specifications — Indian F&O (v1, pre-registered)

Status: **pre-registered**. Every condition, parameter grid and success criterion below is fixed *before* any test is run. Changing anything after seeing results counts as a new trial, which must be logged in `results/TRIALS.md` and charged in the deflated Sharpe.

Research only. No live orders.

---

## Part A — Common definitions (apply to every strategy)

### A1. Time, sessions, bars
- Session 09:15–15:30 IST. That is 375 one-minute bars, and the bar timestamp is the bar **start**, so the 09:15 bar covers 09:15:00–09:15:59.
- "At HH:MM" means "using data up to the **close of the HH:MM−1 bar**", and the order fills on the **HH:MM bar**.
- Indicators on daily data use only days ≤ t−1, unless the spec explicitly says "today's open/gap". The gap is known at 09:15.
- Trading days come from the data, never from a hardcoded calendar.

### A2. Fills and slippage
- **Fill price:**
  - Options and futures fill at the **open of the fill bar**, adjusted against us by slippage.
  - If the bar has bid/ask, buys fill at the ask and sells at the bid, and no extra slippage is added.
  - If there is no bid/ask, the slippage per leg per side = max(1 tick = ₹0.05, `SLIP_PCT` × price).
  - `SLIP_PCT`: index options 0.30%, stock options 1.0%, futures 0.01%. Sweep the options value at {0.15%, 0.30%, 0.60%} as a sensitivity check, not as a parameter.
- **Stops:**
  - Stops are checked on every 1-minute bar using the **adverse extreme**. Short option legs use the bar **high** and long legs the bar **low** to compute worst-case MTM.
  - When a stop triggers, the exit fills at the **next bar open** plus slippage.
  - If the data has only close prices, use the close and flag the run "close-only stops".
- **Missing data:** if a leg has no print in the fill bar, use the next bar that has one, up to 3 bars. After that, skip the trade and count it in `skipped_no_liquidity`.

### A3. Costs (defaults; verify against your own contract notes and override in `config/costs.yaml`)
- **Options, per executed order:**

  | Charge | Rate |
  |---|---|
  | Brokerage | ₹20 |
  | STT | 0.15% of sell-side premium |
  | Exchange transaction | 0.03553% of premium turnover |
  | SEBI | 0.0001% of turnover |
  | GST | 18% of (brokerage + exchange + SEBI) |
  | Stamp duty | 0.003% of buy-side premium |

- **Unit test (must pass):** buy at 100, sell at 100, qty 400 ⇒ total ₹141.83, broken down as brokerage 40, STT 60, exchange 28.42, SEBI 0.08, GST 12.33, stamp 1.
- **Futures, per executed order:**

  | Charge | Rate |
  |---|---|
  | Brokerage | ₹20 |
  | STT (sell side) | `FUT_STT` (default 0.05%; set to 0.02% for trades before the rate change your notes show) |
  | Exchange | 0.00173% |
  | SEBI | 0.0001% |
  | GST | 18% |
  | Stamp duty (buy) | 0.002% |

- **Exercise and settlement:** never hold to expiry unless the spec says so. If you do, apply STT on the settlement value of ITM long options.

### A4. Instruments, strikes and the forward
- **Strike step:** NIFTY 50, BANKNIFTY 100, SENSEX 100, FINNIFTY 50. Stock steps come from the symbol master.
- **Synthetic forward:**
  - At time t, for expiry E: take the strike K0 nearest spot, then F = K0 + C(K0) − P(K0), using mids if bid/ask exist and LTP otherwise.
  - If either leg is missing, use the near-month future price.
- **ATM strike:** the strike nearest F.
- **Round strike:** the nearest multiple of 100 (NIFTY) or 500 (SENSEX/BANKNIFTY).
- **Pricing and IV:** use **Black-76 on F**, with r = 0.065 for discounting (immaterial intraday). Time is measured in trading minutes, T = minutes_to_expiry_close / (375 × 252).
  - **Unit test:** price → IV → price round-trips to within ₹0.01.
- **Lot size:** the lot in force on the trade date, from the symbol master or contract metadata. Report P&L both in **index points per unit** and in **₹ per lot at the historical lot size**.
- **Expiries:** derive them from the contract list in the data, never from weekday rules. NIFTY weekly expiry was Thursday until Aug 2025 and Tuesday afterwards, and holidays shift expiries. BANKNIFTY weeklies were discontinued in Nov 2024.
- **DTE** = trading days from the trade date to expiry, where expiry day = 0.

### A5. Volatility quantities
- **σ_imp_day(t, E):** the implied 1-day σ in index points, derived from the ATM straddle premium Π:
  - σ_full = Π / 0.7979 (the ATM straddle ≈ 0.7979 × σ√T × F)
  - σ_imp_day = σ_full × sqrt(m_today_remaining / m_to_expiry), where m = trading minutes.
- **Implied range IR(t)** = 1.596 × σ_imp_day, the expected high–low range of a Brownian path over the remaining session.
- **VIX σ over a horizon h trading days:** σ_VIX(h) = VIX/100 × F × sqrt(h/252).
- **HAR range forecast RF(t):** forecast of today's log(High/Low) of the NIFTY index, by OLS:
  - Model: y_t = b0 + b1·y_{t−1} + b2·mean(y_{t−5..t−1}) + b3·mean(y_{t−22..t−1}) + b4·|gap_t|, with gap_t = ln(Open_t / Close_{t−1}).
  - Fit on the **train window only**, then refit monthly on an expanding window inside validation and test (walk-forward).
  - RF_points = (exp(RF) − 1) × Open_t.
  - **Reference:** on 2019–2024 daily data, out-of-sample R² was about 0.48 (see `research/nifty_derivatives_tests.py`). Your number should be in that region.
- **Gate ratio G(t)** = RF_points(t) / IR(t), measured at entry time.
- **Realized vol RV_HAR:** the same HAR form fitted to the 1-day-ahead close-to-close realized variance, used by S03.

### A6. Data splits (chronological, set once from your data range)
- **Train:** the first 50% of available days, used to fit forecasts and percentile thresholds.
- **Validation:** the next 25%, used to choose among the pre-registered grid only.
- **Test:** the last 25%, run **once** with the configuration chosen on validation. Report it even if it fails.
- If the data spans fewer than 18 months, switch to monthly walk-forward (train 6m → test 1m, rolled) and report the stitched out-of-sample result.

### A7. Controls (required for every trading strategy)
- **C-ALWAYS:** the same structure, entry time and exits on **every eligible day**, with no gate.
- **C-RANDOM:** the same structure on randomly chosen eligible days with a **matched trade count**, over 1,000 draws. Report the percentile of the strategy's net P&L within this distribution.
- **C-FLAT:** zero exposure, so that return on margin is compared against 0 rather than against nothing.
- **A pass requires:** the strategy beats C-ALWAYS and lands at or above the 90th percentile of C-RANDOM **on test**, after costs.

### A8. Metrics (every run writes all of these)
- **Counts:** trades, skipped (with reasons), and win rate.
- **P&L:**
  - avg / median P&L per trade, in points and ₹/lot, both gross and net
  - total net P&L
  - **return on margin**: net ₹ ÷ (SPAN + exposure margin at entry, computed with `marginism` from that day's SPAN file if available, or by the approximation in A9)
- **Risk-adjusted:**
  - Sharpe from daily P&L, Sortino, max drawdown (₹ and % of margin), and Calmar
  - **worst day, worst 5-day, worst trade**
  - P&L **with and without** the worst 1% of days
- **Tails:** stop-hit rate and target-hit rate.
- **Statistical:**
  - **Deflated Sharpe ratio** with N = the total number of configurations in `TRIALS.md` for that strategy
  - bootstrap 95% CI of mean daily P&L (stationary block bootstrap, block = 5 days)
- **Breakdowns:** by year, by VIX tercile (VIX at entry), by DTE, by weekday, and by expiry vs non-expiry day.

### A9. Margin approximation (only if SPAN files are unavailable)
- Short straddle/strangle ≈ 12% of notional (F × lot) + 2% ELM on expiry day.
- Iron fly/condor ≈ max(wing width × lot, 4% of notional).
- Long options = premium.
- Flag the run "approx margin".

### A10. Pre-test diagnostics
Each strategy has a diagnostic **D-xx**. It is a cheap measurement that must show the premise holds **before** the strategy is backtested. If the diagnostic fails on train+validation, mark the strategy `PREMISE FAILED`, record it, and do not backtest. This stops a full search when the premise is false.

---

## Part B — Strategies

Each strategy is listed with its data needed, premise, diagnostic, rules, grid, kill criteria and priority.
**Data codes:**
- `IDX1m`: index 1-minute OHLC (NIFTY/SENSEX)
- `IDXd`: index daily
- `VIX1m` / `VIXd`
- `OPT1m`: per-contract option 1-minute OHLC with OI, expired contracts included
- `OPTd`: option EOD with OI
- `FUT1m`: futures 1-minute
- `BFO`: SENSEX options
- `STKOPT`: stock options
- `CAL`: an event calendar file
- `PART`: NSE participant-wise OI
- `BAN`: ban-list history

### S01 — Forecast-gated intraday iron fly on the NIFTY weekly ★ priority 1
- **Data:** IDXd, IDX1m, OPT1m (weekly NIFTY), VIXd (optional, for reports).
- **Premise:** the ATM straddle is fairly priced on average, but realized range is forecastable. So selling only on days when RF is well below IR should be profitable.
- **D-01:**
  - On train+validation, compute G(t) at 09:20 for every day, and realized range ÷ IR.
  - **Pass if** realized/IR in the lowest G tercile is below 0.90, **and** below realized/IR in the highest tercile by at least 0.15.
- **Eligible day:** a nearest weekly expiry with DTE ≥ 1. Expiry days are excluded (see S04), and so are days with any leg missing.
- **Entry:** at `T_ENTRY` ∈ {09:20, 09:45}.
  - Sell 1× ATM CE and 1× ATM PE.
  - Buy 1× CE at ATM + W and 1× PE at ATM − W, where W = the strike step closest to 2 × σ_imp_day (minimum 2 steps).
- **Gate:** G(t) ≤ the train-set q-th percentile of G, with `GATE_Q` ∈ {30, 40, 50}.
- **Exits, first hit wins:**
  1. Combined MTM loss ≥ `SL` × net credit, with `SL` ∈ {0.5, 1.0}.
  2. Combined MTM profit ≥ 40% of net credit.
  3. Time exit at 15:15.
- **Grid:** 2 × 3 × 2 = **12 configs**.
- **Controls:** C-ALWAYS (same structure every eligible day), C-RANDOM, C-FLAT.
- **Kill:** fails A7 on test, or net return on margin per trade ≤ 0 on test.

### S02 — Weekend theta capture (NIFTY) ★ priority 2
- **Data:** OPT1m, IDX1m.
- **Premise:**
  - Monday's gap carries about 1.8 weeknights of variance, not 3 (measured on 2012–2024 daily data).
  - If the market marks down IV on Monday morning, a weekend short captures decay that the realized move doesn't take back.
- **D-02 (must run first):** for every weekend (last session of the week → first session of the next), using a fixed expiry with DTE ≥ 4 at entry and the same strike:
  1. ATM IV change from Fri 15:00 → Mon 09:30.
  2. ATM IV change Thu 15:00 → Fri 09:30, as the "normal night".
  3. ATM IV change Fri 11:00 → Fri 15:00, to check for pre-decay.
  - Also compute straddle P&L ÷ σ_imp_day for 1 versus 2.
  - **Pass if** the weekend IV drop beats the normal-night IV drop by at least 0.5 vol points (median), **and** the weekend straddle-seller P&L/σ is above the normal-night P&L/σ, on train+validation.
  - Long weekends with ≥ 3 non-trading days go in a separate bucket.
- **Entry:** at 15:00 on the last session of the week (`T_ENTRY` ∈ {14:30, 15:00}).
  - Expiry: the nearest weekly with **DTE ≥ 4** at entry.
  - Sell ATM CE+PE and buy wings at ±W, where W = the step closest to 2.5 × σ_imp over the weekend. Weekend horizon = 1 trading day + 2 calendar days; measure it as 1.8 × one night of σ_imp_day variance, using σ = σ_imp_day × sqrt(1.8).
- **Exit:** at `T_EXIT` ∈ {09:20, 09:30, 10:00} on the next session. There is no stop over the weekend (the wings are the stop). After the open, apply an intraday stop of 1 × credit.
- **Delta hedge variant `HEDGE`** ∈ {none, futures-at-entry}: futures-at-entry sells or buys near-month futures to bring the net delta to 0 at entry.
- **Grid:** 2 × 3 × 2 = **12 configs**.
- **Controls:**
  - C-WEEKNIGHT: the identical trade on Thu 15:00 → Fri exit.
  - C-RANDOM: random weekday nights with a matched count.
- **Kill:** D-02 fails, or the strategy does not beat C-WEEKNIGHT on test.

### S03 — Monthly VRP iron condor with a regime gate ★ priority 3
- **Data:** OPTd + OPT1m (monthly NIFTY), VIXd, IDXd.
- **Premise:** VIX exceeds subsequent realized vol on most days (about 82% in the last year, per the OpenAlgo course). A regime gate should avoid the spikes.
- **D-03:**
  - Compute VRP_t = VIX_t − realized vol over the next 21 sessions (annualised close-to-close). Report its mean, median, % positive, and the 1st percentile.
  - Split by gate state: gate on vs gate off.
  - **Pass if** mean VRP when the gate is on > mean VRP when it is off, **and** the 1st percentile of VRP when the gate is on is better (less negative), both on train+validation.
- **Entry:** at 10:00 on the first session after the previous monthly expiry, on the next monthly contract. Require DTE in 15–30; if outside that range, skip the month.
- **Gate (all must hold, using t−1 closes):**
  - VIX − RV_HAR forecast > the train median of that spread
  - VIX 5-day % change < +15%
  - front-weekly ATM IV ≤ next-monthly ATM IV + 0.5 (no inversion)
- **Structure:**
  - Short CE and PE at F ± `K_SHORT` × σ_VIX(DTE), with `K_SHORT` ∈ {0.8, 1.0, 1.2}, snapped to the nearest 100.
  - Long wings at F ± 3.5 × σ_VIX(DTE), snapped to 100.
- **Exits:**
  - profit ≥ `TP` × max credit, with `TP` ∈ {0.5, 0.7}
  - loss ≥ 2 × credit
  - DTE ≤ 5, then close everything
- **Sizing for reporting:** the lots such that (wing width − credit) × lot ≤ 2% of a ₹1 crore notional book. Also report per lot.
- **Grid:** 3 × 2 = **6 configs**, plus the ungated twin as C-ALWAYS.
- **Kill:** fails A7, or the worst month exceeds 3 × the average monthly net profit with no gated advantage over ungated in the worst 1% of months.

### S04 — Expiry-day pin (0DTE NIFTY, and SENSEX if BFO is available) ★ priority 4
- **Data:** OPT1m with intraday OI, IDX1m.
- **Premise:** on expiry days the index range was not larger than on other days (weekly era: 116 vs 124 bps). OI is concentrated at round strikes, at about 62% of near-money OI.
- **D-04:**
  - At 13:30 on every expiry day, let K* = the strike with the max (CE OI + PE OI) among round-100 strikes within ±1% of F. Use the latest OI available up to 13:29; if only EOD OI exists, use the previous day's EOD OI and label the run "EOD-OI".
  - Measure d0 = |F_13:30 − K*| and d1 = |Close − K*|.
  - **Placebo:** apply the same procedure on the session before expiry.
  - **Pass if** median(d1/d0) on expiry days < 0.8 **and** < the placebo's median by at least 0.15.
- **Entry:** at 13:30 on expiry day, when d0 ≤ `PIN_BAND` × σ_rem, with σ_rem = σ_imp_day for the remaining minutes and `PIN_BAND` ∈ {0.3, 0.5}.
  - Sell an iron fly centred on K*, with wings at ±max(100, 2 × σ_rem) snapped to 50.
- **Optional gate `GEX`** ∈ {off, on}: on requires net GEX > 0, where GEX = Σ_strikes (OI_CE × Γ_CE − OI_PE × Γ_PE) × F² × 0.01, using the assumption that customers are long calls and long puts. Note the sign convention in the report.
- **Exits:** loss ≥ 1 × credit, or 15:20.
- **Grid:** 2 × 2 = **4 configs**.
- **Controls:** C-ALWAYS (an iron fly at ATM at 13:30 on every expiry day, with no K* logic), C-RANDOM.
- **Kill:** D-04 fails, or the strategy doesn't beat C-ALWAYS on test.

### S05 — NIFTY vs SENSEX implied-vol spread — priority 5
- **Data:** OPT1m (NIFTY) and BFO (SENSEX), IDX1m for both.
- **Premise:** the indices are about 0.98 correlated, but their option books are set by different flows.
- **Daily at 14:00:**
  - Compute the 7-calendar-day constant-maturity ATM IV for each index, by variance-interpolating between the two nearest expiries with DTE ≥ 1.
  - S_t = IV_SENSEX − IV_NIFTY.
  - Z_t = (S_t − mean_60) / std_60 over the trailing 60 sessions.
- **D-05:** report the half-life of S_t (AR(1) on daily S), the share of |Z| > 2 days, and the subsequent 5-day change in S after |Z| > 2. **Pass if** the half-life is ≤ 5 days on train+validation.
- **Entry:** when |Z| > `Z_IN`, with `Z_IN` ∈ {1.5, 2.0}. Sell the ATM straddle of the rich index and buy the ATM straddle of the cheap one, using each index's nearest expiry with DTE ≥ 2.
  - Lots are matched by vega: lots_cheap = round(vega_rich × lot_rich / (vega_cheap × lot_cheap_size)).
  - Add a delta hedge with futures (or the synthetic) on each side at entry.
- **Exits:** Z crosses 0, or 5 sessions pass, or either leg reaches DTE = 0 (close at 15:00 the day before).
- **Grid:** **2 configs**.
- **Kill:** D-05 fails, or net P&L ≤ 0 on test.

### S06 — Earnings straddles on liquid F&O stocks — priority 6
- **Data:** STKOPT (EOD is enough, 1-minute is better), stock daily, CAL (result dates and time: pre-market, intraday or after-market).
- **Universe:** the top 20 F&O stocks by average option premium turnover over the prior 60 days, computed point-in-time.
- **Event day E:**
  - results after the close → E = the next session
  - results before the open or intraday → E = the same day
- **Historical event move H_i:** the median of |ln(Close_E / Close_{E−1})| over that stock's previous 8 results. At least 4 are required.
- **Implied event move I_i:** (front ATM straddle at E−1, 15:15) / spot. Require the front expiry to have DTE ≥ 3 at E−1; otherwise use the next expiry.
- **D-06:** across all events in train+validation, regress the realized |event move| on I and on H. **Pass if** I > realized on average (sellers' premium exists) **and** the ratio I/H sorts realized-minus-implied P&L monotonically across terciles.
- **Trades:**
  - **SELL** when I/H ≥ `R_SELL` ∈ {1.3, 1.6}: an iron fly with wings at ±2 × I × spot.
  - **BUY** when I/H ≤ 0.8: a long ATM straddle.
  - Entry at E−1 15:15. Exit `T_EXIT` ∈ {E 09:30, E 15:15}. Never hold to expiry, because of physical settlement.
- **Costs:** use the stock-options slippage from A2 (1.0%).
- **Grid:** 2 × 2 = **4 configs** for SELL, plus 2 for BUY.
- **Kill:** D-06 fails, or the test net is ≤ 0 after slippage at 1.0%.

### S07 — Put-skew mean reversion / cheap tail hedge — priority 7
- **Data:** OPT1m or OPTd (monthly NIFTY).
- **Skew at 15:00 daily:** SK = IV(25Δ put) − IV(ATM) on the next monthly with DTE ≥ 10, with Δ from Black-76. Pct = SK's percentile versus the trailing 250 sessions.
- **D-07:** report the mean 10-day change in SK conditional on Pct ≥ 90 and on Pct ≤ 10, and the next-20-day realized downside semivariance by Pct decile. **Pass if** Pct ≥ 90 is followed by a fall in SK (mean reversion) on train+validation.
- **SELL-SKEW (Pct ≥ 90):** sell the 25Δ put and buy the 10Δ put.
  - Hold `HOLD` ∈ {5, 10} sessions, or exit at TP 50% of credit, or loss at 2 × credit.
- **BUY-TAIL (Pct ≤ 10):** buy the 25Δ/10Δ put spread. Hold 20 sessions or until DTE = 3. Measure it as a hedge: its P&L on the worst 5% of NIFTY 20-day windows.
- **Grid:** 2 configs (SELL) plus 1 (BUY).
- **Kill:** D-07 fails.

### S08 — Implied correlation / light dispersion — priority 8 (diagnostic first)
- **Data:** OPTd for NIFTY and the top-10 index-weight stocks (point-in-time weights if available, otherwise current weights flagged as a survivorship risk), stock daily.
- **Implied correlation:** ρ_imp = (σ_I² − Σ w_i² σ_i²) / (Σ_{i≠j} w_i w_j σ_i σ_j), using monthly ATM IVs at 15:00 and renormalising weights over the 10 names.
- **Realized correlation:** ρ_real_fwd = the same formula with realized vols and pairwise correlations over the next 20 sessions.
- **D-08:** report the mean of ρ_imp − ρ_real_fwd, and its percentile-sorted means. **Pass if** the mean is > 0.05 **and** the top quintile of ρ_imp has the largest gap.
- **Trade (only if D-08 passes):** when ρ_imp pct ≥ 80, sell the index ATM straddle (1 unit of vega) and buy the 10 stock ATM straddles, vega-weighted by w_i, so total vega = 1 unit. Delta-hedge daily with futures at 15:15. Exit at monthly DTE = 5.
- **Grid:** 1 config. **Kill:** D-08 fails.

### S09 — Overnight NIFTY futures drift — priority 9
- **Data:** FUT1m (near month; roll to the next contract 2 sessions before expiry), IDX1m.
- **Premise:** on the NIFTY index from 2012–2024, the overnight return (previous close → open) was positive every year, while the intraday return was negative in 12 of 13 years (`research/nifty_quick_tests.py`).
- **D-09:** using **futures** prints, measure close(15:25) → open(09:20) versus 09:20 → 15:25 returns, by year. **Pass if** the overnight mean > 0 in at least 70% of years **and** exceeds the round-trip futures cost.
- **Trade:** buy 1 lot at 15:25 and sell at `T_EXIT` ∈ {09:16, 09:20, 09:30}.
  - `FILTER` ∈ {none, index close > SMA50}.
  - Skip roll days and expiry days.
- **Grid:** 3 × 2 = **6 configs**.
- **Kill:** test net Sharpe < 0.5, or worst gap > 5 × average daily profit with no filter benefit.

### S10 — Scheduled event volatility (Budget, RBI MPC, national election results, plus your own list) — priority 10
- **Data:** OPT1m (weekly NIFTY), CAL (`events.csv` with columns date, type).
- **Seed Budget dates:** 2012-03-16, 2013-02-28, 2014-07-10, 2015-02-28, 2016-02-29, 2017-02-01, 2018-02-01, 2019-02-01 (interim), 2019-07-05, 2020-02-01, 2021-02-01, 2022-02-01, 2023-02-01, 2024-02-01 (interim), 2024-07-23, 2025-02-01, 2026-02-01. **Verify these.**
- **Seed elections:** 2014-05-16, 2019-05-23, 2024-06-04. The RBI MPC dates must be supplied.
- **Implied event move IEM:** straddle(E−1, 15:15) / F − σ_imp_day/F of a normal day (the median of the 5 prior non-event days' σ_imp_day/F).
- **D-10:** compare the realized |close_E / close_{E−1} − 1| with IEM. Report the event-day P&L of a short straddle, and the post-event IV crush (ATM IV at E 15:15 minus E−1 15:15).
- **Variants:**
  - **(a) PRE:** sell an iron fly at E−1 15:15 with wings ±2 × IEM × F, exit at E 15:15.
  - **(b) POST:** at E 15:15 sell an iron fly on the next weekly expiry with DTE ≥ 2, wings ±2 × σ_imp_day, exit E+2 15:15 or at a loss of 1 × credit.
- **Grid:** 2 configs. **Kill:** n < 15 events in train+validation means report descriptively only, with no pass/fail.

### S11 — Positioning features as gates (not standalone) — priority 11
- **Data:** PART (FII long/short index futures contracts daily), OPTd OI (for GEX and PCR), FUT OI.
- **Features at t−1:**
  - FII_LR = FII index-fut long / (long + short), with its 250-day percentile and a 5-day streak of changes
  - GEX sign (as in S04, on the full near-month chain at EOD)
  - PCR_OI = total put OI / call OI on the nearest weekly
  - futures build-up class: price up/down × OI up/down, on near-month NIFTY futures
- **Test 1:** add each feature to the HAR range model (A5). Accept a feature only if out-of-sample R² improves by ≥ 0.01 on **both** validation and test.
- **Test 2:** add each accepted feature as an extra gate on S01 and S03, i.e. skip when the feature is in its hostile state, defined on train as the quintile with the worst strategy P&L.
- Each feature-gate is a new trial: charge it in N.

### S12 — F&O ban-list event study (diagnostic) — priority 12
- **Data:** BAN (daily ban list history), stock daily, NIFTY daily.
- **Events:** ban entry (first day in the ban) and ban exit (first day out).
- **Measures:** excess return vs NIFTY over +1, +5 and +10 days, and realized vol over the next 10 days ÷ the prior 20 days, for both entry and exit. Split by the prior 20-day return sign.
- **Pass (a trade spec would be written later, as v2):** |t| > 3 on both halves of the sample for the same sign.

### S13 — Roll cost and basis (support measurement for S03 and S09) — priority 13
- **Data:** FUT1m (near and next month).
- **Measure:**
  - The roll spread (next − near) in the last 5 sessions before expiry, as annualised carry.
  - The bid-ask cost of rolling at 10:00 vs 15:00.
  - Annualised near-month basis vs the 91-day T-bill (if you have it).
- **Output:** a cost table that feeds S09 and S03. There is no pass/fail.

---

## Part C — Run order and reporting
1. **Data inventory.** Write `results/DATA_INVENTORY.md`, mapping each strategy to its data codes. Strategies whose data is missing are marked `BLOCKED: <what is missing>`. Never fabricate or synthesise market data, except the explicitly labelled synthetic straddle described below.
2. **Harness and unit tests:** the cost model (₹141.83 example), Black-76 round-trip, no-look-ahead (shifting a signal by +1 bar must change results, and using future bars must raise an error), the expiry list from data, and lot-size lookup by date.
3. **Run the diagnostics D-01…D-10 and S12/S13** on train+validation. Write `results/DIAGNOSTICS.md`.
4. **Backtest only the strategies whose diagnostic passed**, in priority order. For each, write `results/Sxx/summary.json`, `trades.csv`, `daily_pnl.csv` and `report.md`, plus charts (equity curve, drawdown, P&L by VIX tercile).
5. **Test window: run once.** Record it in `results/TRIALS.md`: strategy, config hash, timestamp, and the split used.
6. **Master table `results/SUMMARY.md`:** one row per strategy with
   - status (BLOCKED / PREMISE FAILED / FAILED TEST / PASSED)
   - n trades, net ₹/lot, return on margin, Sharpe, DSR, max DD, worst day
   - its percentile vs C-RANDOM
   - a one-line verdict

**Optional synthetic fallback** (for S01–S04 only, when OPT1m is missing but IDX1m and VIX exist):
- Price straddles with Black-76 on the index path, with IV = VIX/100 × k, where k is calibrated on any real chain days you have.
- Label every result `SYNTHETIC — gamma/decay only, no microstructure`. Synthetic results can never earn a PASSED status.
