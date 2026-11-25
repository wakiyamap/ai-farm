trial — cheap-chain trial bot (decision 2026-11-17-cheap-chain-trials): Morpho Blue kHYPE/USDC liquidations on HyperEVM by the direct `liquidate` route.

# trial-morpho-khype-hyperevm

## What it does

Morpho Blue on HyperEVM (`0x68e37dE8d93d3496ae143F2E900490f6280C57cD`) pays the liquidation incentive
to any caller of `liquidate()`. The two kHYPE/USDC markets are the busiest liquidation markets on the
chain (22 of the about 80 `Liquidate` events in the ledger for the last 7 days; 7.4M and 6.1M USDC borrowed).

| key | market id | lltv | oracle | borrowers at placement |
|---|---|---|---|---|
| khype77 | `0x96c47d37...a73b9` | 0.77 | `0x3939328b...` | 177 |
| khype62 | `0xe7aa0468...2349b` | 0.625 | `0xe876bfab...` | 508 |

Loop (`bot.py`): every 60 s one Multicall3 `eth_call` reads both oracle prices, both markets' totals
and the positions at debt/maxBorrow >= 0.85; every 30 min all known borrowers are re-read (5 Multicalls)
and new ones are added from Morpho `Borrow` logs. While a position with >= 200 USDC debt is within 0.7%
of the line the timer drops to 2 s (as long as the day's read budget allows). A position over the line
is simulated through the executor (`eth_call`; paper: code override at the fork deployment's address);
live it is sent when simulated gross > the send's gas cap.

Executor `TrialMorphoKhypeTake.take(marketParams, borrower, seizedAssets, repaidShares, pools[], minProfit)`:
Morpho `liquidate` -> in `onMorphoLiquidate` sell the seized kHYPE to WHYPE in pool `0xbe352daf...`
and the WHYPE to USDC in pool `0x6c9a33e3...` (both UniV3-style; the route of actor tx `0xfa43d53d...`)
-> approve exactly the repayment -> revert `NoProfit()` unless USDC grew by `minProfit` -> pay all USDC
to the bot wallet. No principal, no flash loan.

## Competition, last 7 days (blocks 50,870,000 - 51,477,000; `scratch/trial-morpho-khype-hyperevm/competition-7d.json`)

- 18 `Liquidate` events with >= 1 USDC repaid on the two markets (plus 4 dust probes of 0.1 USDC),
  8 sender EOAs, 11 caller contracts.
- 9 of the 18 were sent by keeper `0x6c246928...` through the auctioneer wrapper while the direct
  route still answered `position is healthy` one block earlier: out of reach for this bot.
- 4 large ones (85k-300k USDC repaid, positions of 85k-2.05M USDC debt, winners paid 346-28,187 gwei)
  were over the line one block earlier. A 100k-USDC part does not fit in 700k gas (out of gas), so the
  bot uses a size/gas ladder: 100k and 25k USDC parts at a 1.9M gas limit, a 5k part at 700k
  (`large-cases.json`). The bot's own `attempt()` pinned to the block before each winner
  (`ladder_test.py`, `ladder-test.json`) simulates +6,706 (block 51274520), +11,555 (51209684) and
  +1,811 USDC (51274721, after two failed larger tries); the fourth (51274720) simulates +1,828 USDC
  for a 25k part in `large.py`.
- 5 direct-route takes this bot's executor call would have made one block before the winner (relay
  `eth_call` at that block, code override):

| capture block | market | winner (sender) | repaid USDC | executor gain 1 block before | 3 blocks before | winner gas price |
|---|---|---|---|---|---|---|
| 51209690 | khype77 | 0xd594df22 | 2,916.94 | +219.59 | healthy | 3,393 gwei |
| 51257133 | khype77 | 0xd594df22 | 2,012.00 | +149.18 | healthy | 2,271 gwei |
| 51274507 | khype62 | 0x57d5ea52 | 928.95 | +104.95 | healthy | 1,748 gwei |
| 51273083 | khype77 | 0x2574e8a3 | 997.03 | +71.54 | healthy | 278 gwei |
| 51209691 | khype77 | 0xac5b4731 | 784.21 | +58.78 | healthy | 866 gwei |

- Blocks to take: 1-2 blocks (~1 s each) from takeable to taken. Priority-fee level: 278-3,393 gwei
  on the direct route (winners give up about half the gross as gas) against 0.1 gwei at rest.
- What that means for this bot: its fee cap is about 16 gwei (1 USD per send at 700k gas; about
  6 gwei on the 1.9M tier), so it
  loses every same-block contest; it can win only when its 2 s timer sees the position in the first
  block and its tx lands a block before the incumbents'. Expect mostly `lost` rows; the trial
  measures how late (blocks_after_winner) and how short on fee.

## Loss bound

- Per send: `gas limit x maxFeePerGas`, `maxFeePerGas <= 0.95 USD / (kHYPE/USD x 1.15) / gas limit`:
  700,000 gas (positions up to 5k USDC and the 5k part) gives about 16.4 gwei, 1,900,000 gas (25k and
  100k parts) about 6.0 gwei; either way at most 0.83 USD at kHYPE 72.2. The price is the Morpho kHYPE oracle read in the same
  Multicall (kHYPE >= HYPE, so the cap is on the tight side; 200 USD until the first read). No send
  when the base fee is above the cap or simulated gross <= the gas cap; the gas cap is passed as
  `minProfit`.
- A lost race reverts (`position is healthy` at ~146k gas, or `NoProfit` at ~520k): about 0.004 USD at
  0.1 gwei, at most 0.83 USD at the cap. `capital_usd` 20 is the whole budget.
- Priority fee: at most 40% of simulated gross, never above the fee cap.

## Read cost (live = paper)

| read | per day | CU each | CU/day |
|---|---|---|---|
| poll Multicall `eth_call` (60 s) | 1,440 | 26 | 37,440 |
| full scan (30 min, 5 Multicalls) | 240 | 26 | 6,240 |
| borrower discovery (`eth_blockNumber` + `eth_getLogs`, 30 min) | 48 | 85 | 4,080 |
| dust / borderline re-simulations (`eth_call` + `eth_gasPrice`) | ~100 | 36 | ~3,600 |
| total, quiet day | | | ~51,000 CU = 0.027 USD |

The 2 s timer costs 46,800 CU per hour and runs only while `used today + 0.6 CU/s x seconds left
today <= 90,000` (`fast_allowed`), i.e. under an hour a day; every relay read is counted in
`state/cu.json` and the bot stops reading at 90,000 CU/day (0.048 USD at 0.53 USD per 1M CU). No feed
filter (the oracle's upstream update event is shared by all feeds; a timer is cheaper).

## Logs (`logs/bot.jsonl`, one JSON object per line)

`start` (executor address), `scan` (label full/poll, debtors, candidates, top_ratio, hype_usd = the
kHYPE oracle price), `timer` (fast on/off), `discover`, `opportunity`, `opportunity_skip` (reason and fee
numbers), `simulate_revert`, `paper_sim`, `signer_reject`, `send_result` (won/lost, gas_used,
gas_cost_wei, winner_block, send_block, blocks_after_winner), `read_budget`, `relay_error`, `loop_error`.

At placement one dust position (khype62 `0x1565f3be...`, gross 0.003 USD) is over the line and is
skipped as `gross_not_above_gas_cap` every 30 min; that row is expected.

## Fork proof and known limits

- `scratch/trial-morpho-khype-hyperevm/proof.py`, `selftest.py`, `competition.py`; hashes in the manifest.
- The hyperevm fork serves head storage at any reset block, so the fork success uses a position
  opened on the fork (max LTV + 10 min of interest); the historical cases are shown through the relay.
- Positions above 5k USDC debt are attempted in parts (100k, 25k, 5k); a part that does not simulate
  is logged `simulate_revert` and the next smaller one is tried. After a won partial take the rest is
  tried on the next poll. The 1.9M-gas tier is just under the chain's 2,000,000 per-tx limit.
- `bot.py` is derived from the same author's `trial-morpho-whype-hyperevm` (own copy, no import) by
  `scratch/trial-morpho-khype-hyperevm/mkbot.py` + `patch_ladder.py`.
- Live executor address comes from `EXECUTOR_ADDR_HYPEREVM` / `EXECUTOR_ADDR` only.
