# Legitimate Sources: Trading, Derivatives, Quant Research

Everything listed here is free and legal, or can be bought or borrowed legally. The list is grouped by use.
Items marked **(free)** can be downloaded legally from the author, publisher or institution.

## 1. Strategy databases and idea mines

| Source | What it is | Why it's useful |
|---|---|---|
| [Quantpedia](https://quantpedia.com/screener/) | Screener of 900+ strategies taken from academic papers (partly free) | Each entry links to the original paper, with Sharpe, volatility and holding period |
| [Papers With Backtest](https://paperswithbacktest.com/) | Strategies from papers, with code | Quick path from paper to backtest |
| **(free)** Kakushadze & Serur, *151 Trading Strategies* (SSRN 3247865) | Book-length catalogue covering options, futures, stocks, vol and more | Every strategy is written as formulas, which suits a 1-min options dataset |
| **(free)** Kakushadze, *101 Formulaic Alphas* (arXiv 1601.00991) | 101 real WorldQuant alphas, written as formulas | Can be applied directly to NSE stock OHLCV data |
| [Open Source Asset Pricing](https://www.openassetpricing.com/) (Chen & Zimmermann) | Code and data for about 200 published cross-sectional anomalies | Replication code for the equity factor ideas |
| [SSRN Financial Economics Network](https://www.ssrn.com/index.cfm/en/fen/) | Working papers | Search "option return predictability", "0DTE", "intraday momentum" |
| [arXiv q-fin](https://arxiv.org/list/q-fin/recent) | Preprints: Trading & Market Microstructure, Portfolio Mgmt, Computational Finance | ML and microstructure ideas |
| [NBER working papers](https://www.nber.org/papers) | Academic finance papers | Factor and behavioural research |

## 2. Free research from practitioners

- **(free)** [AQR research library](https://www.aqr.com/Insights/Research): momentum, value, carry, trend-following, "Betting Against Beta", "Time-Series Momentum"
- **(free)** [Man Group / Man Institute](https://www.man.com/insights): trend-following and volatility-selling studies
- **(free)** [Alpha Architect blog](https://alphaarchitect.com/blog/): readable summaries of academic papers
- **(free)** [Robeco quant research](https://www.robeco.com/en-int/insights): low-vol and factor investing
- **(free)** [CFA Institute Research Foundation](https://rpc.cfainstitute.org/research/foundation): full monographs, free PDFs (risk parity, factor investing, alternative data)
- **(free)** [Hudson & Thames](https://hudsonthames.org/) articles and the open-source `arbitragelab` / `mlfinlab` docs: pairs trading, stat arb, meta-labelling
- **(free)** Marcos López de Prado's papers on SSRN: backtest overfitting, deflated Sharpe ratio, PBO. **Read these before trusting any backtest.**

## 3. India-specific (NSE, SEBI, NISM)

- **(free)** [NSE Market Pulse](https://www.nseindia.com/static/research/publications-reports-nse-market-pulse): monthly review with participant-wise F&O data and research summaries
- **(free)** NSE Working Paper series (NSE → Research → Publications): academic papers on Indian microstructure, expiry-day effects and option pricing
- **(free)** SEBI F&O studies ([Sep-2024 press release](https://www.sebi.gov.in/media-and-notifications/press-releases/sep-2024/updated-sebi-study-reveals-93-of-individual-traders-incurred-losses-in-equity-fando-between-fy22-and-fy24-aggregate-losses-exceed-1-8-lakh-crores-over-three-years_86906.html); a FY25 update came out in July 2025). They show who makes money: proprietary traders and FPIs, mostly as algorithmic option sellers. That tells you which side of the trade has the structural edge.
- **(free)** SEBI circular (4 Feb 2025) "Safer participation of retail investors in Algorithmic trading", plus NSE circulars NSE/INVG/67858, 69255, 72657 and 73992: the white-box/black-box rules
- **(free)** [NSE empanelled algo providers list](https://www.nseindia.com/static/trade/empanelled-algo-providers-exchange)
- **(free)** Zerodha Varsity: options theory, option Greeks, trading systems, and the Risk Management & Trading Psychology module
- NISM Series VIII (Equity Derivatives) and XV (Research Analyst) workbooks: cheap and official; useful for contract specs and regulatory nuance
- **Data:** NSE bhavcopy archives (EOD F&O and cash), NSE participant-wise OI (FII/DII/Pro/Client), India VIX history

## 4. Books (buy, borrow from a library, or use O'Reilly/Perlego subscriptions)

**Options and volatility**
- Euan Sinclair, *Volatility Trading*, *Option Trading*, *Positional Option Trading*. The most practical option books available.
- Sheldon Natenberg, *Option Volatility and Pricing*
- Colin Bennett, *Trading Volatility*. The author has made this free on his site in the past; check that first.
- Nassim Taleb, *Dynamic Hedging*
- Jim Gatheral, *The Volatility Surface*
- Kris Abdelmessih, *Moontower* (free newsletter and notes on vol trading)

**Systematic trading**
- Robert Carver, *Systematic Trading*, *Leveraged Trading*, *Advanced Futures Trading Strategies*. His blog (qoppac.blogspot.com) and the `pysystemtrade` repo are free.
- Ernest Chan, *Quantitative Trading*, *Algorithmic Trading*, *Machine Trading*
- Andreas Clenow, *Following the Trend*, *Stocks on the Move*
- Kevin Davey, *Building Winning Algorithmic Trading Systems*
- Perry Kaufman, *Trading Systems and Methods*

**Quant investing and ML**
- Antti Ilmanen, *Expected Returns* and *Investing Amid Low Expected Returns*
- Grinold & Kahn, *Active Portfolio Management*
- Marcos López de Prado, *Advances in Financial Machine Learning*
- Stefan Jansen, *Machine Learning for Algorithmic Trading*. The code is free on GitHub (`stefan-jansen/machine-learning-for-trading`).
- Igor Tulchinsky et al., *Finding Alphas* (WorldQuant)
- **(free)** Daniel Palomar, *Portfolio Optimization: Theory and Application*. Free online at portfoliooptimizationbook.com.

**Microstructure and execution**
- Larry Harris, *Trading and Exchanges*
- Cartea, Jaimungal & Penalva, *Algorithmic and High-Frequency Trading*
- Bouchaud et al., *Trades, Quotes and Prices*

**Free courses**
- [QuantEcon](https://quantecon.org/) lectures (free)
- MIT OCW 18.S096 *Topics in Mathematics with Applications in Finance* (free)
- Coursera/edX audit tracks (e.g. ISB's *Trading Strategies in Emerging Markets*, audit is free)

## 5. Where a legitimate library can replace a torrent

- **Internet Archive / Open Library**: legal controlled lending of many older trading classics
- A **local or university library**, plus **DELNET**, and national libraries on inter-library loan
- **O'Reilly Learning** (includes Wiley finance titles) and **Perlego**: subscriptions give access to most of the books above
- Many authors post **pre-print versions** of their papers and chapters on SSRN, arXiv or their own sites. Search the title plus "pdf" on scholar.google.com and use the author-hosted copy.
