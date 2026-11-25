# Review — 2026-11-13 11:00 UTC

Decision: **demote** (run `03c8763a7fc145fd89c67c660e037ae0`). `next_review_at: null`.

The bot is byte-identical to the last fix review (hashes below), and the earner has since closed lead 21 as `blocked_infra`. The four large purported 916-block windows were same-block Chainlink-update captures (`attempts:1101`); the remaining possible interest-bleed captures have only $3.85–$4.12 proxy gross each and no final-artifact positive wallet delta, guard rollback, or measured net EV. The detector's 1e6 unit error and feed recovery bug from the last review remain. The lead closure records that no further fix round is authorized. Promotion criteria for fork success and recomputed EV are unmet. No repeated fork review or new `attempts` row for unchanged code.

Evidence: KB lead 21, `attempts:1101/1104`; prior review hashes and findings below; `manifest-check.py` passed. No gate action was taken.

Unchanged since `dc28155a78a442438b11c921ec343994`, decision **fix** stood until the lead closure. Only runtime logs/state changed; manifest, bot.js and executor source match the hashes below. The Base Morpho liquidation ledger showed no new event after block 56830695 through its then-current cursor (next block 56854562).

# Review — 2026-11-13 07:56 UTC

Decision: **fix** (run `dc28155a78a442438b11c921ec343994`). `next_review_at: null`; review after code, manifest, or executor source changes and a restarted paper run.

## Blocking findings

1. **The detector's debt units are wrong.** `bot.js:479` divides an 8-decimal cbBTC collateral amount by `10^(8-6)` after multiplying by a 6-decimal USD price. It must divide by `10^8`: both `debt` and `maxDebt` are already USDC base units. For borrower `0x3af516c5...ca31f`, the current log at head 56830695 says debt `1,571,894,344` and maxDebt `2,256,675,132,316,664`; the latter is about 1,000,000 times the correct scale. The paper log contains 816 `check` records and zero `LIQUIDATABLE`, simulations, or simulated sends. Correct the conversion and demonstrate detection at a historical, pre-capture eligible block.
2. **The payout and EV are still unproven.** The named `fork_evidence` expressly leaves the profitable liquidation open. `attempts:1101` found that the four large README rows belong to a same-block price-update batch, so their purported 916-block eligibility windows cannot count. The possible bleed captures at blocks 56523299 and 56524500 have only proxy gross values (~$4.12 and ~$3.85); neither has a final-artifact owner-wallet delta, guard rollback, per-capture gas, or net. Reproduce success and `NO_PROFIT` rollback with the corrected live calldata, then rebuild the per-occurrence table and recompute EV from only captures eligible at least two blocks before taking. No reviewer fork lease or gate action was warranted while the detector and route remain unproved.
3. **Feed recovery can lose an interval.** `bot.js:560` commits the feed cursor and `bot.js:573` commits `lastBlock` before the gap/429/503 relay re-read and state scan succeed. If either read fails, the next cycle resumes past the missing interval. Commit both cursors and feed answers after successful recovery and scan.
4. **The live cost and send estimate need correction.** The manifest uses the feed-byte multiplier `0.04` for ordinary RPC calls. Its stated two scans/minute × nine reads × 1,440 minutes × an illustrative 10 CU/read is **259,200 CU/day, about $0.137/day**, before feed delivery and retries. `bot.js:493-508` treats oracle-priced seized collateral as swap proceeds and uses a pool ETH/USD value captured only at startup for the gas-cap comparison. Measure the sale quote with slippage and refresh the signing-time gas valuation before sending; use the actual read and feed volumes in README and manifest.

`manifest-check.py` PASS; `allowed_contracts: []`, dynamic executor address, Base's $18 native-wallet cap, and the named Solidity source's owner-only atomic flash loan, `NO_PROFIT` guard, and same-tx USDC sweep support the deployment and L/S checks. These do not establish a profitable executable route. Hashes for the unchanged-bot rule: manifest `8635017ae30e5f9966274a365bf04a71e0b575277c458e372879458f84749267`; bot.js `347d7cc5f648d258e787d2c44587e8869d80023c1dfb8de82170a75a6a26127e`; executor source `996982b418f60b1d5dafc4a5d8cd40d0a23c4bd0e3bf5a4ae05cb0a3b288c802`.

# Review — 2026-11-13 06:23 UTC

Decision: **fix** (`attempts:1098`; run `ed0432454d7c4828bde054fd3084631d`). `next_review_at: null`; review after a changed bot, manifest, or executor source and a restarted paper run.

## Blocking findings

1. **No profitable fork success exists for this artifact.** The manifest and README say the tested liquidations all reverted with Morpho's healthy-position error, and the positive wallet-delta proof remains open. The required owner-wallet USDC gain and a separate `NO_PROFIT` rollback have not both been reproduced. Find the exact eligibility block for a monitored borrower, run the final executor calldata there, and record both transaction receipts, gas, and wallet balances. A deploy and a healthy revert do not prove the payout route.
2. **The EV table is a proxy, not proceeds from the executable route.** Its gross is `0.1628 × repaid`, even though the README flags an oracle-versus-pool sizing discrepancy of about 19%. Each row uses `~0.13 USD` gas rather than that capture's measured gas and effective fee. Rebuild the per-occurrence table from actual fork wallet USDC deltas, block gas charges, and net; drop nonpositive net rows and recalculate EV. The current countable EV is unverified, so it cannot be compared favorably with live CU cost.
3. **Paper detection has not shown a payable send.** `logs/detections.jsonl` has 138 `check` records and no `LIQUIDATABLE`, `sim:ok`, or simulated send. Show that the named counted borrowers crossed eligibility while present in the pinned list and that the bot's 30-second scan or feed path detected them before capture. The largest four rows share one cascade at block 56677288, so count that as one opportunity window, not four independent days.
4. **The live read-cost estimate is unsupported.** The manifest says about 13,000 calls/day but assigns about $0.05/day using `0.04 CU` per call; that factor belongs to feed log bytes, not ordinary relay reads. At the conservative illustrative 10 CU per RPC call, `2 scans/min × 9 reads × 1440 × 10 = 259,200 CU/day`, or $0.137/day, before feed logs and error recovery. Measure the actual method CU and feed log byte volume and state the full cost.

## Other checks

- `manifest-check.py` PASS; `allowed_contracts: []`, dynamic `EXECUTOR_ADDR`, and the named artifact fit deployment format. The source contains an owner-only atomic flash loan, liquidation, swap, USDC `NO_PROFIT` check, and same-transaction transfer to the owner wallet. Base's $18 native-wallet cap bounds OP Stack gas exposure. The route is a public Morpho liquidation under S. The missing profitable execution and EV proof make a reviewer fork run and gate action premature.
- README reports four >=2-block rows at about 183 seconds and a minimum of the historical small-capture windows of 35 seconds, with block 56677288 as the last named cascade. Those timing claims still need a working detector and route for this submission. No positive net EV is accepted yet.

Hashes for the unchanged-bot rule: manifest `8635017ae30e5f9966274a365bf04a71e0b575277c458e372879458f84749267`; bot.js `7f841cd004588594b2b5f11b0456e6e805b0a45df79ddb25756409350c828e34`; executor source `4b7bac6937cab8691cc91a2a238cb087a4f10cf1a1394493760898a0ab1c4dd1`.
