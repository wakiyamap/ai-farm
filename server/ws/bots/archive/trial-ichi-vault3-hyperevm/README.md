trial

# trial-ichi-vault3-hyperevm

Cheap-chain trial (decision `2026-11-17-cheap-chain-trials.md`; class allowed by
`2026-11-21-ichi-yes-peapods-fee-no.md` section 1). Third sibling of `trial-ichi-vault-hyperevm` (vault 0xb792f94e)
and `trial-ichi-vault2-hyperevm` (vaults 0x6bd209f2, 0x71b7da3a): the USDC-deposit ICHI vault
`0xd7a533a6f10e09548132316de3735b9957c987d1` (token0 NEST, token1 USDC; own Algebra pool 0xdb544d63).

## Mechanism

`deposit(0, usdc, to)` mints shares at the vault's own pool price; `withdraw(shares, to)` pays pro-rata NEST + USDC.
When NEST is dearer along NEST -> kHYPE (Algebra 0x23d95b24) -> WHYPE (0xbe352daf or 0x705d5dda) -> USDC (0x6c9a33e3)
than on the vault's own pool, one transaction: Morpho Blue flash loan of USDC (no fee), deposit, withdraw, three
swaps, repay, USDC gain to the bot wallet. The executor (`IchiVaultArb2`, same source as vault2's) reverts unless the
USDC gain is at least `minProfit`.

## Competition, last 7 days (blocks 51,208,894-51,828,894, to 2026-11-21 04:44Z)

Source: `scratch/trial-ichi-vault3-hyperevm/measure7.py` -> `measure7-0xd7a533a6.json` (gains are floors; fee USD
there values HYPE at 64.8, pool price was 56.2).

- 217 same-transaction round trips (30.7 a day), 33.08 USDC gained, median 0.033, max 1.454 USDC.
- 22 takes of 0.5 USDC or more (18.34 USDC): 13 at tx index 0, 5 at index 1, 4 at index 2-4; gas price median
  4.3 gwei, fee share of gross median 27 pct. All takes: gas price median 0.35 gwei, gas median 815k.
- Takers (contract / EOA): 0x30e81e4d8790fd5203072ebba81f8e5d85f513a3 / 0x454c16ca.. 157 takes, +17.79 USDC,
  4.49 USD fees; 0x7b9836a3fa0824572c2f7e69beb19c351d80548b / 0x0b8d87ee.. 16 takes, +6.70, 3.99 USD fees, bids
  8-11 gwei and sits at index 0; 0x79350c4b4f09650af22d4755c32727bd87878ea8 / 0x867b39b6.. 15 takes, +5.04,
  5.5 gwei on its largest take; 0x16bc6b3e.. 6 takes; at least 4 more contracts with 3-7 takes each.
- Blocks to take: the larger gaps are taken at tx index 0 of the block after they open (HyperEVM 1 s blocks), so a
  27 s poll sees only gaps the first takers leave or miss. Priority-fee level to win a 0.8 USDC gap: 8-11 gwei
  (about 0.45-0.6 USD on 1M gas); this bot bids at most 35 pct of gross.
- One paid take whose gross exceeds one attempt's gas: 0x221ea9ae4ab7a666f131b4092c4aa2ab9b811202c6a008bf6040b8b9b2705a89
  (+0.839 USDC; a lost attempt is about 1.06M gas = 0.006-0.3 USD at 0.1-5 gwei).

## Loss guard

- Executor: `require(profit > 0 && profit >= minProfit)` after repayment, owner-only, deadline 60 s.
- Bot (`evaluate()`): gas limit = estimate x 1.25 (max 1.9M); maxFeePerGas capped so gas limit x maxFee <= 0.95 USD
  with HYPE valued 15 pct above the pool price; sends only if simulated gain >= 1.2 x that cap; `minProfit` = the
  cap in USDC + 1 unit; the exact calldata is simulated once more before the send.
- capital_usd 20 (native HYPE for gas only; principal is flash-borrowed), max_loss_per_tx_usd 1.

## Read cost

One `eth_call` (scan, 26 CU) every 27 s = 3,200 a day = 83,200 CU; plus 88 CU per evaluated gap (gas price, HYPE
price, estimate, exact simulation) and 20-95 CU per live send (receipt, winner logs). Hard cap 98,000 CU/day in code
(then sleeps to 00:00 UTC; every read goes through `rpc()`, there is no read before the loop). 98,000 CU = 0.052 USD
a day at 1M CU = 0.53 USD. No feed filter.

## Logs (`logs/bot.jsonl`)

`start`, `poll` (heartbeat every 40 polls), `opportunity_skip` (reason), `opportunity`, `paper_sim`, `simulate_revert`,
`send_result` (won / lost, gas_used, send_block, winner_block, blocks_after_winner), `signer_reject`, `read_budget`,
`relay_error`, `loop_error`.

## Live

Needs `EXECUTOR_ADDR_HYPEREVM` or `EXECUTOR_ADDR` (exits if unset). The signer's address is taken with
`["address"]`; `/opt/farm/lib` is appended to `sys.path` before the import. The live branch was read, not run.

## Fork proof

`scratch/trial-ichi-vault3-hyperevm/proof.py` (see `fork_evidence` in the manifest): at the parent block of the
incumbent's take the executor earns +0.844438 USDC (incumbent 0.839429); non-owner, impossible minProfit and
nothing-left calls revert.
