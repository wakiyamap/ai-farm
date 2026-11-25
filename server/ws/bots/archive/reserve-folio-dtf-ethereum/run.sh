#!/bin/bash
# Reserve Folio (DTF) rebalance auction bot. Paper mode: detects AuctionOpened, fetches decayed
# getBid price, simulates the executor on the fork via eth_call (no keys). Live mode: same loop,
# sends the executor bidWithSwap through the signer. Venue calldata built from a live quote.
cd "$(dirname "$0")"
export FORK_URL_ETHEREUM=${FORK_URL_ETHEREUM:-$(fork url ethereum 2>/dev/null || echo "")}
exec python3 bot.py
