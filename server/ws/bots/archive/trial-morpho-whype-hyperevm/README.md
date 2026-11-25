trial — cheap-chain trial bot (decision 2026-11-17-cheap-chain-trials): Morpho Blue WHYPE/USDC liquidations on HyperEVM by the direct `liquidate` route.

# trial-morpho-whype-hyperevm

## What it does

Morpho Blue on HyperEVM (`0x68e37dE8d93d3496ae143F2E900490f6280C57cD`, a standard Morpho Blue) pays the
liquidation incentive to any caller of `liquidate()`. Most liquidations there go through an
auctioneer-gated wrapper (lead 145, closed), but the plain route is open and paid: actor
`0x44f50d4a...` took +163.39 USDC with it at block 51209684 (tx `0x7bb3691a...`).

The bot watches three markets, all USDC debt against WHYPE collateral:

| key | market id | lltv | oracle | borrowers at placement |
|---|---|---|---|---|
| whype77 | `0xd7d38220...c59a8` | 0.77 | `0x194fff37...` | 171 |
| whype62 | `0xd13b1bad...804fc` | 0.625 | `0x194fff37...` | 134 |
| whype86 | `0xf1c3d487...84ebb` | 0.86 | `0xa6ecdf8c...` | 20 |

Loop (`bot.py`): every 60 s one Multicall3 `eth_call` reads both oracle prices, the three markets'
totals and the positions at debt/maxBorrow >= 0.85; every 30 min all known borrowers are re-read and
new ones are added from Morpho `Borrow` logs. While a position with >= 20 USDC debt is within 1.5% of
the line the timer drops to 6 s (as long as the day's read budget allows). A position over the line
is simulated through the executor (`eth_call`; paper: code override at the fork deployment's
address); live it is sent when simulated gross > the send's gas cap.

Executor `TrialMorphoHyperTake.take(marketParams, borrower, seizedAssets, repaidShares, pools[], minProfit)`:
Morpho `liquidate` -> in `onMorphoLiquidate` sell the seized WHYPE to USDC in pool `0x6c9a33e3...`
(UniV3-style, 0.05%, token0 WHYPE, token1 USDC) -> approve exactly the repayment -> revert `NoProfit()`
unless USDC grew by `minProfit` -> pay all USDC to the bot wallet. No principal, no flash loan.

## Competition, last 7 days (blocks 50,865,000 - 51,474,000; `scratch/trial-morpho-whype-hyperevm/competition-7d.json`)

- 16 `Liquidate` events on the three markets, 6 sender EOAs, 10 caller contracts.
- 10 of the 16 were sent by keeper `0x6c246928...` through the auctioneer wrapper while the direct
  route still answered `position is healthy` one block earlier (that route carries its own price):
  out of reach for this bot, and they remove positions before the direct route opens.
- Direct-route takes (takeable = this bot's executor call succeeds at that historical block, relay
  `eth_call` + code override):

| capture block | market | winner (sender) | repaid USDC | executor gain 1 block before | takeable since | winner gas price |
|---|---|---|---|---|---|---|
| 51209684 | whype62 | 0x44f50d4a | 1,726.91 | +212.90 | 2-10 blocks before | 124.7 gwei |
| 51274523 | whype77 | 0x57d5ea52 | 452.40 | +37.67 | 3-9 blocks | 893 gwei |
| 51274511 | whype77 | 0x44f50d4a | 141.26 | +8.53 | 3-9 blocks | 251.9 gwei |
| 51273608 | whype86 | 0x73f7a952 | 15.62 | +0.76 | 3-9 blocks | 5.5 gwei |
| 51276670 | whype77 | 0x7740e851 | 0.30 | +0.02 | 40+ blocks | 0.7 gwei |

- Blocks to take: 3-9 blocks (~1 s each) for the paying cases. Priority-fee level: 5-900 gwei in a
  drop against 0.1 gwei at rest. This bot's fee cap is about 26 gwei (1 USD per send at 450k gas), so
  it can compete for the small quiet-fee cases only; the trial measures how often that wins.

## Loss bound

- Per send: `GAS_LIMIT 450,000 x maxFeePerGas`, `maxFeePerGas <= 0.95 USD / (HYPE/USD x 1.15) / 450,000`
  (about 26 gwei, 0.83 USD at HYPE 69.9). HYPE/USD is the Morpho oracle's own price read in the same
  Multicall (200 USD until the first read). No send when the base fee is above the cap or simulated
  gross <= the gas cap; the gas cap is passed as `minProfit`.
- A lost race reverts (`position is healthy` at ~131k gas, or `NoProfit` at ~338k): about 0.002 USD at
  0.1 gwei, at most 0.83 USD at the cap. `capital_usd` 20 is the whole budget.
- Priority fee: at most 40% of simulated gross, never above the fee cap.

## Read cost (live = paper)

| read | per day | CU each | CU/day |
|---|---|---|---|
| poll Multicall `eth_call` (60 s) | 1,440 | 26 | 37,440 |
| full scan (30 min, 3 Multicalls) | 144 | 26 | 3,744 |
| borrower discovery (`eth_blockNumber` + `eth_getLogs`, 30 min) | 48 | 85 | 4,080 |
| borderline re-simulations (10 min each) | ~144 | 26 | ~3,700 |
| total, quiet day | | | ~49,000 CU = 0.026 USD |

The 6 s timer costs 15,600 CU per hour and runs only while `used today + 0.6 CU/s x seconds left
today <= 90,000` (`fast_allowed`); every relay read is counted in `state/cu.json` and the bot stops
reading at 90,000 CU/day (0.048 USD at 0.53 USD per 1M CU). No feed filter: the oracle's update event
(`ValueUpdate` on the shared RedStone adapter `0x24c89643...`) carries the feed id unindexed and fires
about 2,100 times a day for all feeds, about 74k CU/day on the feed, so a timer is cheaper.

## Logs (`logs/bot.jsonl`, one JSON object per line)

`start` (executor address), `scan` (label full/poll, debtors, candidates, top_ratio, hype_usd),
`timer` (fast on/off), `discover`, `opportunity`, `opportunity_skip` (with reason and fee numbers),
`simulate_revert`, `paper_sim`, `signer_reject`, `send_result` (won/lost, gas_used, gas_cost_wei,
winner_block, send_block, blocks_after_winner), `read_budget`, `relay_error`, `loop_error`.

## Fork proof and known limits

- `scratch/trial-morpho-whype-hyperevm/proof.py` and `selftest.py`; hashes in the manifest.
- The hyperevm fork serves head storage at any reset block, so the fork success uses a position
  opened on the fork (max LTV + 10 min of interest); the historical case is shown through the relay.
- `position is healthy` text is matched on `latest` reads only (the relay's historical node returns
  the raw revert bytes); the bot always reads `latest`.
- Live executor address comes from `EXECUTOR_ADDR_HYPEREVM` / `EXECUTOR_ADDR` only.
