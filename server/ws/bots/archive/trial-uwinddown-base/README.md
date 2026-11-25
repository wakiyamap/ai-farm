trial

# trial-uwinddown-base

Universal Protocol is winding down on Base. Its `UniversalWindDownVault` `0x1f69bbf9f7ed316bcf1e0cf12f81d261a9bdc2ca`
(Blockscout-verified) pays a **fixed USDC rate** per uAsset to anyone: `redeem(asset, amount, minimumUSDCAmount)` pulls
the uAsset, burns it and pays USDC from a pool the owner refills (200,000 USDC on 11-18, 350,000 on 11-19). The uAssets
still trade against WETH in Uniswap-V3-style pools. Whenever a pool prices a uAsset below the vault's rate (ETH fell,
or someone sold into the pool), one transaction earns the difference:

Morpho flash USDC -> USDC/WETH 0.05 % pool -> WETH/uAsset pool -> `vault.redeem` -> repay -> USDC gain to the wallet.

The executor (`WindDownArb`) reverts unless its USDC balance grew by `minProfit`, so a lost attempt costs gas only.

## Competition (the vault's whole life: 2.9 days, blocks 58,882,222-60,121,843)

1,021 redemptions, 378,155 USDC paid. Redeemers (scratch/rf5f3/wd-scan.json, wd-takers.json):

| redeemer | redemptions | USDC redeemed | gain seen in the same tx | tx index median | gas price median |
|---|---|---|---|---|---|
| 0x6f2239cd5d60d0c256bd1c44e24c931cffc3734c (contract, 5 senders) | 467 | 121,596 | none visible (holds inventory) | 20 | 0.024 gwei |
| 0x8cc1665ee965345e79b132adb124782bad8c78e0 (EOA, direct redeem) | 250 | 142,147 | none (holder) | 6 | 0.110 gwei |
| 0xf743c84ae244c5d9005c774dcab9f876f8667b84 (flash, USDC gain) | 205 | 54,751 | median 0.157 USD, max 1.08 | 38 | 0.016 gwei |
| 0x329e8a68143f5d8725e343d125f2193f59dd23f0 (flash, WETH gain) | 25 | 33,297 | sum 65.7 USD, median 2.22 | 33 | 0.010 gwei |
| 0x4d98dbc5bb8c4c830384b9e0a64938f6ee0cc481 (flash, WETH gain) | 16 | 683 | sum 1.6 USD, median 0.075 | 70 | 0.008 gwei |
| 0x7475c030849538ce47990db32429eb4445db0b9d (flash, WETH gain) | 14 | 13,968 | sum 47.0 USD, median 3.25 | 33 | 0.007 gwei |
| 0xa344e1100fe0d0ff86350b047f33f7a3e02c4109 (flash, WETH gain) | 4 | 3,700 | sum 5.7 USD | 47 | 0.041 gwei |

Gas per take 0.004-0.03 USD. Priority fees are at the floor (effective gas price 0.007-0.04 gwei); takes sit at tx
index 5-200, not at the top of the block.

Blocks to take (scratch/trial-uwinddown-base/windows.py, this bot's own scan run at blocks before 26 sampled takes):
open 1 block before in 25 of 26, 3 s before in 25, 10 s before in 21, 30 s before in 14, 3 minutes before in 12.
Median: open for at least 150 blocks (30 s). On 11-18 the uSOL / uADA / uSUI gaps of 1-13 USD stayed open for minutes.

## Routes

23 WETH pools of 19 uAssets. 16 pools of 12 assets read from the incumbents' receipts (uSOL x4, uXRP x2, uDOGE, uADA,
uNEAR, uARB, uSUI, uLTC, uATOM, uLINK, uBTC, uZEC); pool holdings at the redemption rate at 22:49Z: uXRP 267k USD,
uSOL 231k, uDOGE 52k, uADA 47k, uSUI 23k, uNEAR 13k, uLINK 12k; the rest under 3k. 7 pools of assets no incumbent had
arbitraged by 11-20 (Uniswap V3 `getPool(asset, WETH, 3000)`, scratch/rf5f3/wd_more.py): uXLM 8.8k USD, uHBAR 6.3k,
uAVAX 1.9k, uDOT 1.4k, uALGO 1.1k, uSEI 0.6k, uBCH 10 USD. Not covered: the other 80 tokens with a rate (under 2k USD
outstanding each, or no WETH pool holding the token: uPUMP, uOP, uAPT).

## What the bot does

- Every 27 s: one `eth_call` of the executor's `scan()` with 92 candidates (23 routes x 25 / 150 / 800 / 4,000 USDC).
- Best candidate at 0.03 USDC or more: a second scan refines the size (0.4x-3x, at most 12,000 USDC), then gas
  estimate, fee cap and the exact-bytes `eth_call`. A route that was evaluated and not sent waits 120 s.
- Sends only if the simulated gain is at least 1.2 x this send's gas cap (gas limit x maxFeePerGas + L1 fee upper
  bound, under 0.95 USD). `minProfit` = that cap in USDC. Priority fee bid: at most 35 % of the simulated gain.
- Log `logs/bot.jsonl`: `poll` (heartbeat), `opportunity`, `opportunity_skip`, `simulate_revert`, `paper_sim`,
  `send_result` (won / lost, gas used, send block, nearest block where someone else redeemed the same asset).

## Read cost

3,200 scans x 26 CU = 83,200 CU/day, about 160 CU per evaluated opportunity, hard cap 98,000 CU/day in code
(0.052 USD/day at 0.53 USD per 1M CU). No feed filter: the gap follows the ETH price, and the WETH/USDC Swap is a
busy event.

## Limits and risks

- The vault can run dry (171,845 USDC at 22:49Z against about 2.4M USD of uAssets outstanding) or be paused; then
  every probe reverts and the bot idles until the owner refills it. A refill after a dry spell is a burst the bot
  sees at its next poll.
- The owner can change rates while paused. The bot never trusts a stored rate: the scan runs the real redeem.
- Gains are in USDC; gas is paid in ETH from the bot wallet (15 USD, the trial's whole loss budget).
- The class ends when the pools are empty or the vault closes: a short-lived trial by nature.

## Proof

`scratch/trial-uwinddown-base/proof.py` (fork, reset 59,145,100): owner +2.435715 USDC on uSUI with an 800 USDC
flash, 522,469 gas; reverts for a non-owner, for minProfit x 1000 and for the same run repeated. `selftest.py`:
encoder equals `cast calldata`, runtime equals the artifact except the owner immutable, scan answers through the relay.
