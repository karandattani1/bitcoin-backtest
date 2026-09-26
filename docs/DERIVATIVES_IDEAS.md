# Indian Derivatives (F&O) Trading Ideas

Snapshot 2026-09-26. This is research, not investment advice.

**Where the ideas come from:**
- **The OpenAlgo repos.** The quant course chapters on derivatives (ch49–58, ch63–64) include computed outputs from live chains. I also used OpenFly's measured NIFTY and straddle facts, the options tooling (`openbull`, `ExpiryFlow`, `expirymanager`, `marginism`, `opengreeks`), and the execution skills.
- **New measurements on NIFTY daily data (2012–2024)** in `research/nifty_derivatives_tests.py`.

No historical option prices were available offline. So the tests below measure the **realized** side; the **implied** side has to be checked on your chain history.

---

## 0. Facts that constrain every idea

| Fact | Value | Source |
|---|---|---|
| Implied > realized (India VIX vs trailing realized) | Mean +1.93 vol pts over a year, and **implied beat realized on 82% of days** | course ch54 output |
| NIFTY return vs VIX change correlation | −0.75. VIX peaked at 27.9 on 30 Mar 2026 | ch54 |
| ATM weekly straddle vs realized day move | About equal on average ("fairly priced") | OpenFly `nifty-market-facts.md` |
| Share of daily variance from the **overnight gap** | **34%** (range 19–45% by year) | test A |
| Expiry-day index range (weekly era, 2019–24) | Thursday **116 bps vs 124 bps** on other days. Expiry days are *not* wilder for the index | test B |
| Tails vs normal (move ÷ prior-night EWMA σ) | 3σ days are **3.7×** more frequent than normal (2.5/yr); 4σ days about **50×** (0.8/yr) | test C |
| Forecastability of tomorrow's high-low range | Out-of-sample R² **0.48** (HAR + today's gap). Top forecast quintile 201 bps vs bottom 79 bps | test D |
| Monday gap variance | **1.78×** a normal weeknight, **not 3×** | test E |
| Budget-day move | Median **1.1σ**, mean 1.6σ (n = 12). Fat tail: 2021 +4.4σ, 2020 −3.7σ | test F |
| Where liquidity sits | Round 500-point strikes hold **62%** of near-money OI; half-strikes are thin | ch56 |
| Leverage and margin | NIFTY futures lot about 8.8×; stock futures about 5.7×. Short ATM straddle about ₹1.9L/lot | ch58, OpenFly |
| Costs | Short straddle round trip about **0.95% of credit** (discount broker, 1 lot) | OpenFly |

**Implication.** Selling premium has a positive *average* edge, but the tails are fat. Most of the "edge" people see in backtests comes from mixing the premium up with tail luck. The ideas below are designed around **when** to be short vol, **how to bound the tail**, and a few **relative-value** trades where the tail is hedged by construction.

---

## 1. Volatility-selling, done with a filter

### 1.1 Forecast-gated intraday straddle/iron-fly on the NIFTY weekly *(highest priority)*

**Premise:** OpenFly showed the ATM straddle is fairly priced *on average*. So the edge can only come from **selecting days**, and test D shows tomorrow's range *is* forecastable (R² 0.48, a 2.5× spread between quintiles).

**Rule:**
- At 09:20, compute the forecast range from the HAR model plus the opening gap. Compare it with the day-move implied by the ATM straddle (straddle premium × √(minutes left today / minutes to expiry)).
- Sell an iron fly (not a naked straddle) only when forecast ÷ implied < a threshold, for example the lowest 40%.
- Square off by 15:15.

**Why intraday:** it skips the 34% of variance that sits in the overnight gap, which is unhedgeable. It also avoids carry margin.

**Test:**
1. Start with OpenFly's synthetic straddle pricer (Black-76 on VIX, calibrated factor about 1.006).
2. Move to real 1-minute chains from `expirymanager` (Fyers) or `ExpiryFlow` (Dhan).
3. Controls: fixed 09:20 entry every day, random-day entry with a matched trade count, and flat.
4. Metric: **net P&L ÷ margin** (use `marginism` for SPAN).

**Kill if:** the gated version does not beat the always-on control out-of-sample after costs.

### 1.2 Weekend theta capture

**Premise:** if option prices decay on calendar days, the Friday close → Monday open window charges about 3 nights of theta. Test E shows the market delivers only about **1.8 nights** of gap variance over the weekend.

**Rule:** sell a delta-hedged ATM iron fly Friday at 15:00 and buy it back Monday at 09:20–09:30. Use the next-week expiry, since NIFTY weekly expiry is now Tuesday and the current week would be too close to expiry.

**The key unknown:** market makers may already "pre-decay" IV on Friday afternoon. Measure the **ATM IV change from Friday 15:00 to Monday 09:30** on chain history. If IV is marked down about 1–2 vol points on Monday morning with no move, the edge is real. If Friday IV is already lowered, there's nothing there.

**Risk:** weekend news gaps. This is exactly the 4σ tail, so wings are mandatory.

### 1.3 VRP harvest on the monthly, with a VIX regime gate and permanent wings

**Rule:** sell a monthly NIFTY iron condor, with short strikes around 1σ and long wings at about 3.5–4σ, sized so the 4σ loss is ≤ X% of capital. Enter only when:
- VIX minus the HAR realized-vol forecast is above its median
- VIX is not rising more than 15% over 5 days
- the term structure is not inverted (front IV below next IV)

**Why the monthly and not weeklies:** lower gamma, smaller stop percentages (OpenFly notes this), and fewer entries, so fewer costs.

**Evidence:** a +1.9-point average VRP and 82% of days positive. The gate exists because VRP compresses exactly when VIX spikes.

**Honest check:** report the result **with the worst 1% of weeks** included (Mar 2020 and the Mar 2026 spike to 27.9).

### 1.4 Expiry-day (0DTE) pin trade

**Premise:** option gamma peaks on expiry day, but the index's realized range on weekly-expiry Thursdays was *lower* than other days (test B). That fits the hedging flows that pin the index near the heavy strikes (ch56: 62% of OI at round strikes).

**Rule:** after 13:30 on expiry day, if spot is within about 0.3σ-remaining of the max-OI round strike and GEX is positive, sell a narrow iron fly centred on that strike and exit by 15:20. `openbull` already has `maxpain`, `gex` and `oitracker` services.

**Test:** on 1-minute index data plus end-of-day OI, measure the distance to the max-OI strike at 13:30 against the distance at the close.

**Regulatory note:** since the 2024 SEBI F&O framework, expiry-day short options carry **extra ELM (+2%)** and calendar-spread margin benefit is removed on expiry day. Margin drag matters here, so verify the current circulars.

---

## 2. Relative value: tail hedged by construction

### 2.1 NIFTY vs SENSEX implied-vol spread (two exchanges, two expiry days)

**Premise:** NSE weekly expiry is Tuesday and BSE (SENSEX) is Thursday. The underlyings are about 0.98 correlated, but their **implied** vols are set by different order flow, and SENSEX options are thinner and more retail-heavy.

**Rule:**
- When the vol spread (same tenor, ATM, adjusted for beta and notional) is above its 90th percentile, sell the rich index's straddle and buy the cheap one's.
- Match vega or gamma notionals, so it stays roughly vega/gamma-neutral.
- Exit when the spread reverts or on the earlier expiry.

**Risk:** basis and liquidity in BFO, different expiry dates (roll the SENSEX leg), and SENSEX strikes that are 100 points apart.

**Data:** BFO chain history. Check whether Definedge carries BFO options history.

### 2.2 Earnings-event straddles on F&O stocks

**Premise:** per stock, compare the **implied earnings move** with that stock's **historical result-day moves**. The implied move is the front straddle minus normal-day straddle decay.

**Rule:**
- Sell when the implied move is well above the historical median, using defined risk (iron fly) and limited to the top 15–20 liquid F&O names (ch56 warns stock options are "a pond").
- Buy when the implied move is below historical.
- Close the day after results.

**Data:** Definedge `getEarningsCalendar`/`getQuarterlyResults` for dates, plus daily history for past result-day moves. Stock options are **physically settled**, so never hold them into expiry.

### 2.3 Light dispersion: index vs top-10 constituents

**Premise:** implied correlation equals index IV compared with the weight-adjusted average of stock IVs. When implied correlation is high (fear), sell index vol and buy the heavyweights' vol. The ten largest NIFTY names are over 50% of the index.

**Constraints:** heavy margin, stock-option liquidity only in the near month ATM, and physical settlement.

**Start with:** monitoring implied correlation daily from chain snapshots. Only trade if its percentile predicts **realized** correlation badly.

### 2.4 Skew trades

**Premise:** OTM put IV runs about 14% against about 11% ATM (ch53).

**Rule:** when put skew (25-delta put IV − ATM IV) is in its top decile, sell 1×2 put ratio spreads or put spreads and buy calls, i.e. a risk reversal against a flat delta. When skew is at the bottom, buy put spreads as cheap tails for the short-vol book in §1.3.

**Test:** skew percentile against subsequent 5–20 day realized downside and skew mean reversion.

---

## 3. Positioning and structure signals (as filters on §1–2)

**3.1 FII index-futures positioning extremes.**
- **Signal:** the FII long/(long+short) ratio in index futures, from NSE participant-wise OI.
- **Use:** extremes, e.g. below 20% long, as a contrarian regime flag. Cut short-put exposure after long streaks, and cut short-call exposure at extreme shorts (squeeze risk).
- **Rule of thumb from ch64:** use **streaks and changes, not levels**, and confirm with price.

**3.2 GEX regime.**
- **Signal:** aggregate gamma exposure from OI (the openbull `gex` service), using the retail-long-options / institutions-short assumption.
- **Hypothesis:** positive GEX leads to lower next-session realized range, which favours §1.1. Negative GEX leads to trend days, where the straddle should be skipped.
- **Test:** add the GEX sign as a feature to the test-D forecast and see whether R² improves.

**3.3 Futures build-up and rollover.**
- **Signal:** long/short build-up, `getFuturesBuildup`, rollover %, and roll cost in carry bps (ch64).
- **Use:** a directional tilt for the §1 trades, e.g. skew the iron fly's strikes toward the build-up direction. Not a standalone strategy.

**3.4 F&O ban-list event study.**
- **Question:** when a stock enters the ban (OI > 95% MWPL), only unwinding is allowed. What do the forward 1/5/10-day returns and realized vol look like after entry and after exit?
- **Why:** ch64 says it can mark either capitulation or a squeeze. Measure it. `getStocksInBanned` gives the current list; history comes from NSE archives.

**3.5 Basis as signal and as parking yield.**
- **Signal:** annualised NIFTY carry (ch50: 5.78% on the example day) against the money-market rate. A rich basis means crowded longs.
- **Yield:** idle margin can earn the cash-futures carry through an arbitrage fund or your own reverse trade.
- **Dividend season:** around Jul–Sep ex-dates the basis narrows, and fair-value errors appear when dividends are mis-forecast.

**3.6 Scheduled event vol (Budget, RBI MPC, results of national elections).**
- **Premise:** test F shows Budget days have a median 1.1σ move but a fat tail (4.4σ in 2021). Result-day moves often front-run on exit-poll or announcement days (2019 result day was just 0.6σ).
- **Rule:** compare the implied event move (event-week straddle minus the normal week) with that distribution. Sell the event only with wings, and prefer **selling the day after** into the IV crush over carrying the event.

---

## 4. Beyond NSE index options

- **MCX crude oil options.** Evening-session US news, such as EIA inventory (Wednesday evening IST) and FOMC, creates scheduled event vol, and the market is less crowded by NIFTY-style sellers. §1.1 and §3.6 can be applied here.
- **USDINR options (NSE CDS).** Low-vol regime with RBI intervention bands. Short strangles are an RBI-policy bet, so treat them as a tail-risk product.

---

## 5. Build order (what I'd do first)

1. **Data:** get 1-minute NIFTY chain history (expired contracts) plus INDIAVIX 1-minute into DuckDB. `expirymanager` (Fyers) is the most complete off-the-shelf pipeline, and ExpiryFlow (Dhan) already has a dynamic-straddle backtester. If Definedge's data covers expired options, use that instead.
2. **One harness, one cost model, return on margin.** Next-bar fills, per-leg costs (the OpenFly cost breakdown), SPAN plus ELM from `marginism`, and stops checked on bar high/low. Reuse OpenFly's controls: random-entry with matched count, fixed-time entry, and flat.
3. **Run §1.1 → §1.2 → §1.3** on the same harness. All three need only NIFTY chain history, and their test statistics share code (the implied-vs-forecast ratio).
4. **Add §3.2 (GEX) and §3.1 (FII) as features** and check whether they add out-of-sample R² to the range forecast. Keep them only if they do.
5. **§2.1 / §2.2** once BFO chains and the earnings calendar are in the store.

## 6. Traps specific to Indian F&O (from the repos)

- **Price options with Black-76 off the synthetic forward**, not Black-Scholes off spot (ch51). Otherwise every IV and Greek is off by the carry.
- **Snap to round strikes.** Half-strikes have a fraction of the liquidity (ch56).
- **One-legged fills leave naked options.** The completion/unwind logic needs the most testing (OpenFly risks list).
- **Stock options are physically settled.** An ITM contract at expiry becomes a full-notional delivery obligation.
- **Lot sizes and expiry weekdays change.** NIFTY 65, BANKNIFTY 30, FINNIFTY 60; NSE weekly expiry is Tuesday (Thursday before Sep 2025), BSE is Thursday. Read them from the symbol master and never hardcode them.
- **OpenAlgo's `optionchain`/`syntheticfuture` returned "No strikes found"** on valid expiries in OpenFly's install, so resolve chains from `expiry` + `search` instead.
- **Backtests at mid or LTP overstate far-strike and stock-option fills.**
