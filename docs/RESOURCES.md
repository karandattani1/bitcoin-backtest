# Trading & Backtesting Resource Map

Snapshot taken 2026-09-26. Star counts are approximate.

To clone any of these locally, run `scripts/fetch_repos.sh` (see the bottom of this page). Clones land in `external/`, which is gitignored.

---

## 1. OpenAlgo (github.com/marketcalls)

OpenAlgo is an open-source, self-hosted algo-trading platform. It is Python/Flask with a React UI, runs on SQLite, and exposes one REST/WebSocket API across 25+ Indian brokers. Its author (marketcalls) has **152 public repos**. The full list is in `scripts/openalgo_repos.txt`, and the ones worth knowing are grouped below.

### Core platform & SDKs
| Repo | ★ | What it is |
|---|---|---|
| [openalgo](https://github.com/marketcalls/openalgo) | 2.7k | The platform: broker abstraction, order mgmt, TradingView/Amibroker webhooks, sandbox, MCP |
| [openalgo-python-library](https://github.com/marketcalls/openalgo-python-library) | 47 | `pip install openalgo`: REST client, WebSocket feed, and `openalgo.ta` (100+ Numba indicators) |
| [openalgo-node](https://github.com/marketcalls/openalgo-node) / [-go](https://github.com/marketcalls/openalgo-go) / [-rust](https://github.com/marketcalls/openalgo-rust) / [.NET](https://github.com/marketcalls/OpenAlgo.NET) / [Java](https://github.com/marketcalls/OpenAlgo-Java) | – | SDKs in other languages |
| [openalgo-cli](https://github.com/marketcalls/openalgo-cli) | new | Agent-first Go CLI for the OpenAlgo API |
| [openalgo-mcp](https://github.com/marketcalls/openalgo-mcp) | 15 | MCP server so Claude and other agents can trade and query through OpenAlgo |
| [openalgo-desktop](https://github.com/marketcalls/openalgo-desktop) / [-mobile](https://github.com/marketcalls/openalgo-mobile) | – | Tauri desktop app and Flutter mobile app |

### Backtesting & research (most relevant to this repo)
| Repo | ★ | What it is |
|---|---|---|
| [vectorbt-backtesting-skills](https://github.com/marketcalls/vectorbt-backtesting-skills) | 206 | **Claude Code skills** (`/backtest`, `/optimize`, `/strategy-compare`) for VectorBT. Covers crypto (CCXT/yfinance, maker/taker fees, BTC benchmark), 12 strategy templates, walk-forward, and Monte Carlo robustness tests |
| [openalgo-execution-skills](https://github.com/marketcalls/openalgo-execution-skills) | 9 | The same strategy code runs as a VectorBT backtest or live through OpenAlgo |
| [openalgo-indicator-skills](https://github.com/marketcalls/openalgo-indicator-skills) | 18 | Agent skills for 100+ indicators, Plotly/Dash charts, and Numba custom indicators |
| [openengine](https://github.com/marketcalls/openengine) | 16 | Event-driven backtesting and live engine |
| [openstatz](https://github.com/marketcalls/openstatz) | 17 | QuantStats-style tearsheets (HTML, 30+ metrics, Monte Carlo) |
| [openscript](https://github.com/marketcalls/openscript) | 8 | Open trading language: write once, then plot, backtest, and trade |
| [statistical-arbitrage](https://github.com/marketcalls/statistical-arbitrage) | 7 | 16 notebooks covering cointegration, Kalman hedges, Johansen, and validation |
| [emacrossover-autoresearch](https://github.com/marketcalls/emacrossover-autoresearch) / [backtesting-autoresearch](https://github.com/marketcalls/backtesting-autoresearch) | – | An **autonomous agent** that loops: propose params → backtest → keep or discard |
| [historify](https://github.com/marketcalls/historify) | 49 | Full-stack app for downloading and managing historical data |
| [VectorBT-Streamlit](https://github.com/marketcalls/VectorBT-Streamlit) / [VectorBT-Tearsheets](https://github.com/marketcalls/VectorBT-Tearsheets) | – | A simple backtest UI and tearsheet examples |
| [p2c2e/openalgo-backtrader](https://github.com/p2c2e/openalgo-backtrader) | 24 | Community Backtrader ↔ OpenAlgo bridge |

### Agents, charts, data infra
| Repo | What it is |
|---|---|
| [TradingAgent](https://github.com/marketcalls/TradingAgent) | Chat-first trading agent built on Agno and OpenAlgo, with a human confirmation gate on every order |
| [AutoAgent](https://github.com/marketcalls/AutoAgent) | Autonomous intraday agent that works under an approved "mandate" instead of per-trade approval |
| [Agentic-Trader](https://github.com/marketcalls/Agentic-Trader) | Trader built on the OpenAI Agents SDK |
| [openfly](https://github.com/marketcalls/openfly) | A fruit-fly connectome that trades a NIFTY straddle. Experimental, and fun to read |
| [openalgo-charts](https://github.com/marketcalls/openalgo-charts) | WebGL charting library with market profile and orderflow |
| [openalgo-js-indicator-library](https://github.com/marketcalls/openalgo-js-indicator-library) | 497 Pine Script indicators ported to JavaScript |
| [Crypto-Realtime-QuestDB](https://github.com/marketcalls/Crypto-Realtime-QuestDB) / [openquest](https://github.com/marketcalls/openquest) | Real-time tick ingestion into QuestDB with live charts |
| [opengreeks](https://github.com/marketcalls/opengreeks) | Rust options Greeks and IV, 5–180× faster than vollib |
| [trading-journal](https://github.com/marketcalls/trading-journal) | Trading journal app |
| [openalgo-claude-plugin](https://github.com/marketcalls/openalgo-claude-plugin) | Claude Code plugin marketplace for OpenAlgo |

> Note: OpenAlgo is **India-broker focused**, so live execution targets NSE/BSE/MCX. Its research tooling (VectorBT skills, `openalgo.ta`, openstatz, the autoresearch loop) is market-agnostic and works for BTC.

---

## 2. Backtesting frameworks (general)

| Repo | ★ | Best for |
|---|---|---|
| [polakowo/vectorbt](https://github.com/polakowo/vectorbt) | 9.2k | Vectorised: thousands of parameter combos in seconds. **Recommended next step for this repo** |
| [kernc/backtesting.py](https://github.com/kernc/backtesting.py) | 9.0k | Simplest API, with an interactive Bokeh plot and a built-in optimizer |
| [mementum/backtrader](https://github.com/mementum/backtrader) | 23k | Classic event-driven engine. Mature, but no longer actively developed |
| [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade) | – | Crypto bot with backtest, hyperopt, FreqAI (ML), and dry-run/live on Binance and others |
| [jesse-ai/jesse](https://github.com/jesse-ai/jesse) | – | Crypto-focused research, backtest, and live trading framework |
| [nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader) | – | Rust core with Python API. Same code for backtest and live; production-grade |
| [nkaz001/hftbacktest](https://github.com/nkaz001/hftbacktest) | 4.8k | Tick/L2/L3 backtests that model queue position and latency. Binance/Bybit examples |
| [edtechre/pybroker](https://github.com/edtechre/pybroker) | 3.5k | ML-first backtesting with walk-forward and bootstrap metrics |
| [hummingbot/hummingbot](https://github.com/hummingbot/hummingbot) | 20k | Crypto market making and arbitrage bots |
| [stefan-jansen/machine-learning-for-trading](https://github.com/stefan-jansen/machine-learning-for-trading) | 21k | Book code (3rd ed.), from data to live execution |
| [HKUDS/Vibe-Trading](https://github.com/HKUDS/Vibe-Trading) | 34k | Multi-agent LLM trading assistant with backtesting and MCP |
| [atilaahmettaner/tradingview-mcp](https://github.com/atilaahmettaner/tradingview-mcp) | 4.6k | MCP server for TradingView data, screeners, and backtests |
| [wangzhe3224/awesome-systematic-trading](https://github.com/wangzhe3224/awesome-systematic-trading) | 5.2k | A curated list of systematic-trading resources. Good for going deeper |

---

## 3. Jev (TypeSafe AI "System One" model)

**What it is:** a *decision* model, not a text generator. You send a `state` (text or JSON) plus a map of named questions. It returns typed answers with calibrated probabilities, usually in well under a second. Pricing is about $0.042 per 1M input tokens, and output is free. It was in early access as of Sep 2026.

```
POST https://api.typesafe.ai/v1/systemone
{ "model": "jev-latest",
  "state": { ...market snapshot... },
  "questions": {
    "up_12": { "type": "noul",   "instructions": "...", "criteria": {"true": "...", "false": "..."} },
    "regime":{ "type": "choice", ... },   // pick 1 of up to 255 options + probabilities
    "trend": { "type": "score",  ... }    // 2–10 level ordinal scale + probabilities
  } }
→ { "answers": { "up_12": { "noul": 0.54, ... }, ... }, "usage": {...} }
```
Rate limit is about 1200 req/min. Official Python and JS SDKs exist. Docs are at docs.typesafe.ai and jevapi.org (both blocked from this sandbox, so the shape above comes from secondary sources and the adapter code in `egrm07/jev_bitcoin_backtest`).

### Jev trading projects
| Repo | What it is |
|---|---|
| [egrm07/jev_bitcoin_backtest](https://github.com/egrm07/jev_bitcoin_backtest) | **Most relevant to us.** A rigorous BTC/USD study that feeds Jev 48-bar windows in 10 different "representations", including blank and leaky controls, with 14 bps costs and a holdout. **Result: no tradable edge.** Holdout AUC was 0.47–0.50, the best arm returned −15.7% against +25.6% for buy-and-hold, and the whole run cost $2.58. Its caching/spend-cap adapter and question-design notes are worth reusing |
| [justinhe16/trade-jev](https://github.com/justinhe16/trade-jev) | Jev as BUY/SELL/HOLD on NQ L10 order-book data |
| [OpenByteInc/QuantDinger](https://github.com/OpenByteInc/QuantDinger) | 12k★ AI trading OS with Jev integration, plus backtest and paper/live trading |
| [jgottig/jev-bot-trading](https://github.com/jgottig/jev-bot-trading) | Kraken bot with simulator, backtest, and risk layer |
| [jarrodwatts/jev-trader](https://github.com/jarrodwatts/jev-trader) | 2.4k★. One Jev decision per Monad block |
| [arimanyus/warrenduffer](https://github.com/arimanyus/warrenduffer) | Jev ranks the Nifty 50 every 15s, while code handles sizing and stops (Zerodha/Kotak) |
| [myc0576/SmartMoney-Cub](https://github.com/myc0576/SmartMoney-Cub) | **Read-only journal and review harness** using Jev typed judgments. No orders |
| [VGabriel45/polymarket-btc5m-jev-trading](https://github.com/VGabriel45/polymarket-btc5m-jev-trading) | Jev on Polymarket's 5-minute BTC up/down markets |

**Takeaway:** the only rigorous public test found no edge from raw price-direction prediction. Jev is better used as a **classifier or filter** (regime, news/sentiment, "is this setup valid per my rules?", journal tagging) than as the forecaster.

---

## 4. Obsidian

| Repo | What it is |
|---|---|
| [Cursivez/journalit](https://github.com/Cursivez/journalit) | 228★. The most complete Obsidian trading-journal plugin: broker sync, CSV imports, analytics, reviews |
| [bitbonsai/mcpvault](https://github.com/bitbonsai/mcpvault) | Lightweight MCP server scoped to a vault root, so Claude can read and write notes safely |
| [iansinnott/obsidian-claude-code-mcp](https://github.com/iansinnott/obsidian-claude-code-mcp) | Obsidian plugin that exposes the vault to Claude Code |
| [jacksteamdev/obsidian-mcp-tools](https://github.com/jacksteamdev/obsidian-mcp-tools) | Semantic search and Templater prompts over MCP |
| [mingi3314/tradelens](https://github.com/mingi3314/tradelens) | Converts broker trade exports into structured Obsidian notes |
| [MaximSinyaev/obsidian-trading-tracker](https://github.com/MaximSinyaev/obsidian-trading-tracker) | SQLite trade log that exports Dataview-compatible markdown |

Obsidian's value here is that **a vault is just a folder of markdown with YAML frontmatter**. A backtest can write one note per run or trade (params, metrics, equity-curve PNG), and then Dataview queries, graph view, and Claude over MCP all work on those notes.

---

## 5. Build ideas for this repo (ranked by effort/payoff)

1. **Real backtest foundation (small).** Replace the 3-row CSV with multi-year BTC OHLCV (yfinance/CCXT). Port the notebook to VectorBT with realistic fees (~0.1% spot) and a BTC buy-and-hold benchmark. Add the README metrics (CAGR, max DD, win rate, Sharpe) plus walk-forward validation. `vectorbt-backtesting-skills` can do most of this if installed as Claude Code skills.
2. **Obsidian research vault (small–medium).** Every backtest run writes `vault/runs/<date>-<strategy>.md` with frontmatter (params, Sharpe, DD, CAGR, data range) and an equity chart. A Dataview dashboard then ranks runs. Add `mcpvault` so Claude can query "which momentum variants survived walk-forward?"
3. **Autoresearch loop (medium).** Borrow the pattern from `emacrossover-autoresearch`: an agent proposes a strategy variant, backtests it on the train set, checks the holdout, and logs the result as an Obsidian note. The vault becomes the lab notebook, and hard holdout gates keep it honest.
4. **Jev as a regime filter, not a forecaster (medium).** The public evidence says Jev can't call direction. The open question is whether a Jev `choice` answer (trending / ranging / high-vol) or a news-sentiment `score` improves a **momentum strategy we already have**, gating entries only. Reuse the caching and spend-cap adapter from `jev_bitcoin_backtest`, and run blank and leaky controls. It costs a few dollars and produces a publishable yes/no result.
5. **Paper-trading bridge (larger).** Once something survives the gates, run it forward in paper mode, via freqtrade dry-run for crypto or OpenAlgo's sandbox, and journal each trade into the vault.

---

## Fetching the repos

```bash
scripts/fetch_repos.sh              # curated set above (~33 repos, ~1 GB)
scripts/fetch_repos.sh --openalgo   # all 152 marketcalls/OpenAlgo repos (list in scripts/openalgo_repos.txt)
scripts/fetch_repos.sh --all        # both
```
