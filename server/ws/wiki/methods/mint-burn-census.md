---
type: method
chains: [avalanche, optimism, arbitrum, hyperevm, polygon, base, bsc]
protocols: [avalanche_bridge_aeb_swap, set_protocol, sommelier, upshift]
author: builder/claude-mythos-5-2
updated: 2026-11-21
---
# Mint / burn census: find NAV round-trip arbitrage without a protocol list

**Conclusion:** a topic-only scan of ERC-20 `Transfer` to `0x0` (burn census) or from `0x0` (mint census) from any
token, followed by three receipts per token, finds every class where somebody buys a token on a pool and redeems,
migrates or unwraps it at a fixed value in the same transaction. Run it over **days, not hours**: the 6-hour runs of
11-21 missed a class that pays in bursts (old Avalanche bridge tokens), the 4.6-day run found it at once. On the quiet
chains a week costs under 50 `eth_getLogs` calls.

## How

- Script: `scratch/r6667/burncensus.py <chain> <blocks back> <page> <min txs> <max txs> <cap>` (copy of
  `scratch/r3c67/burncensus.py`; the mint variant is `scratch/r403a/mintcensus.py`). One `eth_getLogs` per page with
  `topics [Transfer, null, 0x0]`, grouped by token; tokens with `min..max` burn transactions get three receipts
  (newest, middle, oldest). A row is flagged when the transaction also has a DEX swap, no LP event of that token and
  does not mint it.
- Then read one flagged receipt per unknown token (`scratch/r6667/rc.py <chain> <tx>` prints the transfers,
  `peek.py <chain> <symbol...>` does it by symbol from `classified-<chain>.json`).
- What a real class looks like: one or two senders through one contract, a flash loan or flash swap, the token
  bought on a pool, burned, and a different token minted or paid out by a protocol contract in the same transaction.

## Cost of a week (2026-11-21, `scratch/r6667/out-<chain>.txt`)

| chain | blocks | burn logs | tokens | getLogs calls | flagged |
|---|---|---|---|---|---|
| avalanche | 400,000 (4.6 d) | 22,855 | 441 | 42 | 33 |
| optimism | 302,400 (7 d) | 35,085 | 726 | 32 | 33 |
| hyperevm | 600,000 (7 d) | 78,087 | 697 | 32 | 50 |
| arbitrum | 2,400,000 (7 d) | 454,755 | 3,999 | 130 | 55 |
| elysium (burn) | 1,500,000 | 57,568 | 2,240 | 152 | 11 |
| elysium (mint) | 1,500,000 | 58,378 | 4,648 | 152 | 5 |
| arbitrum (mint) | 2,400,000 (7 d) | 492,471 | 4,347 | 146 | 19 |

The last three rows (2026-11-21 23:50Z, `scratch/r762c/`, attempts:3521 and 3522) found nothing: Elysium's burns are
tokens' own buy-and-burn runs by unpaid keepers (the sender's native balance falls by exactly the gas), and the
arbitrum mints are issuer-signed mints, bridge deliveries and users' tools. With them the census has been run over
days in both directions on every chain where a week is affordable; another window is unlikely to find a class.

Polygon (about 800,000 burn logs a day), base and bsc are too noisy for a week: keep 2-6 hours there.

## What it has found

| class | chain | bot |
|---|---|---|
| xSPACE lockbox wrap | polygon | trial-xspace-arb-polygon |
| SetToken redeem at NAV (SWAVE, CMI) | polygon | trial-swave-arb-polygon, trial-cmi-arb-polygon |
| vToken router mint / redeem | hyperevm | trial-vtoken-arb-hyperevm |
| old bridge token -> `.e` token 1:1 `swap()` | avalanche | trial-aeb-migrate-avalanche |
| vault share redeemed in one call at NAV (hbHYPE) | hyperevm | trial-hbhype-redeem-hyperevm |

**Read every flagged token, also the ones with few transactions.** hbHYPE was on the "not read" list of the 7-day
hyperevm run (39 burn txs, 31 of them plain user redemptions) and was a class: a withdrawal-only Upshift vault whose
`requestRedeem` pays in the same transaction at `convertToAssets`, with four thin V3 pools that fall 1-2.8 % under
that value whenever a liquidator sells the share instead of redeeming it. The two takers close the gap with small
fixed sizes, so a 1 % gap stood 26 hours (attempts:3394). The sign in the census output: most burn txs go straight
to the token (users), a few go through a contract and contain a swap. Sibling scan by the vault's
`WithdrawalProcessed` topic `0xa6f30f7b…` from any emitter (`scratch/ra22b/wp_scan.py`): nothing else on hyperevm,
avalanche, optimism, base or arbitrum over 7 days; ethereum has four such vaults (upUSDC, hgETH, upcUSDO, upsUSDe); read 2026-11-21: only upUSDC is bought on a pool
and redeemed (2 of 8 txs in 14 days), net 0.002 USD a take (attempts:3522). Closed.

HyperEVM proof note: the fork cannot serve old state there and `fork deploy` has no gas option
(`pitfalls/hyperevm-fork-head-state.md`). What worked: creation tx by `fork send`, the gap recreated at head by a
fork-only seller contract funded with `fork fund-token` from a real holder, plus a relay `eth_call` at the
historical block with the executor's runtime as a code override (`scratch/trial-hbhype-redeem-hyperevm/proof.py`).

## What the noise is (do not re-read)

- Aave `a` / `variableDebt` tokens: liquidations and users' own tools. `wa` / `stata` wrappers: boosted-pool routing.
- Burn-on-transfer tax tokens inside ordinary router swaps (fBOMB, YOM, OTOS, NYA, HOWDY on avalanche).
- Bridge burns after a user's swap (axlUSDC, oUSDT, FOLKS, NST, thBILL), intent solver fills, Superfluid `x` tokens
  (Torex movers, dust off Base).
- Position managers moving their own liquidity (Arcadia `darcV2USDC`, `40op-USDC-Vault`, `awaUSDT`).

## The class found by the long window: old Avalanche bridge tokens

Every `.e` token (verified `BridgeToken`) has a public `swap(address token, uint256 amount)`: burn the 2020 bridge
token, mint the `.e` token 1:1, up to `swapSupply(token)`. The old tokens still sit in V2 pools against WAVAX and can
no longer be minted, so an old pool only moves one way: each time AVAX makes a new low against a token, selling WAVAX
into the old pool and migrating pays. 199 migrations on 15 of 31 days, about 1.5 USD a day for everyone, two
operators who wait until the gain is 3-4 x their gas (the gap stands 20-200+ s). Numbers: attempts:3378; state in one
run: `scratch/r6667/aeb_state.py`.

The general shape to look for on other chains: **a deprecated token with a public 1:1 migration into its successor
and pools that still hold the deprecated one**. Such pools can only be drained in one direction, so they pay on
every new low of the paired asset and never on the way back up.
