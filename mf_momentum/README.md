# Momentum in Mutual Funds: which lookback works best (3m, 6m, 1y, 2y)?

An empirical study on **Indian open-ended mutual funds, 2006–2026**, covering every SEBI category
(equity, hybrid, debt, index/ETF, FoF), plus a short review of the academic evidence.

## TL;DR

| Question | Answer |
|---|---|
| Which lookback has the strongest raw signal? | **Short: 3m–6m.** Gross excess returns shrink steadily as the lookback gets longer (3m > 6m > 12m), and the decay is fastest in equity. |
| Best single choice overall? | **A blend of 3m + 6m + 12m returns (average rank).** It has the highest t-stat and rank-IC in equity and hybrid at almost every holding period, and it is more stable than any single window. |
| Does 2y (24m) work? | **Yes, but only for diversified active equity** (Flexi, Multi, Focused, Large & Mid). There it picks up persistent manager skill and low costs more than momentum. It is weak or negative for Mid Cap, Value/Contra, Balanced Advantage and Multi Asset. |
| Is the classic 12-1 (skip last month) better? | **No.** It is the weakest window in almost every group. NAVs don't show the 1-month reversal that individual stocks do, so skipping the last month just discards the freshest information. |
| Can you trade it after costs? | **Only with annual rebalancing.** The 3m signal needs monthly or quarterly switching, and a 1% exit load turns its gross alpha of +1.5–2.3% into a net −1.2% to −2.7%. With annual rebalancing (no exit load, LTCG tax) the edge is **+0.5–1.0% p.a. in equity**, and only marginally significant. |
| Where does momentum matter most? | **Small Cap, Sectoral/Thematic, Value/Contra, Multi Asset**, and ranking across *all* equity funds pooled (that is style/sector rotation). Least: **Large Cap and index funds/ETFs**, where funds in the same category barely differ. |
| Debt funds? | The "winners keep winning" pattern is very significant (t ≈ 3–10), but it is mostly **persistently lower expense ratios** plus carry. It is not momentum you can use for timing. The lookback barely matters, and in Credit Risk the top funds are exactly the ones that blow up in default events (2018–20). |

**Practical rule for equity funds:** once a year, rank funds within their category on a **blend of 3m/6m/12m
returns**. If you prefer one window, use **6m–12m for small/mid/sectoral** and **12m–24m for flexi/multi/focused**.
Hold the top quintile for at least 12 months.

---

## 1. What the literature says

* **Stocks:** Jegadeesh & Titman (1993) found the strongest momentum with **3–12 month** formation periods (the
  6m/6m portfolio is the canonical one). They skip the most recent month because individual stocks reverse over
  a 1-month horizon. Over **2–5 years** stock returns *reverse* (De Bondt & Thaler, 1985).
* **Mutual funds:** Hendricks, Patel & Zeckhauser (1993, "hot hands") found that persistence lasts
  **about 1 year** and is strongest with a ~4-quarter evaluation window. Carhart (1997) showed that most 1-year
  fund persistence is explained by the stock-momentum factor and expenses, and that it fades after about a year.
  The one durable effect is that **poorly performing, high-cost funds stay bad**.
  Bollen & Busse (2005) found persistence on **quarterly** windows that disappears at longer horizons.
  Grinblatt, Titman & Wermers (1995) documented that funds themselves trade on momentum.
* **Industry / sector momentum** (Moskowitz & Grinblatt, 1999) is strongest at short lookbacks and does not show
  the 1-month reversal. This is why sector funds and pooled cross-category ranking favour 3m–6m.
* **Persistence scorecards** (S&P SPIVA India / US) consistently find that few top-quartile funds remain top
  quartile over 3–5 years. Long-window "star" selection rarely works.

The data below for Indian funds matches this literature closely.

## 2. Data & method

* **Data:** AMFI daily NAV archive (mirror: `captn3m0/historical-mf-data`), month-end NAVs from Apr-2006 to
  Oct-2026. It includes funds that were later **merged or closed**, so there is no survivorship bias.
  * Universe: **open-ended, Regular plan, Growth option** (2,951 schemes). Direct plans start in 2013 and would
    duplicate the same portfolios. IDCW/dividend options were dropped because payouts distort NAV returns.
  * Categories come from AMFI's current classification, collapsed into 30+ peer groups. Funds that closed before
    the 2018 SEBI re-categorisation carry the old labels ("Growth", "Income") and form their own groups.
  * Data-error filter: monthly moves beyond ±60% (equity), ±30% (hybrid) and ±25% (debt) are discarded.
* **Signal:** trailing total return over **3m, 6m, 12m, 24m**, the **12-1m** variant (skip the latest month),
  and a **blend** (average percentile rank of 3m, 6m and 12m).
* **Portfolio:** each month, within each peer group (at least 10 funds with full history), buy the
  **top quintile** equal-weighted and hold for **H = 1, 3, 6, 12 months**, using overlapping
  Jegadeesh–Titman cohorts.
* **Benchmark:** the equal-weighted average of *all* eligible funds in the same peer group, so the result
  measures fund *selection* and not market timing.
* **Metrics:** annualised excess return, Newey-West t-stat (12 lags), hit rate, top-minus-bottom quintile
  spread, rank IC (Spearman correlation of the signal with the next-H-month return), and turnover.
  Net returns subtract a **1% exit load** on every switch made within 12 months (the equity and hybrid norm).
* Sub-periods: 2007–2017 and 2018–2026 (after SEBI re-categorisation).

## 3. Results

### 3.1 Averages across peer groups (full period)

Excess return of the top quintile vs the category average, % p.a. Each cell is gross / *net of exit load*, with
the average t-stat in brackets.

| Asset class | Hold | 3m | 6m | 12m | 24m | 12-1m | **blend** |
|---|---|---|---|---|---|---|---|
| Equity | 1m | 2.32 / *−2.68* (2.4) | 2.08 / *−1.39* (2.2) | 1.49 / *−0.95* (1.8) | 1.43 / *−0.32* (1.6) | 1.15 / *−1.30* (1.5) | 2.32 / *−1.30* (**2.7**) |
| Equity | 3m | 1.65 / *−1.23* (2.0) | 1.56 / *−0.46* (1.9) | 1.14 / *−0.25* (1.5) | 1.17 / *+0.16* (1.4) | 0.86 / *−0.54* (1.2) | 1.79 / *−0.23* (**2.4**) |
| Equity | 12m | 0.72 (1.5) | 0.38 (0.7) | 0.45 (0.8) | **0.84** (1.2) | 0.32 (0.7) | 0.75 (1.2) |
| Hybrid | 3m | 1.00 / *−1.74* (2.2) | 1.10 / *−0.82* (2.2) | 0.91 / *−0.45* (1.7) | 0.50 / *−0.46* (1.3) | 0.86 / *−0.50* (1.5) | 1.08 / *−0.87* (2.2) |
| Hybrid | 12m | **0.78** (2.1) | 0.61 (1.6) | 0.49 (1.0) | 0.33 (1.0) | 0.42 (0.9) | 0.67 (1.6) |
| Debt | 3m | 0.57 (3.3) | 0.57 (3.4) | 0.50 (3.1) | 0.50 (3.2) | 0.45 (3.0) | 0.55 (3.2) |
| Debt | 12m | 0.41 (3.5) | 0.35 (3.4) | 0.37 (3.0) | 0.31 (2.7) | 0.35 (3.0) | 0.36 (3.4) |

(Averages are across the individual SEBI peer groups, excluding the pooled universes. Details are in
`results/summary_tables.md`.)

What the table shows:

1. **Shorter lookbacks give stronger raw signals**, and the alpha decays quickly. With 1m holding, equity alpha
   goes 2.3% (3m) → 2.1% (6m) → 1.5% (12m). With 12m holding, all windows fall to roughly 0.3–0.8%.
2. **Turnover decides whether you can trade it.** Only 28% of the 3m top-quintile funds are still in the top
   quintile 3 months later, against 65% for 12m and 75% for 24m. With a 1% exit load, the 3m signal on quarterly
   rebalancing loses about 1.2% p.a. net. Only the 24m window survives quarterly rebalancing, and only barely.
3. **The blend is the most robust choice.** Its rank IC is the highest or close to it in every asset class
   (equity IC ≈ 0.12–0.13, compared with 0.09–0.12 for the single windows).
4. **12-1m (skipping the last month) never helps** for funds.

### 3.2 Annual rebalance (no exit load): excess % p.a. (t-stat), equity & hybrid peer groups

| Peer group | 3m | 6m | 12m | 24m | 12-1m | blend | Best |
|---|---|---|---|---|---|---|---|
| Large Cap | 0.36 (1.4) | 0.35 (1.2) | 0.39 (1.0) | 0.52 (1.2) | 0.51 (1.4) | 0.36 (1.0) | 24m (weak) |
| Large & Mid Cap | 0.99 (2.3) | 0.78 (1.5) | 0.52 (1.0) | **1.32 (2.1)** | 0.48 (0.9) | 0.53 (0.9) | 24m / 3m |
| Mid Cap | 0.05 | −0.14 | −0.33 | −0.39 | −0.48 | 0.20 | none |
| Small Cap | 0.73 (1.3) | 0.24 | 0.65 (1.2) | 0.72 (1.1) | 0.52 | **0.84 (1.4)** | blend |
| Multi Cap | 0.71 | 0.51 | 1.34 (1.6) | **2.02 (2.0)** | 1.13 | 0.97 | 24m |
| Flexi Cap | 0.99 (1.9) | 0.53 | 1.36 (2.2) | **1.96 (3.0)** | 1.29 (2.0) | 1.42 (2.5) | 24m |
| Focused | 0.54 | −0.08 | **1.43 (2.5)** | 1.37 (2.1) | 1.13 (2.1) | 1.04 (2.2) | 12m–24m |
| Value/Contra | **1.29 (2.6)** | 0.73 | −0.49 | −0.44 | −0.64 | 0.16 | 3m |
| ELSS | 0.69 (2.6) | 0.49 | 0.31 | 0.56 | 0.21 | **0.78 (2.1)** | blend / 3m |
| Sectoral/Thematic | 1.36 (1.9) | 0.54 | 0.65 | **2.13 (1.5)** | 0.41 | 1.56 (1.3) | 24m / 3m |
| Index Funds/ETFs | 0.39 | 0.66 | 0.62 | 0.66 | 0.65 | 0.42 | none (≈ costs) |
| **All equity pooled** | **1.23 (2.4)** | 0.76 | 0.47 | 1.35 (1.8) | 0.30 | 1.09 (1.5) | 3m / 24m |
| Aggressive Hybrid | 0.62 (1.8) | 0.48 | 0.46 | **0.88 (1.9)** | 0.28 | 0.70 (1.7) | 24m |
| Balanced Advantage | 0.41 | 0.07 | −0.39 | −0.54 | −0.32 | −0.06 | none |
| Multi Asset | **2.18 (2.5)** | 1.67 | 2.08 | −0.19 | 1.58 | 2.27 (2.0) | 3m / blend |

CAGR of the top quintile compared with the category average over the same funds and months (annual rebalance):

| Group | 3m | 6m | 12m | 24m | blend |
|---|---|---|---|---|---|
| All equity pooled | 13.7% vs 12.1% | 12.5% vs 11.5% | 12.0% vs 11.5% | 13.3% vs 11.8% | 12.8% vs 11.5% |
| Small Cap | 16.9% vs 15.9% | 17.1% vs 16.8% | 18.6% vs 17.8% | 19.0% vs 18.1% | 18.9% vs 17.8% |
| Flexi Cap | 11.9% vs 10.8% | 10.2% vs 9.6% | 14.6% vs 12.8% | 15.3% vs 13.0% | 14.6% vs 12.8% |
| Sectoral/Thematic | 14.1% vs 12.4% | 12.4% vs 11.5% | 12.2% vs 11.4% | 14.5% vs 12.1% | 13.2% vs 11.4% |
| Large Cap | 12.0% vs 11.6% | 11.3% vs 10.8% | 11.3% vs 10.7% | 11.3% vs 10.5% | 11.2% vs 10.7% |
| Mid Cap | 15.0% vs 14.7% | 14.0% vs 13.9% | 13.5% vs 13.8% | 13.8% vs 14.1% | 14.2% vs 13.8% |

(The comparison months differ by lookback because a 24m signal needs 2 years of history.)

### 3.3 Two patterns by category

* **Style- and sector-driven groups favour short windows (3m–6m):** Small Cap, Value/Contra, Sectoral/Thematic,
  Multi Asset, and pooled equity. Funds in these groups differ mainly in *what* they hold, so ranking them is
  sector/factor momentum, which is a short-horizon effect.
* **Diversified, manager-driven groups favour long windows (12m–24m):** Flexi Cap, Multi Cap, Focused,
  Large & Mid, and Aggressive Hybrid. Here a 2-year record identifies durable process and cost advantages. The
  2018–2026 sub-period keeps Flexi (+1.5%) and Multi (+2.0%) positive on the 24m window.
* **Large Cap and index funds:** no lookback adds much (≤0.5% p.a.). Funds in these categories are close to
  the index and to each other, and most of the gap between them is the expense ratio.

### 3.4 Stability (sub-periods, annual rebalance)

* 2007–2017: long windows (24m) dominate in Flexi, Focused, Small Cap, Sectoral and pooled equity.
* 2018–2026: short windows (3m–6m or the blend) dominate in Mid, Small, Value and pooled equity. Sectoral is a
  tie between 3m and 24m. Long windows still
  lead in Flexi and Multi Cap. Large Cap and index-fund momentum is flat to negative.
* The **blend** is positive in most groups in both sub-periods. The exceptions are Mid Cap and Value in
  2007–17 and index funds in 2018–26. It is never the worst window by much, and that consistency is the main
  reason it is the recommended default.

### 3.5 Debt funds

Every lookback works about equally well (excess 0.3–0.6% p.a., t ≈ 3–10 in Liquid, Money Market, Ultra Short
and Overnight), so this is **expense-ratio and carry persistence**, not momentum. A 12m or 24m window, or
simply looking at the expense ratio, captures it just as well. In **Credit Risk**, chasing the top performers
earns about +0.9% p.a. until a default (IL&FS 2018, DHFL 2019, Franklin Templeton 2020). Momentum in debt is
largely compensation for that credit risk.

## 4. Caveats

* The benchmark is the category average, not the index. The results say whether momentum helps you *choose
  funds within a category*, not whether the funds beat Nifty.
* Regular plans only. Direct plans have about 0.5–1% lower costs, which shifts levels but not rankings.
* Categories are AMFI's latest labels applied to the full history. Some funds changed mandate at the 2018
  re-categorisation.
* Several peer groups have only 15–25 funds, so a quintile is 3–5 funds. Treat t-stats of about 2 as suggestive
  only, and note that testing 6 lookbacks × 4 holding periods × 30+ groups makes some "best" cells luck.
* Short-term capital gains tax (holdings under 12 months for equity) is not modelled. It strengthens the case
  for annual rebalancing.

## 5. Reproduce

```bash
git clone --depth 1 --filter=blob:none --no-checkout https://github.com/captn3m0/historical-mf-data
# check out only the last few files of each month (~1,000 files, ~600 MB), then:
python build_panel.py historical-mf-data/data out/      # month-end NAV panel + categories
python backtest.py out/ results/                        # all lookbacks × holds × groups
python report_tables.py > results/summary_tables.md
```

Outputs: `results/results.csv` (every group × lookback × hold × period), `results/summary_tables.md`,
`results/fund_groups.csv` (scheme → peer group mapping).
