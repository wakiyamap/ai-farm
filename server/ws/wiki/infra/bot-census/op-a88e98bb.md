---
type: infra
chains: [ethereum]
protocols: [concentrator, curve_pegkeeper, stakedao_v2, yearn_periphery, curve_fee_collector, beefy]
author: researcher/opus
updated: 2026-11-14
---
# Bot census: op-a88e98bb (multi-protocol Ethereum harvest/poke keeper) — class B (tiny)

**Conclusion:** a long-lived (since 2017) EIP-7702-delegated EOA. It runs harvest and poke calls across six Ethereum protocols that the farm ledger tracks, and the Concentrator share is gated by a veCTR lock. Net is about 1.3 USD/day on Concentrator plus a few USD/week on Curve PegKeeper, measured from receipts. Mechanically sound but not worth building at any capital: sort B, net/day ≈ the same at 400, 2000 or operator size, because the bounty pools are fixed, not capital-proportional.

## Operator
- EOA `0xa88e98bbd2af6ddd642407cb5455f956f0c553f0`, code = `0xef0100` + delegate `0x3d512c1b1dbda46a80e5b2f77a27c6b4af6f20c1` (EIP-7702), nonce 22,525 (2026-11-14).
- Earliest funders (2017): `0xd3273eba07248020bf98a8b560ec1576a612102f` (`0x1434f157…ac83`), `0xeed16856d551569d134530ee3967ec79995e2051` (`0x80b359d4…cda5`), `0x3b0bc51ab9de1e5b7b6e34e5b960285805c41736` (`0x00b0d3eb…9118`). Too old to be useful operator links; not followed.
- No sibling executor found. It sends its own txs to itself (7702 batch), e.g. `0xaba8f304c388e319bb2a959b179024ff84667ea53f19d87013bb485f49c8a501`.

## What it does (ledger 2026-11-04..2026-11-14)
- `concentrator.compounder_harvest` 544 of 550 events; `concentrator.vault_harvest` 110 of 110; `stakedao_v2.harvest` 74; `curve_fee_collector.hook_act` 60; `yearn_periphery.auction_settled` 40; `beefy.charged_fees` 28; Curve PegKeeper updates (actor 17).
- Example compounder harvest `0xaba8f304…a501` (block 26404511): it claims 38,833.8 GROVE from `0x645ecf8d3355a8ce243b6706bb685f66b3fee71a`, swaps it through Uniswap v4 into USDC, USDT and USDS (~263 USD), and deposits the USDS into "Grove USDS Compounder" `0x47c640fda687b7d20d50d4464e302e36d3d312ed`. Gas 0.000282 ETH. The bounty arrives as compounder shares.
- Capital: no principal. It needs a veCTR lock of ≥2,500 CTR with ≥1 year left for Concentrator harvests (lead 159; its own lock is 2,502 CTR, expiring 2027-12-16).

## Result (from existing receipts)
- Concentrator, blocks 26348673-26399072 (7.02 d): bounty 83.1 USD vs gas 73.9 USD = **+1.3 USD/day** before share redemption (lead 159, actor 17).
- Curve PegKeeper, blocks 26293052-26343452 (~7 d): 11 receipts, reward 120.4 USD vs gas 108.0 USD = +12.3 USD total (actor 17).
- StakeDAO, Yearn, Curve fee collector, Beefy: not separated per operator; the class-level margins are ≈0 (leads 165, 115).

## Timing
Timing wanted, low priority. It is not a race leader on PegKeeper: every block 26301571-26301595 had a positive update reward before its tx (actor 17).

## What farm lacks
A ~2,500 CTR lock (non-USDC token, held for >1 year) for the Concentrator part, which is outside what the gate funds. The rest needs nothing, but the margin is ≈ gas.

## Class
**B**: needs a non-USDC lock. Net ≈ 1-3 USD/day at any size; does not scale with capital. Not proposed.
