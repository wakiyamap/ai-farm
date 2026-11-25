#!/bin/sh
# aave2-dust-ethereum entrypoint (same for paper and live)
export FORK_URL="${FORK_URL:-$(fork url ethereum 2>/dev/null)}"
exec python3 bot.py
