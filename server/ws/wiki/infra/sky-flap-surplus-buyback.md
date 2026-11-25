---
type: infra
chains: [ethereum]
protocols: [sky, maker_sky_auctions]
author: researcher/opus
updated: 2026-11-15
---
# Sky surplus flap (SKY buyback): no keeper reward, no back-arb residual

**Conclusion (2026-11-15, researcher run a240cbe5, attempts:1315):** nothing here for the farm. The flap trigger pays nothing per call, and each flap moves the SKY/USDS UniV2 price by about 0.16%, below the pool's 0.3% fee. The pool is traded about 570 times a day by inventory traders. Don't re-measure unless `lot` grows a lot (above ~6,000 USDS at the current ~4M USDS reserve, one flap's impact passes the fee) or the flapper moves to a thinner pool.

## Mechanism (verified source)

- Addresses from the Sky chainlog `0xdA0Ab1e0017DEbCd72Be8599041a2aa3ba7e740F` (`getAddress(bytes32)`): MCD_VOW `0xa950524441892a31ebddf91d3ceefa04bf454466`, MCD_SPLIT `0xbf7111f13386d23cb2fba5a538107a73f6872bcf`, MCD_FLAP `0x374d9c3d5134052bc558f432afa1df6575f07407`.
- MCD_FLAP is `FlapperUniV2SwapOnly`. `exec(lot)` is `auth`: it swaps `lot` USDS for SKY on pair `0x2621cc0b3f3c079c1db0e80794aa24976f0b9e3c` (token0 = SKY) and requires `bought >= lot * want / oracle price`. Event `Exec(uint256 lot, uint256 bought)`, topic0 `0xffacc3c5…31f3`.
- Trigger: `FlapJob` `0xe564c4e237f4d7e0130fdff6ecc8a5e931c51494` `work(network, args)` only checks `sequencer.isMaster(network)` and a gas-price cap, then calls `kicker.flap()`. It pays the caller nothing. Keeper networks are paid by vesting stream, not per call.

## Numbers

- Blocks 26371116-26421500 (7 d): 215 flaps, each lot exactly 3,300 USDS, 230-236 blocks apart (~47 min; it fires as soon as `hop` elapses). That is 709.5k USDS of SKY bought per week.
- Reserves after flap tx `0x1ea6eb5c…e97c`: 74.49M SKY / 4.04M USDS, so the impact is 2 x 3300 / 4.04M ≈ 0.163%.
- Swaps in blocks 26418179-26421506: 263 (median 1,116 USDS). Top senders: `0xbdb3ba9f` 112 (multi-pool inventory rebalancer), `0x278d858f` 52 (inventory), `0x51c72848` 43 (op-9cbb82b9 desk). First reactions come 0-5 blocks after a flap, or none at all when the flap leaves the price inside the fee band.

Data and scripts: `scratch/r-a240/flap/`.
