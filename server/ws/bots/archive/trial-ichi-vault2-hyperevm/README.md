trial

# trial-ichi-vault2-hyperevm

Cheap-chain trial (decision 2026-11-17-cheap-chain-trials), attempts:3030 / 3031 and the IV-NEST-17 addendum row of
the same run. Sibling of the live `trial-ichi-vault-hyperevm` (IV-NEST-16, USDC deposit); the class was opened by the
human in `decisions/human/2026-11-21-ichi-yes-peapods-fee-no.md` (section 1): arbitrage between an ICHI vault's
deposit / withdraw pricing and the market.

**What it takes.** The two WHYPE-deposit ICHI vaults on Nest. `deposit(whype)` mints shares at the price of the
vault's own Algebra pool (spot / TWAP); `withdraw(shares)` pays the pro-rata two tokens. When the vault's other token
is dearer on another pool than on the vault's own pool, one transaction through the `IchiVaultArb2` executor
flash-borrows WHYPE from Morpho Blue `0x68e37de8d93d3496ae143f2e900490f6280c57cd` (no fee), deposits, withdraws the
shares just minted, sells the other token for WHYPE, repays, unwraps the WHYPE gain and pays it to the bot wallet as
**native HYPE**. It reverts unless the gain is at least `minProfit`.

| route | vault | own pool | sell hops | flash sizes (WHYPE) |
|---|---|---|---|---|
| A | IV-NEST-2 `0x6bd209f208d58f1db5497ec49d14bf9945f5b104` (NEST, WHYPE) | `0x535f30f50ebda33575242c38b976e681d13db6fa` | NEST -> kHYPE on Algebra `0x23d95b24ad0c1ff48816a87e1e65dac4fa883afb`, kHYPE -> WHYPE on `0xbe352daf66af94ccf2012a154a67daef95facb91` | 15 / 40 / 80 / 120 / 180 / 260 |
| B | the same | the same | the same first hop, kHYPE -> WHYPE on `0x705d5dda03d170384eb43eb1aa692a6fc548306f` | the same |
| C | IV-NEST-17 `0x71b7da3a4f9a5964f34d997faa72eb7ac037e02f` (WHYPE, USDC) | `0xbe512f5881b85c48d9c17bc5bb2be047d156d696` | USDC -> WHYPE on UniV3-style `0x6c9a33e3b592c0d65b3ba59355d5be0d38259285` | 300 / 1k / 3k / 10k / 30k / 64k / 120k |

kHYPE is `0xfd739d4e423301ce9385c1fb8850539d657c296d`. No HyperCore precompile is read on these routes (unlike the
IV-NEST-16 bot), so the fork proofs need no fixture. Morpho held 487,474 WHYPE at block 51,771,270.

**How it waits.** A gap opens on swaps of busy pools; the bot polls: one `eth_call` of the executor's `scan()` every
27 s returns the gain of all 19 candidates from the same state (0.15 s). It acts on the best one only if the gain is
at least 1.2 x that send's gas cap; `minProfit` is the gas cap in wei + 1.

Not covered: closes through venue `0xed2ef1b0..` (18 of 579 takes on IV-NEST-2, 22 + of 197 on IV-NEST-17) and the
other IV-NEST-17 sell venues (`0x76abc66e..` / `0xfdad4b27..` 22 takes, `0x5520385b..` 11): not traced.

## Competition, last 7 days (7.06 d to 2026-11-20 19:43-19:52Z)

`scratch/trial-ichi-vault2-hyperevm/measure7.py <vault>` -> `measure7-<vault>.json` (share mints of the vault that
are burned in the same transaction; gain = net WHYPE Transfer logs into the sender or its contract, a floor: some
contracts keep it where the script does not see it; HYPE at 61.3 USD). Control: the same filter shape without topic1
returns the vault's Transfer logs.

| | IV-NEST-2 | IV-NEST-17 |
|---|---|---|
| blocks | 51,175,836-51,795,836 | 51,176,327-51,796,327 |
| round trips | 579 = 82 a day (per day, newest first: 89 / 132 / 11 / 21 / 57 / 107 / 162) | 197 = 28 a day |
| measured gain | 2.3539 WHYPE = 144 USD | 3.3296 WHYPE = 204 USD |
| median / max take | 0.00107 / 0.03974 WHYPE | 0.00244 / 0.4499 WHYPE |
| takes of 0.01 WHYPE or more | 80, 91 USD; tx index 0 in 44 | 66, 190.5 USD; tx index 0 in 41 |
| fee share of gross on those, median | 22 % | 15 % |
| gas price median, those / all | 5.1 / 0.63 gwei | 5.4 / 1.22 gwei |

| taker contract (EOA) | IV-NEST-2: takes, WHYPE, fees USD | IV-NEST-17: takes, WHYPE, fees USD |
|---|---|---|
| `0x30e81e4d8790fd5203072ebba81f8e5d85f513a3` (`0x454c16ca...`) | 352, 0.900, 9.75 | 81, 1.516, 17.35 |
| `0x7b9836a3fa0824572c2f7e69beb19c351d80548b` (`0x0b8d87ee...`) | 75, 0.860, 27.78 | 17, 0.553, 9.54 |
| `0x79350c4b4f09650af22d4755c32727bd87878ea8` (`0x867b39b6...`) | 69, 0.500, 5.91 | 24, 0.474, 2.51 |
| others | 83, 0.09, about 39 | 75, 0.79, about 35 |

Blocks to take: not measured (the block where each gap opened was not reconstructed; it could be, from the pools'
Swap logs, since no off-chain price is involved). What history shows: 85 of the 146 larger takes are the first
transaction of their block, 61 are not. Priority-fee level: `0x79350c4b` a steady 5.1 gwei; `0x7b9836a3` 6-52 gwei;
`0x30e81e4d` near the base fee on small takes and 33-186 gwei on the largest IV-NEST-17 gaps (0.10-0.45 WHYPE).
This bot's fee ceiling is about 11-13 gwei (0.95 USD cap at a 1.0-1.2M gas limit): it can outbid the 5.1 gwei taker
but not the bids on the largest gaps.

## Loss guard

- Executor: `require(profit > 0 && profit >= minProfit)` after the flash loan is repaid; a losing route already fails
  at Morpho's repayment pull; deadline.
- Bot: gas limit = estimate x 1.25 (max 1.9M); `maxFeePerGas` = base fee x 1.3 + bid, never above the fee at which
  gas limit x fee is 0.95 USD (HYPE at the WHYPE/USDT0 pool price x 1.15); no send unless the simulated native gain
  is at least 1.2 x gas limit x maxFeePerGas. Bid at most 35 % of gross.
- A lost attempt: 0.8-1.0M gas = 0.006 USD at the 0.1 gwei floor, 0.01 USD at the 0.18 gwei seen 19:53Z, never more
  than 0.95 USD.

## Proof

Real fork transactions through this artifact, nothing overridden, owner `0x1111111111111111111111111111111111111111`.

`python3 scratch/trial-ichi-vault2-hyperevm/proof.py` (`proof.json`): IV-NEST-2, reset 51,759,512 = the parent of
incumbent take `0xe25b232db71c4e630003d8184e00b833d63940b9e183db2910cd598427f7b892` (index 0, +0.016833 WHYPE).

| fork tx | result |
|---|---|
| deploy `0x39c4158898fea3573c764428d7399c18c0be7c14cd1fedb172516dd682757a86` | executor `0x8f7a45eb...`, 1,316,598 gas |
| non-owner `0xac8c0b5e70a48ab4e4769ba3113c088e6414e39bf038b3b9180edc8ec14da465` | reverts (`owner`) |
| minProfit 10 WHYPE `0x923168615c196abd77e1e2e0e3d10ffe41e611148beb44a5580d6eb3ae3fdc4c` | reverts (`no profit`), 978,455 gas |
| success `0xeb067027565c970c0e1538d40b658766363c472ca00d62f5b96dc23cad0db6d2` (block 51,759,516) | 100 WHYPE flash, route B: owner native +0.015733146 HYPE before gas (+0.014857665 after the fork's gas fee), 812,832 gas; executor holds 0 native, 0 WHYPE, 0 NEST, 0 kHYPE, 0 shares, allowances 0 |
| the same again `0x9255c12fdb407937591b4d87018ca860912017a2af0b7113e8938f2a4d9997ee` | reverts (nothing left), 969,595 gas |

`scan()` before the take (WHYPE gain): route A 10 -> 0.003817, 25 -> 0.008719, 50 -> 0.014356, 100 -> 0.015325;
route B 0.003861 / 0.008828 / 0.014571 / 0.015746; 200 / 400 / 800 -> 0 on both; after the take: 0 for all.

`python3 scratch/trial-ichi-vault2-hyperevm/proof17.py` (`proof17.json`): IV-NEST-17, reset 51,771,270 = the parent
of incumbent take `0xbe899f6d9ee4ec34cba4daaec3a8ee402d2366c1e194a1b24811e917bd36bff2` (index 0, +0.053799 WHYPE with
a 63,600 WHYPE flash).

| fork tx | result |
|---|---|
| deploy `0x75a62a9edaa73363ddf0d5c36ce3609b7b61827ff6e59c32e4a7588ca8badb50` | executor `0x8f7a45eb...`, 1,316,598 gas |
| non-owner `0x3cffe30b51af2467c3da569ac6651bacf11871f7efc4a97b522ec1e3d5096cd2` | reverts (`owner`) |
| minProfit 10 WHYPE `0x205ec36381aaac51b33dec7afd7372b93b05d3f6407e6b4a403232d0c4ccc335` | reverts (`no profit`), 818,291 gas |
| success `0xae3009ecebc9aad113a7cac25f1f079eec81b6ae4ee83de02ed57e8f2da86445` (block 51,771,274) | 63,600 WHYPE flash, route C: owner native +0.053798770 HYPE before gas (the incumbent's gain to 6 digits; +0.053062020 after the fork's gas fee), 684,701 gas; executor holds 0 native, 0 WHYPE, 0 USDC, 0 shares, allowances 0 |
| the same again `0x5edc636232f4ff398315a3fcac1add0ebee535a303afde854e9d1fd83e375740` | reverts (nothing left), 812,850 gas |

`scan()` before the take: 300 -> 0.003945, 1,000 -> 0.011728, 3,000 -> 0.026563, 10,000 -> 0.045381,
30,000 -> 0.053020, 63,600 -> 0.053799, 120,000 -> 0.053599; after the take: 0 for all.

`selftest.py` (`selftest-result.json`, block 51,796,501): the bot's hand encoder equals `cast calldata` for `run()`
on all three routes and for `scan()`; the paper runtime equals the artifact's runtime with the owner filled in;
through the relay with the code override `scan()` answered for all 19 candidates (A / B: dust gains of 7e-7 to 1e-5
WHYPE, below `MIN_GAIN_WEI`; C: 0; no gap open). Positive control for those zeros: `owner()` answers, `run()` with
minProfit 1 wei completes on A and B, and on C it runs deposit, withdraw and the swap and fails only at Morpho's
repayment pull (`transferFrom reverted`), i.e. the route ran and lost at that moment. `evaluate()` on a fake gain
ends in `simulate_revert` at the exact-bytes check on both vaults.

## Read cost

3,200 polls x 26 CU = 83,200 CU/day, plus about 88 CU per evaluated gap; hard cap 98,000 CU/day in code
(0.052 USD/day at 1M CU = 0.53 USD). No feed filter: the gaps depend on swaps of busy pools.
Every read, startup included, is inside the loop's handler; at the cap it sleeps until 00:00 UTC.

## Logs (`logs/bot.jsonl`)

`start` (with `executor=`), `poll` heartbeat, `opportunity`, `opportunity_skip` (reason), `simulate_revert`,
`paper_sim`, live: `send_result` with `result` won / lost, `gas_used`, `send_block`, `winner_block`,
`blocks_after_winner`, `route`; `signer_reject`, `read_budget`, `relay_error`, `loop_error`.

## Not checked

- No gap was open while the bot was built, so no paper `opportunity` row exists yet; the live path beyond the scan
  is covered by the fork proofs and by reading, not by a paper capture.
- The vault source was read for IV-NEST-16 (same ICHIVault family, attempts:3014), not again for these two
  addresses; the bot relies only on what deposit / withdraw / the swaps pay inside the transaction.
- The vault owner can change `hysteresis`, the deposit maximum or the TWAP periods; then `deposit` reverts (gas only
  when sent; the scan shows 0 first).
- The gain is paid in native HYPE, so the bot wallet's native balance is both gas and profit.
- The live branch (signer send) is the same code shape as the live sibling bot; it was not exercised in paper.
- Whether Morpho still holds enough WHYPE for the 64k / 120k sizes at send time: a size it cannot lend scans 0.
