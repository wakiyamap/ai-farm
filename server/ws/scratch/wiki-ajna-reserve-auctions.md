---
type: infra
chains: [ethereum, arbitrum, optimism, polygon, base]
protocols: [ajna]
---
# Ajna Claimable Reserve Auctions (CRA): alive on 4 chains, too small for a farm bot (2026-11-11)

**Conclusion.** Ajna's reserve auctions are a real fee/revenue auction class. Anyone may call `kickReserveAuction()` on a pool. Anyone may then `takeReserves(maxAmount)`: the taker pays AJNA at a Dutch price, the AJNA is burned, and the taker receives the pool's quote-token reserves. The class's whole real-valued flow is about **1.5 USD/day summed over Ethereum, Arbitrum, OP Mainnet and Polygon**, and it arrives in weekly batches of cent-to-dollar lots. That is below the 1 USD/day-per-bot bar. **Do not build.** The new ledger source `ajna.reserve_auction_take` watches it. The OP Mainnet lot below is a one-off that is still open.

## Mechanism (measured on chain, run 1a4364c4)
- Events: `KickReserveAuction(uint256 claimableReservesRemaining, uint256 auctionPrice, uint256 currentBurnEpoch)` topic0 `0x3dacf6b1...df960`, and `ReserveAuction(uint256,uint256,uint256)` (the take) topic0 `0x21157129...4d699`. Nothing is indexed. Amounts are WAD (18-dec normalised) quote units. The price is WAD AJNA per quote unit.
- The start price is about 1e9 AJNA per unit of claimable value, and it halves every hour. Observed takes come 13-23 h after the kick on Ethereum, about 31 h on Polygon and about 36 h on Arbitrum (near-zero price). Crossing times are therefore precomputable, so this is not a mempool race.
- **The kicker is not paid.** The trace of the Arbitrum kick `0xd4579d02...5261` shows no transfer to the caller. Kickers are unpaid maintainers: `0x953c1ba7029c92741a1739dcd18a8a462109b618` batch-kicks on ETH/ARB/Polygon, and `0x4dc9d8184e15f23f68e0356920a7f2a5f7a1f080` kicks on ETH/OP.
- An atomic route exists, so it fits L. Ethereum take `0x37544606...a017` by `0x888f4aca2483d5201e1218e368a21847c8e14188` used a Morpho WETH flash loan of 0.00535 WETH, bought 11,818 AJNA on the Uniswap V2 AJNA/WETH pair `0x9fdd7f845baca6d71d93f1619250c6f0b7a58842`, took 12.82 DAI for 11,544 AJNA, swapped back and repaid. Net 0.00046 WETH (about 1 USD) at 662k gas and 0.06 gwei, plus a 0.00004 ETH builder tip.
- AJNA token (ethereum) `0x9a96ec9b57fb64fbc60b423d1f4da7691bd35079`. Liquidity: the Uniswap V2 pair held 1.27M AJNA / 0.53 WETH (AJNA about 4.2e-7 ETH, about 0.001 USD) and the 1% V3 pool `0xb79323dd...` held 0.24 WETH.
- ERC20PoolFactory (ethereum) `0x6146DD43C5622bB6D12A5240ab9CF4de14eDC625` lists 224 pools. 16 of the 19 pools that ran auctions are in it; the other 3 come from another factory (ERC721 or older), not checked.

## Measured flow
| chain | window | auctions | real-valued reserves taken | takers |
|---|---|---|---|---|
| ethereum | 30 d to block 26390101 | 19 kicks / 19 takes | about 25 USD (12.8 DAI, 1.6 DAI, about 3 USDC/USDT, about 0.0035 WETH). A 228 YUSD lot (`0x44d13160...3129`, 5 transfers in 28 d, no market) is not counted | 8 distinct: c0ffeebabe `0xc0ffeebabe5d496b2dde509f9fa189c25cf29671`, `0x888f4aca...` (flash route), `0xb00953bf65acc54dde7f6f450a52ed4f84e02f86` (11 pools in one deploy-tx), others |
| arbitrum | 7 d to block 523213269 | 6 / 6 | about 4.8 USD (4.4 USDC/USDT0, 0.0006 WETH) | `0xd3fb81805ce31bb7f952915d24fed8f4b9f63f5d` alone, at the end of the curve (paid about 0.03 AJNA total) |
| polygon | 30 d to block 97117215 | 5 / 5 | 0.017 units of lending-wrapper WETH tokens (LVTTWETH, jWETH...) | `0x3a65f764623cbbcc6bb22141c9b44a3d2082d53f` |
| optimism | 30 d to block 159391247 | 1 kick / 0 takes | **22.04 sUSD never taken** in pool `0xbb61a35aa9c5ee7662330e32e4bcb1e26ef9e78c` (wOptiDoge/sUSD). `reservesInfo()` still shows 22.04 unclaimed, last kick ts 1792466149. `eth_call kickReserveAuction()` does not revert at 07:2xZ 11-11 | none |
| base | 30 d to block 55954281 | 0 | 0 | none |

Unkicked stock (ethereum, all 224 factory pools, `eth_call` + `debug_traceCall` of `kickReserveAuction()`): 59 pools are kickable now and together hold under 1 USD of USD-valued reserves. The rest are AJNA-quoted pools (pennies) or no-market tokens (STABLE_T 70, MEME 2.3). There is no neglected stock to sweep.

## Why not worth it
- The uncontested part (Arbitrum and Polygon, taken at a near-zero price) is under 1 USD/day. The contested part (Ethereum) is about 0.8 USD/day gross, with flash-route and MEV takers already crossing at break-even.
- A bot would need executors on 3-4 chains plus a swap of each quote token back to native/USDC. That costs more to deploy than a month's flow.
- Reopen if `ledger query "SELECT chain,COUNT(*) FROM events WHERE source_id='ajna.reserve_auction_take' GROUP BY chain"` shows takes that are routinely worth more than 5 USD per lot. The 20-emitter cap per chain means pools outside the installed list are not seen, so rerun the stock scan (`scratch/ajna-1a43/stock.py <chain> <factory>`) before reopening.
