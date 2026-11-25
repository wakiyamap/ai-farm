# morpho-watcher-ethereum: recent blue-pool captures vs the pinned market set (earner run e92242bc)

- The newest whale-scale morpho_blue.liquidate capture on ethereum (block 26391872, tx 0x75c6e8f80bcf, repaid 61.29 WETH ~126k USD) landed in market 0x88abdf8693e663144c3544b9442e9b04520016d6ebc57aa76424c00ab1683c9d - NOT in the bot's code-pinned MARKETS (bot.js line 49). The bot's pinned WBTC/USDC-class market 0x94b823e6... took only a 7-wei dust capture at 26391772.
- Bot itself is healthy (heartbeat 13:45Z, block 26392068, debtors 392, underwater_now 6, live_loss_usd 0, zero sends).
- For the reviewer/live-operator: before the next review round, check whether the pinned-market design covers the currently active WETH/USDC market 0x88abdf86... (full measurement in attempts:913; the capture census is ledger-only, 0 RPC).
