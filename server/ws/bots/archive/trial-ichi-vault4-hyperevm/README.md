trial

# trial-ichi-vault4-hyperevm

Cheap-chain trial (decision `2026-11-17-cheap-chain-trials.md`; class allowed by
`2026-11-21-ichi-yes-peapods-fee-no.md` section 1). Fourth sibling of the live `trial-ichi-vault*-hyperevm` bots:
the WHYPE-deposit ICHI vault IV-NEST-8 `0xcde75a121bb461e89eddd05958fc2cd33504abb4` (token0 WHYPE, token1 UBTC; own
Algebra pool 0xcd238eaf), sold on WOOFi's WooPPV2 `0x5520385bfcf07ec87c4c53a7d8d65595dff69fa4`.

History: run ce0e2ed8 generated this directory with V3 routes only and abandoned it (0.3 USD a week). Run 681105b6
identified the incumbents' sell venue 0x5520385b as a WOOFi WooPPV2 (`swap(address,address,uint256,uint256,address,address)`
= 0x7dc20382, Wooracle `state()` / `postPrice` in the trace), added that hop to the executor (IchiVaultArb3) and
placed the bot.

## Mechanism

`deposit(whype, 0, to)` mints shares at the vault's own pool price; `withdraw(shares, to)` pays pro-rata WHYPE + UBTC.
When UBTC is dearer on the WooPP (oracle-priced) than on the vault's own pool, one transaction: Morpho Blue flash
loan of WHYPE (no fee), deposit, withdraw, sell the UBTC (route E: one WooPP swap UBTC -> WHYPE; routes C / D:
UBTC -> USDC on 0xe7aea6b7 / 0x10e8c38b, USDC -> WHYPE on 0x6c9a33e3), repay, unwrap, native HYPE gain to the bot
wallet. The executor reverts unless the gain is at least `minProfit`.

## Competition, last 7 days (7.06 d to head 51,829,283, 2026-11-21 about 04:50Z)

Source: `scratch/trial-ichi-vault4-hyperevm/measure7-0xcde75a12.json` (gains are floors), `backscan3.json`,
`trigger.json`.

- 281 same-transaction round trips (39.8 a day), 1.6448 WHYPE gained (92 USD), median 0.00026, max 0.462 WHYPE.
  92 of them sell on the WooPP and earn 1.51 WHYPE.
- 18 takes of 0.01 WHYPE or more (1.42 WHYPE): every one sent by EOA 0x0b8d87ee4ee429a60e8f5738c3a2d7d6e8ad8471
  through contracts 0x7b9836a3.. (20 takes, +0.52), 0x7484eb5f.. (6, +0.56), 0x3ad8bef9.. (7, +0.32) and
  0x50381ce3..; 9 at tx index 0; gas price median 9.95 gwei (0.2-0.42 USD a take). Small takes: 0x30e81e4d.. /
  EOA 0x454c16ca.. 127 takes, +0.069 WHYPE, 0.42 gwei median.
- Blocks to take: this bot's scan at the parent block of the 18 large takes finds 11 (1.246 WHYPE); two blocks
  before the take only 3 (0.131 WHYPE); eleven blocks before, 1 (0.008). The incumbent takes in the first block
  (1 s) after the gap opens. What opens it: a Wooracle price post (5 of 11), a liquidity change of the vault's pool
  (3 of 11), neither (3 of 11): no single event to wait on.
- Priority-fee level to win: about 10 gwei (the incumbent's ceiling so far). This bot's fee ceiling is about
  15 gwei at a 950k gas limit; it bids at most 35 pct of gross. Being in time, not the fee, is the limit: a 27 s poll
  sees only gaps that outlive the first block and what a first take leaves.
- One paid take whose gross exceeds one attempt's gas: 0xc6d3183ef5c40772c9b1ddaa2a9795113bb3962831cbac34cca908cb8ff9969b
  (+0.462 WHYPE = 26 USD; a lost attempt is about 913k gas = 0.005-0.5 USD at 0.1-10 gwei).

## Loss guard

- Executor: `require(profit > 0 && profit >= minProfit)` after repayment, owner-only, deadline 60 s.
- Bot (`evaluate()`): gas limit = estimate x 1.25 (max 1.9M); maxFeePerGas capped so gas limit x maxFee <= 0.95 USD
  with HYPE valued 15 pct above the pool price; sends only if simulated gain >= 1.2 x that cap; `minProfit` = the
  cap in wei + 1; the exact calldata is simulated once more before the send.
- capital_usd 20 (native HYPE for gas only; principal is flash-borrowed), max_loss_per_tx_usd 1.

## Read cost

One `eth_call` (scan of 27 candidates, 26 CU) every 27 s = 3,200 a day = 83,200 CU; plus 88 CU per evaluated gap
(gas price, HYPE price, estimate, exact simulation) and 20-95 CU per live send (receipt, winner logs). Hard cap
98,000 CU/day in code (then sleeps to 00:00 UTC; every read goes through `rpc()`, there is no read before the loop).
98,000 CU = 0.052 USD a day at 1M CU = 0.53 USD. No feed filter.

## Logs (`logs/bot.jsonl`)

`start`, `poll` (heartbeat every 40 polls), `opportunity_skip` (reason), `opportunity`, `paper_sim`, `simulate_revert`,
`send_result` (won / lost, gas_used, send_block, winner_block, blocks_after_winner), `signer_reject`, `read_budget`,
`relay_error`, `loop_error`.

## Live

Needs `EXECUTOR_ADDR_HYPEREVM` or `EXECUTOR_ADDR` (exits if unset). The signer's address is taken with
`["address"]`; `/opt/farm/lib` is appended to `sys.path` before the import. The live branch was read, not run.

## Fork proof

`scratch/trial-ichi-vault4-hyperevm/proof3.py` (see `fork_evidence` in the manifest): at the parent block of the
incumbent's take the executor earns +0.461451 HYPE (incumbent 0.462002); non-owner, impossible minProfit and
repeat-after-take calls revert.
