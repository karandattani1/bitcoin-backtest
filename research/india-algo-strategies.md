# Algo trading strategies for Indian markets: research notes

*Compiled 7 Oct 2026. Sources are listed at the end.*

> **How this was gathered.** This sandbox's network policy blocks direct page loads from
> Dhan (`algos.dhan.co`, `dhanhq.co`), Stratzy, X/Twitter, Medium and most blogs. Those
> sources were read through search-engine results instead of the full pages, and GitHub
> repos were read directly. Performance numbers below are **claims made by vendors or
> authors and have not been checked**. Use them to decide what to test, not as evidence that
> something works.

---

## 1. Rules that shape any strategy built in 2026

These are recent changes, and every backtest has to model them or its results won't hold up.

| Change | Detail | Why it matters for a strategy |
|---|---|---|
| **SEBI retail algo framework** (circular Feb 2025, **fully enforced 1 Apr 2026**) | Every algo order is tagged and goes through the broker. **White-box** (transparent rules) algos are registered once with the exchange. **Black-box** providers must be SEBI Research Analysts. Open APIs are banned: you need a client-specific API key plus a **static IP whitelisted** with the broker. Above **10 orders/sec** you must register the strategy. | Running your *own* strategy under 10 OPS through your own API key with a static IP is allowed. Selling or sharing it with others requires empanelment. |
| **Weekly expiries cut** (Sep 2025) | Only **NIFTY (Tuesday)** on NSE and **SENSEX (Thursday)** on BSE still have weekly options. BankNifty, FinNifty and Midcap are **monthly only**, on the last Tuesday. | Any "BankNifty weekly straddle" backtest from before Sep 2025 is now irrelevant. Test on NIFTY and SENSEX weeklies. |
| **Lot sizes** (Jan 2026) | NIFTY **65** (was 75), BankNifty **30**, FinNifty 60, Midcap 120. Contract value must be ₹15–20 lakh. | Position sizing and the minimum capital per lot. |
| **STT hike** (Budget 2026, effective 1 Apr 2026) | Options premium **0.15%** (was 0.1%), futures **0.05%** (was 0.02%), exercise 0.15%. | Hits high-frequency, small-edge strategies hardest, such as re-entry straddles and scalping. Put these exact rates in the cost model. |
| **Intraday position limits** (from Oct 2025, expiry penalties from Dec 2025) | ₹5,000 cr net / ₹10,000 cr gross per entity, checked by random intraday snapshots. This followed the Jane Street case. | Irrelevant at retail size, but it changed how expiry-day moves behave, so expiry data from 2023–24 is suspect. |
| **SEBI F&O study** | **91%** of individual F&O traders lost money in FY25 (total net loss ₹1.06 lakh cr). About 96% of prop and FPI profits came from algos. | The edge sits in disciplined, systematic, low-cost execution, not in discretionary option buying. |

---

## 2. Strategy catalog

### 2A. Option-selling / volatility strategies (the bulk of Indian retail algos)

These rest on the **volatility risk premium**: Nifty implied volatility tends to sit above realised volatility. Academic work on NIFTY/India VIX data from 2021 to 2025 found a VRP that was consistently positive and significant. Short straddles, VIX futures shorts and delta-hedged straddles all made money in normal regimes, with **losses concentrated in volatility shocks**.

| # | Strategy | Rules (as published) | Notes |
|---|---|---|---|
| 1 | **9:20 short straddle** | Sell ATM CE and PE at 09:20. Each leg has an SL of 25–30% of its premium. Square off at 15:15. | The most-copied retail algo in India, popularised by Jitendra Jain ("the 9:20 straddle trader", 90k+ followers). The logic is to sell while opening IV is still high and let it settle. Claimed figures: 25% SL gives a 65–70% win rate, but average losses are 2–3× average wins. Real results are said to come in 15–30% worse than backtests. |
| 2 | **Optimised 9:20 straddle** | Same as #1, with filters meant to avoid V, N and M-shaped days (whipsaws that hit one leg's SL and then the other's). | Medium post claims over 80% a year on BankNifty (Algotest backtest). Treat as heavily overfitted. |
| 3 | **Combined-premium SL straddle** | Sell ATM straddle. The SL is on the *combined* premium (e.g. +30–40%), not on each leg. | Has fewer whipsaw exits than per-leg SL, but the tail loss is bigger. |
| 4 | **Rolling / re-entry straddle** | Sell ATM straddle. SL at ±200 pts on the underlying. After an SL, re-enter at the new ATM, at most 3 times a day, between 09:20 and 15:20. | Re-entries add trades, so the higher STT bites. Algotest has a variant that flips long after the SL is hit. |
| 5 | **Time-of-day straddle grid** | Run the same straddle at 09:20, 09:30, 10:15, 11:00 and so on, and compare. | Mostly useful for research: it shows which entry times carry the edge. |
| 6 | **Expiry-day ATM straddle** | Enter around 09:30 on expiry. SL at 40–50% of premium, target 60–70% decay by about 14:30. Convert to an iron condor if a leg comes under pressure. | Theta decays fastest on expiry. Now only possible on NIFTY (Tue) and SENSEX (Thu). |
| 7 | **Iron fly / iron condor** | Short ATM straddle plus long OTM wings. Intraday iron fly or overnight iron condor. | Risk is defined, so margin is lower. One trader's rule of thumb: use iron flies when ATR is "cooling". |
| 8 | **Short strangle** | Sell OTM CE and PE, chosen by delta (e.g. 16–30Δ) or by points away. | Lower premium, but a wider breakeven. |
| 9 | **Overnight / BTST short straddle or credit spread** | Enter near the close and exit the next morning, to capture overnight theta. | Stratzy's "Bullion Strategy" is an overnight short straddle using "Rangetrap" logic. Gap risk is the main danger. |
| 10 | **VIX / IV-percentile regime filter** (overlay) | Sell premium only when IV percentile is above roughly 50–80. Cut size when India VIX is above 20. Sit out around events (budget, RBI, elections). | Cheap to add, and it often improves any of #1–9. |

### 2B. What is on Dhan Algos (the Stratzy "whitebox" list)

Dhan Algos is a marketplace limited to exchange-approved providers, mostly SEBI-registered RAs. **Stratzy** is the largest provider, with 43+ algos. Most need at least ₹1 lakh; Single Kurtosis Straddle needs ₹2.5 lakh. Names and published descriptions:

| Algo | Type | Published logic |
|---|---|---|
| Bullion Strategy Automated | Overnight short straddle | "Rangetrap" mechanics: sell when the index is expected to stay inside a range. |
| Single Rangetrap Straddle | Nifty non-directional selling | Single-entry version of Rangetrap. |
| Single Kurtosis Straddle | Short straddle | Trades on kurtosis of the return distribution, i.e. sells when tail risk is low. |
| SkewHunter | Nifty option *buying*, directional, held until EOD | Enters only when **IV skew across strikes** and **volume/OI flow skew** point the same way. Uses an adaptive trailing SL. |
| Index Sniper | Option buying | "Strongest market moves with surgical entries"; no detail published. |
| Fixed RR 1:3 (30% SL) | Option buying | Fixed 1:3 risk/reward with a 30% premium SL. |
| Zen Credit Spread Overnight | Credit spread | Mean-reversion signals from volatility and volume. |
| Curvature Credit Spread Overnight | Credit spread | Reads liquidity flow, "viscosity" and IV-curve **curvature** across strikes, and bets the curve rebalances. |
| Delta-Rotation Credit Spread Expiry | Nifty expiry credit spread | An "alpha" built from IV, IV curvature, option-chain "Hamiltonian"/entropy/eigenvalues and predicted vol, combined with spot momentum. |
| Damper Credit Spread / Ratio-Fluxer Credit Spread Expiry | Credit spreads | No logic published. |
| Stocks Select, High Volatility Stocks, Wealth Magnet, Dividend Dons | Equity | Stock selection and rotation baskets. |

**What you can take from these:** the language is marketing, but it points to signals you can build yourself from a full option chain:
1. **IV skew** (25Δ put IV − 25Δ call IV) and its change
2. **IV smile curvature** (the second derivative of IV against strike)
3. **OI and volume imbalance** across strikes (put-call ratio by strike, change in OI)
4. **Realised vs implied vol gap** (VRP) and return-distribution **kurtosis**

Use these as filters on whether to sell or buy premium.

### 2C. Directional / intraday index strategies

| # | Strategy | Rules | Notes |
|---|---|---|---|
| 11 | **Opening Range Breakout (ORB)** | Mark the high/low of 09:15–09:30 (15-min) on spot. Go long above the high, short below the low, with the SL at the opposite side or a fixed amount. Execute with futures or ATM options. | Published BankNifty backtests show much of the edge disappears once slippage and charges are included. Always model costs. |
| 12 | **Intraday trend-following** (EMA/Supertrend/ADX) | e.g. a fast/slow EMA cross on 5-min bars with a Supertrend filter. Exit at EOD. | Old Marketcalls Supertrend reports on Nifty futures: win rate about 40%, positive only because winners run. |
| 13 | **"Highest Open / Lowest Open" reversal** | Intraday reversal on stocks that open at the day's extreme. | Open-source repo wired to Kite. |
| 14 | **Multi-factor setup scoring with vol-sized positions** | Score technical setups and size by ATR. Trade futures or weekly options. | Example: `nifty-algo-trading-bot` (asyncio, defaults to paper trading). |

### 2D. Swing / positional equity strategies (lower costs, no F&O STT)

| # | Strategy | Rules | Evidence |
|---|---|---|---|
| 15 | **Momentum rotation** (the index method) | Universe Nifty 200/500. Rank by **6- and 12-month returns divided by 12-month volatility**. Hold the top 30–50. Rebalance semi-annually (NSE index) or monthly/quarterly. | NSE whitepaper (Apr 2005 to Feb 2026, annualised): **Nifty200 Momentum 30 19.2% vs 15.1%** for Nifty 200; Midcap150 Momentum 50 23.0% vs 17.2%; Nifty500 Momentum 50 21.9% vs 18.9%. This is the best-documented edge in the whole list. |
| 16 | **Momentum with regime filter** | #15, plus moving to cash or liquid funds when Nifty is below its 200-DMA (or market breadth is weak). | Substack backtests show smaller drawdowns, at the cost of some CAGR. |
| 17 | **RSI(2) mean reversion (Connors)** | Trade only when price is above the 200-DMA. Buy when RSI(2) is below 10, exit when the close is above the 5-DMA. Use liquid large caps and indices. | Classic rules. Reported to work on Nifty, BankNifty and large caps, and to fail in downtrends. |
| 18 | **Connors RSI (3,2,100)** | Same idea with a composite oscillator. | Same as above. |
| 19 | **Quality + momentum blend** | e.g. the Nifty500 Multicap Momentum Quality 50 index methodology. | Index factsheets are available. |

---

## 3. Using Claude with a live broker account (MCP)

Claude can trade a real Indian broker account through MCP servers. The options as of Oct 2026:

| Server | Who built it | Can trade? | Notes |
|---|---|---|---|
| **Kite MCP** (`https://mcp.kite.trade/mcp`) | Zerodha, official, open source (`zerodha/kite-mcp-server`) | **The hosted version excludes destructive and trading tools.** A self-hosted copy exposes `place_order`, `modify_order`, `cancel_order` and the GTT tools. | Tools include `get_quotes`, `get_ltp`, `get_ohlc`, `get_historical_data`, `get_holdings`, `get_positions`, `get_margins` and order/GTT management. To connect Claude Desktop: `npx mcp-remote https://mcp.kite.trade/mcp`. A tool can be switched off with `EXCLUDED_TOOLS`. |
| **Dhan MCP** (`docs.dhanhq.co/mcp`) | Dhan, official, hosted | **Yes, built for execution**: place/modify/cancel, super orders (target + SL), margin checks, alerts that trigger linked orders. | Also returns option chains, depth and historical candles. The most execution-focused official broker MCP. |
| Upstox MCP (`ravikant1918/mcp-server-upstox`) | Community | Read-only | Market data, technicals, account info. |
| **OpenAlgo** (marketcalls) | Open source (AGPL), self-hosted | Yes | One API over 30+ brokers (Zerodha, Dhan, Angel, Upstox, Fyers, Shoonya, Flattrade…). Has an MCP layer and TradingView/Amibroker/ChartInk webhooks. **The best base for running one strategy across brokers.** |
| TurtleStack Lite | Community | Yes | One MCP over Kite, Groww, Dhan and AngelOne. |
| Indian-Option-MCP (`pdthekd`) | Community | Analytics | Option chains, Greeks, 34+ strategy payoffs, OI, IV smile, max pain. |
| nse-research-mcp | Community | Research | NSE + Yahoo fundamentals, FII/DII flows, option chains. Designed to sit alongside Kite MCP. |
| indian-trading-skills (`ajeeshworkspace`) | Community | n/a | Claude **Skills** for F&O analysis, flows, breadth and a "backtest-expert". Uses Kite MCP. |
| india-trade-cli ("Vibe Trading", `hopit-ai`) | Community, MIT | Yes (Zerodha, Fyers) plus a paper mode | 7 LLM analyst agents debate bull vs bear. 58-strategy library with walk-forward backtests. |
| Claude-Trader (`avmkmk`), DHAN AI TRADER (dhanbot.in) | Community / commercial | Yes | Bots that call Claude to make trade decisions. |

**Evidence on letting an LLM trade on its own:** it has done poorly so far. Claude was **down 30.8%** in the Alpha Arena 2025 real-money test, and lost 3.3% in a separate 14-day stocks-and-crypto test. A $50k experiment in 2026 used Claude only for *research* under rules set by a human, with no autonomous execution.

**Practical takeaway:** use Claude and MCP for **research, monitoring, coding and position reporting**, not for deciding trades live. Let a **deterministic, backtested rule engine** decide entries and exits. That is also what SEBI's white-box model assumes: the rules have to be documented and replicable.

---

## 4. Recommended build plan for this repo

The repo is a Python/pandas backtester. A suggested order:

1. **Cost model first.** Brokerage, the 2026 STT rates, exchange fees, SEBI fee, stamp duty, GST, and slippage of 0.5–1 tick per leg for options. Model the NIFTY lot size of 65.
2. **Data.** NIFTY/SENSEX 1-min spot and option chains (from broker historical APIs: Kite `get_historical_data`, Dhan historical candles, or a paid vendor), plus daily NSE bhavcopy for equities and India VIX.
3. **Strategies to build first**, ordered by evidence quality and simplicity:
   - **#15/16 momentum rotation**, end-of-day only. The strongest published evidence, low cost, no F&O.
   - **#1 9:20 NIFTY straddle** plus the **#10 VIX/IV filter**. It's the benchmark everyone compares against. Test it only on post-Sep-2025 Tuesday-expiry data, and on older data as a sensitivity check.
   - **#6/#7 expiry-day iron fly** on NIFTY Tue and SENSEX Thu.
   - **#11 ORB** on NIFTY futures, as a check of whether any edge survives after costs.
   - Later: **option-chain signals** like Stratzy's (IV skew, curvature, OI imbalance) used as filters.
4. **Validation.** Walk-forward or out-of-sample split, parameter-stability heatmaps, and stress periods (Mar 2020, Jun 2024 election day, Jan–Feb 2025 sell-off).
5. **Execution.** OpenAlgo or broker SDK, a static IP, under 10 OPS, kill-switch and MTM square-off. Claude/MCP is used read-only for daily reports.

---

## Sources

**Dhan / Stratzy**
- [Dhan Algos marketplace](https://algos.dhan.co/) · [Stratzy algos on Dhan](https://algos.dhan.co/managers/stratzy) · [Understanding Dhan Algos](https://dhan.co/blog/feature-updates/understanding-dhan-algos/) · [DhanHQ launch post on X](https://x.com/DhanHQ/status/1982670727150031016)
- [Bullion Strategy Automated](https://dhanhq.co/algos/managers/stratzy/bullion-strategy-automated/6720fc4c16d421e2ca239a97) · [SkewHunter](https://dhanhq.co/algos/managers/stratzy/skewhunter/683c4a5bed2623775f750340) · [Delta-Rotation Credit Spread Expiry](https://algos.dhan.co/managers/stratzy/delta-rotation-credit-spread-expiry/692811d5b3dc6cfbe85053a2) · [Single Kurtosis Straddle](https://dhanhq.co/algos/managers/stratzy/single-kurtosis-straddle/67e6f0b74c46f3287d97ca34) · [Single Rangetrap Straddle](https://algos.dhan.co/managers/stratzy/single-rangetrap-straddle/6845a2e71f9886e2caa9c462) · [Index Sniper](https://dhanhq.co/algos/managers/stratzy/index-sniper/672de2fb58f8d0f97e2d0c28) · [Damper Credit Spread](https://dhanhq.co/algos/managers/stratzy/damper-credit-spread/68c9b755c7ed8fff5c5de9af) · [Ratio-Fluxer](https://dhanhq.co/algos/managers/stratzy/ratio-fluxer-credit-spread-expiry/698075eaf867bf12b20442e5)
- [Stratzy strategy list](https://stratzy.in/algo-trading-strategies?filterBy=all) · [Stratzy: common algo strategies](https://stratzy.in/blog/common-algo-trading-strategies-and-examples/)

**Regulation and market structure**
- [Zerodha: SEBI algo regulations explained](https://zerodha.com/z-connect/business-updates/explaining-the-latest-sebi-algo-trading-regulations) · [AlgoBulls: SEBI rules 2025–26](https://algobulls.com/blog/industry-insights-and-updates/sebi-new-algotrading-regulations-for-retail-investors-2026) · [Mastertrust: white box vs black box](https://www.mastertrust.co.in/blog/white-box-vs-black-box-algo-strategy-what-sebi-s-rules-mean-for-your-swing-trading-strategies-1)
- [Business Standard: Thursday expiry ends](https://www.business-standard.com/markets/news/nse-bids-adieu-to-thursday-expiry-as-dates-swap-come-into-effect-explained-125082800635_1.html) · [Strota expiry schedule 2026](https://strota.in/india-expiry-schedule)
- [HDFC Sky: lot size revision Jan 2026](https://hdfcsky.com/news/nse-revises-market-lot-sizes-for-major-index-derivatives-effective-january-2026) · [5paisa: STT hike from 1 Apr 2026](https://www.5paisa.com/news/stt-hike-on-fo-to-take-effect-from-april-1-amid-rising-options-activity)
- [Moneylife: SEBI study, 91% lost money](https://moneylife.in/article/91-percentage-of-retail-traders-lost-money-in-derivatives-losses-in-fo-surged-41-percentage-to-rs105-lakh-crore-in-fy25-sebi-study/77613.html) · [Outlook Business: intraday index option limits](https://www.outlookbusiness.com/markets/sebi-ups-intraday-limits-for-index-options-but-tightens-grip-on-scrutiny)
- [Bloomberg: How India built (and broke) the world's biggest options casino](https://www.bloomberg.com/features/2026-india-options-market-boom-bust-sebi/)

**Strategy write-ups and backtests**
- [Optimised 920 straddle (Medium)](https://medium.com/@amit179.iitk2/optimized-920-straddle-strategy-to-get-more-than-80-return-annually-e977453dca80) · [AlgoTest: backtest the 920 straddle](https://docs.algotest.in/Time-Based-Algo-Trading/how-to-backtest/backtest-920-Straddle/) · [AlgoTest: rolling straddles](https://algotest.in/blog/how-to-backtest-rolling-straddles-with-indicators/) · [QuintalMind: time-based straddle](https://www.quintalmind.com/blog/time-based-straddle-strategy-nifty-options) · [AlgoTradersLab](https://www.algotraderslab.com/) · [OpenAlgo: intraday rolling straddles](https://docs.openalgo.in/trading-platform/python/intraday-rolling-straddles)
- [ORB backtest on BankNifty](https://financewithsai.com/orb-backtest-on-banknifty/) · [Wright Research: expiry strategies](https://www.wrightresearch.in/blog/top-5-options-expiry-strategies-for-intraday-traders-a-complete-guide/) · [@Prakashplutus on X: iron fly / condor regimes](https://x.com/Prakashplutus/status/2046786423379169666) · [@AlgoTest_in on X](https://x.com/AlgoTest_in)
- [SSRN: VRP on Nifty 50](https://papers.ssrn.com/sol3/Delivery.cfm/6876580.pdf?abstractid=6876580&mirid=1) · [India VIX as a regime signal](https://dev.to/shaktitiwari/india-vix-mastery-how-to-use-fear-as-a-trading-signal-4ghk)
- [NSE momentum whitepaper 2026](https://www.niftyindices.com/docs/default-source/indices/nifty200-momentum-30/momentum-strategy-whitepaper_2026.pdf) · [Momo India: reducing momentum drawdowns](https://momoindia.substack.com/p/backtest-reducing-momentum-drawdowns) · [Wright Research: rebalancing frequency](https://www.wrightresearch.in/blog/optimal-rebalancing-frequency-how-often-rebalance-momentum-portfolio/)
- [RSI(2) for Indian markets](https://onetradejournal.com/strategies/rsi-2-strategy) · [Connors RSI](https://onetradejournal.com/indicators/connors-rsi) · [Marketcalls Supertrend backtests](https://www.marketcalls.in/tag/backtest-report)

**GitHub**
- [buzzsubash/algo_trading_strategies_india](https://github.com/buzzsubash/algo_trading_strategies_india) (0920 straddles, strangles, MTM/trailing SL, Kite auto-login)
- [JabirMJ1/nifty-algo-trading-bot](https://github.com/JabirMJ1/nifty-algo-trading-bot) · [anirudhatalmale6-alt/nifty-banknifty-intraday-trend-algo](https://github.com/anirudhatalmale6-alt/nifty-banknifty-intraday-trend-algo) · [abdussamikhan1999-stack/money-making](https://github.com/abdussamikhan1999-stack/money-making) · [TARUN17999/BankNifty-back-testing](https://github.com/TARUN17999/BankNifty-back-testing) · [GitHub topic: banknifty](https://github.com/topics/banknifty)

**Claude / MCP**
- [zerodha/kite-mcp-server](https://github.com/zerodha/kite-mcp-server) · [Zerodha: connect Kite to AI assistants](https://zerodha.com/z-connect/featured/connect-your-zerodha-account-to-ai-assistants-with-kite-mcp) · [Dhan MCP docs](https://docs.dhanhq.co/mcp/) · [MadeForTrade: official Dhan MCP](https://madefortrade.in/t/official-dhan-mcp-server-for-direct-cloud-ai-integration-advanced-analysis/89843) · [Tradehull: Claude + Dhan MCP](https://tradehull.com/trade-smarter-with-claude-ai-using-dhan-mcp-ai-powered-trading-workflow/)
- [Upstox MCP](https://github.com/ravikant1918/mcp-server-upstox) · [OpenAlgo docs](https://docs.openalgo.in/llms-full.txt) · [OpenAlgo MCP architecture](https://docs.openalgo.in/developers/design-documentation/41-mcp-architecture) · [TurtleStack Lite](https://github.com/turtlehq-tech/turtlestack-lite) · [Indian-Option-MCP](https://github.com/pdthekd/Indian-Option-MCP) · [nse-research-mcp](https://github.com/sanjeev0291/nse-research-mcp) · [indian-trading-skills](https://github.com/ajeeshworkspace/indian-trading-skills) · [india-trade-cli](https://github.com/hopit-ai/india-trade-cli) · [Claude-Trader](https://github.com/avmkmk/Claude-Trader) · [DEV: best Indian market MCPs 2026](https://dev.to/govind_sisara/indian-stock-market-mcp-the-best-mcp-servers-for-nse-bse-data-2026-p28)
- [Algotrader.ch: can Claude trade for you?](https://algotrader.ch/ai-trading/claude-ai-trading/) · [ExplainX: Claude portfolio experiment](https://explainx.ai/blog/claude-portfolio-autopilot-ai-trading-experiment-august-2026) · [DHAN AI TRADER](https://dhanbot.in/)
