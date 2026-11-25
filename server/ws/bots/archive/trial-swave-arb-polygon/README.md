trial: SWAVE SetToken NAV redemption against its Polygon V3 pool, flash funded in one transaction.

## Route and competition

SWAVE holds native USDC (0x3c499c54...3359, the farm's configured Polygon USDC). A 25 native-USDC Morpho flash loan buys SWAVE along the USDC -> WPOL -> SWAVE V3 path (fees 500 and 3000); the public DebtIssuanceModuleV2 redeems it for native USDC; Morpho pulls its 25 USDC back and the rest goes to the bot wallet. The executor reverts unless the bot wallet's native USDC balance grows by `minProfit`. USDC.e is not touched: the incumbents' two USDC.e legs (flash in USDC.e, swap to and from native USDC) are gone, which saves about 170k gas. Its constructor contains the owner only; all targets and the path are call arguments.

The 7 days ending 2026-11-21 05:16Z have 15 SWAVE redeem events from the module (complete scan in `scratch/trial-set-arb-polygon/swave-7d-logs.json`, blocks 97,280,000-97,688,500). Eight are atomic takes: five from 0xc3afb378 via 0x91a7fbae and three from 0xde0a99fb via 0x3cb2452c. The other seven are inventory redeems by 0xc3afb378. The eight atomic takes sit at tx indices 0-152; the two sampled priority fee caps are 28 and 506 gwei (txs 0xd7aa2a37 and 0xddbc69d3; `tx-old.json` and `tx-latest.json`). Measured incumbent payouts are 0.129-0.301 USDC.e per take in `scratch/r3c67/setmeasure.json`. Most recent take: 0xddbc69d32ebc34aab50c6d1d95d1bc397f87acd61e8535655ecf743701835caf, block 97,684,358, 2026-11-21 03:33Z. The bot aims to win a minority of these, sending only when its gross is at least twice its gas cap. It does not watch pending transactions.

## Fork proof

`scratch/trial-set-arb-polygon/proof-usdc.py` (fix run 54a3d48c, 2026-11-21; result in `proof-usdc-result.json`) resets Polygon to block 97,684,357 (the parent of that take), deploys, funds, and sends three calls with the 25 USDC size:

| call | tx | status | gas | owner native USDC |
|---|---|---|---|---|
| guard (minProfit 1e9) | 0x85dafb5348c3d86b4aed7bb0a6d9101494c502e663cbfbea99351d43b7e81be2 | 0 | 513,782 | unchanged |
| non-owner | 0x1bbccb21639bdf6876e01257a61900d6a6ee45ba48e5b880e42dd74cb8be7912 | 0 | 30,130 | unchanged |
| success (minProfit 1) | 0xe0be2fc279587c588d82efae3b5b82b26f57f614aa54cfbaef7d407afc37c5cb | 1 | 410,975 | +0.209510 |

Owner USDC.e is unchanged; the executor ends with 0 USDC, USDC.e, SWAVE and WPOL and 0 allowances to the router and Morpho. Morpho held 138,542 native USDC at that block. `executor-runtime.hex` in this directory is `eth_getCode` of that fork deployment, 0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352 (owner 0x1111...1111 = the paper owner).
The bot's exact `calldata(1)` with that runtime as a code override returned 209510 native USDC units in an archive relay `eth_call` at the same parent block, and `calldata(10**9)` reverted with `NoProfit(209510, 1000000000)` (`scratch/trial-set-arb-polygon/selftest-usdc.py`, `selftest-usdc-result.json`).

Before the fix (review f1a26021) the executor borrowed and paid out USDC.e, which the gate does not count: 0.204496 USDC.e for 583,612 gas at the same block.

## Limits and operation

The bot checks every 30 s with one `eth_call`, then reads base fee, estimates gas, and simulates the exact guarded call only when the first call shows at least $0.05 gross. It caps gas at 3,000,000, its signed gas cost at $0.95 using 0.20 USD/POL, and the bid at half of simulated gross. The signer provides the final signing time loss check. Capital is $10 native POL for gas, with no USDC principal; winnings arrive in the bot wallet as native USDC, which the gate counts and sweeps. Worst case is signed gas; principal is flash borrowed and repaid atomically. Its first chance after live start is the next pool price gap, timing unknown.

Base read cost: 2,880 `eth_call` per day x 26 CU = 74,880 CU/day, plus about 100 CU per opportunity. Cap 95,000 CU/day. At 0.53 USD per 1M CU, base cost is about $0.040/day. No feed filter. Logs under `logs/bot.jsonl` record each opportunity and simulation or send, won/lost, gas used, and the winner's block.

This bot covers SWAVE only. CMI and IAD are not routed.
