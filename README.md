# bitcoin-backtest
Simple momentum-based Bitcoin backtesting model (Python + Pandas + NumPy).
Goal: To test if short-term momentum filters can improve return consistency in crypto markets.

Tools Used:

Python (Pandas, NumPy, Matplotlib)

Historical BTC-USD data (Yahoo Finance / Kaggle CSV)

Metrics Generated:

CAGR

Max Drawdown

Win Rate

Sharpe Ratio

Future Enhancements:

Position-sizing module

Volatility filter

Risk-adjusted trade sizing

## Research

Pre-registered, testable strategy conditions are in [docs/STRATEGY_SPECS.md](docs/STRATEGY_SPECS.md); [prompts/PC_CLAUDE_CODE_PROMPT.md](prompts/PC_CLAUDE_CODE_PROMPT.md) is a copy-paste prompt for running them on local data with Claude Code. See [docs/DERIVATIVES_IDEAS.md](docs/DERIVATIVES_IDEAS.md) for Indian F&O trading ideas (with realized-vol tests in `research/nifty_derivatives_tests.py`), [docs/INDIA_IDEAS.md](docs/INDIA_IDEAS.md) for Indian-market trading ideas distilled from those repos (with NIFTY tests in `research/`), and [docs/RESOURCES.md](docs/RESOURCES.md) for a map of OpenAlgo, backtesting frameworks, Jev (TypeSafe) trading experiments and Obsidian tooling, plus build ideas. `scripts/fetch_repos.sh` clones them into `external/` (gitignored).
