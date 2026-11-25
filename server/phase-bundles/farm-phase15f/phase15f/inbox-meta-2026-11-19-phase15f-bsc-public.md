# phase 15f: a second public bsc node in the relay (human, 2026-11-19)

Answer to your note of 11-18 15:45Z, item 1. relay.json `chains.bsc.public` now starts with `https://bsc-dataseed.binance.org` (serves eth_getLogs; scout run 9d4669bb measured 20k-block pages), then the old `bsc-dataseed.bnbchain.org`. When a lane's Alchemy budget is spent, bsc reads go to public nodes like every other chain instead of failing with `no provider available`. Large getLogs ranges may still be refused by the public node: page them. The rule in TOOLS.md stays: never curl a node directly.

Item 2 (paper-reviewer interval while the trials are 30/30): the human keeps it as it is, so a freed slot is filled quickly.
