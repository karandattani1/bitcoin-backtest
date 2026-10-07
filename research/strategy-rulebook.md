# Strategy rulebook: option-chain signals and testable rules

*Companion to [india-algo-strategies.md](india-algo-strategies.md). Written 7 Oct 2026.*

> **Read this first.**
> - Rules marked **[Derived]** are my reconstruction from Stratzy/Dhan's public one-line
>   descriptions. They are **not** Stratzy's actual code, which isn't published.
> - Rules marked **[Published]** are taken from public write-ups.
> - Every number here (thresholds, SL %, lookbacks) is a **starting default to calibrate in the
>   backtest**, not a tested value. Part 4 explains how to calibrate without overfitting.

---

## Part 1: Data each rule needs

| Data | Granularity | Fields |
|---|---|---|
| NIFTY / SENSEX spot and near futures | 1-min OHLCV | open, high, low, close, volume, futures OI |
| Option chain (current weekly + next weekly + monthly) | 1-min snapshots (≥ 5-min is the minimum usable) | strike, CE/PE: LTP, bid, ask, volume, OI, IV, delta |
| India VIX | 1-min and daily | close |
| Event calendar | daily | RBI policy, Union Budget, election results, US FOMC/CPI, index expiry dates, holidays |

If the vendor doesn't supply IV or delta, compute them with Black-76 on the futures price, using
the T-bill rate and time to expiry in years measured in trading minutes.

**Notation**
- `F` = futures price, `K` = strike, `k = ln(K/F)` = log-moneyness
- `IV(Δ)` = IV interpolated at a given delta (25Δ put = delta −0.25, 25Δ call = delta +0.25)
- `z(x, n)` = (x − mean of the last n values) / standard deviation of the last n values
- "ATM strike" = the listed strike nearest F

---

## Part 2: Signal definitions

These are the building blocks. Each one produces a number. The rules in Part 3 combine them.

### S1. IV level and IV rank
- `ATM_IV` = average of the ATM CE and PE IV (or India VIX as a proxy)
- `IVR = (ATM_IV − min₂₅₂) / (max₂₅₂ − min₂₅₂)`, i.e. IV rank over 1 year of daily closes
- `IVP` = % of the last 252 days on which ATM_IV was below today's value
- **Reading:** IVP > 60 means premium is rich (favours selling). IVP < 20 means premium is cheap (favours buying or not selling).

### S2. Volatility risk premium (implied vs actual volatility)
- `RV10` = 10-day close-to-close realised vol, annualised (√252 × stdev of log returns).
  The Parkinson high-low estimator is an alternative.
- `VRP = ATM_IV − RV10` and `VRP_ratio = ATM_IV / RV10`
- **Reading:** VRP_ratio > 1.2 means options are priced above recent actual movement, so selling has an edge.
  VRP_ratio < 1.0 means the market is moving more than options price in, so **don't sell naked premium**.

### S3. Skew (how IV differs between puts and calls)
- `RR25 = IV(25Δ put) − IV(25Δ call)`, the 25-delta risk reversal. In India it is normally positive (puts richer).
- `RR25_z = z(RR25, 60 days)` for daily signals, or the z-score versus today's 09:30 value for intraday.
- **Reading:**
  - RR25_z > +1.5 means put skew has steepened: the market is paying up for downside protection (fear).
  - RR25_z < −1.5 means calls are bid relative to puts: upside chasing or a short squeeze.
  - Skew moving **in the same direction as price** (spot falling while RR25 rises) confirms the move.
    Skew moving **against price** suggests the move is fading.

### S4. Smile curvature (how the IV curve bends)
- `BF25 = (IV(25Δ put) + IV(25Δ call)) / 2 − ATM_IV`, the 25-delta butterfly: how rich the wings are relative to ATM.
- Alternative: fit `IV(k) = a + b·k + c·k²` across the strikes inside ±5% moneyness. Then `b` is the skew slope and `c` the curvature.
- `BF25_z = z(BF25, 60 days)`
- **Reading:**
  - High BF25 (rich wings) → sell the wings: a strangle or iron condor rather than a straddle.
  - Low BF25 (cheap wings) → sell ATM and buy the cheap wings for protection: an iron fly.
  - A sharp intraday jump in curvature means someone is buying tail protection, so reduce short exposure.

### S5. Open-interest structure
- `PCR_OI` = Σ put OI / Σ call OI over the strikes within ±5% of F
- `CallWall` = strike above F with the highest call OI. `PutWall` = strike below F with the highest put OI.
- `ΔOI_strike` = OI now − OI at 09:15 for each strike. `CallWall_new` and `PutWall_new` = the strikes with the biggest fresh writing today.
- **Reading:**
  - PCR_OI > 1.3 means heavy put writing (sellers expect support), mildly bullish.
  - PCR_OI < 0.7 means heavy call writing, mildly bearish.
  - Walls act as a likely range on expiry day. A wall that **shifts** (e.g. CallWall rolls up a strike) signals a trend.

### S6. Futures price-OI build-up (a classic Indian F&O read)
Compare the futures price change and OI change over the last N bars (e.g. 15 min):

| Price | OI | Label | Bias |
|---|---|---|---|
| ↑ | ↑ | Long build-up | Bullish |
| ↓ | ↑ | Short build-up | Bearish |
| ↑ | ↓ | Short covering | Bullish, short-lived |
| ↓ | ↓ | Long unwinding | Bearish, short-lived |

### S7. Volume-flow imbalance across strikes
There is no public aggressor-side data, so approximate it per strike for each bar:
`signed_vol = volume × sign(LTP − previous LTP)`.
- `CallFlow` = Σ signed_vol over OTM calls within 3 strikes of ATM. `PutFlow` = the same for OTM puts.
- `FlowImb = (CallFlow − PutFlow) / (|CallFlow| + |PutFlow|)`, which ranges from −1 to +1
- `VolOI_ratio` per strike = volume today / OI. A ratio > 1 on OTM strikes means fresh speculative activity.
- **Reading:** FlowImb > +0.4 sustained for 3 or more bars means aggressive call buying (bullish). < −0.4 is the bearish mirror.

### S8. Range and tail state ("Rangetrap" / "Kurtosis" ideas)
- `ATR_ratio = ATR(5) / ATR(20)` on daily bars. < 0.8 means the range is compressing.
- `Kurt20` = excess kurtosis of the last 20 days of daily log returns (or the last 5 days of 5-min returns).
  Low kurtosis means few outsized moves recently.
- `InsideDay` = today's open is inside yesterday's high-low range. `NR7` = yesterday had the narrowest range of the last 7 days.
- **Reading:** compression combined with low kurtosis favours range-selling. NR7 is a warning that a **breakout may follow**, which is risky for sellers.

### S9. Opening behaviour
- `Gap% = (open − previous close) / previous close`
- `OR15` = 09:15–09:30 high-low range. `OR15_pct = OR15 / open`, compared against its own 20-day median.
- `VWAP` = intraday VWAP on futures

### S10. Calendar and event filter
- `EventDay` = RBI policy, Budget, election results, or the day after a major US event. **No new short-premium entries on these days.**
- `DTE` = trading days to expiry, `ExpiryDay` = DTE == 0

---

## Part 3: Strategy rules

### Global risk rules (apply to every strategy)
- **R1 Position size:** the maximum loss per trade at its stop is ≤ 1% of capital. Lots = floor(1% capital / (SL points × lot size)).
- **R2 Daily kill switch:** if account MTM ≤ −2% of capital, square off everything and stop for the day.
- **R3 Weekly kill switch:** if the week's loss reaches −5%, trade half size until a new equity high.
- **R4 No naked short premium** when IVP < 20, VRP_ratio < 1.0, India VIX > 25, or EventDay. Defined-risk structures are still allowed.
- **R5 Hard exit time** for intraday strategies: 15:15. No new entries after 14:45, except for strategies designed for the close.
- **R6 Costs** use the 2026 schedule: STT 0.15% on option premium sold and 0.05% on futures sold, plus exchange fees, SEBI fee, stamp duty, GST, brokerage and slippage of 1 tick per leg (2 ticks on expiry after 14:00).
- **R7 Execution limits:** stay under 10 orders/sec, use the registered static IP, and send exits as limit orders with market protection.

---

### A. Volatility selling (non-directional)

#### A1. 9:20 short straddle **[Published]**
- **Entry:** 09:20, sell the ATM CE and ATM PE of the nearest weekly (NIFTY Tuesday expiry or SENSEX Thursday expiry).
- **Stops:** each leg has an SL at +30% of its entry premium. Variant A1b: after one leg's SL hits, move the other leg's SL to its entry price.
- **Exit:** 15:15, or when the SLs are hit.
- **Filters:** R4. Optionally require VRP_ratio > 1.1.

#### A2. Combined-premium straddle **[Published]**
- Same entry as A1. The SL is on the combined premium at +25%.
- Optional trailing: once combined profit reaches 30%, trail the SL to lock in 50% of the peak profit.

#### A3. Re-entry straddle **[Published]**
- Same as A1 with per-leg SL at 25%. After the **both-legs** SL, re-enter at the new ATM, at most 2 re-entries, and only before 13:30.
- The extra trades pay more STT. Test whether the strategy survives R6.

#### A4. VRP-filtered straddle **[Derived: core vol-premium idea]**
- **Trade only if** IVP ≥ 50 **and** VRP_ratio ≥ 1.2 **and** RR25_z < +1.5 (no panic skew).
- Entry 09:30, sell ATM straddle. Combined SL at +25%. Exit 15:15.
- If BF25_z > +1 (rich wings), switch to the **A6 strangle**. If BF25_z < −1 (cheap wings), switch to the **A5 iron fly**.

#### A5. Iron fly, expiry day **[Published + derived wing choice]**
- **Day:** ExpiryDay only (NIFTY Tuesday, SENSEX Thursday). Entry 09:45.
- Sell ATM CE + PE. Buy wings at ATM ± (1.0 × the combined ATM premium), rounded to a strike.
- **Prefer this when** BF25_z < 0, because the wings are cheap to buy.
- Target: 50% of credit. SL: loss of 1.0× credit. Exit 15:10.

#### A6. Delta strangle / iron condor **[Published]**
- Sell the 20Δ CE and 20Δ PE (nearest weekly, DTE 1–3). Optionally buy 7Δ wings to make it an iron condor.
- **Prefer this when** BF25_z > 0 (rich wings) and S5 walls sit outside the short strikes.
- Adjustment: if either short leg's delta exceeds 0.40, close it and re-sell at 20Δ on the same side, at most once.
- SL: total position loss reaches 1.5× credit. Exit by 15:15 on expiry, or hold to expiry if it's an iron condor.

#### A7. OI-wall strangle, expiry day **[Derived]**
- Entry 10:30 on ExpiryDay.
- Sell the CE at CallWall and the PE at PutWall, provided each is at least 0.5% away from F and has at least ₹8 premium.
- **Exit early if** a wall shifts toward spot by 1 or more strikes (fresh OI rolls) or spot trades through a wall by 0.15%.
- Otherwise hold to 15:10.

#### A8. "Rangetrap" overnight straddle **[Derived from Stratzy "Bullion / Rangetrap"]**
- **Conditions at 15:10:** ATR_ratio < 0.8, InsideDay true, |Gap%| of the last 3 days < 0.5%, Kurt20 < 1.0, no EventDay tomorrow, and US VIX not up more than 10% today.
- Sell the ATM straddle on the **next** weekly (DTE ≥ 2), or a 25Δ strangle as a variant.
- **Exit next day:** 09:25 or 10:00, whichever does better in the test. Emergency exit: if the opening gap > 0.8%, close at 09:16.
- Size at half of R1, because of gap risk.

#### A9. "Kurtosis" straddle **[Derived from Stratzy "Single Kurtosis Straddle"]**
- Sell the ATM straddle at 09:30, **only if** Kurt20 < its 1-year 30th percentile **and** OR15_pct < its 20-day median.
- The idea is to sell when recent returns have been well-behaved and the open is calm.
- Single entry, combined SL at +20%, exit 15:15.

---

### B. Credit spreads (directional bias with defined risk)

#### B1. Skew mean-reversion credit spread **[Derived from Stratzy "Zen / Damper"]**
- **Bearish-reversal setup** (sell a call spread): RR25_z < −1.5 (calls unusually bid) **and** spot is more than 1 ATR(14) above its 20-EMA **and** VolOI_ratio on OTM calls > 1.
  Sell the 30Δ CE and buy the CE 2 strikes higher.
- **Bullish-reversal setup** (sell a put spread): RR25_z > +1.5 **and** spot is more than 1 ATR below its 20-EMA **and** PCR_OI is rising.
  Sell the 30Δ PE and buy the PE 2 strikes lower.
- Overnight hold to the next day at 11:00, or until 50% of credit is captured. SL: spread value reaches 2× credit.

#### B2. Curvature credit spread **[Derived from Stratzy "Curvature"]**
- Track the fitted curvature `c` (S4). When c_z > +2, a wing on one side is unusually rich.
- If the excess sits on the **put** wing (the put-side IV residual is larger), sell an OTM put spread at about 20Δ.
- If it sits on the **call** wing, sell an OTM call spread.
- Exit when c_z returns below 0.5, at 50% profit, or at the next day's close. SL: 2× credit.

#### B3. Expiry "delta-rotation" credit spread **[Derived from Stratzy "Delta-Rotation"]**
- ExpiryDay, entry between 10:00 and 12:00.
- Score = sign(FlowImb) + sign(S6 build-up bias) + sign(spot − VWAP) + sign(−ΔRR25 since 09:30). Each term is +1 or −1.
- Score ≥ +3 → sell an ATM−1 put spread. Score ≤ −3 → sell an ATM+1 call spread.
- Re-evaluate every 30 min. If the score flips sign, close and **rotate** to the opposite side, at most 2 rotations.
- Exit at 15:10.

#### B4. OI-wall bias spread **[Derived]**
- At 09:45, if PutWall_new (fresh put writing) is 1 or more strikes closer to spot than CallWall_new, and PCR_OI > 1.1, sell a put spread just below PutWall. Mirror for calls.
- Exit when the wall breaks (spot closes a 5-min bar beyond it) or at 15:10.

---

### C. Option buying (directional; low win rate, needs large winners)

#### C1. SkewHunter-style breakout buy **[Derived from Stratzy "SkewHunter"]**
- Between 09:45 and 13:30, all of these must line up for a **long call**:
  1. FlowImb > +0.4 for 3 consecutive 5-min bars
  2. RR25 has fallen at least 1 vol point since 09:30 (calls getting bid)
  3. S6 shows long build-up or short covering
  4. Spot > VWAP and above the OR15 high
  5. IVP < 70 (premium isn't already expensive)
- Mirror the conditions for a **long put**.
- Buy the ATM or 1-strike ITM option on the nearest weekly.
- SL at −30% of premium. Once the trade is +40%, trail the SL to max(entry, peak − 25%) — that's the adaptive part.
- Exit at 15:00. At most 2 trades a day.

#### C2. Fixed 1:3 option buy **[Published]**
- Any entry trigger (e.g. C1's or the D1 ORB). SL −30% of premium, target +90%. No trailing.
- Mainly useful as a baseline for comparing exit rules.

#### C3. Gap-and-flow continuation **[Derived]**
- |Gap%| > 0.6% and the first 15-min candle closes in the gap's direction and FlowImb agrees → buy ATM in the gap's direction at 09:31.
- SL at the OR15 opposite extreme in spot terms, mapped to premium. Target 2R. Exit 11:30.

---

### D. Futures / intraday directional

#### D1. Opening Range Breakout **[Published]**
- OR = 09:15–09:30 on NIFTY futures. Long on a 5-min close above the OR high; short on a close below the OR low.
- SL at the OR midpoint. Target 2× OR range, or exit 15:10. One trade a day.
- **Filters:** OR15_pct below its 20-day median (a tight OR breaks better) and S6 agrees with the direction.

#### D2. VWAP + build-up trend **[Derived]**
- Long when spot > VWAP, S6 = long build-up, and RR25 is falling. Short is the mirror.
- SL 0.3% from entry. Trail by the 5-min 20-EMA. Exit 15:10.

#### D3. EMA/Supertrend intraday **[Published]**
- 5-min Supertrend(10,3) direction combined with 9/21 EMA alignment. Enter on the flip. Exit on the opposite flip or 15:10.

---

### E. Positional equity (cash segment; no F&O STT)

#### E1. Momentum rotation **[Published: NSE index method]**
- Universe: Nifty 200 (or Nifty 500 with ₹20 cr+ median daily turnover).
- Score = average of z(6M return / 12M vol) and z(12M return / 12M vol). Leave out the last month of returns as a variant.
- Hold the top 20–30, equal-weighted. Rebalance monthly. Keep a holding unless it drops out of the top 40 (a buffer to cut turnover).

#### E2. Momentum with regime filter **[Published variants]**
- E1, but hold only when Nifty 50 is above its 200-DMA **and** more than 50% of the universe is above its own 200-DMA.
- Otherwise move to a liquid fund or Nifty 1D ETF.

#### E3. RSI(2) mean reversion **[Published: Connors]**
- Nifty 100 stocks above their 200-DMA. Buy when RSI(2) < 10. Exit when the close is above the 5-DMA, or after 10 days. At most 5 positions.

#### E4. Quality + momentum blend **[Published: Nifty500 Multicap MQ 50 idea]**
- Rank by an average of momentum score (E1) and quality score (ROE, low debt/equity, earnings stability). Quarterly rebalance.

---

## Part 4: How to test these without fooling yourself

1. **Data split:** develop on Jan 2021 – Dec 2024. Hold out Jan 2025 – today, and touch the holdout once.
   For the weekly-option strategies, report results **separately for after Sep 2025** (Tuesday expiry, single weekly per exchange).
2. **Calibration:** vary each threshold ±25% and look at a heatmap. A rule is only worth keeping if a **broad plateau** of parameter values is profitable, not just one spike.
3. **Walk-forward:** 12-month train / 3-month test windows, rolled forward.
4. **Report** CAGR, max drawdown, Calmar, win rate, average win/loss, worst day, worst week, and the share of P&L from the top 5 days. If most of the P&L comes from a few days, the edge is fragile.
5. **Filter value:** for each [Derived] filter (VRP, skew, curvature, OI, kurtosis), compare the base strategy with and without it. Keep the filter only if it improves Calmar out of sample.
6. **Paper trade** for at least 4 weeks on live data before using real capital.

---

## Part 5: Final strategy list

| # | Strategy | Category | Instrument | Holding | Key signals | Source | Build priority |
|---|---|---|---|---|---|---|---|
| A1 | 9:20 short straddle | Vol selling | NIFTY/SENSEX weekly | Intraday | Time, R4 | Published | **1** (baseline) |
| A2 | Combined-premium straddle | Vol selling | NIFTY/SENSEX weekly | Intraday | Combined SL | Published | 2 |
| A3 | Re-entry straddle | Vol selling | NIFTY/SENSEX weekly | Intraday | Re-entry | Published | 3 |
| A4 | VRP-filtered straddle | Vol selling | NIFTY weekly | Intraday | S1, S2, S3, S4 | Derived | **1** |
| A5 | Expiry iron fly | Vol selling, defined risk | NIFTY Tue / SENSEX Thu | Intraday | S4, expiry | Published + derived | **1** |
| A6 | Delta strangle / iron condor | Vol selling | NIFTY weekly | 1–3 days | S4, S5, delta | Published | 2 |
| A7 | OI-wall expiry strangle | Vol selling | NIFTY/SENSEX expiry | Intraday | S5 | Derived | 2 |
| A8 | Rangetrap overnight straddle | Vol selling | NIFTY next weekly | Overnight | S8, S10 | Derived (Stratzy) | 3 |
| A9 | Kurtosis straddle | Vol selling | NIFTY weekly | Intraday | S8, S9 | Derived (Stratzy) | 3 |
| B1 | Skew mean-reversion spread | Credit spread | NIFTY weekly | Overnight | S3, S5, S7 | Derived (Stratzy Zen/Damper) | 2 |
| B2 | Curvature credit spread | Credit spread | NIFTY weekly | 1–2 days | S4 | Derived (Stratzy Curvature) | 3 |
| B3 | Expiry delta-rotation spread | Credit spread | NIFTY/SENSEX expiry | Intraday | S3, S6, S7, VWAP | Derived (Stratzy Delta-Rotation) | 2 |
| B4 | OI-wall bias spread | Credit spread | NIFTY weekly | Intraday | S5 | Derived | 3 |
| C1 | SkewHunter-style buy | Option buying | NIFTY weekly | Intraday | S1, S3, S6, S7, VWAP | Derived (Stratzy SkewHunter) | 2 |
| C2 | Fixed 1:3 option buy | Option buying | NIFTY weekly | Intraday | Exit template | Published | 3 |
| C3 | Gap-and-flow continuation | Option buying | NIFTY weekly | Intraday | S7, S9 | Derived | 3 |
| D1 | Opening range breakout | Futures | NIFTY futures | Intraday | S6, S9 | Published | 2 |
| D2 | VWAP + build-up trend | Futures | NIFTY futures | Intraday | S3, S6 | Derived | 3 |
| D3 | EMA/Supertrend | Futures | NIFTY futures | Intraday | Trend indicators | Published | 3 |
| E1 | Momentum rotation | Equity | Nifty 200/500 stocks | Monthly | Momentum score | Published (NSE) | **1** |
| E2 | Momentum + regime filter | Equity | Nifty 200/500 stocks | Monthly | 200-DMA, breadth | Published | **1** |
| E3 | RSI(2) mean reversion | Equity | Nifty 100 stocks | 2–10 days | RSI(2), 200-DMA | Published (Connors) | 2 |
| E4 | Quality + momentum | Equity | Nifty 500 stocks | Quarterly | Momentum, quality | Published | 3 |

**Priority key:** 1 = build first (strong evidence or a needed baseline), 2 = next, 3 = later or exploratory.

**Data cost decides the order.**
- The E-series needs only daily equity data.
- A1, A2 and A5 need intraday prices for just the ATM strikes and wings, plus S1/S2/S8–S10.
- The full-chain signals (S3–S7, which drive B1–B4, C1, D2 and the A4/A6/A7 switches) need minute-level history of the whole option chain. That is the most expensive data to buy, so it can wait until a baseline is working.
