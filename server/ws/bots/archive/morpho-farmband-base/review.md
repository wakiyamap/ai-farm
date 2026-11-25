# Review — 2026-11-12 13:34 UTC

Decision: **demote** (`attempts:1006`; run `0ac28c0338504a189b0b480efb9226fc`).

Reason: the measured, currently viable pinned markets have no capture window that covers the 15-second poll plus about 2 seconds to inclusion and pays enough to cover the live read cost. The cbBTC captures were taken 3–5 blocks (~1 second) after the matched feed drop; older cbBTC windows were 13/16 blocks. WETH-USD windows were 77/81/542 blocks (~15.4/16.2/108 seconds), but the sole reachable 542-block capture repaid only $0.32 and yields about $0.04 gross at the fork-measured 12.6% take. Estimated live reads are ~0.8M CU/day, or ~$0.42/day at $0.53/M CU. The viable profitable route is a speed race excluded by `decisions/human/2026-11-12-morpho-stop-researcher-runs.md`. The cbZEC 153–155-block windows are from a dead market. Evidence: `attempts:1001`, README capture table, `scratch/mb157-window.json`, and paper stdout showing AnswerUpdated drops through block 56500250.

`manifest-check.py` passes and the repaired detector is active. Fork reproduction was unnecessary because the capture-window and cost criteria already rule out promotion. Next review: none (archived).

---

# Review — 2026-11-12 12:05 UTC

Decision: **fix** (`attempts:998`; run `47e078155ac84eb09edcfa8098e85ef9`).

Next review: after the earner repairs and restarts the paper detector, corrects the capture evidence, and updates the code/manifest or named executor source. No fork reproduction was attempted this round because the current detection path fails before a usable candidate can be simulated.

## Blocking findings

1. **Detection stalls after a feed update.** `bot.js:435` stores a `BigInt` in `st.answers[agg]`; `saveState()` calls plain `JSON.stringify` at line 230. Paper stdout repeats `cycle error: TypeError: Do not know how to serialize a BigInt` after block 56469152, including after a logged price drop at 56470083. `state/bot.json` remains at `lastBlock=56469074`; the last detection row is 56470083 and there are no `LIQUIDATABLE` records. Persist feed answers as strings and restore them as `BigInt`; show the block cursor advancing through multiple feed updates with no cycle errors.
2. **Capture-window EV counts a route that this poller cannot take.** README counts block 56242285 at 24 blocks / 5 seconds as eligible despite the 15-second timer plus send-to-inclusion time. Exclude it. The README's other 153-155-block / 30-second captures are mostly from the now-dead cbZEC market; the current WETH-USD market's three dust captures have no eligibility-to-capture windows. Recompute EV only for currently viable, monitored markets, with each past occurrence's window. If none remain after the latency filter, archive this speed-race route under the 2026-11-12 human decision instead of another fix round.
3. **Discovered feeds do not demonstrate coverage of measured captures.** `markets.json` pins cbXRP, cbBTC, WETH-USD; startup discovered no cbXRP feed, and the measured cbXRP capture at block 55691587 used feed `0x243d5582c12c905c939f97e66f8ee0cdec80ce02` (`scratch/mb157-window.json`). `bot.js:290` polls only the other discovered addresses. Pin and verify the actual market feed for a viable historic capture, then show a paper log of a matching drop and borrower health check. Current WETH-USD logs say `no-position`.

## Other checks

- `manifest-check.py` PASS; `allowed_contracts: []`, runtime `EXECUTOR_ADDR`, and eight constructor words are present. Executor source lines 157-163 guard an increased USDC balance and transfer the gain to owner in the same transaction. Earner proof `scratch/mb157-proof.json` reports +21.674726 USDC to owner and zero executor leftover; this reviewer has **not** independently reproduced it yet.
- Base native wallet cap is $18. The bot signs 1,300,000 gas at 1 gwei with zero value, so the native fee field is at most 0.0013 ETH at signing; the signer enforces L.
- Live read estimate from the current loop: 5,760 `eth_blockNumber` calls/day at ~40 CU = 230,400 CU; about 2,700 `eth_getLogs` at ~100 CU = 270,000 CU; roughly 170 full safety scans × 23 reads at ~90 CU = 351,900 CU, plus drop scans. Total ~0.85M CU/day ≈ $0.45/day at $0.53/M CU. The README's 1-2 USD/day EV is unsubstantiated after excluding the 5-second and dead-market captures.
- Ledger's latest liquidation at block 56463494 belongs to market `0x9125d0fa...` outside this bot's three pinned markets, so it is not counted as a miss. The WETH market's last named capture is block 56381105, a dust repayment.

Hashes for unchanged review rule: manifest `c75790824a09bb48fd75f24175ef75457f023120ea693d607351491a260f9552`; bot.js `248e9709b94206e433e97f3ac0e8e38bc14ce38644bde82b80ed02f7e11408a1`; executor source `4b7bac6937cab8691cc91a2a238cb087a4f10cf1a1394493760898a0ab1c4dd1`.

---

# Review — 2026-11-12 10:29 UTC

Decision: **fix** (`attempts:993`; run `64688fb555294bf7adc64188fc35243b`)

Next review: after the earner changes code, manifest, or named executor source and restarts paper. The current service has no valid detection path.

## Blocking findings

1. **No borrower position can be read.** `bot.js:251` returns `null` from `discoverBaseSlot()` whenever `keccakOk` is false; it is hardcoded false at line 175. `state/bot.json` has `baseSlot:null`, and `checkMarket()` skips every borrower whose shares and collateral remain unknown (`bot.js:333-335`). Enable and verify slot discovery or use the deployed `position(bytes32,address)` getter. Show a real borrower check and a historical capture detected in paper.
2. **Every market check stops before the borrower loop.** `bot.js:318-320` treats `accrueInterest(...)`'s `eth_call` result as two total-borrow words. Paper `logs/detections.jsonl` contains only `accrueInterest-reverted` for cbXRP/cbBTC/cbZEC. Obtain totals from `market(bytes32)` after accrual in a fork or use a correct current-state read, and retain the actual RPC error in the log. Validate the computed debt and health at capture minus one against the protocol's values.
3. **Price update discovery has not worked.** The most recent startup logged `aggregators discovered: {}` even though the scan returned three logs. Both discovery and polling use trailing `null` topics (`bot.js:220,380`), a relay shape documented to silently return empty results. Remove the trailing entries; verify actual feed addresses and show a matching `AnswerUpdated` drop cycle. The observed logs also require correcting or proving the price-ratio matching at `bot.js:234-235`.
4. **Profit remains outside the bot wallet.** `MorphoFarmLiquidator.sol:155-158` checks only the executor's USDC balance and retains the proceeds there. The bot never calls `sweep`; `bot.js:294-365` only submits `liquidate`. The watchdog counts this as lost. Return USDC to `owner` in the liquidation transaction after repayment, and guard the bot wallet's USDC balance gain. Reproduce the wallet gain and a guard revert on the fork with the final artifact. The existing `scratch/mb157-proof.json` measures `+21.674725` USDC in the executor, not the bot wallet.
5. **Paper simulation is not an execution test.** `bot.js:359` calls from the executor to itself; `liquidate` is owner-only. Reproduce calldata from the bot wallet to a deployed executor, including the actual detected share count and swap amounts. Record a profitable success and a no-profit revert. No reviewer fork reproduction was run this round because the live detection and payout paths above already fail.
6. **Capture evidence and cost need a README.** There is no bot README. Add each past occurrence's eligibility and capture block/time, median and minimum, and exclude windows shorter than poll interval plus inclusion. `scratch/mb157-window.json` includes a 24-block/5-second capture at block 56242285 and a 155-block/30-second capture at 56245267; the manifest's claimed minimum of 153 blocks omits the shorter case without an explicit exclusion. Give a live CU/day calculation based on the final call counts and interval. The manifest estimates ~800K CU/day (~$0.42/day at $0.53/M CU), but the current service has not demonstrated the claimed detection or EV.

## Other checks

- `manifest-check.py`: PASS. `allowed_contracts: []` and runtime `EXECUTOR_ADDR` are correct. The source's `NO_PROFIT` guard and owner-only entrypoint exist. The signed cap shown in code is 1,300,000 gas × 1 gwei = 0.0013 ETH plus zero value, within the stated $5 at current ETH prices; Base's $18 native wallet cap is the enforceable OP Stack loss bound.
- Public Morpho liquidation is an allowed payout route. The known last capture is tx `0x8840c48bd2f5905d655f27f1af822d12d0d75959b56efb6f6a5c52efb0eba02f` at block 56245267.

Hashes for unchanged review rule: manifest `4786bbe4d31249a3f74d4515257ea23271c44f79fde24003dc6fdcfa7f4c4217`; bot.js `883db26940381069901d408fbd3d3c772295cf81b6d23d4c6aa8e4452b048e59`; executor source `53fa4b12ed294897157a64787b9328ab5d2adafb6521f83796c1cd42ec1af924`.
