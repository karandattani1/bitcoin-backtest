#!/usr/bin/env bash
# Shallow-clone reference repos into external/ (gitignored) for local study.
#
# Usage:
#   scripts/fetch_repos.sh              # curated trading/backtesting set (default)
#   scripts/fetch_repos.sh --openalgo   # every public repo under github.com/marketcalls (OpenAlgo)
#   scripts/fetch_repos.sh --all        # both of the above
#
# Re-running updates repos that already exist (git pull --depth 1).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/external"
mkdir -p "$DEST"

CURATED=(
  # OpenAlgo core + backtesting
  marketcalls/openalgo
  marketcalls/openalgo-python-library
  marketcalls/vectorbt-backtesting-skills
  marketcalls/openalgo-execution-skills
  marketcalls/openalgo-indicator-skills
  marketcalls/openalgo-skills
  marketcalls/openengine
  marketcalls/openstatz
  marketcalls/openscript
  marketcalls/historify
  marketcalls/statistical-arbitrage
  marketcalls/emacrossover-autoresearch
  marketcalls/backtesting-autoresearch
  marketcalls/openalgo-charts
  marketcalls/openalgo-mcp
  marketcalls/TradingAgent
  marketcalls/Agentic-Trader
  marketcalls/Crypto-Realtime-QuestDB
  p2c2e/openalgo-backtrader
  # Backtesting frameworks
  polakowo/vectorbt
  kernc/backtesting.py
  mementum/backtrader
  nkaz001/hftbacktest
  edtechre/pybroker
  freqtrade/freqtrade
  jesse-ai/jesse
  nautechsystems/nautilus_trader
  # Jev (TypeSafe System One) trading experiments
  egrm07/jev_bitcoin_backtest
  justinhe16/trade-jev
  OpenByteInc/QuantDinger
  jgottig/jev-bot-trading
  # Obsidian
  Cursivez/journalit
  bitbonsai/mcpvault
)

list_marketcalls() {
  # Snapshot list (api.github.com is not reachable from every environment).
  grep -v '^#' "$ROOT/scripts/openalgo_repos.txt" | sed 's|^|marketcalls/|'
}

case "${1:-}" in
  --openalgo) REPOS=($(list_marketcalls)) ;;
  --all)      REPOS=("${CURATED[@]}" $(list_marketcalls)) ;;
  "")         REPOS=("${CURATED[@]}") ;;
  *) echo "unknown option: $1" >&2; exit 2 ;;
esac

ok=0; fail=0
for full in $(printf '%s\n' "${REPOS[@]}" | sort -u); do
  dir="$DEST/${full//\//__}"
  if [ -d "$dir/.git" ]; then
    echo "update  $full"
    git -C "$dir" pull -q --depth 1 && ok=$((ok + 1)) || fail=$((fail + 1))
  else
    echo "clone   $full"
    git clone -q --depth 1 "https://github.com/$full.git" "$dir" && ok=$((ok + 1)) || fail=$((fail + 1))
  fi
done
echo "done: $ok ok, $fail failed -> $DEST"
