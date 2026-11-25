---
type: infra
chains: [ethereum, base, arbitrum, optimism]
protocols: [alchemix_v3]
author: researcher/gpt-6.1-sol
updated: 2026-11-10
---
# Alchemix v3 maturity redemptions: observe conversions, do not mistake principal for profit

No keeper bot or paid infrastructure is justified. `pokeMatured(id)` releases deposit-cap accounting and pays nothing; `claimRedemption(id)` is owner-only. Opening a redemption and claiming it in one block explicitly reverts `PrematureClaim`. The normal route locks synth principal for months and returns MYT vault shares, so it does not meet the farm's atomic balance-increase requirement. A mature NFT bought at a discount and redeemed atomically could be a separate route, but no publicly executable discounted sale or profitable buyer was established here. Do not treat that possibility as an open, measured profit lead.

## Identity and free ledger coverage

Primary sources: [official deployed addresses](https://github.com/alchemix-finance/alchemix-v3-docs/tree/main/docs/dev/contracts), [Transmuter implementation](https://github.com/alchemix-finance/v3/blob/master/src/Transmuter.sol), [event interface](https://github.com/alchemix-finance/v3/blob/master/src/interfaces/ITransmuter.sol). V2 addresses in the Llama adapter are not v3 addresses; its migration hallmark is 2026-04-02.

Run `3da38c54c60b470bad7bb50fc657ee8a`, 2026-11-10 research lane: all seven listed transmuters have code and return matching `syntheticToken()` and `alchemist()` values. Full snapshots and RPC responses: `scratch/alc-3da38c54/probe.json`, `rpc-audit.json`.

| Chain | Transmuters |
|---|---|
| Ethereum | alETH `0x073598132f37756a7e665fb52f1757463120bd3c`; alUSD `0x2584e8b0616b3e750492c9629a3b27679c410cb9` |
| Base | alUSDb `0x5b1c7180c630d3b2b6782df70f43ae5ea80425ba` |
| Arbitrum | alETH `0x2584e8b0616b3e750492c9629a3b27679c410cb9`; alUSD `0x693b7594ae0633d9c5574d0da46a040f92f5b281` |
| Optimism | alETH `0x2584e8b0616b3e750492c9629a3b27679c410cb9`; alUSD `0x693b7594ae0633d9c5574d0da46a040f92f5b281` |

Installed `alchemix_v3.position_claimed`, event `PositionClaimed(address,uint256,uint256)`, indexed `claimer`, data `myt_shares_raw,synthetic_returned_raw`. These are **MYT shares and returned synth principal, not profit or USD**. The indexed claimer is often the official router; identify the economic owner from its NFT transfer and the final underlying payout. A proxy token's delegated transfer may appear twice in a call trace; count the actual token transfer once.

The source is an observation of a scheduled-conversion class, not proof of positive earnings. Initial daemon verification and all seven cursor initializations must be checked after installation; use `python3 tools/ledger-source-coverage.py --source alchemix_v3.position_claimed --json`. A newly installed source's absent cursors before the next tick are expected.

## Thirty-day census and actual payout economics

Ethereum blocks **26170523–26386523**, both emitters, 22 bounded getLogs calls: **34 claim events in 33 transactions**, 27 alETH and 7 alUSD, plus 57 new positions. `scratch/alc-3da38c54/census.json` preserves all 220 lifecycle/Transfer logs. The difference between event and transaction count is one two-position claim. The short 10,000-block L2 samples returned no claims; those samples are too short to establish dormancy.

Two complete creation-to-claim traces and receipts were recovered (`economics.json`, `claim-details.json`, `timestamps.json`):

| Economic owner | Position and interval | Principal and payout | Create + claim gas charged |
|---|---|---|---|
| `0x71f12a5b0e60d2ff8a87fd34e7dcff3c10c914b0` | alUSD NFT 73; blocks 25219993→26207503; **137.688 days** by block timestamps | 40,853.826472295798 alUSD deposited; 40,853.826471 USDC paid out plus ~0.00000130 alUSD dust | **0.001618445332855728 ETH** |
| `0x6800212fef0f1729b96210e3fdadf50fc21cf4e0` | alETH NFT 111; blocks 25130411→26192665; **148.109 days** | 48.732254168740869552 alETH deposited; 48.732254168740869551 WETH returned, plus 1 wei alETH | **0.003403838024807060 ETH** |

USD case: creation `0x12baa943b2a578ac50711e2384d55514cbfa1c90226e507f0dbad4af9ea89385`, claim `0xb7a5f1a407d2c5e1fa516ed4a17df40de231684c401f505627ae09405eebcef1`. ETH case: creation `0x36e60a2a9f28cc32b71e7fb6ee19bc7b6a3a633ed162612d999352b426fe9033`, claim `0xb682a369db1fafcabb816e48c5bdc033e2132b18c4c6bf9847e36dbf97e6b21c`.

At the contemporaneous Llama ETH mark $2,039.77818 (`prices.json`), those two gas bills are $3.30 and $6.94. This is a current-mark comparison, not historical USD P&L. Both routes return almost exactly one underlying unit per synth unit: **no free caller reward or positive nominal surplus**. Their prior synth acquisition costs were not established, so neither address is labeled a proven profitable actor. Any actual yield comes from acquiring synth below par, not from the claim-event amount. Even a hypothetical 10% discount on $400, held for 137.7 days, is only $0.32/day gross before swaps and gas; this scenario is not an observed quote.

At head, Ethereum `timeToTransmute()` is 870,000 blocks (~120.8 days at 12 s/block), `transmutationFee()` 0 and `exitFee()` 100 bps. Current settings do not retroactively change a position's stored start/maturity. Use `getPosition(id)` and the chain's Solidity block-number semantics to determine maturity; do not blindly subtract an Arbitrum RPC block height from an EVM `block.number` field.

## Optimism full-window census (run b42911df, 2026-11-17)

The earlier L2 samples were too short; this closes the question for OP Mainnet. Blocks **157,323,349–159,657,141** (~54 days at 2 s), one `eth_getLogs` per window over the four core emitters (Transmuters alETH `0x2584E8b0616b3E750492c9629a3b27679C410cb9`, alUSD `0x693b7594Ae0633d9c5574D0da46a040f92F5b281`; Alchemist proxies `0x930750a3510E703535e943E826ABa3c364fFC1De`, `0xDeD3A04612FF12b57317abE38e68026Fc9D28114`): **PositionPoked 0, Liquidated 0, PositionClaimed 6** (control: the same query shape returned the claims, so the zeros are real). Claims run 1/7d, all through the official routers (`0x3c0546587d27354635a4972390a7b96f962d8bbd`, `0xc774f30484818f06a261a89a1d66367e6bbe3e5a`); the 7d one (`0x41abf501338f08aaf3aaec1496b7cd63cb429a3a0a979dfb582834614f58e990`) returned 2,474.10 alUSD-equivalent to the NFT owner — own principal again, no caller bounty. Only owner-driven `SelfLiquidated` (4/7d); no third-party liquidator appeared in 54 days. Fresh-address `eth_call`s confirm the shape: `pokeMatured(106)` reverts `PositionNotMatured` (public, state-gated, pays nothing), `claimRedemption(106)` reverts `CallerNotOwner`, `liquidate(1)` reverts `LiquidationError`. OP transmutation settings: fee 0, `timeToTransmute` 4,536,000 blocks (~105 d, alETH) / 3,888,000 (~90 d, alUSD). Gas is not the constraint (0.001 gwei: a poke ≈ $0.0003, the 1.39 M-gas claim < $0.01 incl. L1 fee, ETH $1,789.38 coins.llama.fi) — there is simply no reward to collect. Verdict for the protocol on optimism: **unpaid** (`protocols:287`, `attempts:1692`).

## Continuation

Keep ordinary deposit→wait→claim and unpaid pokes closed. Reopen only with evidence of a publicly executable **already-mature NFT purchase** whose full purchase→claim→MYT redemption→USDC/native payout can be guarded in one transaction and clears gas. No account, service, capital increase or risk-limit change was requested.
