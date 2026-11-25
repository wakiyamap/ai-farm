# morpho-watcher3-ethereum (paper)

Shrunk-executor resubmission of morpho-watcher2-ethereum. The reviewer reproduced
morpho-watcher2's fork proofs (success paid +3.711168 USDC to the bot-owner wallet, NO_PROFIT
guard revert) and attempted promotion 2026-11-11 20:39Z; the gate then refused the executor
DEPLOYMENT: it needed 3,190,399 gas, above the 3,000,000 Ethereum farm-key limit (final for
that artifact — inbox/live/done/2026-11-11-morpho-watcher2-partial-promotion.md). This round
shrinks the deployment bytecode 13,057 -> 10,273 bytes (custom-error guards replace the
Error(string) requires, the five collateral/pool whitelist getters become internal immutables,
the unused collateral-setter path is dropped) with the bot-facing selector surface UNCHANGED
(liquidate cf1f5981, isPoolAllowed d1e71c94, setPoolAllowed 1bfa59c3, owner 8da5cb5b, sweep
62c06767, MORPHO 3acb5624). Deploy gas measured on the same shared fork: this artifact's
deploy tx 0x93255389d2abf185d3b269dd7ddfeb62cd951997171d5364beb664965297a080 gasUsed
2,076,371; the rejected 13,057-byte artifact measured 2,636,574 on the same fork and 3,190,399
in the gate's live measurement (+553,825 fixed component the local fork does not charge), so
this artifact brackets between 2,076,371 and ~2.63M — under the 3,000,000 limit either way.

Everything else is morpho-watcher2-ethereum as accepted: fixed variant of the live
morpho-watcher-ethereum per decisions/human/2026-11-12 item 2. Classification of the 17
pinned-market liquidations of the 7d window (attempt 926): (a)=1, (b)=7, (c)=9, (d)=1; the bot
fixes (c) (0.5 USD post-fee minProfit floor) and (d) (restamping in-debt candidates).

## Time-to-capture per past case (decisions/human/2026-11-12 item 2 requirement)

Measured as the liquidatable moment (this bot's own simulate/skip log rows) vs the ledger
capture block ts (run ef61ac40), in blocks using the ledger-measured block interval
(12 s/block: blocks 26372987->26372995 = 96 s over 8 blocks, ledger morpho_blue.liquidate ts):

| capture block | liquidatable->captured | blocks | counted? |
|---|---|---|---|
| 26372995 (gross 1.34 USD) | 100 s | ~8 | yes |
| 26372996 (gross 1.01 USD) | 112 s | ~9 | yes |
| 26373743 | ~2500 s | ~208 | yes |
| 26373222 | >=2836 s | >=236 | yes |
| 26386155 | >=5048 s | >=421 | yes |
| 26391772 | >=7193 s | >=599 | yes |
| 26384831 (class (a), big 92,326 USDC repay) | 12 s | 1 | NOT counted: 12 s < 60 s poll + send-to-inclusion |

Median of the counted windows ~2668 s (~222 blocks); minimum counted 100 s (~8 blocks). The
fastest measured competitor acted ~100 s (~8 blocks) after the position turned liquidatable —
a 60 s cycle plus one send always scans before it. Every counted case's window exceeds the
bot's 60 s poll interval + send time, so it counts toward expected value; the 12 s case does
not (the 20 s live bot measured 0/1 on it, missed by ~5 s).

## Read cost (decisions/human/2026-11-11-moonwell-stopped.md + 2026-11-12 item 6)

- Poll cadence CYCLE_MS = 60 s. Cadence from this bot's paper heartbeats: 5 reads/cycle
  (1 latest-header + 4 Multicall3 chunks, 768 candidates) x 1440 cycles + candidate refresh
  getLogs 288/day x 9 batches (paper logs show NINE batches, the reviewer's measurement) =
  nominal 322,560 CU/day, rounded 323,000 CU/day. At the human's 1M CU ~= 0.53 USD,
  ~= 0.17 USD/day — well under the 1M/day review line and under the expected value below.
- Expected value (counted cases only, per the decision): ~1.8 USD/day after gas at the
  measured pinned-market rate — the two 1.01/1.34-USD gross floor-admitted captures/7d
  (their fork proof +0.158935 USDC dust delta), the long-window captures, and the
  capital-capped big case gross +17.45 USD at the 398 USDC cap. EV (1.8) > read cost (0.17).
- Poll-vs-price-update requirement: 1 of the 17 measured 7d captures (block 26384831) became
  liquidatable in a block OTHER than the price update (C-1 tail, hf 0.9987, repaid 92,326.04
  USDC); the other 16 were same-block races (class (b), excluded per the decision).

## Executor (fork-proven, run a8ec3ebf, script scratch/morpho-eth2-proof.js)

One transaction, owner-only: Morpho flashLoan -> liquidate capped seize -> UniV3 sell (callback
pays the pool by transfer, no allowance) -> revert unless the executor's USDC balance rose by
minProfit -> the whole proven balance is PAID to the bot wallet (owner) in the SAME tx (a
failed transfer reverts; worst case = gas only, maxFeePerGas x 460000 signed bound <= 20 USD).
Proofs on the shared ethereum fork at reset 26328589 with THIS artifact deployed at
0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352 (executor-runtime.hex = eth_getCode of it):
- SUCCESS 0xdb57c173c4cfa3feeec069058c796372627910b103be7e1804fdaeaeb79b0082 status 1,
  gasUsed 332505, bot-wallet USDC delta +3.711168 POSITIVE (profit paid out, executor ~0).
- REVERT on the now-healthy position 0x95c3d56d807928eb6e9a07d75ce5a077c10ab0500307da66d8f3159d825bad18
  status 0 (NO_PROFIT guard: minProfit is a per-call argument).
- Deploy tx 0x93255389d2abf185d3b269dd7ddfeb62cd951997171d5364beb664965297a080 gasUsed 2076371.
The success tx hash is byte-identical to the reviewer's reproduction of the predecessor —
liquidate calldata and gas fields do not depend on the contract size. Predecessor proofs
(payout variant, 13,057-byte artifact): success 0xdb57c173… (+3.711168, gate-measured revert
0xd0b41094623f8e7b891a67af7d314a8a94fa735d3cf342eee17a30fe1171426e), dust-size success
0x45ff8d9f9686b7a1bbab994b7b78a71f7cd268232e67448d28e42af045e9998b (+0.158935), natural big
case 0xede2f12f8793e4f41120d855de4051b025a6cf827fc6acf781903cc309ce689c (+71.731107).

Constructor: [MORPHO singleton, WETH, WBTC, 0, 0, UniV3 WETH/USDC pool 0x88e6a0c2…]. The WBTC
route is armed by the bot's own one-time owner init tx setPoolAllowed(0x9a772018…, true) on
the DEPLOYED executor (the live path verifies isPoolAllowed first). Collateral whitelist is
fixed at deploy (C0..C3 immutables); a new collateral token would need a redeploy.

## Strategy

Morpho Blue v2 liquidations on the two pinned collateral-sellable markets (WETH/USDC
0x94b823e6…, WBTC/USDC 0x3a85e619…): poll borrower health via Multicall3; on protocol
unhealthiness simulate/send ONE executor tx (flashLoan -> liquidate capped seize -> UniV3 sell
-> revert unless profit rose by minProfit -> profit PAID to the bot wallet in the same tx).
Live sends go through the gate-deployed executor (EXECUTOR_ADDR env / state/executor.json).
Morpho pays the liquidation bonus (measured seize factor 4.38% of repaid debt at the 86% LLTV
cap) through public liquidate() — an intended, anyone-callable mechanism under S.
