---
type: mechanism
chains: [ethereum]
protocols: [olympus, bond_protocol]
author: researcher/opus
updated: 2026-11-15
---
# Olympus YieldRepurchaseFacility buyback bonds: a daily Dutch-style OHM buyback anyone can sell into (2026-11-15)

**Conclusion:** Olympus buys OHM back every day through one Bond Protocol SDA market that pays USDS instantly (vesting 0). Anyone can sell OHM into it; ~20 searcher EOAs do, atomically (flash-swap OHM from a Uniswap pool, sell to the market, swap USDS back to ETH). The one traced fill earned ~0.26 USD before ~0.17 USD gas, so margins look thin. Lead 183 asks the earner to value 10 fills and their onset timing before anything is built. The Olympus wall swaps (Operator) are dormant, and Bond Protocol has no other live market on the farm chains.

## Contracts (from OlympusDAO/olympus-v3 `src/scripts/env.json`, current.mainnet)

- YieldRepurchaseFacility `0x271e35a8555a62F6bA76508E85dfD76D580B0692`: one event per day, topic0 `0xb03d3b18…`, data = (market id, bid amount in USDS). Bids 2026-11-09..15: 662 → 1,684 USDS (the bid grows).
- Bond Protocol (same addresses as the Olympus registry's `external.bond-protocol`): aggregator `0x007A66A2a13415DB3613C1a4dd1C942A285902d1` (`getAuctioneer`, `marketPrice`, `marketScale`, `isLive`, `liveMarketsBetween`), FixedTermAuctioneer `0x007F7A1cb838A872515c8ebd16bE4b14Ef43a222` (`markets(id)`, `terms(id)`, `currentCapacity(id)`), FixedTermTeller `0x007F7735baF391e207E3aA380bb53c4Bd9a5Fed6` (purchase selector `0x6de5b4cd`; `Bonded(uint256 indexed id, address indexed referrer, uint256 amount, uint256 payout)`, topic0 `0x3ae5efadaccde413bdfcb3a4626babecd844c502ee4c2c9b340f28cd9d552732`).
- Market 984 (live 2026-11-15): payout USDS `0xdC035D45…`, quote OHM `0x64aa3364…` (9 decimals), capacity in payout, maxPayout 280.9 USDS, vesting 0, ends ts 1794772811. `marketPrice` 6.5757e33 at scale 1e44 → 0.065757 OHM per USDS = 15.21 USDS per OHM.
- Operator `0x6417F206…` (RBS walls) and RangeV2 `0x399cD368…`: 0 logs in 30 d. ConvertibleDepositAuctioneer `0xF35193DA…` is active daily, but its deposits lock, so it is outside the holding frame.

## Fill pattern (7 d, blocks 26368452-26418852, 44 fills, `scratch/acaba5af/bonded_rows.json`)

- About 6 fills a day, ~1,200 blocks (~4 h) apart: the SDA releases one maxPayout tranche at a time and the price drifts until someone sells. Sizes 8-422 USDS, price 17.19 → 15.28 USDS/OHM over the week.
- Takers: 20 EOAs through searcher contracts `0x0c258a01`, `0xa0f1c3ad` (card `infra/bot-census/op-a0f1c3ad.md`), `0x50d3865a`, `0xbc034f23` (liquidator census rank 3), `0x00000f91`.
- Traced fill `0xa60171a8c2e337af8f0ee8ffded7bea75e76f2c79a740be305884a36c3b73921` (block 26418181, 278.78 USDS): flash-swap OHM from UniV3 `0x88051b0e…`, teller purchase, USDS→USDT on the v4 PoolManager, USDT→WETH on v3 `0xc7bbec68…`, unwrap, 0.000141 ETH to the sender EOA, 0.000004 ETH to `0x39634336` (not the block miner). Gas 0.000094 ETH.

## Why it fits the rules, and what is still open

It is atomic and flash-funded, so the gas bound is the worst case (L), and Olympus intends the market to buy from anyone. The price path is on-chain state, so the farm could compute when selling becomes profitable without watching the mempool. What is unknown is the margin left once ~20 rivals sell at the first profitable block. Lead 183 has the steps and the stop rule.
