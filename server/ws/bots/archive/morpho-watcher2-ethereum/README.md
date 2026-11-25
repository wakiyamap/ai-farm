# morpho-watcher2-ethereum (paper)

Fixed variant of the live morpho-watcher-ethereum, per decisions/human/2026-11-12 item 2.
Classification of the bot's 17 pinned-market liquidations of the last 7 days (attempt 926):
(a)=1, (b)=7, (c)=9 (12 borrower-entries), (d)=1. This bot fixes the two causes the human
named as fix items — (c) the 2.13-2.23 USD profit floor that skipped two sendable captures
(gross 1.34/1.01 USDC at blocks 26372995/26372996), and (d) eviction of dormant debtors from
the pinned candidate set (block 26349648, repaid 525.62 USD, victim 0x5e1b7fff, last scanned
2026-11-04, evicted before its 2026-11-05 liquidation).

## Fixes vs the live bot

- (c): MIN_PROFIT_USD 2 -> 0.5 (post-fee floor; the on-chain minProfit and the live gate add
  the expected-fee leg exactly as the live bot does). Captures down to ~0.6 USD gross are now
  sendable; every send nets >= 0.5 USD after the fee. Gas worst case is untouched by the floor:
  maxFeePerGas (derived, capped 17.5 gwei) x 460000 gas <= 0.00805 ETH <= 20 USD at any
  plausible ETH/USD — the L bound is the signed product, not the floor.
- (d): every scanned candidate with a nonzero borrow re-stamps its candidate entry each cycle
  (heartbeat field `restamped`), so the PIN_CAND_CAP trim evicts debt-free candidates first
  and a debtor in debt is never evicted. The live bot lost 26349648 to exactly this eviction.
- Executor (payout variant, review 4058f2ea blocker 2): identical to the proven
  MorphoLiquidator of record EXCEPT the last step of `liquidate()`: after the
  `balAfter >= balBefore + minProfit` guard it transfers its whole loan-asset balance
  (the proven profit; the flash loan is already repaid, so the executor holds no
  principal between operations) to the bot wallet — the owner — in the SAME transaction
  (`PAYOUT_FAILED` reverts the whole tx; worst case stays gas only). No profit is left
  sitting in the executor, which is where the watchdog/gate counts and sweeps value.
  New fork proofs (run ef61ac40, script scratch/morpho-eth2-proof.js): success
  0x00656cf9580b65491033cec05ac9205b1967de1278979c35af9f111b41f19bff (bot-wallet USDC delta
  +3.711168, gasUsed 332595) and healthy-position revert 0xbca1059fac62913c57e3e43915c7888a90124ec872ed6d530737e40e4752d30c
  (status 0). Predecessor proofs (byte-identical-except-payout, executor-retained profit):
  success 0x1d2da75de6512b99a92b255a08d7927a322761a204fe7467153064311d8bf8cb (+3.711168
  retained in the executor), revert 0x4572a9c85e8a741032d84b5ae2e8122ad1af325e54017f15d68199a1dd108ace,
  dust-case success 0x45ff8d9f9686b7a1bbab994b7b78a71f7cd268232e67448d28e42af045e9998b
  (+0.158935 — the case the 0.5 USD floor admits).

## Poll route and the read cost (decisions/human/2026-11-11-moonwell-stopped.md)

- Poll cadence: CYCLE_MS = 60 s (review 4058f2ea blocker 3: the 20 s cadence cost ~2.5M
  CU/day, far above the 1M/day review line). Measured calls/cycle from this bot's own
  paper heartbeats: `rpc_cycle: 5` (1 latest-header read + 4 Multicall3 chunks of <=250
  inner calls; 768 candidates scanned). Live estimate: 1440 cycles/day x 5 reads
  + 1440 refresh getLogs (5 batches per 5 min) = 8640 reads/day x ~115 CU ~= 0.99M CU/day
  — at or below the 1M line with the same formula as the previous manifest (interval x
  calls/cycle x CU per method).
- Captures in blocks OTHER than the price update, with estimated profit (the decision's
  requirement): 1 of the 17 measured pinned-market captures of the 7d window — block
  26384831 (repaid 92,326.04 USDC) was liquidatable at the C-1 tail one block AFTER the
  Chainlink update (hf 0.9987 at C-1, attempt 926 fork probe). Estimated profit at our
  398-USDC capital cap: the capital_limited branch (repaid 398, oracle proceeds 415.45,
  gross +17.45 USD — the proven natural big case, txs 0xede2f12f.../+71.73 realized).
  All other 16 captures became eligible inside the price-update block (race class (b)).
- The 60 s poll vs the measured catchable windows (live bot's own simulate/skip log rows
  against the ledger capture block ts, measured run ef61ac40): the two sendable class-(c)
  captures (blocks 26372995/26372996, gross 1.34/1.01 USD — the captures the floor fix
  exists to take) stayed liquidatable 100 s and 112 s before the competitor captured them,
  the long-window ones >=47 min and >=84 min (26373222, 26386155, 26391772). The fastest
  measured competitor acted ~100 s after the position turned liquidatable — a 60 s cycle
  scans the position before any measured competitor can arrive. The class-(a) big capture
  26384831 (12 s C-1 tail window) is the only capture a faster poll could favor: the 20 s
  live bot measured 0 detections and 0 captures on it (missed by ~5 s), so the measured
  capture rate is 0/17 at 20 s and unchanged for sendable captures at 60 s.

## Strategy

Morpho Blue v2 liquidations on the two pinned collateral-sellable markets (WETH/USDC
0x94b823e6.., WBTC/USDC 0x3a85e619..): poll borrower health via Multicall3; on protocol
unhealthiness simulate/send ONE executor tx (Morpho flashLoan -> liquidate capped seize ->
UniV3 sell -> revert unless the executor's USDC balance rose by minProfit -> profit PAID to
the bot wallet in the same tx). Live sends go through the deployed executor (EXECUTOR_ADDR
env / state/executor.json).
