# Strategy Ideas Backlog (NSE: 1-min options + stock data)

This is a working list of testable ideas, each written as a spec we can backtest.
Sources are the public "white box" algo descriptions on Dhan Algos / Stratzy, AlgoTest's registered-RA algos, and published research (see `SOURCES.md`).

---

## 0. First, what "white box" actually gets you

- Under SEBI's 4-Feb-2025 retail algo framework and NSE circulars (NSE/INVG/67858, 69255, 72657, 73992):
  - A **white box** algo is one whose logic is disclosed and replicable.
  - A **black box** algo has undisclosed logic, and its provider needs a SEBI Research Analyst licence plus a research report for each algo.
  - Each registered algo gets an exchange **Algo ID**, mandatory on orders from 1-Apr-2026.
- **NSE and SEBI do not publish a public list of registered strategies or their logic.**
  - NSE publishes only the list of *empanelled algo providers*.
  - A white-box strategy's logic is disclosed to users on the provider's or broker's page.
  - So the "scan" below comes from provider pages (Dhan Algos / Stratzy, AlgoTest).
- Stratzy's public descriptions are **partial**. They name the inputs ("alpha from IV, curvature, Hamiltonian, entropy, eigenvalues") and sometimes the exact thresholds, stop-losses and trading windows. The feature formulas themselves are not published.
- Where a formula is missing, this file gives our own **proxy definition**, marked `PROXY`, so the idea is still testable. Do not treat a proxy as Stratzy's real formula.

---

## 1. Shared option-chain features (build these once)

Compute them per minute, from the 1-min option chain, for the nearest weekly expiry. Use the ATM strike ± N strikes.

| Feature | Definition | Used by |
|---|---|---|
| `iv_atm` | IV of ATM call/put (average), Black-76 on futures or synthetic forward | everything |
| `iv_skew` | `IV(OTM put, 0.25Δ) − IV(OTM call, 0.25Δ)`; also OTM-vs-ITM skew per side | SkewHunter, B8 |
| `iv_curvature` | `IV(K_atm+k) + IV(K_atm−k) − 2·IV(K_atm)` (smile convexity) | Curvature/Delta-Rotation spreads |
| `oi_entropy` (PROXY) | Shannon entropy of normalised OI (or volume) across strikes. Low = concentrated positioning | Credit spreads, strangles |
| `surface_eig` (PROXY) | Rolling PCA on minute changes of the IV smile. Share of variance in PC1 (level) vs PC2/PC3 (skew/curvature) | Credit spreads |
| `energy` (PROXY for "Hamiltonian") | `0.5·(spot 1-min return / σ)² + 0.5·((spot − VWAP)/σ)²` (kinetic + "potential" around an anchor) | Credit spreads, strangles |
| `vol_oi_ratio` | `Δvolume / ΔOI` for OTM calls vs ITM puts (flow vs fresh positioning) | SkewHunter |
| `iv_rank` | Percentile of `iv_atm` over the last 252 days (or India VIX percentile) | Strangles, filters |
| `rv_1m` | Realised vol from 1-min returns (Parkinson or close-to-close), annualised | VRP filters |
| `straddle_px` | ATM CE + PE premium (a single time series) | Straddle-chart ideas |

Turn each raw feature into `alpha ∈ [0,1]` with a rolling percentile rank. Stratzy's disclosed thresholds (0.75/0.8, 0.25/0.2) are on this percentile scale.

---

## 2. Reconstructed Stratzy / Dhan white-box algos

### A. Directional option buying (NIFTY)

**A1. SkewHunter**: *disclosed logic, good first test*
- **Alphas:**
  - `alpha1`: volume-ratio and OI-change for OTM calls vs ITM puts (`vol_oi_ratio`, percentile ranked)
  - `alpha2`: IV skew between OTM and ITM options, calls and puts (`iv_skew`, percentile ranked)
- **Entry:**
  - Long ATM/near-OTM **call** if `alpha1 > 0.75 AND alpha2 > 0.8`
  - Long **put** if `alpha1 < 0.25 AND alpha2 < 0.2`
- **Window:** new entries only between 10:15 and 14:15
- **Filters:** skip if option premium < ₹20
- **Exit:** SL 40% of entry premium; square off at end of day
- **Variant A1b, SkewHunter TSL:** same entry, with a trailing SL instead of a fixed one

**A2. Index Sniper**
- **Disclosed:** morning entry; books partial profit at a preset target; holds the rest to end of day
- **PROXY entry:** break of the 09:15–09:30 opening range on NIFTY futures → buy ATM option in the breakout direction
- **Exit:** book 50% at +40% of premium; rest runs to 15:15 with SL at 30%
- **Sweep:** the range length and the target

**A3. Exit-wrapper family** (same entry, different exits)
- These are Stratzy products that disclose only the risk/reward exit, not the signal:
  - Fixed RR 1:3 (30% SL)
  - Burst RR 1:2 (25% SL)
  - Burst GRID (30% SL)
  - Savdhaan (35% SL)
  - Settle-Down (40% TSL)
- **Test:** fix one entry signal (A1 or A2), then compare the exit rules on it. Fixed RR vs trailing vs grid scale-in, and SL of 25/30/35/40%.
- **Why it's useful:** it separates entry edge from exit edge, and most retail "algos" differ only in the exit.

### B. Option selling and spreads (NIFTY)

**B1. Intraday Short Strangle**
- **Disclosed:** `alpha` built from IV, curvature, Hamiltonian, eigenvalues, entropy and predicted vol; enters when "volatility and time are right"; uses a stop-loss
- **PROXY entry:** composite `alpha = mean(pct_rank(iv_rank), 1 − pct_rank(energy), 1 − pct_rank(oi_entropy))`. Enter after 09:45 when `alpha > 0.7`. Sell OTM CE/PE at about 0.20Δ.
- **Exit:** SL at 1.3× combined premium, or 30% per leg; flat at 15:15

**B2. Expiry Short Strangle**: *disclosed logic*
- **Conditions (all required):**
  1. Low `alpha` (mean-reversion regime)
  2. High close-price gaps
  3. High IV rank
- **Trade:** on expiry day, sell CE at ATM+100 and PE at ATM−100
- **PROXY for condition 2:** gap = `|open − prev close| / ATR` above its 70th percentile

**B3. Lattice Short Straddles / Holonomy's Short Strangles**
- **Disclosed:** a lattice-based decision model (straddle) and a cyclical, pattern-repeating model (strangle). Non-directional; ₹3L minimum capital.
- **PROXY:**
  - Lattice: sell ATM straddle when the binomial-tree expected move for the remaining time is below the straddle premium, i.e. implied move > forecast move.
  - Holonomy: day-of-week × time-of-day seasonality of straddle decay, estimated in-sample. Enter only in the historically best (DOW, time) cells.

**B4. Single Kurtosis Straddle**
- **Disclosed:** carries the short strangle from one expiry to the next, aiming to capture the whole premium decay
- **PROXY filter:** enter only when the rolling 20-day kurtosis of NIFTY returns is below its median (fewer fat-tail days)
- **Hedge:** buy far-OTM wings, turning it into an iron condor, to cap gap risk

**B5. Credit-spread family**
- Stratzy products: Delta-Rotation, Ratio-Ripple, Ratio-Fluxer, Curvature
- **Disclosed:**
  - `alpha` from IV, curvature, Hamiltonian, eigenvalues, entropy and predicted vol
  - `alpha2` from spot returns and changes in IV curvature
  - A trade triggers when `alpha` crosses a threshold. The direction (bull put vs bear call) comes from the signal.
  - The approach is *contrarian*: it fades stretched conditions measured by IV entropy ratios, curvature imbalance and skew.
- **Variants to test:**
  - *Expiry*: enter and hold into expiry
  - *Exit-Early*: take profit at 50–70% of max credit
  - *Overnight*: hold one night; tests the overnight theta vs gap trade-off
  - *Delta-Rotation*: pick the short strike by delta (0.25–0.35Δ) and the wing by width
- **PROXY signal:** `alpha2 = pct_rank(30-min spot return) − pct_rank(Δ iv_curvature)`. If the spot rally is stretched while curvature rises, sell a call spread; mirror the rule for put spreads.

### C. Equity

**C1. Crossover Formula** (monthly, F&O universe): *disclosed logic*
- **Features:** short/long average ratios of price- and volume-derived variables (not just a price MA cross)
- **Selection:** rank all F&O stocks (about 207 in the source description) and hold the top 10% for the month
- **Weighting:** inverse volatility
- **Spec:** ratios `SMA20/SMA200` of close and `SMA20/SMA100` of turnover; z-score each and average; top decile; weights ∝ 1/σ₆₀; rebalance monthly
- **Warning:** use the *point-in-time* F&O list, or you'll get survivorship bias

**C2. Uncorrelated weekly basket**
- **Disclosed:** a weekly basket of uncorrelated stocks
- **PROXY:** among the top 30 momentum names, greedily pick about 8 with pairwise 60-day correlation < 0.5; equal risk weights; rebalance weekly

**C3. Stratzy blog examples** (simple baselines)
- BankNifty mean reversion: buy at the lower Bollinger Band, exit at the mid-band, skip when IV percentile > 80
- Momentum filter: 5-day ROC > 5% and volume above its 20-day average

### D. AlgoTest RA example

**D1. "All-in-One" expiry straddle**
- **Disclosed:** on expiry day, sell the ATM straddle when the *straddle-premium* candle closes below both its VWAP and Supertrend. The aim is to collect the whole straddle premium.
- **Build:** a 1-min (or 5-min) `straddle_px` series. VWAP uses combined option volume. Exit when the candle closes back above VWAP, or at a fixed premium SL.

*Not reconstructable:* Bullion Strategy Automated (MCX). No logic was found publicly. Obvious alternative: a gold/silver ratio pair trade on MCX.

---

## 3. Research-backed ideas that fit our data

**Index options (1-min)**

| # | Idea | Rule sketch | Reference |
|---|---|---|---|
| R1 | 09:20 short straddle baseline | Sell ATM straddle at 09:20, 25–30% SL per leg, exit 15:15. Every other option idea should beat this. | Common Indian retail benchmark |
| R2 | Variance risk premium filter | Sell only when `iv_atm − forecast RV` (HAR-RV on 1-min data) is in its top tercile | Carr & Wu (2009); Bollerslev et al. |
| R3 | India VIX regime switch | VIX percentile < 30 → buy options / debit spreads; > 70 → sell with wings | Sinclair, *Positional Option Trading* |
| R4 | Market intraday momentum | Sign of the 09:15–09:45 return (plus previous close-to-open) predicts the 14:45–15:30 return; trade NIFTY futures or ATM options in the last 30 min | Gao, Han, Li & Zhou (2018), JFE |
| R5 | Expiry pinning | On expiry afternoon, spot drifts toward the max-OI strike. Sell a butterfly centred there after 13:30. | Ni, Pearson & Poteshman (2005) |
| R6 | Skew mean reversion | z-score of 25Δ risk reversal > 2 → sell the rich side's vertical and buy the cheap side's | Kakushadze & Serur, *151 Strategies* §2 |
| R7 | Term structure / calendar | Weekly IV ≫ monthly IV (after events) → short weekly, long monthly calendar | *151 Strategies*; Sinclair |
| R8 | Event IV crush | Sell straddle/iron fly just before RBI policy / Budget / results announcements, exit after the announcement; compare with the implied move | Dubinsky et al. (2019) earnings IV |
| R9 | Futures OI buildup | Classify 5-min bars by price and OI change: long buildup, short buildup, short covering, long unwinding. Trade continuation of long and short buildup. | NSE participant data; Varsity |
| R10 | Put-call parity / basis | Synthetic future (C−P+K) vs actual future. Trade when the deviation exceeds costs. Mostly a data-quality test. | Arbitrage basics |

**Stocks (1-min and daily)**

| # | Idea | Rule sketch | Reference |
|---|---|---|---|
| S1 | Short-term reversal | Buy the prior week's bottom decile of F&O stocks, short the top decile (futures) | Jegadeesh (1990); Lehmann (1990) |
| S2 | 52-week-high momentum | Rank by close / 52-week high; long the top decile, monthly | George & Hwang (2004) |
| S3 | Time-series momentum | NIFTY/BANKNIFTY futures: sign of 12-month (and 3-month) return, vol-targeted | Moskowitz, Ooi & Pedersen (2012) |
| S4 | Low-vol / BAB | Long lowest-beta Nifty-500 quintile, beta-scaled | Frazzini & Pedersen (2014) |
| S5 | Overnight vs intraday split | Measure overnight (close→open) vs intraday returns by stock. Hold the overnight-drift names; fade intraday. | Lou, Polk & Skouras (2019) |
| S6 | Intraday VWAP reversion | Large-caps: fade moves > 2σ from VWAP when volume is not spiking; exit at VWAP | Chan, *Algorithmic Trading* |
| S7 | Sector pairs / stat arb | Banks, IT, auto: Engle–Granger or Kalman-hedge spread on 5-min bars; enter at \|z\| > 2 | Gatev, Goetzmann & Rouwenhorst (2006) |
| S8 | Index lead–lag | 1-min: NIFTY futures vs heavyweights (HDFCBANK, RELIANCE, ICICIBANK); trade the laggard | Microstructure literature |
| S9 | 101 Formulaic Alphas | Run all 101 on the F&O universe; keep the ones with t-stat > 3 after costs, out of sample | Kakushadze (2016) |
| S10 | Turn-of-month | Long NIFTY from the last 4 trading days of the month to day 3 of the next | Lakonishok & Smidt (1988) |
| S11 | Results straddle | Stock options: compare the implied results-day move to realised history; sell when implied > 1.3× historical median | Earnings IV literature |

---

## 4. Backtest checklist for Indian F&O

1. **Contract structure has changed. Split backtests by regime.**
   - Nov-2024 SEBI measures: one weekly expiry per exchange, higher lot sizes, upfront premium collection, and an extra ELM on expiry day
   - BANKNIFTY weeklies ended in Nov-2024
   - The NIFTY weekly expiry day moved from Thursday to Tuesday from Sep-2025
2. **Costs.** Parameterise brokerage, STT, exchange fees, SEBI fees, stamp duty and GST. Rates have changed several times (e.g. STT on options, Oct-2024), so check current rates before trusting any result.
3. **Fills.**
   - Signal on bar *t* close, fill on bar *t+1* open, plus slippage
   - For illiquid strikes, a 1-min "close" can be a stale print. Use bid/ask mid if you have it, and drop minutes with no volume.
4. **Universe.**
   - Use the point-in-time F&O stock list (stocks get added and removed)
   - Skip names in the F&O ban period
   - Stock options are physically settled at expiry, so exit them before expiry
5. **Margin.** Size by SPAN + exposure margin, not premium; hedged positions get margin benefits. Report return on margin.
6. **Overfitting.**
   - Walk-forward optimisation
   - Report the **deflated Sharpe ratio** and **probability of backtest overfitting** (López de Prado)
   - Count every parameter sweep you ran
7. **Tail risk.** Short-vol ideas must be stress-tested on Mar-2020, the Jun-2024 election-result day, and gap-open days. Report the worst day and worst week, not just the Sharpe.

## 5. Suggested build order

1. Data layer: 1-min chain → per-minute features table (§1)
2. R1 baseline and D1 (simple, disclosed logic) → validates the engine and cost model
3. A1 SkewHunter (fully disclosed thresholds) → first "reverse-engineered" test
4. A3 exit-wrapper comparison on the A1/A2 entries
5. B2 and B5 credit spreads with PROXY alphas; R2 VRP filter as an overlay
6. Equity: C1, S1–S3 on the daily data; S7/S8 on the 1-min data

## Sources for §2

- Dhan Algos, Stratzy manager pages: [SkewHunter TSL](https://dhanhq.co/algos/managers/stratzy/skewhunter-tsl/683c633ced2623775f750344), [SkewHunter](https://dhanhq.co/algos/managers/stratzy/skewhunter/683c4a5bed2623775f750340), [Expiry Short Strangle](https://dhanhq.co/algos/managers/stratzy/expiry-short-strangle/67ef94cc9d589eae0aaacdbb), [Intraday Short Strangle](https://dhanhq.co/algos/managers/stratzy/intraday-short-strangle/672ddda758f8d0f97e2d0c25), [Lattice Short Straddles](https://dhanhq.co/algos/managers/stratzy/lattice-short-straddles/672dec4858f8d0f97e2d0c2e), [Holonomy's Short Strangles](https://dhanhq.co/algos/managers/stratzy/holonomys-short-strangles/678f6f119fa2420a7fbe690d), [Single Kurtosis Straddle](https://dhanhq.co/algos/managers/stratzy/single-kurtosis-straddle/67e6f0b74c46f3287d97ca34), [Ratio-Ripple Credit Spread](https://dhanhq.co/algos/managers/stratzy/ratio-ripple-credit-spread-exit-early/697f126e90e1715ab2c37b44), [Delta-Rotation Credit Spread](https://algos.dhan.co/managers/stratzy/delta-rotation-credit-spread-expiry/692811d5b3dc6cfbe85053a2), [Curvature Credit Spread Overnight](https://dhanhq.co/algos/managers/stratzy/curvature-credit-spread-overnight/687d08f09107a80e07401e57), [Index Sniper](https://dhanhq.co/algos/managers/stratzy/index-sniper/672de2fb58f8d0f97e2d0c28), [Fixed RR 1:3](https://dhanhq.co/algos/managers/stratzy/fixed-rr-13-30-sl/6845cc951f9886e2caa9c466), [Burst RR 1:2](https://dhanhq.co/algos/managers/stratzy/burst-rr-12-25-sl/685848b09edddcb829103b9b), [Burst GRID](https://dhanhq.co/algos/managers/stratzy/burst-grid-30-sl/68583ce39edddcb829103b96), [Settle-Down 40% TSL](https://dhanhq.co/algos/managers/stratzy/settle-down-40-tsl/699c0254738c5d8c44dbb3c6), [Crossover Formula Automated](https://dhanhq.co/algos/managers/stratzy/crossover-formula-automated/6720fba916d421e2ca239a96)
- Stratzy blog: [common strategies and examples](https://stratzy.in/blog/common-algo-trading-strategies-and-examples/)
- AlgoTest: [All-in-One multi-indicator options](https://docs.algotest.in/signals/famous-strategies/all-in-one/), [RA algos](https://algotest.in/ra-algo)
- Framework: [NSE empanelled algo providers](https://www.nseindia.com/static/trade/empanelled-algo-providers-exchange), [Zerodha overview of the NSE circular](https://zerodha.com/z-connect/general/a-comprehensive-overview-of-nses-circular-on-the-new-retail-algo-trading-framework), [NSE circular INVG/67858](https://nsearchives.nseindia.com/content/circulars/INVG67858.pdf)
