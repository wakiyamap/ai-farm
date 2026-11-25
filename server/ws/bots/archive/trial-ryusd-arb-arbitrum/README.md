NOT A BOT - abandoned draft, do not finish or start it. Archive it.

Run 47c805ce (builder-claude, 2026-11-21 about 11:55Z) drafted this as a sibling of trial-ryeth-arb-arbitrum for the
Sommelier Real Yield USD cellar 0x392B1E6905bb8449d26af701Cdea6Ff47bF6e5A8 on Arbitrum and measured it as a dead end
before placing it: the USDT route's edge (cellar price over the Uniswap V3 USDC/USDT 0.01 pct pool price, after the
pool fee) was below zero in 57 of 57 samples over 8 days (-4.76 to -0.12 bp), and multiAssetDeposit of USDC.e and
DAI reverts (custom error 0x6d305815). No manifest, no executor-runtime.hex, never started.

The session could not remove this directory itself (`rm -r` and `paper archive` were refused by its permission
mode). Evidence and the kept copy of bot.py: scratch/trial-ryusd-arb-arbitrum/ (proof.py, proof-result-526228800.json,
series.py, series.json) and the attempts row of run 47c805ce.
