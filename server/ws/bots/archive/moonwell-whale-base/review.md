# Review 2026-11-10T01:22Z — wait (gate funding refusal)

- Decision: **wait**; `next_review_at: 2026-11-11T12:00:00Z` to check the human funding decision and retry only if funds are available. Run `247ca66322ad4b9e892275400106818e`; `attempts:752`. `gate promote moonwell-whale-base` refused: `intermediate wallet on base has less than 120.00 USD + gas; deposit first`. This funding refusal is final for this review. Gate status showed Base intermediate native 21.25 USD, so the shortfall is at least 98.75 USD plus gas. Proposal: `inbox/human/2026-11-10-moonwell-base-promotion-funding.md`.
- All five promotion criteria pass on submitted code SHA256 `05e0290590926206c32258a1961809bf79b4593ef356b1ab9ac592be12086847`, unchanged manifest and executor source SHA256 `e3f390320ed30a7b056f54e04a7fe63022d30efe19c105c762cba190350e6f45`. `manifest-check`, `node --check`, and `node scratch/mw-whale-fix/settle-proof.js` pass (including a pending receipt across many heartbeats and damaged-state recovery). The Base $18 native-wallet cap and the executor's strict USDC gain guard establish L. Paper has no signer send; public liquidation and sale comply with S.
- Independent Base fork reset 53265094 with the current eight-argument artifact: deployed runtime matched the submitted runtime. Success tx `0x04ddea227a56316c9aefbe2b20f71b4c236ea47d065a5b1a4942f69d5badbbb2` gained 3.914436 USDC at 1,641,107 gas. Guard tx `0x63becbb623931398ce62ff5ca72189f51ad34f8ebc4b79a1950d5027a4c4d71b` reverted `NO_PROFIT`, USDC 0 to 0. Script `scratch/mw-whale/review-7cbf-moonwell.py` printed `PROOF_OK True`; lease released. The historical fixture proves the mechanism, not a current capture.
- Detection: supervised paper heartbeat advanced to Base block 55415084 with `runtime_ok=true`. Ledger has no new Moonwell capture after the previous reviewed block 55381952 through the core cursor 55415788; ext emitters are unevenly backfilled, with some older cursors. The latest reviewed captures use unsupported collateral or borrow routes. No new supported detection miss established. `next_review_at` is a funding check, not a prediction of a liquidation.

--- Previous review ---

# Review 2026-11-09T23:45Z — fix

- Decision: **fix**; `next_review_at: null`; run `c0654dd11c2a4bb78603c9bdf4ad7a5c`; `attempts:743`. No promotion attempted.
- `manifest-check`, `node --check`, and the submitted `settle-proof.js` pass. Current bot.js SHA256 `53e9330d896d4c65310846ff6bf92879f69369f3eb1b76185c48c00e623b8b9b`; manifest/source/artifact hashes remain `bf7b5eec`/`e3f39032`/`e0c339bd`, independently fork-proven in review `7cbf8b95` (success +3.914436 USDC and NO_PROFIT revert). The Solidity guard at `MoonwellWhale.sol:182` and Base's $18 native-wallet cap still bound transaction loss. The new stop defect blocks promotion, so no fork rerun was needed.
- **Fix checklist item 9, and extend item 10's test:** `recoverLossFromLogs()` keeps only accepted hashes after the second-to-last heartbeat (`bot.js:340-343`). A receipt can remain pending through more than two 15-second cycles when receipt reads or valuation fail; the live send gate correctly prevents a new send during that time. If `state.json` is then damaged, recovery drops that older uncharged hash, restores the last heartbeat's $29 loss, and `cycle()` persists the incomplete state before rearming sends. `node scratch/review-c0654dd1-recovery-probe.js` exercises the current recovery function with a still-unconfirmed hash and three later heartbeats: `pending=0, loss=29`. Retain *all* accepted hashes whose settlement is not durably recorded, or write a durable stop marker when their status cannot be reconstructed. Test an old pending receipt that spans several heartbeats, followed by a damaged state file and a full load → persist → send-gate check.
- Also ensure the accepted hash is recoverable when the signer replies with `txHash`: the live path accepts `s.hash || s.txHash` at `bot.js:726`, but the `live_send` log at line 725 records only `s.hash`; a `txHash`-only acceptance is absent from the recovery log. Item 9 fails on that response shape too.
- Detection: paper heartbeat advanced to Base block 55387224 with `runtime_ok=true`. Since the previous review, ledger Moonwell events at 55363032/55378306/55381952 use collateral market `0x73902f...` without a measured sale route; 55367522 borrows mcbBTC, which the executor cannot repay. No executable detection miss established. Paper has no signer send.

--- Previous review ---

# Review 2026-11-09T22:12Z — fix

- Decision: **fix**; `next_review_at: null`; run `7ba9c267d87f4c99aec9ea28dceeca35`; `attempts:736`. No promotion attempted.
- `manifest-check`, `node --check`, and `node scratch/mw-whale-fix/settle-proof.js` pass. Current bot.js SHA256 `5cdc5e2c66c434f759830ac941b6a0af33a0e6a76ecf72c80a04fb931f46117f`; manifest, artifact, source, and runtime retain the hashes independently fork-proven in review `7cbf8b95` (success and `NO_PROFIT` revert, `scratch/review-7cbf-moonwell.json`). Base's $18 native cap and atomic USDC increase guard establish L. Paper log through block 55359349 shows an advancing, healthy cursor and no signer send.
- **Fix checklist item 9 at the cycle boundary:** `loadState()` marks missing or unreadable live `state.json` as failed and initializes `liveLoss` to zero. `cycle()` then calls `persist()` at line 685 before any candidate send; a successful write saves zero and clears `stateWriteFailed`. A previous pending tx hash or realized loss can be lost forever when the state file is damaged before `STOPPED.json` was written. The offline test checks the flag immediately after loading but does not exercise this automatic rearm. Preserve the halt until prior loss history is recovered or a durable stop marker is written; test the full load → cycle persistence → send gate sequence. Other ten-item checklist checks pass the current code and test.
- New ledger Moonwell event at block 55347112, tx `0x79974409f9cf792d38da6785dd505dd98592cea2d12a94be342c37e89ce4dc14`, repaid mcbBTC against mcbXRP collateral; both are outside this bot's executable routes. No supported detection miss is established.

--- Previous review ---

# Review 2026-11-09T20:39Z — fix

- Decision: **fix**; `next_review_at: null`; run `13c8597093704211b0b3657425d05997`; `attempts:729`. Current bot.js SHA256 `3ff69747ae9f71220ea3a66d99521dc3b031ed6b36ca0dfc2093076be23dc5cc`. No promotion attempted.
- `manifest-check` and `node --check` pass. Executor and manifest are unchanged from the independent fork success/NO_PROFIT proof in review `7cbf8b95`; no fork rerun because the live stop criterion fails. Base's $18 native cap and executor USDC gain guard establish L. Paper heartbeat reached block 55331478 with `runtime_ok=true`.
- **Fix the $30 live stop in one pass:** `bot.js:630` blocks pending receipts only when the price is stale. A fresh price with an unavailable receipt or missing inclusion fees leaves gas uncounted but permits another send at line 636. Block all sends while `pending.length > 0` after settlement. Lines 369-371 use an observation-based `1e-6 ETH` estimate for absent Base fee components, though those fees have no signed cap; retain the receipt until the full charged amount is known or establish a bound. Missing/malformed gas fields default to zero and must remain pending. `saveState` at 306 writes directly, so a crash can truncate it; `loadState` at 302-305 resets unreadable live state to zero, and startup ignores `STOPPED.json`. Use atomic state writes and fail closed on startup. `liveLossStopWrite` swallows errors but sets `stopLogged`; retry until the reason is persisted. Update the offline test for fresh/failed price, missing fee, threshold crossing, and restart: `node scratch/mw-whale-fix/settle-proof.js` currently fails on the changed no-fee behavior.

--- Previous review ---

# Review 2026-11-09T19:05Z — fix

- Decision: **fix**. `next_review_at: null`; run `2939f16ecf5b4f66b21da92dc87db945`; `attempts:720`. No promotion attempted.
- Current hashes: bot.js `4d23994ca3ca08f5bd731012b615424f2d0ce30c66d609c11139763765dbcb25`; manifest `bf7b5eec744165ddfba9584a47a43f25adecab4e076f115fab77fa58cea9db87`; runtime `2c7af2bacfa71868db2d8545596a1a2b6edfbc19b807b0ae2b739bc907507626`; source `e3f390320ed30a7b056f54e04a7fe63022d30efe19c105c762cba190350e6f45`; artifact `e0c339bda73f94a7e2cd3a8c1bbd35b458d37122353ee50a80f51537bc3a8259`.
- `manifest-check` and `node --check` pass. The fresh-price change at bot.js:635-636 defers receipt settlement when `refreshEthUsd()` fails. The unchanged artifact/source had independent WADO-route success (+3.914436 USDC) and `NO_PROFIT` revert in prior review `7cbf8b95`, proof `scratch/review-7cbf-moonwell.json`; no fork rerun because the live stop criterion already fails. Atomic flash, liquidation, sale, repayment and USDC increase guard remain in the source. The Base $18 native wallet cap and zero principal bound L; paper sends nothing and public liquidation meets S.
- **Fix the $30 live stop:** bot.js:345-353 removes a confirmed receipt from `pending` if *any* of `l1Fee`, `operatorFee`, or `l2FeesIn11Eth` is present, even when another separately charged fee is unavailable. When none is present it uses `1e-6 ETH`, called an upper bound based only on a prior observation; Base inclusion fees have no signed cap, so that is not a proven bound. Keep the receipt pending and block new sends until the actual full inclusion cost can be accounted for. Also bot.js:635-636 can leave receipts pending after a failed price refresh, while bot.js:532 accepts the prior price for up to 15 minutes and bot.js:599-617 can still send. Stop sending while confirmed gas is unvalued, then persist the settlement before another send.
- Detection: ledger `moonwell_core.liquidate_borrow` has a supported $368.332055 mUSDC/mWETH capture at block 55297682, tx `0xf0579b9d69c3712b5ddbdc91b033e98bf4ff3714702232d003d772258bbc2f55`. Relay `getAccountLiquidity` for its borrower returned liquidity $60.5978, shortfall 0 at blocks 55297670/76/81, then shortfall $29.7769 at capture block 55297682; same-block crossing is outside the intended polling window. Paper heartbeat reached Base 55303528 with `runtime_ok=true`. No supported detection miss is established.

--- Previous review ---

# Review 2026-11-09T17:30Z — fix

- Decision: **fix**. `next_review_at: null`; run `7cbf8b954a9b452bbfa3bd771c83bc32`, `attempts:710`. No promotion attempted because cumulative-loss valuation can be stale.
- Reviewed SHA256: bot.js `43c46aaafba4aa0081199804d71414aa00dcfdbe091075f092350efba3a15323`, manifest.yaml `bf7b5eec744165ddfba9584a47a43f25adecab4e076f115fab77fa58cea9db87`, executor-runtime.hex `2c7af2bacfa71868db2d8545596a1a2b6edfbc19b807b0ae2b739bc907507626`, source `e3f390320ed30a7b056f54e04a7fe63022d30efe19c105c762cba190350e6f45`, artifact `e0c339bda73f94a7e2cd3a8c1bbd35b458d37122353ee50a80f51537bc3a8259`.
- `manifest-check` and `node --check` pass. I deployed the current eight-argument artifact on the leased Base fork at reset 53265094. WADO-route tx `0x04ddea227a56316c9aefbe2b20f71b4c236ea47d065a5b1a4942f69d5badbbb2` succeeded, adding 3.914436 USDC at 1,641,107 gas. At local 0.1 gwei and paper ETH/USD $2122.64, gas cost was about $0.35, leaving about $3.56 before small Base inclusion fees. `NO_PROFIT` tx `0x63becbb623931398ce62ff5ca72189f51ad34f8ebc4b79a1950d5027a4c4d71b` reverted, USDC stayed zero; a healthy control reverted. Proof: `scratch/review-7cbf-moonwell.json`. The executor is atomic and Base's $18 native-wallet cap enforces manifest L=$18. Paper reads the relay and public liquidation is within S.
- **Loss-stop valuation can be stale:** `cycle()` calls `refreshEthUsd()` then `liveLossSettle()` at `bot.js:623-625`, but a failed refresh leaves the prior global `ETH_USD` in place. `liveLossSettle()` tests only `ETH_USD <= 0`, not whether `ETH_USD_AT` was refreshed in this cycle. A receipt confirmed during a price-read failure is removed from `pending` and its gas permanently valued at the old price. If ETH/USD rose, the $30 cumulative loss can be understated. Keep the receipt pending until a fresh valuation succeeds, then persist the charge before another send. The `1e-6 ETH` fallback for missing Base fee fields is an estimate, not a bound on an unknown L1/operator fee; settle only when the full inclusion cost can be accounted for or justify a conservative bound.
- Detection: paper heartbeats advanced with `runtime_ok=true` through Base head 55272605. Ledger Moonwell core last capture remains block 55232124, before the last detection review; no newly missed executable event is established. Signed L2 cap is 2.2m gas x 2 gwei with zero value; the Base wallet cap also bounds inclusion fees.

--- Previous review ---

unchanged since 811c0a9f096640b9ba60cc98e190addc, decision fix stands. Detection-only check, run 233973f5be2e4f9ab5f3de40b56f194e: bot.js, manifest.yaml and named artifact predate the prior review; only state/state.json changed. New mUSDC LiquidateBorrow events at Base blocks 55229643, 55230112, 55230716, 55232124 were for borrower 0x41f9bd8fc3587b4a6abb7e318dc104edee591c89. The watcher retained that borrower in candidates (state added at 55229669, lastBlock 55232145), scanned through 55244973, and logged no underwater opportunity or send. Direct relay getAccountLiquidity at capture-minus-one blocks 55229642/55230111/55230715/55232123 returned shortfall 0 each time: same-block price-cross captures, excluded by the no-latency-race decision, not a detection miss. Block 55224690 collateral 0x3bf937... is watch-only and logged. Existing fix for Base L1/operator fee accounting remains. No fork rerun or attempts row. next_review_at: null.

# Review 2026-11-09T14:10Z — fix

- Decision: **fix**. `next_review_at: null`; include all Base inclusion fees in cumulative live loss. Run `811c0a9f096640b9ba60cc98e190addc`.
- `manifest-check` passes for the new eight-address artifact. The changed bot includes the prior receipt-pending and immediate stop-write repairs. The Base native wallet cap remains $18 and the executor's final USDC increase guard bounds principal. Executable WADO route has prior independent fork success; the newly added mcbXRP P4 route remains watch-only under `attempts:678` (same-block capture) and is not credited as an executable profit opportunity. Paper heartbeats advance; `attempts:679` found no new supported whale capture.
- **Stop-loss accounting error:** `bot.js:320-321` adds only `gasUsed * effectiveGasPrice`. A real Base receipt for Moonwell capture tx `0xa59906ecda168467dbafeb3538d7fead09d96811257885e7f1780b2168ec6fcb` also has nonzero `l1Fee=0x77d2f255` (relay paper lane). Base's L1 data and operator fees are charged separately at inclusion per common instructions. The bot's cumulative $30 loss can therefore undercount what it paid. Include the receipt's L1 fee and any separately reported operator fee, with a conservative fallback if unavailable; persist and stop on the full loss. After the fix, reproduce current eight-arg artifact success and guard revert before promotion. Public Moonwell liquidation is within S; paper sends nothing.

--- Previous review ---

# Review 2026-11-09T07:52Z — wait

- Decision: **wait**. `next_review_at: 2026-11-12T12:00:00Z` (next plausible supported whale capture). No promotion attempted. Run `f9712fc5f072496eb0e579a221be513f`.
- The seven-address `executor_args` now decode, in constructor order, to the comptroller, Morpho, USDC, and the four pinned pools in `MoonwellWhale.sol`. `manifest-check` passes. The artifact, source, and submitted runtime retain the SHA256 hashes from review `f680575b219047aba2f6db41c956298e`; the changed `bot.js` adds a catch-up seed filter and does not change the atomic send target. Current bot.js SHA256 `c6f1e0050d85ca186d9ba4c4d96ef79a58f3671ecec4091778723bdc05907110`; manifest SHA256 `54b579fc35b7ff7e3c0587fd5e9de4ed36058e84e86a669dba5bb72b139bec12`.
- Independent Base fork reproduction used `scratch/review-f680575b-moonwell.py`, leased/reset to block 53265094, deployed the current seven-arg artifact, verified the deployed runtime equals `executor-runtime.hex`, and released the lease. WADO→WETH→USDC liquidation succeeded: tx `0x8ef583a1b252f1c000f97cc5b845484628c463fcd2e0a392891428935d1ba56f`, 1,639,248 gas, executor USDC 0 → 3.912517. Higher minProfit reverted `NO_PROFIT`, USDC 0 → 0 (tx `0x1bce618f262f8f167e93489416afeaed42f2cd3c004c762d3932e7976d7b9ae7`); zero repay reverted `NOT_LIQUIDATABLE` (tx `0x5270961616ae69a0f0ff76312ac72310fa7552854f8958cc68beca108e6b73b1`). Proof `scratch/review-f680575b-moonwell.json`. The executor's owner-only flash, liquidation, collateral sale, repayment and final USDC increase are atomic. The Base native-wallet cap is $18, matching manifest L=$18; signed gas cap is 2.2m × 2 gwei, value zero. Public liquidation and pool sale meet S; paper reads the relay and makes no send.
- Since the previous review, paper logged 251 advancing heartbeats through Base head 55101367, `runtime_ok=true`, zero simulations or simulated sends. The ledger's new captures through block 55095245 are unsupported borrow/collateral routes or dust: core block 55095124 repaid 0.220073 USDC, core block 55089164 repaid 0.141415 USDC, and ext blocks 55095244–55095245 use borrow market `0x9a858e...`, outside the USDC/WETH route. Ledger Moonwell cursors reached next_block 55100905. The historical WADO proof is profitable on its fork, but a natural supported, after-gas paper capture remains absent. Wait for that event.

--- Previous review ---

# Review 2026-11-09T06:17Z — fix

- Decision: **fix**. `next_review_at: null`. No promotion attempted. Run `f680575b219047aba2f6db41c956298e`.
- **Deployment blocker:** `manifest.yaml` names a real artifact, but it omits `executor_args`. The named artifact ABI has a seven-address constructor. Independent `fork deploy base scratch/mw-whale/contracts/out/MoonwellWhale.sol/MoonwellWhale.json` without args reverted (tx `0x7b1e1db69954c363db4185ea85465519e9f51384442a6bb4272e32c6f10191ea`, gas 377620, empty revert) at reset 53265094; lease released. Add the seven ABI-encoded constructor addresses as `executor_args` and check that the gate's deployment configuration resolves to the intended live executor. The addresses are stated in `executor_note`, but that prose is not ABI-encoded deployment input.
- **Safety reproduction:** fresh `forge build` passed. On the leased Base fork, the submitted seven-arg artifact deployed with the constructor addresses in `executor_note`, and its deployed runtime matched `executor-runtime.hex`. The executable WADO route succeeded at reset 53265094 (tx `0xb5ad0d9699a68916cdba44e08a7acd6ef994dfc46b962c33deaf2590620ec5a2`, gas 1629051, executor USDC 0 → 3.914436). A higher minProfit reverted `NO_PROFIT` with USDC 0 → 0 (tx `0x86cc74ec3c8ce8291c01c64f5905e3b91366a14515a1bcb37b6eed816661c955`); zero repay reverted `NOT_LIQUIDATABLE` (tx `0x03ad846696c3dd76a859c99d39a29f1b1c8de55b086bcfe916d5edf99a2f2cde`). Proof `scratch/review-f680575b-moonwell.json`; lease released. The EURC and cbBTC collateral routes are watch-only in `bot.js`, so their unproven/cash-starved paths are not credited as executable. Public liquidation and pool sale comply with S; paper uses relay reads and no signer send.
- **Loss and detection:** Base's $18 native-wallet cap enforces manifest L=$18. Signed gas 2.2m × 2 gwei = 0.0044 ETH, $9.37 at the 06:13 paper price $2130.38/ETH, value zero. Since the 05:28 restart, paper logged 177 advancing heartbeats through head 55071866, `runtime_ok=true`, zero executor simulations/sends, and only watch-only or dust opportunities. The last core LiquidateBorrow is block 55028217, mWETH borrow with unsupported collateral 0xb805...; the latest ext event is block 55058449, mEURC borrow, outside supported borrow markets. Ledger cursors for both sources reached next_block 55068300. A natural supported profitable paper capture still has not occurred; after the manifest fix, wait for that event instead of fabricating one.
- Reviewed SHA256: bot.js `16c82f64a5bc4e8e0131f90642f163da7c09b6c939418aa8b37ec87e2e25912e`; manifest `b0fc6c4972c9086f29262838d6587456631b5bc9faf21e864097d329e94f7c23`; runtime `797c6555b863712bffebf8eb9b0060cf4f799b1920a0528e32930fdc7893637f`; source `fedc9e97655e5243bfba91492bbdccfc53569d8f4748b8e59ef88c653bdb12ce`; artifact `86674748c9c22111382fedb8129c5de6cbc5c1f013f035c74279628b091a9d3b`.

--- Previous review ---

# Review 2026-11-09T04:35Z — fix

Decision: **fix**
Reviewed by: paper-reviewer / gpt-6-sol
Run: 6f9f5d6f22c84dd383b12064e77610b7
next_review_at: null

The changed bot enables the mcbBTC collateral route on PancakeV3 cbBTC/USDC. At the bot's own paper opportunity for holder `0x470bac04fb3bb9cc0af3f4c4cdbd956753ab92a7` (Base block 54922895, $100.6206 shortfall), the submitted runtime and exact route calldata revert `NO_REDEEM` in a historical relay `eth_call` with the runtime code override. The same call reverts at blocks 54925000 ($23.5430 shortfall) and 54942703 ($6.2998 shortfall). The mcbBTC market held only 140 raw cbBTC units at the first two blocks and 4 at the third, with cbBTC decimals 8. Evidence: `scratch/mw-whale/review-6f9f-relay.json`. At block 54925221 the account was healthy, and at block 54958964 it was healthy again just before the recorded 54958965 liquidation. Thus the manifest's claim of a continuous >=110 minute liquidation window is inaccurate; there were separate windows.

Independent Base fork reset to block 54922895, lease released, reproduced the route failure with the deployed artifact: tx `0x537660158e4a0ec8944953e715b0bd0004c81b07829a100cb820921d8e9c1e32` status 0, gasUsed 1,037,938, trace reason `NO_REDEEM`, executor USDC 0 before and after. The deployed runtime matched `executor-runtime.hex`; `OWNER()` returned the test owner. A zero-repay control reverted `NOT_LIQUIDATABLE` (tx `0xae77404514d5d3e62617f1785175b81f7595da7414779e80ec28e11f3750d85a`), also without balance loss. Evidence: `scratch/mw-whale/review-6f9f-cbbtc.json`. There is no successful fork proof for this newly enabled route. Return it to watch-only or supply an independently reproducible successful cbBTC route with a redeemable market and positive after-gas net; correct the window claim.

The unchanged executor source and prior WADO-route independent fork success and NO_PROFIT revert remain recorded in review `8222f536141845838c6a5996934ae2d5`. The Base gate native cap is $18, matching manifest L=$18; the fixed signed L2 cap is 2.2m gas × 2 gwei = 0.0044 ETH, $9.42 at the paper heartbeat's $2141.62/ETH. The executor still makes flash, liquidation, redemption, sale and repayment atomic and requires a USDC gain; public liquidation and AMM sale meet S. Since the 04:09Z restart, 93 heartbeats through block 55042089 had `runtime_ok=true` but zero `simulate` or simulated sends. The old 54922895 detection was watch-only in the prior version, so it is not a miss by the changed route. No natural after-gas profitable capture supports promotion. No gate promotion attempted.

Reviewed SHA256: bot.js `931f4acf7f25ae7b32b77b9719b48335604d3c10983a733b966bf4c78bc7b981`; manifest `bdfaf5dbfdc3455a46e818d7747d50f2cfd4ffa688930b25aab1426aca3b3c98`; runtime `8fba08e3eca3a14948659bf8f1673b02e97728a857c6e16cf64151272c86639f`; named source `5d4bde01708c94c3702000f478d9a3ff6cbe652490137fe1bbd5f6c9c095a48d`. KB attempts:632.

--- Previous review ---

Decision: wait
Reviewed at: 2026-11-08T12:51Z
Reviewer: paper-reviewer / gpt-6-sol
Run: 8222f536141845838c6a5996934ae2d5
next_review_at: 2026-11-09T12:00:00Z (check for the next supported natural whale capture)
Code SHA256: 669584544e9757ce18ad51ad44e53d570bd7b0f0c1ef0759832a5c4092cbd029
Manifest SHA256: 051a1645363d1e146443f3232261927ea7bed7da68ba3399d584972582d22315
Runtime SHA256: 8fba08e3eca3a14948659bf8f1673b02e97728a857c6e16cf64151272c86639f
Executor source SHA256: 5d4bde01708c94c3702000f478d9a3ff6cbe652490137fe1bbd5f6c9c095a48d

Unchanged code, manifest, runtime and named executor source. Independent Base fork reset 53265094 reproduced a successful supported WADO route (tx 0x38ecfd45b56a3a2a9e8038d4789ef630a916d82df264a5dd9b0edb33a7af06c7, executor USDC +$3.914436, 1,637,426 gas), a NO_PROFIT revert with USDC unchanged (tx 0xee4e37f22671310da34e7f98f2fd790df53f2b55b72941613fd0454521b1dd85), and NOT_LIQUIDATABLE revert (tx 0x7175066703b16b47be5aad7d186ce5b6b3e561226b98519d68f61cff5b3c87a2). Proof: scratch/mw-whale/review-8222f536-moonwell.json; lease released. Flash loan, liquidation, redemption, sale, repayment and USDC gain guard are atomic. The Base native-wallet cap of $18 enforces manifest L=$18; signed L2 limit remains 2.2m gas x 2 gwei = 0.0044 ETH, with zero value. Paper sends no transactions. Public liquidation reward is within S.

Since the prior review, the ledger shows one ext-market liquidation, block 54697042 tx 0x64b9fbed5c5e89c40c8e02e6c41a742d71c011cfec320b659385b2f7398b5ae2, borrow market 0xb682c840...; the executor supports only USDC/WETH borrow markets, so this was outside its awaited executable route. Core's last event remains block 54550654. Both ledger cursors are verified through next_block 54758161. Paper heartbeat reached block 54759405, runtime_ok true; since prior review it logged no simulations or simulated sends, only watch-only and dust skips. No supported natural capture proves positive net after gas and a polling-to-inclusion window, so wait. No gate promotion attempted.

--- Previous review ---

Decision: wait
Reviewed at: 2026-11-08T01:49:50Z
Reviewer: paper-reviewer / gpt-6-sol
Run: becae925782a46b4b5f80aaf0701c98f
next_review_at: 2026-11-08T12:00:00Z (next supported natural whale capture is plausible at the measured roughly 1.4/day cadence)
Code SHA256: 669584544e9757ce18ad51ad44e53d570bd7b0f0c1ef0759832a5c4092cbd029
Manifest SHA256: 051a1645363d1e146443f3232261927ea7bed7da68ba3399d584972582d22315
Runtime SHA256: 8fba08e3eca3a14948659bf8f1673b02e97728a857c6e16cf64151272c86639f
Executor source SHA256: 5d4bde01708c94c3702000f478d9a3ff6cbe652490137fe1bbd5f6c9c095a48d

The submitted code fixes the live preflight to call OWNER() selector 0x117803e3, and the cbBTC collateral route is now watch-only (COLL_ROUTES[M_CBBTC] = null) until eligible evidence exists. On the Base fork, the deployed OWNER() getter returned the deployer 0x1111...1111 and the deployed runtime byte-matched executor-runtime.hex. The live path targets the executor only; paper mode uses relay eth_call with a runtime override and no signer send. The Solidity executor performs flash loan, liquidation, redemption, sale and repayment atomically, and liquidate() requires its ending USDC balance to exceed its starting balance plus minProfit. Public liquidation and collateral sale meet S. capital_usd=120, principal_usdc=0. The Base gate's native wallet cap is $18, equal to manifest L=$18; the signed L2 field ceiling is 2,200,000 gas x 2 gwei = 0.0044 ETH, about $9.82 at the paper ETH/USD 2231, with value=0.

Independent Base fork reproduction (leased and released, reset block 53265094, final generation 252) passed: WADO-route success tx 0xf77bb875f0d716c2b8f08468aafe663dd86041d7469f2d90e8a1a04461591b8a used 1,629,011 gas and raised executor USDC by $3.914436; guard tx 0x6cd1546f95116676065324f87d7f7203804202dac10a747df7032bd08da8b780 reverted NO_PROFIT with no USDC loss; zero-repay eligibility tx 0x6ec4bef9dbdd7e39bbd4a55f6d372f7e73b594f1b51bf8ad739bda0b275c1b70 reverted NOT_LIQUIDATABLE. Evidence: scratch/mw-whale/review-becae925-moonwell.json. This historical success tests the guard; it is not a natural qualifying paper capture.

Since the prior review, ledger Moonwell core liquidation tx 0x8f9faf474c6fd0cc7b916f5f9f5ca58d824433c46fc0ee384fa69ac4fafc08e8 at Base block 54550654 liquidated 10 mUSDC borrowers for only $0.036-$0.059 each. Paper found all ten by block 54550668 and logged opportunity records, then skipped simulation as dust; none supports a profitable send. From the 00:32:34Z service restart through this review, paper had zero simulated successes or net passes; its heartbeat advanced beyond block 54560000 with runtime_ok=true. Core and ext ledger cursors were verified through block 54556780. The only remaining promotion evidence is one natural supported, previously discovered paper simulation with at least $1 gross, positive after-gas net at an includable fee, and a measured polling-to-inclusion window. Wait until the next plausible event. No gate promotion attempted. KB attempts:476.

--- Previous review ---
Decision: fix
Reviewed at: 2026-11-08T00:15Z
Reviewer: paper-reviewer / gpt-6-sol
Run: c4297fae2d864569bba8a7c91ebf3d81
next_review_at: null (resubmit after live owner selector is corrected, new route is proven on an eligible fork position, and a natural supported profitable paper capture is logged)
Code SHA256: 11a00eee598022df2d61e9a235da6f9d757e6b67a1c6294af0b32e64c4425d52
Manifest SHA256: 150ec3810b52ac765e58ffc175ebed233ed6721100e958a935ec51af22e38e43
Runtime SHA256: 8fba08e3eca3a14948659bf8f1673b02e97728a857c6e16cf64151272c86639f
Executor source SHA256: 5d4bde01708c94c3702000f478d9a3ff6cbe652490137fe1bbd5f6c9c095a48d

Required fix: bot.js defines SEL_EXEC_OWNER = 0x8da5cb5b (`owner()`) at line 46 and calls it in the live preflight at line 416. MoonwellWhale.sol declares `address public immutable OWNER` and has no `owner()` function. Its getter is `OWNER()` selector 0x117803e3. The compiled ABI contains only OWNER, and a direct Base fork call to OWNER() returned the deployer 0x1111111111111111111111111111111111111111 while owner() reverted with empty data. Thus every otherwise profitable live opportunity is skipped with "owner() read failed" before any signer send. Change the bot's selector to OWNER(), then verify the preflight on a fork-deployed executor with the actual live owner convention. The manifest executor is now a valid exact artifact path; that prior defect is resolved.

Safety reproduction: forge build passed. On leased Base fork reset at block 53265094, a copied and updated proof used the named six-argument artifact, not the old five-argument build. Its WADO two-hop liquidation succeeded in tx 0xb42a0fd78c72105849c24efbcc3710aaa857a4e2a9bdf904a72e1b527b9a03d2, gasUsed 1628967, executor USDC 0 -> 3.914436. A fresh reset with minProfit above realized proceeds reverted NO_PROFIT (tx 0xd989f069a6ec6b0078e7f82411901db4f1c1f39af1959b4417a7e38980ba8e1a), USDC 0 -> 0; zero repay reverted NOT_LIQUIDATABLE. The deployed runtime exactly equals executor-runtime.hex (SHA256 8fba08e3...). Evidence: scratch/mw-whale/review-c4297fae-moonwell.py and .json; lease released. The single transaction flashes USDC, liquidates, redeems, sells, repays and checks end USDC >= start + minProfit + 1. Public liquidation is an intended mechanism under S. Paper uses relay eth_call; live send is to the executor only. Base gate native-wallet cap is $18, equal to manifest L; signed 2.2m gas x 2 gwei = 0.0044 ETH, about $9.84 at paper $2235/ETH, and value=0. capital_usd=$120, principal_usdc=0.

The new P2 cbBTC route remains unproven as an executable liquidation: its own proof12.json has proof_ok=false, LIQUIDATE_SEIZE_TOO_MUCH on the only liquidatable candidate, and no success/NO_PROFIT guard leg on that route. Its pool orientation and runtime immutables were checked, but show a successful eligible P2 fork capture or keep that route watch-only before promotion. Since the prior review, Base Moonwell events at blocks 54519639 and 54520123 used unsupported borrow market 0x73902f..., logged watch-only. Verified core/ext ledger cursors next_block 54528950; current paper logs show runtime_ok=true, advancing head, no successful simulations or natural supported profitable send. The previously required natural capture with positive after-gas net and a measured polling-to-inclusion window is still absent. No gate promotion attempted; no bot code edited by reviewer.

--- Previous review ---
Decision: fix
Reviewed at: 2026-11-07T22:40:42Z
Reviewer: paper-reviewer / gpt-6-sol
Run: 29c1855dc0aa4bdf82d81ccd96266b43
next_review_at: null (resubmit with an exact executor artifact path and a natural supported profitable paper capture)
Code SHA256: aa9c284f021d43d5246c76ce7d51d85c257bbd0f51daa2b09e24484fe36cd399
Manifest SHA256: cf855b686bfe8a3d2440fb23b28947189f2c8fffdba6d819e176dcd9919461a9
Runtime SHA256: b1164e1d0cf8d6888766cc735314fe792e083f676f2d629f82979ce8cf136f39
Executor source SHA256: c23f134baf61e9cb8d0d143001fac183819a4295d791b75dea7628f0debc6919

Required fix: manifest.yaml `executor` is a folded prose scalar, not the artifact path. `yaml.safe_load` yields a string beginning `scratch/mw-whale/contracts/out/MoonwellWhale.sol/MoonwellWhale.json (forge build; constructor args: ...`; `os.path.isfile(manifest["executor"])` is false. Set `executor` to exactly `scratch/mw-whale/contracts/out/MoonwellWhale.sol/MoonwellWhale.json`, and move constructor/route explanation to a separate note. The deploy gate needs the exact artifact name. This is the same deployment defect corrected in the Gearbox manifest (review d40566ec).

The changed bot drops a candidate after LIQUIDATE_SEIZE_TOO_MUCH and filters small shortfalls before eth_call. The owner-only live path still targets the executor; paper still only uses relay eth_call. The named Solidity source and submitted runtime match the 2026-11-06 18:51Z independent Base fork proof: successful atomic liquidation, NO_PROFIT revert preserving USDC, and NOT_LIQUIDATABLE revert (scratch/mw-whale/review-1d413416-proof.json). The source flashes USDC, liquidates, redeems, sells, repays, then requires ending USDC to exceed starting USDC. Base's gate native-wallet cap is $18, equal to the manifest's per-tx loss limit; signed 2.2m gas x 2 gwei = 0.0044 ETH and value=0. Capital $120 includes no USDC principal. Public liquidation and AMM sale comply with S. No new fork run was needed for the unchanged executor.

No natural eligible profit is established: since the prior review at 12:00Z, 5,105 paper `simulate` records had sim_ok=0 and gate_pass_net=0; the latest failed supported mWETH/mUSDC holder still reverted LIQUIDATE_SEIZE_TOO_MUCH. The two new ledger captures at Base blocks 54489919 and 54499944 are on borrow market 0x73902f... outside the executor's USDC/WETH borrow routes; paper logged the borrower 0xfb98... as watch-only. Moonwell ledger cursors are verified through next_block 54500975; paper heartbeats reached block 54503992 with runtime_ok=true. A natural previously discovered supported simulation with measured positive net after gas and a polling-to-inclusion window remains necessary before promotion. No gate promotion, bot code edit, or mainnet send.

--- Previous review ---
Decision: wait
Reviewed at: 2026-11-07T12:00:11Z
Reviewer: paper-reviewer / gpt-6-sol
Run: 41ff39bae9344b40b856622ecd74ede2
next_review_at: 2026-11-08T12:00:00Z (roughly one day at the measured 0.91/day qualifying-capture cadence; retain the 12-hour candidate window)
Code SHA256: b5fa3bb4490400dd2d0b86e40d23d2e005d2f84b2657112fe2add2762c16d63d
Manifest SHA256: c7414a620aa26883c6ecafe01cd9ff1d2c1424bb284643871988f00774951973
Runtime SHA256: b1164e1d0cf8d6888766cc735314fe792e083f676f2d629f82979ce8cf136f39
Executor source SHA256: c23f134baf61e9cb8d0d143001fac183819a4295d791b75dea7628f0debc6919

The code, manifest, runtime and executor source are byte-identical to the 2026-11-06 18:51Z full review. Its independent Base fork success, NO_PROFIT revert and eligibility revert still apply; no fork rerun was needed. The Base native-wallet cap remains $18 per gate status, matching the manifest per-tx loss limit; capital_usd=120, principal_usdc=0. No recent human decision excludes this measured long-window Moonwell route.

Ledger Moonwell core/ext cursors are verified through next_block 54308843. Since the prior review, new captures at blocks 54158849, 54158851 and 54167202 have unsupported borrow or collateral markets: 54158849 borrows 0xb682... and the others seize 0xb682... or 0xb4fb.... Paper discovered the 54158849/54158851 borrowers by 03:29Z and logged watch-only or no sale route. No supported profitable-capture detection miss is established. The 54167202 mUSDC event seized unsupported 0xb4fb... collateral. The 8,172 simulate records from the previous review through 11:59:58Z all reverted, chiefly LIQUIDATE_SEIZE_TOO_MUCH on collateral-depleted holders; none had sim_ok or gate_pass_net. Heartbeats advanced to the current head with runtime_ok=true. Await one naturally pre-discovered supported executor simulation with at least $1 gross, positive estimated net after gas, and a measured polling-to-inclusion window. No promotion attempted.

--- Previous review ---
Decision: wait
Reviewed at: 2026-11-06T18:51:30Z
Reviewer: paper-reviewer / gpt-6-sol
Run: 1d4134161fd24ea6924250b7c8340942
next_review_at: 2026-11-07T12:00:00Z (next supported whale event is plausible at the measured roughly 1.4/day recurrence; retain the 12-hour candidate window)
Code SHA256: b5fa3bb4490400dd2d0b86e40d23d2e005d2f84b2657112fe2add2762c16d63d
Manifest SHA256: c7414a620aa26883c6ecafe01cd9ff1d2c1424bb284643871988f00774951973
Runtime SHA256: b1164e1d0cf8d6888766cc735314fe792e083f676f2d629f82979ce8cf136f39
Executor source SHA256: c23f134baf61e9cb8d0d143001fac183819a4295d791b75dea7628f0debc6919

The revised bot.js now requires a successful executor eth_call with returned USDC delta >= $1 and positive estimated net after gas before a live signer send (lines 409-463). It prices 2,200,000 gas conservatively if eth_call supplies no gasUsed; the cached includable fee falls back to the signed 2 gwei cap when stale. This resolves the previous gross-only send gate defect. The signed transaction fixes gasLimit 2,200,000, maxFeePerGas 2 gwei, value 0. At ETH/USD 2230.4 the L2 field cap is about $9.81; gate status confirms the Base native-wallet cap is $18, equal to the manifest per-tx limit and below L=$50. capital_usd=120 and principal_usdc=0. Paper mode uses relay eth_call with a runtime code override and has no signer send path; live mode sends only to the owner-only executor. The public liquidation and AMM sale meet S.

I independently repeated the named proof on a leased Base fork reset to block 53786332 (generations 156-158); the lease was released. Deployed runtime SHA256 equals the submitted runtime. Success tx 0x131fc8d0d7fdeb826f1ec677bf665a94977ba2fb63f8a0dd2fce88304ecf1da3 used 1,520,989 gas and raised executor USDC by $0.042771. A clean reset with a higher floor reverted NO_PROFIT in tx 0x9be26b5e8e9d0d142d1062e42890776de74bd4b454253977230c3ffed9541970 with zero balance change; zero repay reverted NOT_LIQUIDATABLE in tx 0xdccad76478f211dc4bc7f3ec4795f21a2900393338e618f2d39e9ba7cac33c31. Evidence: scratch/mw-whale/review-1d413416-proof.json. The executor flashes, repays, seizes, redeems, sells, repays the flash and checks USDC balance increase in one transaction; owner and pool callback checks are present. The successful historical proof is below the bot's $1 floor and does not count as a qualifying paper capture.

Since the 17:53Z restart, paper has logged no sim_ok; the supported holder 0x21df358f reverts LIQUIDATE_SEIZE_TOO_MUCH after its collateral was depleted. The latest ledger Moonwell core/ext liquidations remain blocks 53799599/53948856, with the ext event's borrow market unsupported; there is no new supported event to test detection. Keep the paper service running until a naturally detected supported simulation passes the final net gate with an includable fee and a measured polling-to-inclusion window. No promotion attempted.

--- Previous review ---
unchanged since 71396b4d6be44a9a960fa1a4985be474, decision fix stands. Check run 3cb48d637a024dd38ec0944ea93f240d at 2026-11-06T17:16Z: code, manifest, runtime and named executor source SHA256 match the last full review; only state changed. New moonwell_core.liquidate_borrow_ext at block 53948856 tx 0xbfd51fe4201658d3436f17968030172215fdb1103ddc943d3a09a047c4646f7f borrows unsupported market 0x9a858ebff1beb0d3495bb0e2897c1528ed84a218; bot logs opportunity_watch_only for borrower 0x73ebc72977819b1735ecc4adf515e47b18970200. No supported detection miss; verified next_block 53973787. No fork reproduction or attempts row. next_review_at remains null.

Decision: fix
Reviewed at: 2026-11-06T15:42:30Z
Reviewer: paper-reviewer / gpt-6-sol
Run: 71396b4d6be44a9a960fa1a4985be474
next_review_at: null (resubmit after a natural supported after-gas profitable simulation and a net-gas send gate)
Code SHA256: 3a6b797c4012923a2d8208d4b4dfb1b2bc06adcd7bf1a3fe903c6925e4e10572
Manifest SHA256: d8e9d2b0007ad8cb24bfb42e803e9c2430c66696961156a39552b681d3586fc1
Runtime SHA256: b1164e1d0cf8d6888766cc735314fe792e083f676f2d629f82979ce8cf136f39
Executor source SHA256: c23f134baf61e9cb8d0d143001fac183819a4295d791b75dea7628f0debc6919

The changed executor source compiles. I independently ran its proof on a leased Base fork reset to block 53786332, without modifying bot files. The deployed runtime SHA256 exactly matches the submitted paper runtime. Success tx 0x074bed1b46ec5e3a315e6f72b37f36ee4f115c4a78ba94de5b9ee652c7f04036 used 1,520,328 gas and increased executor USDC 0 -> 0.042771. A clean reset with higher floor reverted NO_PROFIT in tx 0x2e999d46636d2eadca542d252130c82d5192b05d510b770b104b7718404b1dc4, preserving USDC 0; zero-repay eligibility reverted NOT_LIQUIDATABLE in tx 0x3439cb6a0c80d8d8121c02e9c744e0df5f461347f2aed8eff22b8ed56eb6925c. Evidence: scratch/mw-whale/review-71396b4d-proof.json. Lease released. The source performs flash, liquidation, redeem, sale and repayment in one owner-only transaction, then requires a USDC balance increase. Base gate status caps native wallet at 18 USD, matching L=18; capital_usd=120, principal_usdc=0. Paper uses relay eth_call and no signer; public liquidation and AMM sale meet S.

The proof is below the submitted bot minProfit=1 USDC and is not an executable paper win. Its 1.52M gas also makes the 0.042771 USDC gross result negative after gas at any realistic inclusion fee. Since the restart at 14:55Z, 3,086 paper simulations through 15:41Z have zero sim_ok. The supported holder 0x21df358f now reverts LIQUIDATE_SEIZE_TOO_MUCH after collateral depletion; ledger core/ext have no new LiquidateBorrow after block 53799599 through verified next_block 53946150. No new awaited supported profitable event occurred, so no detection miss is established.

There is also a concrete send-gate defect: bot.js:395 sends when simulated USDC delta >= 1 USD, without subtracting gas. The code calculates a signed worst-case gas cap of about 9.75 USD at this head (:383) but uses it only in the log. A valid 1 USD gross simulation can therefore trigger a live transaction with negative net PnL. Estimate executable gas and an includable fee, and require positive net profit before sending. Then demonstrate one naturally detected, supported profitable simulation under that final gate. The 2026-11-07 next_review_at in the manifest does not cure this code issue. No promotion attempted, no bot code edit or mainnet send by reviewer.

--- Previous review ---
Decision: fix
Reviewed at: 2026-11-06T14:08:00Z
Reviewer: paper-reviewer / gpt-6-sol
Run: b23a1139030243f2bc61d9b1c4cd9878
next_review_at: null (resubmit after flash sizing and profit estimation are repaired and a natural profitable paper simulation is observed)
Code SHA256: 33b629b2472d3fcb055eed9b677cf6b92621b5f3a719b8b06547c20fd92241aa
Manifest SHA256: 564ec7fe074c113b7dd3568af3832de1e9d978f30918252a076408bac67f85a5
Runtime SHA256: 116c5abf22a11bbe8e7cbcb13dfc58e4b19fd4100fbe10fee7867c4ccbcdcfc5
Executor source SHA256: b6e18f6a0bd8b2cda437fb38778a6dd49e0944f1f4e6cfe25418b0e0fbe8bc5f

The revised executor compiles, and I independently reproduced an atomic success and NO_PROFIT revert on Base fork generations 145-146, reset to 53786332. The submitted runtime bytes exactly match the code of that tested fork deployment. With a 5.60 USDC flash cap, success tx 0x6dd65c3fd0b8053ef4879bb69f04a699bb109096701afc855357a979c50e2185 used 1,518,435 gas and raised executor USDC from zero to 0.042771. Raising the floor to 0.052772 USDC reverted NO_PROFIT in tx 0xb2e83cd9c4aa3732c502b2749749009268d309edd697664ac79f8142517313e6 with USDC unchanged. The zero-repay eligibility test reverted NOT_LIQUIDATABLE. The lease was released.

The bot does not send the successful proof calldata. bot.js MAX_REPAY_WEI is 300000000 (300 USDC) and MIN_PROFIT_WEI is 1000000 (1 USDC). Independently testing those exact amounts on the same state, fork generation 147, yielded status 0, transferFrom reverted in tx 0xc2c33f2eb850175baad8867054fd62cd597428af7c517ebecca6780c524c8c34: the executor spends the whole flash on USDC-to-WETH, caps the WETH repayment at debt/16, and cannot earn back the unused roughly 294 USDC needed for Morpho repayment. Current paper simulations for the supported mWETH/mUSDC holder through 14:07Z likewise all have sim_ok=false, presently LIQUIDATE_SEIZE_TOO_MUCH. The proof profit of 0.042771 USDC also falls below the bot 1 USDC contract floor before gas.

bot.js estimates profit as 6 percent of half the USD shortfall, but neither the flash amount nor the actual debt/16 repayment and sale proceeds follow that number. At 14:07Z it logged shortfall 77 USD and est_profit_usd 1.78 while the executor reverted. Correct flash sizing and compute economics from the exact simulated executor balance delta and executable gas, then demonstrate a natural qualifying capture. The code fee constant 25,000,000 wei is 0.025 gwei, despite comments saying 25 gwei; validate inclusion feasibility with the corrected documentation. The latest ledger liquidation remains block 53799599, verified through next_block 53913516; no new awaited natural event since the prior review.

The owner-only live path calls the executor in one transaction; the executor compares ending USDC with its starting balance, restricts swap callbacks, and performs flash repayment atomically. Base native-wallet cap is 18 USD per gate status, matching the manifest L value; capital 120 USD, no USDC principal. Paper uses relay eth_call only. Public liquidation and AMM sale meet S. No promotion attempted. KB attempts:297. No bot code edit, key access, or mainnet send by reviewer. No embedded instruction observed.

--- Previous review ---

unchanged since e12914d4ba984d339cbca2780067b4ff, decision fix stands. Check 2026-11-06T12:32Z run dfc56aae9b784907a84b26c1b6310a2b: code, manifest, runtime, and named executor source SHA256 match the last full review. No new Base moonwell_core.liquidate_borrow or liquidate_borrow_ext after prior review through verified cursors next_block 53876088. State-only change; no fork reproduction or attempts row. next_review_at remains null.

unchanged since e12914d4ba984d339cbca2780067b4ff, decision fix stands. Check 2026-11-06T11:00:09Z run 325468a3f96544cfa2806ae9d043bb32: code, manifest, runtime, and named executor source SHA256 match the last full review. Base moonwell_core.liquidate_borrow max block 53799599; both core and ext verified cursor next_block 53857713; no new awaited event, so no detection exception. State-only change; no fork reproduction or attempts row. next_review_at remains null.

Decision: fix
Reviewed at: 2026-11-06T09:25Z
Reviewer: paper-reviewer / gpt-6-sol
Run: e12914d4ba984d339cbca2780067b4ff
next_review_at: null (resubmit after correct USD units, a successful executor simulation on the revised source, and a natural profitable capture)
Code SHA256: f3cfaeae3f8abff35e56eb394be338f70b34bb8411051f9710255d1f8ec852e9
Manifest SHA256: f40a43f37479b9027f9009e7169c685e494371026788a5500cc75158a71cfcc1
Runtime SHA256: 4e5d86ac4a14bcbe3580d6accd17ad2470ce6172edcb6be77bcda02c19e81974
Executor source SHA256: 36a5ce35895e1a23c83b825993dbf53c3e8cb8b124cd0787e3d5fb700b4be142

The changed source attempts to cap mWETH repay after the borrow swap, but the currently running paper bot has no successful simulation on the supported route. Its holder 0x21df358f (mWETH borrow, mUSDC collateral) repeatedly reverts LIQUIDATE_SEIZE_TOO_MUCH; all 76 simulate records through 09:24Z have sim_ok=false. Earner fork attempts 275 and 277 also report this revert on the revised source. The last reviewed source hash was 8e4aeac0; the artifact/runtime is unchanged, so the prior fork success and NO_PROFIT reproduction do not establish success for this changed source. A fresh independent fork proof would be needed after execution is repaired; the current deterministic revert decides fix, so I did not use a fork lease.

bot.js:323 divides the 1e18 USD shortfall by 1e12, producing 1e6 microdollars, then labels it dollars and computes estProfit from it. A shortfall logged as $78 yields repay_est_usd=39245161 and est_profit_usd=2354709.16 in the 09:24 paper simulate line, while the actual proposed flash cap is $300. Fix the units before live use: sim_ok plus this inflated estimate would pass MIN_SEND_PROFIT_USD despite an unmeasured after-gas edge. The event repayment logger likewise divides an 18-decimal mWETH amount by 1e6 and reports 2,945,867,630.85 instead of 0.0029458676 WETH. These logs cannot support economic promotion evidence.

Ledger Moonwell core's latest event remains block 53799599, with all 17 source cursors verified through next_block 53830201. Today's service restart at 09:14Z has discovered candidates and found three underwater accounts, but no new post-review natural liquidation or profitable simulated send. Keep fix; demonstrate a current-source fork success and guard, correct unit accounting, then a naturally caught >gas profitable opportunity with its measured window. Base's $18 native wallet cap still bounds gas loss; no gate promotion attempted. KB attempts:278.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-06T07:51:57.926485+00:00
Reviewer: paper-reviewer / gpt-6-sol
Run: 7e653174a7094a19bf8f3acc88f78829
next_review_at: null (resubmit after a naturally eligible, profitable executor simulation with measured capture window)
Code SHA256: 50c6a3109c4b8a37738ef69ad808ec9c424f052a0e6aadf779003d068da3c01c
Manifest SHA256: 9de57bf99c787589ca9e4af0fbab34409fde168e2455567b7e5cb64db2421f4e
Runtime SHA256: 4e5d86ac4a14bcbe3580d6accd17ad2470ce6172edcb6be77bcda02c19e81974
Executor source SHA256: 8e4aeac0dfcbbd1e7226155d24bb92b804508b946edd487e51b8d3c6335ad4ac

bot.js changed at 07:51Z while this review was in progress and paper restarted at 07:51:14Z; this decision supersedes the immediately prior state-only check below. The change adds fifteen Moonwell emit markets to EMIT_MARKETS and marks their non-USDC/WETH borrow positions watch-only in simulate(). The executor, runtime, manifest, and prior atomic fork evidence remain unchanged. This broadens candidate discovery but does not produce an executable sale route or a natural successful simulation.

Ledger detection check through verified Base cursor next_block 53802670: mUSDC events 53799551 and 53799599 seize unsupported collateral 0xb4fb8fed; mWETH event 53786333 seizes mUSDC but repays 0.002945867630849210 ETH (about $6.57 using the bot log's $2230.90 ETH price), below the manifest's >$1 after-gas evidence threshold on its own stated 6% gross estimate. None is the awaited supported profitable WADO sale. After restart, paper heartbeat at head 53805496 reports 19 discovered candidates, zero underwater, runtime_ok=true; no natural sim_ok profitable record. The manifest still describes the old two-market discovery set and a next_review_at of 2026-11-07, but the review stays fix pending observed executable economics. No promotion or fork rerun; the unchanged executor proof was reviewed earlier, and the missing natural capture decides this review.

--- Previous review ---

unchanged since last full review, decision fix stands. Check 2026-11-06 run 7e653174a7094a19bf8f3acc88f78829: code, manifest, runtime, and named executor source SHA256 match last full review. Detection exception checked: new mUSDC events at 53799551/53799599 seize unsupported 0xb4fb8fed collateral; mWETH event 53786333 seized mUSDC and repaid 0.002945867630849210 ETH, outside supported WADO sale route. Verified cursor next_block 53802670; no eligible profitable simulated-send miss. No fork reproduction or attempts row. next_review_at remains null.

unchanged since 7fc3cc47d8b94d95b087e14af759fc42, decision fix stands. Check 2026-11-06T06:16Z run da3e4b7a15804d50950943f26ec02836: code and manifest hashes match last full review; only state changed. Detection exception checked through verified ledger cursors: no new eligible awaited capture. No fork replay or attempts row. next_review_at remains null.

unchanged since 7fc3cc47d8b94d95b087e14af759fc42, decision fix stands. Check 2026-11-06T04:43Z: code, manifest, runtime, and named executor source SHA256 match the last full review. State-only change. No new awaited ledger event after the prior reviewed cutoff through verified cursors (Arbitrum 521688075; Base 53747596; Ethereum 26353455); no detection exception, fork replay, or attempts row. next_review_at remains null.

unchanged since 7fc3cc47d8b94d95b087e14af759fc42, decision fix stands. Check 2026-11-06T03:11Z run bce15686fe9f42ffbcff64eb22f48ea6: code, manifest, submitted runtime and named executor source SHA256 match the recorded full review. No new Base Moonwell liquidation after cutoff 53692113 through verified ledger next_block 53719800. State-only change; no fork reproduction or attempts row. next_review_at remains null.

unchanged since 7fc3cc47d8b94d95b087e14af759fc42, decision fix stands. Check 2026-11-06T01:36Z run 91e6759c1b6243a99965a39a43768bf1: code, manifest, submitted runtime and named executor source SHA256 match the recorded review. Detection: New mUSDC LiquidateBorrow block 53690197 tx 0x64f75505c073398b6f518c8d2687cd2fb6eff83202cf64ffde852bc69297063d repaid 3.295203 USDC with mToken collateral 0x73902f619ceb9b31fd8efecf435cbdf89e369ba6, outside the supported mWADO sale route; verified ledger next_block 53692114. State-only change; no fork reproduction or attempts row. next_review_at remains null.

Decision: fix
Reviewed at: 2026-11-06T00:03:00Z
Reviewer: paper-reviewer / gpt-6-sol
Run: 7fc3cc47d8b94d95b087e14af759fc42
next_review_at: null (resubmit after a naturally observed eligible profitable simulation with a measured window and persistent candidate coverage)
Code SHA256: 3a0cb440ef3061f6f7d59f452c40470894b53178a1242ea63d17431eb4c02528
Manifest SHA256: 9de57bf99c787589ca9e4af0fbab34409fde168e2455567b7e5cb64db2421f4e
Runtime SHA256: 4e5d86ac4a14bcbe3580d6accd17ad2470ce6172edcb6be77bcda02c19e81974
Executor source SHA256: 8e4aeac0dfcbbd1e7226155d24bb92b804508b946edd487e51b8d3c6335ad4ac

The decoder now starts ABI words at offset 2 and the live branch calls the signer with a gate-deployed executor address after owner and native-balance checks. This repairs two previous concrete blockers. The unchanged Solidity source and runtime passed the prior independent atomicity/NO_PROFIT review; those fork transactions were not repeated. The revised 12-hour candidate TTL is longer than before, but shorter than the manifest's roughly once-per-day repeat-default class, so document why it preserves the specific intended candidates or extend it. Current state contains two historical dust borrowers (last repayments 0.000446 and 0.066958 USDC), not a whale-sized natural opportunity. Logs through 00:01:53Z have advancing heartbeats, runtime_ok=true, zero opportunity/simulate after the revision. Ledger's latest Moonwell event remains block 53550622 before service restart. Prove one naturally pre-discovered eligible capture, successful final-sized executor simulation, after-gas profit, and measured 15-second polling-to-inclusion window before promotion. No new fork claim is trusted; no promotion attempted. KB attempts:229.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-05T22:28:12+00:00
Reviewer: paper-reviewer / gpt-6-sol
Run: 9acd1dfc0fe148feb2c95c556c9a698f
next_review_at: null (resubmit after correct event decoding, persistent candidate coverage, an enabled live path, and a naturally observed profitable simulation with a measured eligible window)
Code SHA256: 77203f7f4471a7ba7c4c0093159ed4e7ca6967b2b0b54b945a48aba8e4c3f30b
Manifest SHA256: 830b30d408ce955a5a7bab4718d4b3010441071fc3f6f1e04e6dcdb47c9abe41
Runtime SHA256: 4e5d86ac4a14bcbe3580d6accd17ad2470ce6172edcb6be77bcda02c19e81974
Executor source SHA256: 8e4aeac0dfcbbd1e7226155d24bb92b804508b946edd487e51b8d3c6335ad4ac

The live path is deliberately disabled: bot.js:82 sets LIVE_FEE_CAP_ENFORCED=false and bot.js:317 returns before signer send. The current common Base policy already enforces L through the gate/signer 18 USD native wallet cap; replace this dead switch with a working send policy before resubmission.

The LiquidateBorrow decoder starts each ABI word at data.slice(10+64*i) instead of data.slice(2+64*i) (bot.js:142-144). On real mUSDC event block 53550622, tx 0x7725909706db31f70628bba0bb98391d1c820b5ed90861c16f09eeed12b53afd, the true borrower is 0xa55ab0d1f583bc0a7754d634bb12111399fa0308, collateral market 0x628ff693426583d9a7fb391e54366292f509d457, repay 66958 raw USDC. This bot decodes borrower 0xf583bc0a7754d634bb12111399fa030800000000, market 0x426583d9a7fb391e54366292f509d45700000000, repay 287582420205568. Thus all candidate probes target wrong accounts; the 13 candidates added on startup are invalid. Independently reproduced from an eth_getLogs relay response for that tx.

Candidate retention also defeats repeat-default watching: CAND_TTL_PROBES=3 and the healthy branch deletes a holder after four 15-second cycles (bot.js:68, 365). Paper logs show 13 candidates at 21:49:23Z and zero by 21:50:09Z, with zero opportunity or simulate records. The manifest's >=32-block window is only >=6.4 seconds at the observed 75 Base blocks per 15-second heartbeat, shorter than one cycle, and its sampled window file includes several liq8=false captures. Measure the actual eligible time, keep valid borrowers long enough to re-default, and demonstrate a natural capture at the final poll cadence. Ledger moonwell_core cursor reached Base block 53632500 with no new event after block 53550622; no natural event occurred since this service started. No justified wait date exists.

Atomic mechanics passed independently on a leased Base fork reset at 53265094, using scratch/mw-whale/proof10.py and the named forge artifact (forge build passed). Success tx 0x37217a1b009f9d1369996affa661f9323d8288d8ad2ff4d5764ef8e957f97adb used 1638484 gas and left +3.912517 USDC; guard tx 0x520e0852339bac856397b0409e1cebaf4a1dc95afce3a384f87ad3f371219121 reverted NO_PROFIT with zero USDC delta; eligibility tx 0x43882658b75ce6b88d796e94b6b589196bb107cffc3ced69270ca5e5b60ea0bd reverted NOT_LIQUIDATABLE. The owner-only contract flashes, liquidates, redeems, sells, repays, and requires a strict USDC gain in one transaction; Base gate/signer wallet cap bounds gas loss to 18 USD. Paper mode sends nothing and reads via the relay. Public liquidation and pool sale meet S. No gate promotion attempted.
