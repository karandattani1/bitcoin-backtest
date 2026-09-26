# Indian Market Trading Ideas — from a scan of 167 repos

Snapshot 2026-09-26. This is research, not investment advice.

**Scope.** I scanned every repo in `external/`: all 152 OpenAlgo/marketcalls repos plus the curated backtesting set. Several were read closely: the honest research write-ups (AutoAgent progress logs, the `statistical-arbitrage` notebooks, OpenFly's NIFTY facts), the OpenAlgo quant course (`openalgo-webpage/content`, about 280 chapters) and the strategy templates. Where local data allowed, I tested ideas in `research/nifty_quick_tests.py`.

**Data reality.** None of these repos ships usable Indian stock history. The single exception is `marketcalls/data/NIFTY_daily_data.csv` (NIFTY price index, daily, 1990 to Jan 2024), which the index tests below use. Everything else fetches live from a broker through OpenAlgo. Data options are covered in section 4.

---

## 1. What the repos already proved does *not* work (save yourself the time)

| Idea | Evidence | Verdict |
|---|---|---|
| Intraday EMA 10/20, Supertrend 3/10 and SMA10/EMA30 crossovers on 5-minute bars (5-stock basket) | `AutoAgent/docs/progress/003`: all three lost money over 93 sessions. The best had expectancy −0.125R and profit factor 0.73. **Gross P&L is flat to negative even at zero slippage**, so the signal itself is the problem, not costs | Avoid |
| Classic pairs trading (HDFCBANK/KOTAKBANK z-score) | `statistical-arbitrage/07`: looks great in-sample. Out-of-sample and net of costs it is "at best marginal". Cointegration fails in most rolling windows | Avoid as a standalone strategy |
| Cross-sectional short-term reversal (factor-neutral, NIFTY 50) | `statistical-arbitrage/10`: turnover of about 235× a year, and costs **invert the sign** of the edge. The short leg is also hard to implement in India | Avoid |
| 6-month cross-sectional momentum, long/short NSE stocks | Quant course ch60: Sharpe **−0.67** in their window. Losers beat winners, so the market showed reversal. The effect depends on the regime | Only test with many windows and a long-only version |
| Jev (LLM) predicting price direction | `jev_bitcoin_backtest`: holdout AUC was about 0.5 | Use Jev as a classifier, not a forecaster |

## 2. Index tests run here (NIFTY daily, costs 5 bps per side, in-sample 1996–2011 / out-of-sample 2012–2024)

Reproduce with `python3 research/nifty_quick_tests.py`.

| Test | In-sample | Out-of-sample | Read |
|---|---|---|---|
| Buy & hold (price index, no dividends) | CAGR 10.9%, Sharpe 0.52, MaxDD −60% | CAGR 14.2%, Sharpe 0.88, MaxDD −38% | Baseline |
| **Long when close > SMA50, else earn 6% cash** | CAGR 21.3%, Sharpe 1.16, DD −31% | CAGR 11.9%, **Sharpe 1.12, DD −15%** | Better risk-adjusted in *both* periods. Gives up some CAGR out-of-sample |
| Long when close > SMA200, else 6% cash | Sharpe 0.74, DD −33% | Sharpe 0.68, DD −23% | Weaker than SMA50 out-of-sample |
| **Overnight vs intraday** (prev close→open vs open→close) | +11.5% vs +2.4% annualised | **+30.7% vs −16.0%** annualised | Overnight is positive in **every year 2012–2024** and the open is not stale. All of NIFTY's gain came overnight |
| **Turn of month** (last day + first 3 days) | 25.1 vs 0.9 bps/day | 12.9 vs 4.1 bps/day | Persists across both periods. About 20% of days carry a large share of the return |
| Day of week | Wednesday +33 bps (t = 5.6) | Tuesday +14 bps (t = 3.5) | The in-sample Wednesday effect is the **pre-2002 weekly-settlement era** and has since faded. Tuesday is interesting, but NIFTY's weekly expiry moved to Tuesday in Sep 2025, so re-check |
| After a −2% day, next 1d/5d return | Mixed | Mixed | Not robust |
| High vs low volatility regime → next 20 days | Inconsistent sign | Inconsistent sign | Not robust |

**Caveats.** About 12 variants were tested here, so some "wins" are luck. Apply a deflated Sharpe (`statistical-arbitrage/12`) before believing any of them. Buy & hold is also understated by about 1.2–1.5%/yr of dividends. Finally, every switch in and out of an ETF is a **taxable short-term gain**, while futures avoid the ETF round trips but add roll costs.

---

## 3. Ideas worth building, ranked by (evidence × ease) ÷ risk

### Tier 1: low turnover, positive evidence, doable with ETFs

**1. NIFTY trend timer with a cash sleeve**
- **Rule:** hold NIFTYBEES (or NIFTY futures) when NIFTY closes above its 50-day SMA. Otherwise park in a liquid/overnight fund ETF (e.g. LIQUIDBEES).
- **Evidence:** section 2. Out-of-sample drawdown fell from −38% to −15% and Sharpe rose from 0.88 to 1.12.
- **Next steps:** add total-return data, taxes, lookbacks from 20 to 250 days (report the *distribution*, not the best one), and a walk-forward check.
- **Reuse:** `vectorbt-backtesting-skills` (the Dual Momentum and Buy & Hold templates already use NIFTYBEES/GOLDBEES) and `openalgo-execution-skills` (the same file runs as a backtest and live).

**2. Calendar overlay: turn of month and overnight timing**
- **Cheapest version:** if you are going to buy anyway (SIPs, rebalancing), **buy near the close, not at the open**, and add around month end. The intraday leg lost money in 12 of 13 recent years.
- **Trading version:** hold NIFTY futures close→open only. That nets about 5.5%/yr on notional after 10 bps/day, so it is highly cost-sensitive.
- **Blocker:** futures fills don't match index prints. **Verify first** on NIFTY futures 1-minute data (from Historify, `expirymanager` or `ExpiryFlow`).

**3. Sector rotation with sector ETFs or indices**
- **Rule:** monthly, rank the 12 NSE sector indices on relative strength and momentum against NIFTY (RRG quadrants), and hold the top 2–3 "Leading/Improving" sectors.
- **Why it might work:** low turnover suits delivery costs (0.11% + ₹20).
- **Reuse:** `sector-rotation-map` already computes RS-Ratio/RS-Momentum.
- **Warning:** ch60 shows momentum can flip to reversal in India. Test formation windows of 1, 3, 6 and 12 months across rolling windows, and combine with trend timer #1 to avoid momentum crashes.

**4. Dual momentum across assets**
- **Rule:** hold NIFTYBEES, GOLDBEES, or a liquid fund, whichever has the best trailing 6–12 month return. Hold cash if nothing beats the liquid fund.
- **Reuse:** template `dual_momentum_backtest.py` exists in `vectorbt-backtesting-skills`.
- **Why:** India-specific diversification, since gold is often negatively correlated with NIFTY in rupee terms.

### Tier 2: event-driven, needs event-date data

**5. Index reconstitution run-up**
- **Rule:** NIFTY 50/Next 50/Midcap changes are announced about 4 weeks before the effective date. Buy additions after the announcement and exit into the rebalance-day index-fund demand.
- **Source:** course ch63 ("an edge born from obligation").
- **Data:** a list of NSE index-change announcements (scrape NSE press releases locally), then an event study.

**6. Post-earnings drift (PEAD) proxy**
- **Rule:** rank result-day gap × volume surprise and hold 10–40 days.
- **Data:** results dates from the Definedge `getEarningsCalendar` or `getQuarterlyResults` tools, which are available in this session after login.
- **Source:** ch63 suggests the gap/volume proxy when analyst estimates are unavailable.

**7. Buyback tender arithmetic**
- **Rule:** when the tender price is well above market, the small-shareholder reserved acceptance ratio makes the return computable.
- **Nature:** a spreadsheet trade, not a model. Low frequency, and fine for small capital.

### Tier 3: derivatives, higher risk, paper-trade first

**8. Short-straddle day selection (variance risk premium)**
- **The facts:** OpenFly measured that NIFTY's full-day realised move ≈ the straddle premium, so selling blindly is fairly priced. **The edge must come from choosing days and hours.**
- **Test:** sell only when implied vol (INDIAVIX) exceeds a realised-vol forecast by a margin. Skip event days and expiry-day gamma.
- **Numbers to budget for:** one lot is 65 (NIFTY). Margin is about ₹1.9L per short straddle. Costs are about 0.95% of credit per round trip.
- **Data and reuse:** `ExpiryFlow` has a dynamic-straddle backtester on Dhan expired-options data. `marginism` computes SPAN offline and `opengreeks` handles the Greeks.

**9. OI build-up and FII flow streaks as a *filter***
- **Rule:** don't trade them standalone. Use "FII net sellers 8 of the last 10 sessions" or "short build-up in index futures" to cut size on long strategies (course ch64).
- **Data:** participant-wise OI and FII/DII files from NSE, joined by date. The Definedge `getFuturesBuildup` and `getOptionsBuildup` tools also cover this.

### Tier 4: infrastructure that makes all of the above faster

**10. Autoresearch loop with honest gates**
- **Pattern:** from `backtesting-autoresearch`. `backtest.py` is fixed and the agent may only edit `strategy.py`, with results logged to `results.tsv`.
- **Upgrades:** add a locked holdout, a deflated Sharpe that counts *every* trial, and write each run to an Obsidian vault note, so the lab notebook builds itself.

**11. Jev as a regime and news classifier, gating tier 1–2 strategies.** Examples: "is today an event day?", "classify this results headline as beat / inline / miss". Cheap to run. Measure against a blank-state control.

---

## 4. Getting Indian data (this sandbox blocks Yahoo and NSE; your machine won't)

| Source | What | Cost | Notes |
|---|---|---|---|
| OpenAlgo + your broker → `historify` (DuckDB) | Equity, index and F&O daily/intraday | Broker API (often free) | What all the marketcalls research uses |
| `openchart` (pip) | NSE public chart API: equity, index and F&O, 1-minute to monthly | Free | No login. Blocked here, fine locally |
| yfinance `RELIANCE.NS`, `^NSEI` | Daily EOD, adjusted | Free | Good enough for tier 1 |
| `expirymanager` (Fyers) / `ExpiryFlow` (Dhan) | **Expired** option and future contracts with OI | Broker API | Needed for idea 2 (futures) and idea 8 |
| Definedge MCP (connected in this session) | History, RS/momentum scanners, sector performance, earnings calendar, OI build-up | Needs a Definedge login | Not used yet: it requires signing in with your account |

## 5. India-specific gotchas found in the repos (read before backtesting)

- **Brokerage** is the *lower* of 0.03% or ₹20 per order, not a flat %. Getting this wrong made a cost model 7.2× too pessimistic (AutoAgent 003).
- **Cost defaults per side:** intraday 0.0225%, delivery 0.111% (STT-heavy), futures 0.018%, options 0.098%, plus ₹20 per order (`openalgo-execution-skills/rules/transaction-costs.md`).
- **OpenAlgo's Supertrend direction flag is inverted:** −1 means price is above the line. EMA has no warm-up NaNs, so you must mask warm-up bars.
- **Model fills at the next bar's open.** Live signals should read `iloc[-2]`, the last *closed* bar.
- **Symbols change.** For example, TATAMOTORS became TMCV after the demerger, and silent drops shrink your universe. Survivorship bias matters for NIFTY-constituent universes.
- **NIFTY weekly expiry is Tuesday** (Thursday before Sep 2025). Lot sizes: NIFTY 65, BANKNIFTY 30, FINNIFTY 60. The freeze quantity for NIFTY is 1,800.
- **Shorting stock overnight** requires SLB or stock futures. MWPL ban lists apply, so long/short backtests often aren't implementable as written.
