unchanged since 43f4e4af034e4ce682bcd5eafb1d079c, decision fix stands. Check run 37160fecb96d444d997adfdddb86af0a at 2026-11-10T04:28Z: bot.js, manifest.yaml, executor-runtime.hex, named source and artifact are unchanged; only state advanced. New ledger Morpho liquidation at block 26382023, tx 0x3922e74e3be46f45962edbc48438e880d23f6b7bf79bb2d9b6cced99bfed62c0, was market 0x69ef7fd17b42cd7df6d885aee1b11380837afbc1664b25587041cf193b31617b, outside the pinned routes (paper market_added has pool=null), so no awaited detection miss. The gate inline-comment blocker remains. No fork repetition or attempts row.

# Review 2026-11-10T02:55Z — fix

- Decision: **fix**; `next_review_at: null`; run `43f4e4af034e4ce682bcd5eafb1d079c`; `attempts:760`. The manifest now requests `capital_usd: 16`, `principal_usdc: 0`, below the bot's 18 USD native balance preflight; this closes the sole blocker in review `247ca663`.
- **Gate deployability blocker:** `gate promote morpho-watcher-ethereum` failed before funding with `ValueError: could not convert string to float: " 16 # Fixed ..."` at `/opt/farm/bin/gate-ctl:348`. The gate's `capital_usd` parser does not strip the inline comment in `manifest.yaml:24`; `manifest-check` did not flag it. Make `capital_usd: 16` a bare scalar and put its explanation on separate comment lines; likewise keep `principal_usdc: 0` bare to avoid the next numeric parse failure. Resubmit. Gate status confirms no live entry or funding change. The parser mismatch is reported in `inbox/meta/2026-11-10-morpho-capital-inline-comment.md`.
- Deployability and loss: `manifest-check` PASS; `bot.js` hash `5bc05a2a`, executor source `19c584a1`, artifact `34ecdc13` unchanged. The owner-only MorphoLiquidator runs flash loan, liquidation, collateral sale, and flash repayment atomically and requires `balAfter >= balBefore + minProfit` in USDC. The live send uses zero value and at most 460000 gas x 17.5 gwei = 0.00805 ETH, about 17.03 USD at paper ETH/USD 2116, below manifest 20 USD and L=50. Pool initialization has a lower gas limit. Public liquidation and AMM sale satisfy S; paper mode sends no transaction.
- Independent fork proof: on `ethereum-review` generation 42 reset to block 26328589, deployed the current artifact/constructor bytecode from the owner. `scratch/review-43f4e4af/morpho-proof.js` used current bot sizing/encoding and confirmed the deployed runtime. Guard tx `0x6fd779664b5dea208c6d117e290fdab66f53528f724e64ff9ca991f200058068` reverted `NO_PROFIT`, USDC balance 0 -> 0. Success tx `0x6f6b2b55a64600437112d9e4af8c9fc419e2ec263931b8f1e185e7fbfc9849e0` succeeded, USDC 0 -> 3.711168. Proof: `scratch/review-43f4e4af/morpho-proof.json`. Fork lease released.
- Detection and stop: paper heartbeat at 02:53Z reached Ethereum block 26381643, `runtime_ok=true`, scanning 734 candidates; ledger Morpho liquidation cursor reached 26381556 with no new event after block 26378725, previously classified outside the pinned markets. The manifest names pinned events at blocks 26372984-26373743. `node --check` and `scratch/morpho-fix-13c85970/stop-test.js` PASS. Source and test satisfy all ten items in `pitfalls/live-loss-stop-checklist.md`: every send gated; pending receipts block; fresh price; malformed receipts retained; Ethereum full gas charge; units; atomic persistence before send; sticky `STOPPED.json`; restart recovery including receipts pending across many heartbeats; offline tests. The live stop threshold is 30 USD.

--- Previous review ---

# Review 2026-11-10T01:22Z — fix

- Decision: **fix**; `next_review_at: null` (resubmit after funding configuration is corrected). Run `247ca66322ad4b9e892275400106818e`; `attempts:753`. No promotion attempted.
- **Operational blocker:** `manifest.yaml:24` requests `capital_usd: 400` and specifies no `principal_usdc`, so the manifest funding split sends 400 USD as Ethereum native gas. `bot.js:193,901-909` sets `LIVE_BALANCE_CAP_USD = 18` and returns without sending whenever the native wallet is above 18 USD. The gate has funded other Ethereum bots at their manifest native capital, so this bot would start funded but unable to act. Set native funding to an amount compatible with its own 18 USD preflight and resubmit; this is a manifest/configuration fix, with no change to the atomic executor needed.
- Other criteria pass on current bot.js SHA256 `5bc05a2acaf393d539339fd54fee316f867a69585438196dcfd17f54125a2c16`: `manifest-check`, `node --check`, and `node scratch/morpho-fix-13c85970/stop-test.js` pass, including long-pending receipt recovery after state damage. Independent Ethereum fork reset 26328589 deployed the unchanged artifact; guard tx `0x6fd779664b5dea208c6d117e290fdab66f53528f724e64ff9ca991f200058068` reverted `NO_PROFIT`, executor USDC remained 0; success tx `0x6f6b2b55a64600437112d9e4af8c9fc419e2ec263931b8f1e185e7fbfc9849e0` gained 3.711168 USDC. Lease released. The signed 460,000 gas × 17.5 gwei cap is 0.00805 ETH, below the manifest 20 USD at the current paper price. Public liquidation and sale comply with S; paper makes no signer send.
- Detection: paper heartbeat reached Ethereum block 26381183, `runtime_ok=true`; ledger has no new `morpho_blue.liquidate` after block 26378725 through cursor 26381162. That event is outside the two executable pinned markets. No new detection miss established.

--- Previous review ---

# Review 2026-11-09T23:45Z — fix

- Decision: **fix**; `next_review_at: null`; run `c0654dd11c2a4bb78603c9bdf4ad7a5c`; `attempts:744`. No promotion attempted.
- `manifest-check`, `node --check`, and the submitted `stop-test.js` pass. Current bot.js SHA256 `eb7beb03cbe3d79e8eeeae97c7e39c16dd123ff53f67b14353bd2c209d18ee37`; manifest/source/artifact hashes remain `91da15ed`/`19c584a1`/`34ecdc13`, independently fork-proven in review `7cbf8b95` (success +3.711168 USDC and NO_PROFIT revert). The Solidity guard at `MorphoLiquidator.sol:153` and signed 460000 gas × 17.5 gwei = 0.00805 ETH (~$17.13 at paper $2128/ETH) remain within manifest L=$20. The new stop defect blocks promotion, so no fork rerun was needed.
- **Fix checklist item 9, and extend item 10's test:** `recoverLossFromLogs()` keeps only accepted hashes after the second-to-last heartbeat (`bot.js:670-672`). A receipt can remain pending through more than two 20-second cycles when receipt reads or valuation fail. If `state.json` is then damaged, recovery drops that older uncharged hash, restores the last heartbeat's $29 loss, and `scanCycle()` persists the incomplete state before rearming sends. `node scratch/review-c0654dd1-recovery-probe.js` exercises the current recovery function with a still-unconfirmed hash and three later heartbeats: `pending=0, loss=29`. Retain *all* accepted hashes whose settlement is not durably recorded, or write a durable stop marker when their status cannot be reconstructed. Test an old pending receipt followed by damaged state and a full load → persist → send-gate check.
- Detection: paper heartbeat reached Ethereum block 26380702 with `runtime_ok=true`, 731 scanned candidates, and no signer send. Ledger `morpho_blue.liquidate` has no new Ethereum event after block 26378725, already classified outside the pinned markets. No new detection miss established.

--- Previous review ---

# Review 2026-11-09T22:12Z — fix

- Decision: **fix**; `next_review_at: null`; run `7ba9c267d87f4c99aec9ea28dceeca35`; `attempts:737`. No promotion attempted.
- `manifest-check`, `node --check`, and `node scratch/morpho-fix-13c85970/stop-test.js` pass. Current bot.js SHA256 `2daaa8e5c0e6138ae6225a6861bf0ab2c0655da5791f8057c832be817fe777e7`; manifest, artifact, source, and runtime retain the hashes independently fork-proven in review `7cbf8b95` (success and `NO_PROFIT` revert, `scratch/review-962b34af/morpho-proof.json`). Signed 460000 gas × 17.5 gwei = 0.00805 ETH, about $17.06 at paper ETH/USD $2119, below L=$20, with zero value. Paper log through Ethereum block 26380236 shows advancing scans and no signer send.
- **Fix checklist item 9 at the cycle boundary:** `loadState()` returns zero loss and an empty pending list when live `state.json` is missing or unreadable, setting `stateWriteFailed=true`. `scanCycle()` immediately calls `persistState(state)` at line 1072 before candidate sends; a successful write saves zero and clears the guard. Prior uncounted receipt hashes or realized losses can disappear permanently before the $30 stop marker was written. The offline test explicitly expects this first zero-state write to clear the guard, so it does not prove restart safety. Preserve the halt until prior loss history is recovered or a durable stop marker is written; test the full load → cycle persistence → send gate sequence. Other ten-item checklist checks pass the current code and test.
- Ethereum ledger `morpho_blue.liquidate` has no new event after block 26378725, already classified outside the pinned markets. No new detection miss is established.

--- Previous review ---

# Review 2026-11-09T20:39Z — fix

- Decision: **fix**; `next_review_at: null`; run `13c8597093704211b0b3657425d05997`; `attempts:730`. Current bot.js SHA256 `fc536ad3602784408a9724d78bef6da025f716c59c5720cb203da50f61307c60`. No promotion attempted.
- `manifest-check` and `node --check` pass. Executor and manifest are unchanged from the independent success/NO_PROFIT fork proof in review `7cbf8b95`; no fork rerun because the live stop criterion fails. Signed 460000 x 17.5 gwei = 0.00805 ETH, about $17.08 at paper $2122/ETH, below manifest $20; zero value. Paper heartbeat reached block 26379773 with `runtime_ok=true`. Ledger has no new Morpho Liquidate after block 26378725, already classified outside pinned markets.
- **Fix the $30 live stop in one pass:** `bot.js:727` gates pending receipts only when the gas price was not freshly valued. A failed receipt read leaves a receipt pending, yet a fresh price permits pool-init and liquidation sends. Block every signer send while `pending.length > 0` after settlement. The pool-init send at 750 lacks a `stateWriteFailed` check. Lines 929-930 default missing/malformed gas fields to zero and remove the receipt; retain it until actual gas is decoded. `saveState` at 603-616 writes directly, while `loadState` at 627-649 resets missing/unreadable live state to zero; use atomic writes and fail closed at live startup, including when `STOPPED.json` exists. `liveLossStopWrite` swallows errors but sets `stopLogged` without retry. Provide an offline test for price failure, receipt failure, threshold crossing, and restart. These fail checklist items 1, 2, 4, 7, 8, 9, and 10.

--- Previous review ---

# Review 2026-11-09T19:05Z — fix

- Decision: **fix**. `next_review_at: null`; run `2939f16ecf5b4f66b21da92dc87db945`; `attempts:721`. No promotion attempted.
- Current hashes: bot.js `fcb0232bc1c52f92f75154989fdda55e5048f14ae54654e2d78baa3257e23e95`; manifest `91da15ed5b85db183aa22352ae3205a4caeb29d6a0699145e0f19ef0db6d4a8d`; runtime `b3010db2727e12da2f3ab578e24fadb77a7e98bd6c0055e6adfd46a7a90b5d49`; source `19c584a18042a3c59065fdce487e1fe7119ed39d7830c3f7297757f993f9a65e`; artifact `34ecdc1339237fe511c37caf14d3b276e709cc6c79ef388544806bd0c57a5391`.
- `manifest-check` and `node --check` pass. The fresh-price change at bot.js:997-1003 now settles receipts after this cycle's oracle valuation. The unchanged artifact/source had independent success (+3.711168 USDC) and `NO_PROFIT` revert in prior review `7cbf8b95`, proof `scratch/review-962b34af/morpho-proof.json`; no fork rerun because the live stop criterion already fails. The owner-only executor atomically flashes, liquidates, sells, repays and requires a USDC gain. Signed 460000 gas x 17.5 gwei = 0.00805 ETH, about $17.05 at paper ETH/USD 2117 and below manifest L=$20; zero value. Paper sends nothing; public liquidation meets S.
- **Fix the $30 live stop:** bot.js:721-734 sends a `setPoolAllowed` initialization transaction before the `state.liveLoss.usd >= 30` check at bot.js:839. A new pool can therefore spend gas after the stop was reached, even though `scanCycle()` wrote `STOPPED.json`. Move the stop check before every signer send, including pool initialization. Also bot.js:997-1003 leaves confirmed receipts pending if the current oracle valuation fails, while bot.js:706 accepts a price cached for up to 15 minutes and the signer paths at 721-734 / 834-860 may still send. Block sends until pending gas has been valued and persisted with a fresh oracle read.
- Detection: Ethereum ledger `morpho_blue.liquidate` has no event after block 26378725, which the previous review classified as outside the pinned markets. Paper heartbeat reached block 26379309, `runtime_ok=true`, scanning 730 candidates with only dust/watch-only opportunities. No new awaited capture to reproduce.

--- Previous review ---

# Review 2026-11-09T17:30Z — fix

- Decision: **fix**. `next_review_at: null`; run `7cbf8b954a9b452bbfa3bd771c83bc32`, `attempts:711`. No promotion attempted because cumulative-loss valuation can be stale.
- Reviewed SHA256: bot.js `d9452a2bfcbc12e0cf1c1a89cc33ccdb7551af89dcaed1ea1824c75d8fd7ad79`, manifest.yaml `91da15ed5b85db183aa22352ae3205a4caeb29d6a0699145e0f19ef0db6d4a8d`, executor-runtime.hex `b3010db2727e12da2f3ab578e24fadb77a7e98bd6c0055e6adfd46a7a90b5d49`, source `19c584a18042a3c59065fdce487e1fe7119ed39d7830c3f7297757f993f9a65e`, artifact `34ecdc1339237fe511c37caf14d3b276e709cc6c79ef388544806bd0c57a5391`.
- `manifest-check` and `node --check` pass. I leased the Ethereum review fork, reset 26328589, deployed the current six-argument artifact and verified its runtime. `NO_PROFIT` tx `0x6fd779664b5dea208c6d117e290fdab66f53528f724e64ff9ca991f200058068` reverted with zero USDC retained; success tx `0x6f6b2b55a64600437112d9e4af8c9fc419e2ec263931b8f1e185e7fbfc9849e0` gained 3.711168 USDC at 308025 gas. Proof: `scratch/review-962b34af/morpho-proof.json`; lease released. The signed 460000 gas x 17.5 gwei bound is 0.00805 ETH, about $17.16 at paper $2132/ETH, below manifest L=$20. The executor is atomic; paper sends nothing; public Morpho liquidation is within S.
- The prior restart-safety defect is repaired: accepted hashes and settled loss are now saved after each change, and sends stop while persistence fails. **One stop defect remains:** `scanCycle()` settles receipts at `bot.js:927` before reading the current cycle's gas valuation at line 984. `liveLossSettle()` checks only `ETH_USD <= 0` at line 899. If the oracle read failed in prior cycles, it uses a cached price, removes a confirmed receipt from `pending`, and never revalues that gas. A rise in ETH/USD can make persisted cumulative live loss smaller than the $30 stop threshold. Settle only after a fresh valuation succeeds in that cycle; otherwise retain the receipt.
- Detection: ledger's new Ethereum Morpho liquidation at block 26378725, tx `0x9dcc3d090fcc64970dc7d45230143822a44c4f82dd48de39bb265f213e5a0816`, was in market `0x0655e0c8...`, outside executable pinned markets. Paper heartbeats advanced through block 26378794 with only dust/watch-only skips. No supported detection miss is established.

--- Previous review ---

unchanged since 811c0a9f096640b9ba60cc98e190addc, decision fix stands. Check run 233973f5be2e4f9ab5f3de40b56f194e: bot.js, manifest.yaml and named artifact predate the last review; only state/state.json changed. Ethereum ledger morpho_blue.liquidate last block remains 26375628, before the prior review; paper heartbeat reached 26378337. No new awaited event, fork rerun or attempts row. next_review_at: null.

# Review 2026-11-09T14:10Z — fix

- Decision: **fix**. `next_review_at: null`; persist loss and pending sends after each scan/send/settlement, failing closed if persistence fails. Run `811c0a9f096640b9ba60cc98e190addc`.
- `manifest-check` passes. I independently leased/reset `ethereum-review` fork generation 34 to 26328589, funded the owner, deployed the current six-arg named artifact, and ran `scratch/review-962b34af/morpho-proof.js`; deployed runtime matched. NO_PROFIT tx `0x6fd779664b5dea208c6d117e290fdab66f53528f724e64ff9ca991f200058068` reverted and retained zero USDC; success tx `0x6f6b2b55a64600437112d9e4af8c9fc419e2ec263931b8f1e185e7fbfc9849e0` gained 3.711168 USDC at 308025 gas. Lease released. The signed 460000 x <=17.5 gwei bound is 0.00805 ETH, about $17.06 at the $2119 paper price, below manifest $20; zero value. The owner-only executor is atomic, paper uses relay calls, and public Morpho liquidation meets S. Ledger's last new liquidation block 26375628 predates the prior review and is outside pinned markets; heartbeats now reach 26377815 with dust/watch-only skips and no eligible detection miss.
- **Live stop persistence fails on restart:** `bot.js:879-917` updates `state.liveLoss.usd`, `pending`, and `stopLogged` in every scan, and `bot.js:725,850` adds send hashes in that scan. But `saveState(state)` appears only in the five-minute `refreshCandidates` path (`bot.js:1057`, with no save after `scanCycle` at 1068-1075). A service restart after a send or receipt can reload an old total and lose the pending hash, letting cumulative loss cross $30 without a stop. Save durably after each change to liveLoss and before another send; keep STOPPED.json and the state total consistent.

--- Previous review ---

# Review 2026-11-09T07:52Z — wait

- Decision: **wait**. `next_review_at: 2026-11-10T12:00:00Z` (roughly one day at the measured 0.49/day pinned-market cadence). No promotion attempted. Run `f9712fc5f072496eb0e579a221be513f`.
- The manifest now names exactly one existing artifact and six ABI-encoded constructor addresses in the order in `MorphoLiquidator.sol`; `manifest-check` passes. The executable watcher, submitted runtime, Solidity source, and artifact retain the hashes of review `f680575b219047aba2f6db41c956298e`; only the manifest changed (SHA256 `91da15ed5b85db183aa22352ae3205a4caeb29d6a0699145e0f19ef0db6d4a8d`).
- Independent `ethereum-review` fork reproduction leased/reset block 26328589, deployed the manifest artifact with its current `executor_args`, verified byte-identical submitted runtime, and released the lease. `scratch/review-962b34af/morpho-proof.js` produced high-minProfit revert `NO_PROFIT`, USDC 0 → 0 (tx `0x6fd779664b5dea208c6d117e290fdab66f53528f724e64ff9ca991f200058068`), then snapshot-controlled success, USDC 0 → 3.711168 at 308,025 gas (tx `0x6f6b2b55a64600437112d9e4af8c9fc419e2ec263931b8f1e185e7fbfc9849e0`). The owner-only flash, liquidation, swap, repayment and USDC increase are atomic. The signed 460,000 gas × 17.5 gwei cap is 0.00805 ETH, about $16.84 at the paper price $2092/ETH, below manifest L=$20; value zero. Public liquidation and pool sale meet S; paper makes no send.
- Since the previous review, the ledger has two Ethereum Morpho liquidations at blocks 26375576 and 26375628, but their market IDs `0x4fa31e...` and `0xdbffac...` are outside the pinned WETH/USDC and WBTC/USDC routes. The paper log shows 272 advancing heartbeats through block 26375948, `runtime_ok=true`, zero executor simulations or simulated sends, with only pinned-market deterministic dust skips and unsupported-market watch-only entries. No new eligible detection miss is established. A natural polling-compatible supported capture with positive after-gas paper simulation remains the sole missing promotion evidence.

--- Previous review ---

# Review 2026-11-09T06:17Z — fix

- Decision: **fix**. `next_review_at: null`. No promotion attempted. Run `f680575b219047aba2f6db41c956298e`.
- **Deployment blocker:** parsed YAML `executor` is 1,163 characters of path plus prose; `os.path.isfile(manifest["executor"])` is false. The artifact itself exists at `scratch/morpho-executor-eth/contracts/out/MorphoLiquidator.sol/MorphoLiquidator.json`, but that must be the complete scalar field value. Its ABI has a six-address constructor and `executor_args` is absent; provide the ABI-encoded six addresses already stated in the prose in a separate `executor_args` field. This is the same path failure documented in `wiki/pitfalls/manifest-path-scalar.md` and the Reserve Folio review. The revised dust skip cannot make this artifact deployable.
- The code revision moves the deterministic dust skip to the cycle's `MIN_PROFIT_USD + expectedFeeUsd` floor, matching the on-chain minProfit and live send gate; `attempts:636` and paper logs since 05:41 show 92 completed 20-second heartbeats, 92 `simulate_skip` records, zero executor simulations and zero simulated sends, with `runtime_ok=true`. The previously alleged large-borrower detection misses were measured as zero-block oracle races (`attempts:615,635`), excluded by the 2026-11-06 human decision. The residual 26373743 dust captures were poll-catchable but too small to pay gas. Ethereum `morpho_blue.liquidate` has no new event after block 26373743 through verified cursor next_block 26375389, so there is no new detection exception. A natural polling-compatible supported capture with positive after-gas simulation remains unobserved.
- Named Solidity source and submitted runtime are unchanged from the independent guarded fork success/NO_PROFIT reproduction recorded in review `962b34af056e488395db560928c5c0a8`, so no new mechanics claim is taken from the changed watcher. The live action still targets only the owner-controlled atomic executor; paper uses relay reads and no signer. Signed worst case 460000 × 17.5 gwei = 0.00805 ETH, $17.13 at the 06:13 paper price $2128/ETH, below manifest L=$20; value zero. Public Morpho liquidation and AMM sale comply with S. Promotion remains blocked by the manifest, then by the missing natural profitable capture.
- Reviewed SHA256: bot.js `f4c327227f837d1d528b290b0c80c0ce57498d05a7310f1e1907c24bc0`; manifest `98423b345d59c635492574ea8fe4726ee1078dd10b60f966b377d123a548aff2`; runtime `b3010db2727e12da2f3ab578e24fadb77a7e98bd6c0055e6adfd46a7a90b5d49`; source `19c584a18042a3c59065fdce487e1fe7119ed39d7830c3f7297757f993f9a65e`; artifact `34ecdc1339237fe511c37caf14d3b276e709cc6c79ef388544806bd0c57a5391`.

--- Previous review ---

unchanged since b87263e4fbc640c686d48ed8abbd20b9, decision fix stands. Check run 6f9f5d6f22c84dd383b12064e77610b7 at 2026-11-09T04:36Z: bot.js, manifest.yaml, executor-runtime.hex and named executor source retain their recorded hashes; Ethereum morpho_blue.liquidate has no new event after reviewed cutoff block 26373743. Only state changed; no fork reproduction or attempts row. next_review_at remains null.

unchanged since b87263e4fbc640c686d48ed8abbd20b9, decision fix stands. Check run 064237d0ae6545f8a3a54e76fb1fee33 at 2026-11-09T02:49Z: bot.js, manifest.yaml, executor-runtime.hex and named executor source retain their recorded hashes; only state changed. Ethereum morpho_blue.liquidate has no new event after the previous reviewed cutoff block 26373743, so no detection exception; no fork reproduction or new attempts row. next_review_at remains null.

Decision: fix
Reviewed at: 2026-11-09T01:15Z
Reviewer: paper-reviewer / gpt-6-sol
Run: b87263e4fbc640c686d48ed8abbd20b9
next_review_at: null
Code SHA256: 35f25829da8feb1089e71178adde80822f40e5a4fd3e57d8ded7d67f0e6dcfe1
Manifest SHA256: dc943dea7ae0b7262095dabb0a4de8de15df18881caeefda6f97612a47ef9063
Executor source SHA256: 19c584a18042a3c59065fdce487e1fe7119ed39d7830c3f7297757f993f9a65e

Only state changed, so the prior independent atomic executor fork proof stands. Detection changed: the ledger records nine new Liquidate logs on the pinned WETH/USDC market after the last review, including 23,844.771353 and 16,087.611716 USDC repaid at block 26372984 (2026-11-08T21:55:47Z) and 113.745767 USDC at block 26372986 (21:56:11Z). The watcher ran throughout: the 21:54:35Z refresh held 726 candidates, with heartbeats at 21:55:37Z, 21:55:58Z and 21:56:18Z. It produced no opportunity or simulated send for the 16,087.61 and 113.75 USDC borrowers, while other actors captured them. Its 12 simulations in that period all reverted (11 NO_PROFIT, one healthy) on two different dust borrowers. The 23,844.77 USDC borrower was monitored but remained healthy at HF 1.0062 at 21:55:37Z; that capture may have been an oracle same-block race and is not the detection finding.

Decision **fix**: trace why the two missed borrowers were absent from opportunity/simulation output, and show a naturally observed, polling-compatible supported capture with profitable after-gas simulation before resubmission. No code, manifest or executor review was repeated; no fork lease or gate promotion.

--- Previous review ---
Decision: wait
Reviewed at: 2026-11-08T00:15Z
Reviewer: paper-reviewer / gpt-6-sol
Run: c4297fae2d864569bba8a7c91ebf3d81
next_review_at: 2026-11-09T00:00:00Z (roughly one day at measured 0.49/day post-cliff pinned-market cadence)
Code SHA256: 35f25829da8feb1089e71178adde80822f40e5a4fd3e57d8ded7d67f0e6dcfe1
Manifest SHA256: dc943dea7ae0b7262095dabb0a4de8de15df18881caeefda6f97612a47ef9063
Runtime SHA256: b3010db2727e12da2f3ab578e24fadb77a7e98bd6c0055e6adfd46a7a90b5d49
Executor source SHA256: 19c584a18042a3c59065fdce487e1fe7119ed39d7830c3f7297757f993f9a65e

Only state changed since the last full review; the named executor, code, manifest and runtime hashes match. The prior independent Ethereum fork success (USDC +3.711168, tx 0x6f6b2b55a64600437112d9e4af8c9fc419e2ec263931b8f1e185e7fbfc9849e0) and NO_PROFIT revert (tx 0x6fd779664b5dea208c6d117e290fdab66f53528f724e64ff9ca991f200058068) still establish the atomic guard. The 460000 gas x 17.5 gwei signing cap is 0.00805 ETH, about $18.01 at the current paper ETH/USD $2237 and within manifest L=$20. No route-excluding human decision applies.

The Ethereum morpho_blue.liquidate ledger has four events after the previous verified cursor 26359064, at blocks 26363468, 26365385, 26365517 and 26365781. Their market IDs (0x864c..., 0x4bb2..., 0x8ab1..., 0xf78b...) differ from the two executable pinned markets (0x94b823..., 0x3a85e619...). Verified cursor next_block 26366425. Paper logs through 00:12Z/head 26366482 show 20-second heartbeats, runtime_ok=true, zero executor simulations, and only deterministic dust skips or unsupported-market watch-only opportunities. Thus no awaited supported capture occurred to test detection, and the natural profitable polling-compatible event required for promotion remains absent. Continue supervised paper observation; no promotion attempted.

--- Previous review ---
Decision: wait
Reviewed at: 2026-11-06T23:29Z
Reviewer: paper-reviewer / gpt-6-sol
Run: 962b34af056e488395db560928c5c0a8
next_review_at: 2026-11-08T00:00:00Z (about one day; supported pinned-market natural captures recur roughly 0.49/day in the measured post-cliff sample)
Code SHA256: 35f25829da8feb1089e71178adde80822f40e5a4fd3e57d8ded7d67f0e6dcfe1
Manifest SHA256: dc943dea7ae0b7262095dabb0a4de8de15df18881caeefda6f97612a47ef9063
Runtime SHA256: b3010db2727e12da2f3ab578e24fadb77a7e98bd6c0055e6adfd46a7a90b5d49
Executor source SHA256: 19c584a18042a3c59065fdce487e1fe7119ed39d7830c3f7297757f993f9a65e

The changed manifest extends measured watcher evidence; bot code, submitted runtime and named executor source are byte-identical to the last full review. Capital is $400, principal_usdc is absent (zero), and the action uses a Morpho flash loan. The live send targets only the gate-deployed executor. Its owner-only liquidate() flashes USDC, liquidates, sells seized collateral through the allowed Uniswap V3 pool, repays the flash loan and requires the executor's USDC balance to rise by minProfit; failures revert atomically. The signed 460000 gas x <=17.5 gwei cap is <=0.00805 ETH, $17.99 at the paper heartbeat's $2235/ETH, below the manifest's $20. The signer makes the final signing-time USD check. The pool-init owner transaction is <=100000 gas under the same fee cap. Paper mode uses relay eth_call and no keys or send. Public Morpho liquidation and AMM sale meet S.

Independent mechanics reproduction: forge build passed; ethereum-review fork generation 7 reset at 26328589, deployed constructor-patched runtime byte-matched the submitted runtime. A high-minProfit fork send reverted NO_PROFIT and preserved USDC balance zero (0x6fd779664b5dea208c6d117e290fdab66f53528f724e64ff9ca991f200058068). On a clean snapshot, the success send 0x6f6b2b55a64600437112d9e4af8c9fc419e2ec263931b8f1e185e7fbfc9849e0 used 308025 gas and raised executor USDC from zero to 3.711168. Proof: scratch/review-962b34af/morpho-proof.json. A separate fork replay of the historical 0x0969c9fd... transaction reverted; its same-block preconditions were not reproduced, so it is not used as executor evidence. The fork lease was released.

Detection and economics still await a natural supported capture. The running paper service has no restarts, and its 21:54-23:27Z logs show 271 completed heartbeats, zero simulations, and only dust skips or unsupported-market watch-only entries. Ethereum morpho_blue.liquidate has no event after block 26356592 through verified cursor next_block 26359064; that last event was in unsupported market 0xbc99de6a.... The manifest names the last pinned captures at blocks 26349528 and 26349648, both measured as zero-block oracle races. The required evidence is one naturally detected supported WETH/USDC or WBTC/USDC opportunity with final sizing, positive after its own includable gas fee, and a polling-compatible liquidation window. The mechanics and watcher pass; a natural event is the only missing evidence, so wait under the role's wait criterion. No gate promotion attempted. KB attempts:343.

--- Previous review ---

unchanged since 7496ff6e5e96499781cecffcc589e285, decision fix stands. Check run 7d21923c90844d96a1000ea6c9b87272 at 2026-11-06T21:54Z: code, manifest, runtime and named executor source SHA256 match the last full review; only state changed. Ethereum morpho_blue.liquidate last block 26356592; verified cursor next_block 26358598. No new awaited event, fork reproduction or attempts row. next_review_at remains null.

unchanged since 7496ff6e5e96499781cecffcc589e285, decision fix stands. Check run 652aaf23bc4249198d4e61ac1e224af2 at 2026-11-06T20:22Z: code, manifest, runtime and named executor source SHA256 match the last full review; only state changed. Ethereum morpho_blue.liquidate remains at block 26356592 through verified ledger next_block 26358130. No new awaited event, fork reproduction or attempts row. next_review_at remains null.

unchanged since 7496ff6e5e96499781cecffcc589e285, decision fix stands. Check run 1d4134161fd24ea6924250b7c8340942 at 2026-11-06T18:51:30Z: code, manifest, submitted runtime and named executor source SHA256 still match the last full review; only state changed. morpho_blue.liquidate remains at block 26356592; Ethereum ledger verified through next_block 26357669. No new awaited event, fork reproduction or attempts row. next_review_at remains null.

unchanged since 7496ff6e5e96499781cecffcc589e285, decision fix stands. Check run 3cb48d637a024dd38ec0944ea93f240d at 2026-11-06T17:16Z: code, manifest, runtime and named executor source SHA256 match the last full review; only state changed. Ethereum morpho_blue.liquidate last block 26356592 was already reviewed as unsupported; verified next_block 26357213. No new awaited supported event, fork reproduction or attempts row. next_review_at remains null.

unchanged since 7496ff6e5e96499781cecffcc589e285, decision fix stands. Check run 71396b4d6be44a9a960fa1a4985be474 at 2026-11-06T15:42Z: code, manifest, runtime and named executor source SHA256 match the last full review; only state changed. New Ethereum Morpho liquidation at block 26356592, tx 0x359f30a778bee85a1b3e6b704d338e6c1cdf1d12417549ef4fe82011041fbe68, uses unsupported market 0xbc99de6a88904cd0e69042ad6f266e63182801f030c636507c3caf590ffd84fe. Verified next_block 26356754. No awaited supported event, fork reproduction or attempts row. next_review_at remains null.

unchanged since prior full review, decision fix stands. Check 2026-11-06T14:04:44.385781+00:00 run b23a1139030243f2bc61d9b1c4cd9878: code, manifest, runtime, and named executor source hashes match; only state changed. morpho_blue.liquidate last block 26355519 (unsupported market per prior review), verified next_block 26356211; no new awaited eligible event, so no detection exception. No fork reproduction or attempts row. next_review_at remains null.

unchanged since 7496ff6e5e96499781cecffcc589e285, decision fix stands. Check 2026-11-06T12:32Z run dfc56aae9b784907a84b26c1b6310a2b: code, manifest, runtime, and named executor source SHA256 match the last full review. New Ethereum morpho_blue.liquidate tx 0x186d10551b87a8a210bf969a6513b09f64e96e46d8e015edbf7db838d446ee9e at block 26355519 has market 0x8411eeb07c8e32de0b3784b6b967346a45593bfd8baeb291cc209dc195c7b3ad, outside the pinned WETH/USDC and WBTC/USDC markets; no supported detection miss. Verified cursor next_block 26355748. State-only change; no fork reproduction or attempts row. next_review_at remains null.

unchanged since 7496ff6e5e96499781cecffcc589e285, decision fix stands. Check 2026-11-06T11:00:09Z run 325468a3f96544cfa2806ae9d043bb32: code, manifest, runtime, and named executor source SHA256 match the last full review. Ethereum morpho_blue.liquidate max block 26353731; verified cursor next_block 26355287; no new awaited event, so no detection exception. State-only change; no fork reproduction or attempts row. next_review_at remains null.

unchanged since 7496ff6e5e96499781cecffcc589e285, decision fix stands. Check 2026-11-06 run e12914d4ba984d339cbca2780067b4ff: code SHA256 35f25829, manifest 3884bf55, runtime b3010db2, source 19c584a1 match the last full review. No new Ethereum morpho_blue.liquidate after block 26353731 through verified next_block 26354829; state-only change. No fork reproduction or attempts row. next_review_at remains null.

unchanged since last full review, decision fix stands. Check 2026-11-06 run 7e653174a7094a19bf8f3acc88f78829: code, manifest, runtime, and named executor source SHA256 match last full review. No new Ethereum morpho_blue.liquidate after prior reviewed block 26353731 through verified next_block 26354371; state-only change, no detection exception. No fork reproduction or attempts row. next_review_at remains null.

unchanged since 7496ff6e5e96499781cecffcc589e285, decision fix stands. Check 2026-11-06T06:16Z run da3e4b7a15804d50950943f26ec02836: code and manifest hashes match last full review; only state changed. Detection exception checked through verified ledger cursors: no new eligible awaited capture. No fork replay or attempts row. next_review_at remains null.

unchanged since 7496ff6e5e96499781cecffcc589e285, decision fix stands. Check 2026-11-06T04:43Z: code, manifest, runtime, and named executor source SHA256 match the last full review. State-only change. No new awaited ledger event after the prior reviewed cutoff through verified cursors (Arbitrum 521688075; Base 53747596; Ethereum 26353455); no detection exception, fork replay, or attempts row. next_review_at remains null.

unchanged since 7496ff6e5e96499781cecffcc589e285, decision fix stands. Check 2026-11-06T03:11Z run bce15686fe9f42ffbcff64eb22f48ea6: code, manifest, submitted runtime and named executor source SHA256 match the recorded full review. No new Ethereum Morpho liquidation after cutoff 26352531 through verified ledger next_block 26352993. State-only change; no fork reproduction or attempts row. next_review_at remains null.

unchanged since 7496ff6e5e96499781cecffcc589e285, decision fix stands. Check 2026-11-06T01:36Z run 91e6759c1b6243a99965a39a43768bf1: code, manifest, submitted runtime and named executor source SHA256 match the recorded review. Detection: No new Ethereum Morpho liquidation after reviewed cutoff 26351728 through verified ledger next_block 26352532. State-only change; no fork reproduction or attempts row. next_review_at remains null.

unchanged since 7496ff6e5e96499781cecffcc589e285, decision fix stands. Check 2026-11-06T00:03:00Z run 7fc3cc47d8b94d95b087e14af759fc42: code, manifest, runtime and named source hashes match prior review. New Ethereum Morpho events through block 26351728 are outside supported market 0x3a85e619751152991742810df6ec69ce473daef99e28a64ab2340d7b7ccfee49. State-only change; no fork or attempts row.

unchanged since 7496ff6e5e96499781cecffcc589e285, decision fix stands. Check 2026-11-05T22:28:12+00:00 run 9acd1dfc0fe148feb2c95c556c9a698f: code, manifest, runtime and named source hashes match prior review; no new Ethereum Morpho capture after previous verified block 26350626 through ledger next_block 26351542. State-only change, no detection exception, fork or attempts row.

unchanged since 7496ff6e5e96499781cecffcc589e285, decision fix stands

Check 2026-11-05T20:50Z, run 554faf76303b4306ac05e28c1a7e2dc6: code, manifest, submitted runtime and named executor source SHA256 match the last full review. New Ethereum Morpho event at block 26350626 uses unsupported market 0x140fe48783fe88d2a52b31705577d917628caaf74ff79865b39d4c2aa6c2fd3c; ledger next_block 26351082. Only state changed; no fork re-review or attempts row. next_review_at remains null.

Decision: fix
Reviewed at: 2026-11-05T19:15:01Z
Reviewer: paper-reviewer / gpt-6-sol
Run: 7496ff6e5e96499781cecffcc589e285
next_review_at: null (resubmit after a natural supported profitable capture with measured polling-compatible window)
Code SHA256: 35f25829da8feb1089e71178adde80822f40e5a4fd3e57d8ded7d67f0e6dcfe1
Manifest SHA256: 3884bf558f92247fc415d4cbf45c56bcec5289785239a5c9f7629de8eaabbfd3
Runtime SHA256: b3010db2727e12da2f3ab578e24fadb77a7e98bd6c0055e6adfd46a7a90b5d49
Executor source SHA256: 19c584a18042a3c59065fdce487e1fe7119ed39d7830c3f7297757f993f9a65e

The new PIN_CAND_CAP=1200 is applied to both candidate trimming and pinned-market scan caps, and the manifest now names the latest pinned captures 26349528/26349648. The supervised service has stayed active since 18:19:57 UTC without restarts; logs 18:22..19:13 contain 123 heartbeats, 246 deterministic dust skips, zero executor simulations, and no errors. State deepDone is true. This improves dormant-borrower retention but does not yet demonstrate capture of a profitable position.

Independent mechanics reproduction passed on the leased ethereum-review fork, reset 26328589: fresh forge build succeeded; deployed creation bytes produced runtime identical to the submitted runtime. The guarded send 0x6fd779664b5dea208c6d117e290fdab66f53528f724e64ff9ca991f200058068 reverted with NO_PROFIT, preserving executor USDC 0; a clean snapshot send 0x6f6b2b55a64600437112d9e4af8c9fc419e2ec263931b8f1e185e7fbfc9849e0 succeeded, gas 308025, executor USDC 0 -> 3.711168. Evidence scratch/review-7496ff6e/morpho-proof.json; fork lease released. The owner-only flash-loan, liquidation, collateral sale and end-balance check are atomic. Live sends carry gasLimit 460000 and maxFeePerGas <=17.5 gwei plus a fresh USD bound. Paper uses the relay and sends nothing; public liquidation/AMM sale comply with S.

Required before promotion: one naturally detected supported WETH/USDC or WBTC/USDC position, exact final sizing and executor simulation, positive after its own includable gas fee, and an eligibility window long enough for the measured 20-second scan and inclusion. The previous real pinned captures had zero-block oracle-race windows. Seven new Morpho liquidation logs in Ethereum blocks 26350214..26350423 through verified next_block 26350619 all use other market IDs, so no detection exception was triggered. The refreshed manifest last-event evidence is now current; an unscheduled capture provides no justified wait date. KB attempts:207. No promotion attempted; no bot code changed by reviewer.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-05T17:40:19Z
Reviewer: paper-reviewer / gpt-6-sol
Run: bfcc6de358b5425b971016b29f692a50
next_review_at: null (resubmit after a natural supported profitable capture with a measured polling-compatible window and updated last-event evidence)
Code SHA256: cf5b708328b3632339b584f96de17c21066a1e8096190d942888571654f47267
Manifest SHA256: 3eeb3ac776449b8433edaf4913c07f0c43acf225bb0bc91d3d48ff56e7e58cc5
Runtime SHA256: b3010db2727e12da2f3ab578e24fadb77a7e98bd6c0055e6adfd46a7a90b5d49
Executor source SHA256: 19c584a18042a3c59065fdce487e1fe7119ed39d7830c3f7297757f993f9a65e

Do not promote yet. The revised service started at 17:21:02 UTC, is active with zero restarts, and through 17:38:32 logged 52 completed heartbeats, 4 candidate refreshes, 104 deterministic dust skips, zero executor simulations, and zero errors. Steady scans spent 4 relay reads per ~20 s (~12/min), below the manifest's 60/min budget. Its deep backfill finished (state.deepDone=true; cursor 26350166). The new scan and accounting changes are useful, but no naturally detected supported profitable liquidation has exercised the final send gate. The latest pinned WBTC capture was block 26349528, tx 0x8011e403397d4d9fd70dd8ce4c42103f1e68aed73369ea8ae35d94db410227cc, before this revision; the previous review documented its detection miss. The manifest still names older block 26338616 as the last WBTC event and must be corrected. The only new Ethereum Morpho liquidation since the prior review is block 26349831, tx 0xa30415287d1fee1f14e1764d284818f301592d8897cc45add94ac94e10dc3075, in unsupported market 0x4fa31e3f8ba345227d44e1cf48559eea53a90dd5311dc006984c060f2f311d96. Verified ledger cursor is next_block 26350163. An awaited qualifying event is unscheduled, so no justified wait date exists.

Independent mechanics reproduction: fresh forge build succeeded; named Solidity source and submitted runtime hashes are above. On a leased ethereum-review fork reset to parent block 26328589, deployed the submitted creation bytes from 0xffff...fffe; deployed address 0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352 had byte-identical submitted runtime. After the historical local time advance used in the prior fixture, the exact exported sizing/calldata path produced guard tx 0x6fd779664b5dea208c6d117e290fdab66f53528f724e64ff9ca991f200058068 status 0 with NO_PROFIT and executor USDC 0 -> 0; a clean snapshot then produced success tx 0x6f6b2b55a64600437112d9e4af8c9fc419e2ec263931b8f1e185e7fbfc9849e0 status 1, gas 308025, executor USDC 0 -> 3711168. Evidence: scratch/review-bfcc6de3/fork-proof.json. This is a zero-base-fee historical mechanics fixture, not proof of contemporary profitability or a polling-compatible capture.

The owner-only executor flash-loans USDC, liquidates, sells seized collateral and checks final USDC balance in one transaction; revert restores principal. The Ethereum send signs gasLimit 460000 and maxFeePerGas <=17.5 gwei, bounding gas by 0.00805 ETH, and the live path checks fresh ETH/USD before its <=$20 gate. Paper sends no transaction and accesses no keys; public liquidation and pool sale comply with S. The current code and manifest cannot be promoted because the prior natural catchability blocker remains. Gate status: capital $72.04/$2000, daily loss $0, not frozen, no live bots. KB attempts:201. No gate promotion attempted and no bot code or service changed by reviewer. No embedded instruction observed.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-05T16:06:55.128780+00:00
Reviewer: paper-reviewer / gpt-6-sol
Run: 389147c26a15455ea8718a807d4ce107
next_review_at: null (resubmit after a natural contemporary profitable capture with polling-compatible eligibility and independent fork reproduction)
Code SHA256: 15e7df2c11ca3eb0e0d8a19a9d3885beb746a65cf92257561e0d59a404afd974
Manifest SHA256: 96203857cffb19e9236011065590f8ee0beb231b8d05bcd634a0d1b88b76abb8
Runtime SHA256: b3010db2727e12da2f3ab578e24fadb77a7e98bd6c0055e6adfd46a7a90b5d49
Executor source SHA256: 19c584a18042a3c59065fdce487e1fe7119ed39d7830c3f7297757f993f9a65e
State-only change; four new Ethereum Morpho Liquidate events through verified next_block 26349662 use market ids 0x38fa7d75c15a0f11cc46e2d1987a05c26a836d0da6b4430657ec5ece38a25a45, 0x3a85e619751152991742810df6ec69ce473daef99e28a64ab2340d7b7ccfee49 and 0xa0534c78620867b7c8706e3b6df9e69a2bc67c783281b7a77e034ed75cee012e; only the second is pinned WBTC/USDC. The WBTC event at block 26349528 is a new awaited executable capture and triggers detection review: paper log saw victim 0xcff5904295eff623d668061cc27aa479871ab821 as healthy (HF 1.0037214) at 15:27:52 UTC and has no matching simulate. This is a capture the 20 s poll did not catch; the logged pre-capture HF suggests an oracle race, while the exact eligibility transition and profitable window remain unmeasured. Decision fix continues. No fork reproduction or new attempts row.

--- Previous review ---

unchanged since 9fe6b863a4fd4f489f7016cb5fd1b69d, decision fix stands

Check 2026-11-05T14:33:22.527390+00:00, run d2a377e8018f4704ba5e8d23db77c563: code, manifest, submitted runtime and named executor source SHA256 match last full review. State-only changes are not a resubmission. Detection: Ethereum Morpho verified next_block 26349207, zero new events after prior 26348740. No fork reproduction or new attempts row. Existing fixes and next_review_at unchanged.

unchanged since 9fe6b863a4fd4f489f7016cb5fd1b69d, decision fix stands

Check 2026-11-05T13:00:03.813593+00:00, run 2acf28edc09a42b9aba0ab4c342bed45: code, manifest, submitted runtime and named executor source SHA256 match the last full review. State-only changes are not a resubmission. No new awaited ledger event since prior cutoff through verified next_block 26348740. No detection exception, fork reproduction or new attempts row. Existing fixes and next_review_at remain unchanged.

unchanged since 9fe6b863a4fd4f489f7016cb5fd1b69d, decision fix stands

Check 2026-11-05T11:18:03.096984+00:00, run 3c9b5d18bc744ad1bef76135351f8bce: code, manifest, submitted runtime and named executor source hashes match the last full review. State-only changes are not a resubmission. No new awaited capture in the verified ledger since the previous review cutoff through Ethereum next_block 26348208. No detection exception, fork reproduction or new attempts row. Existing fixes and next_review_at remain unchanged.

unchanged since 9fe6b863a4fd4f489f7016cb5fd1b69d, decision fix stands

Check 2026-11-05T09:42:44.698072+00:00, run cc0348c28e9e4600b8bbaf100661e778: code, manifest, submitted runtime and named executor source hashes match the last full review. State-only changes are not a resubmission. No new Ethereum Morpho liquidation since prior verified cursor 26347292 through verified 26347748. Paper since 08:09 UTC: 270 heartbeats, 18 refreshes and 810 healthy near-threshold labels, no executor simulation. No fork reproduction or new attempts row. Existing fixes and next_review_at remain unchanged.

Decision: fix
Reviewed at: 2026-11-05T08:09:08.055034+00:00
Reviewer: paper-reviewer / gpt-6-sol
Run: 9fe6b863a4fd4f489f7016cb5fd1b69d
next_review_at: null (resubmit after a natural contemporary profitable capture with polling-compatible eligibility and independent fork reproduction)
Code SHA256: 15e7df2c11ca3eb0e0d8a19a9d3885beb746a65cf92257561e0d59a404afd974
Manifest SHA256: 96203857cffb19e9236011065590f8ee0beb231b8d05bcd634a0d1b88b76abb8
Runtime SHA256: b3010db2727e12da2f3ab578e24fadb77a7e98bd6c0055e6adfd46a7a90b5d49
Executor source SHA256: 19c584a18042a3c59065fdce487e1fe7119ed39d7830c3f7297757f993f9a65e

Manifest-only change: post-fee-cliff blocks26322217,26328590,26338616 are described with their own fee floors; the author states each is an oracle race with zero-block eligibility. This supports current-era fee viability for those captures but does not combine it with a polling-compatible window. The hypothetical next event is not evidence and has no scheduled time. Last decision's requirement remains: one naturally pre-discovered supported final-sized profitable executor execution through the final live gate at contemporary fees and a measured window, plus independent genuine NO_PROFIT rollback preserving balances. Submitted fork hashes remain untrusted because no independent reproduction; Ethereum fork is currently leased by another run, respected. Existing Solidity/runtime/JS hashes are unchanged. No gate promotion attempted.

Paper since prior review: 449 heartbeats, 31 refreshes, near-threshold opportunity labels but no executor simulation. No new Ethereum Morpho capture since block26346454 through verified cursor26347292. Public liquidation/AMM sale complies with S. KB attempts:170.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-05T05:33:28.294625+00:00
Reviewer: paper-reviewer / gpt-6.1-sol
Run: 7880fdd76ce14eada2c9bd1618b32126
next_review_at: null (resubmit after concrete blockers below are resolved)
Code SHA256: 15e7df2c11ca3eb0e0d8a19a9d3885beb746a65cf92257561e0d59a404afd974
Manifest SHA256: 2fc6663193f9775dea5a5e2d0e03eb2b2adf1b59eb998874bc2dd22fe8d6de0f
Runtime SHA256: b3010db2727e12da2f3ab578e24fadb77a7e98bd6c0055e6adfd46a7a90b5d49
Executor source SHA256: 19c584a18042a3c59065fdce487e1fe7119ed39d7830c3f7297757f993f9a65e

Manifest-only resubmission — decision fix (KB attempts160, lead14 updated).

Accepted scope: new big-case documentation uses the event's own parent/winner fees, discloses the favourable pool/oracle divergence and failed initial guard choice, and honestly names the one-block window. Existing source/code/runtime, raw-unit fractional-profit gate and scan-cycle stale-policy clearing remain unchanged and previously accepted. Fresh forge artifact matches and runtime matches the entire template plus expected immutables.

Required before promotion:
Supply ONE natural supported pre-discovered case combining final capped sizing/actual live gate, profitable executor sale at CONTEMPORANEOUS inclusion fees, and a polling-compatible measured eligibility window, plus traced NO_PROFIT rollback preserving balances. The new biggest case26300862 can improve the fee/profit evidence, but does not resolve timing: independent exact accrued scan through relay reproduces parent26300861 HF0.992854112, preceding26300860 HF1.008783327. That is one block; the bot waits20s AFTER each completed scan, so it remains a race-like example, not the accepted longer-window earning class. Do not combine a profitable one-block case with a different long-window case whose actual-era final floor still rejects. Keep the previously measured longer-window subset accepted and limit blocked_infra to measured race cases.

Submitted +71.731107USDC era success/NO_PROFIT hashes remain untrusted as independently unreproduced this session because of the active shared fork lease. No stronger claim is made from fresh compile or relay eligibility reads. The manifest's generic 'multi-block window for6/13' still conflates parent-underwater (6) with multi-block (5 in its own list, including this one-block case); distinguish these counts.

Paper03:57:25..05:28:47:266 heartbeats,18 refreshes,532 healthy near-threshold labels, no error or executor simulation. Labels with healthy=true are not executable opportunities.

No new queued-protocol captures since the last review through verified Ethereum next_block26346454, Base next_block53533134 and Arbitrum next_block521385043; later ledger tail unknown. No new detection miss established. Awaited mechanisms have named real historical events, but no scheduled next event justifies wait. Six of12 paper slots; no capacity demotion. Gate status: capital77.45USD/2000, daily loss0, frozen=false, halted=false, live empty. No promotion attempted, no repeat of previous gate rejection.

Fork reproduction was attempted, NOT completed or trusted: Ethereum replay of Aave winner8a8a9177... and reset26300861 for Morpho were refused by the active earner lease6879654c516f447f9e31916bb2321ed2. Lease respected, no --force or fork mutation. New successful execution/guard evidence is not independently credited; the concrete source/policy/evidence blockers suffice for fix. Reproduce exact executor success and traced NO_PROFIT rollback before promotion. Fresh forge builds were performed from reviewer snapshots and match named artifact creation/deployed bytecode; compile success alone is not fork execution proof.

Paper execution branches send nothing and do not access keys; reads use relay. Actual live signer/socket/keys/credentials were not accessed; the deterministic Compound fixture mocks chain reads and traps unexpected signer access. Public liquidation/reserve purchase and ordinary AMM sale satisfy S. No mainnet mutation or embedded instruction observed. No bot code, manifest, runtime, source, artifact or service changed by reviewer; only review.md changed under bots/. Evidence scratch/review-7880fdd7/.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-05T03:57:19.037949+00:00
Reviewer: paper-reviewer / gpt-6.1-sol
Run: 6b61bdcba9c645a0a7d28194f615673a
next_review_at: null (resubmit after concrete blockers below are resolved)
Code SHA256: 15e7df2c11ca3eb0e0d8a19a9d3885beb746a65cf92257561e0d59a404afd974
Manifest SHA256: 9b247278927f20e4623ff98d3c671e71865408a4970a8cd28975a633c44877c2
Runtime SHA256: b3010db2727e12da2f3ab578e24fadb77a7e98bd6c0055e6adfd46a7a90b5d49
Executor source SHA256: 19c584a18042a3c59065fdce487e1fe7119ed39d7830c3f7297757f993f9a65e

Accepted code repairs:
Exact current simulateLiquidation in an explicitly MOCKED-success eth_call/RPC fixture with stub signer now retains oracle profit2.36813USDC, expected fee0.04143131712048USD, raw on-chain floor2041432, and reaches a captured send (previous truncated2USD was suppressed). Exact scanCycle starts with valid old policy, injects four failed header reads, clears feePolicy=null; feeBound is false, then actual simulateLiquidation reaches fee policy missing skip after stub address/code/owner/nonce reads, without any send. updateFeePolicy alone still retains policy on failure, but the sole production scanCycle caller now clears it; that repair is accepted. See morpho-mock-live-fixture.js, morpho-stale-check.js and their JSON. Documentation count/sample/init-fee corrections were already accepted last review and remain accepted.

Required before promotion:
Supply a natural pre-discovered final-sized positive executor execution through the final live gate with CONTEMPORANEOUS inclusion fees and a measured polling-compatible eligibility window. The resubmission again substitutes39628498wei modern basefee into historical parent26302108; it is counterfactual profitability. Its own winner-era5.483491711gwei run still reverts NO_PROFIT (delta0, fee4.617USD). A repaired gate and mechanics under local altered fees do not establish natural historical profitability. Preserve the accepted longer-window subset and limit blocked_infra labels to measured oracle races. No new event in the verified ledger resolves this gap.

Supervised start03:11:31 follows02:28 code/02:29 manifest edits. Paper02:21..03:53:22:272 completed heartbeats,20 candidate refreshes,544 healthy opportunity labels,2 starts, no errors or executor simulation. Healthy labels are not executable opportunities. KB attempts153, lead14 updated. next_review_at null pending the concrete evidence above.

Independent fresh forge builds match the named artifacts' creation and deployed bytecode. Readable executors and submitted runtime are unchanged from the last full independent fork review. Owner-only atomic executor action and final positive base/loan-token balance guard remain present; signed gas cap and fresh USD guard bound gas at20USD. Paper does not send or touch keys; chain reads use relay. Public liquidation/reserve purchase and AMM sale comply with S. No security exploit or embedded instruction observed.

Fresh independent fork reproduction was ATTEMPTED, not completed: fork reset ethereum26302108 was refused because earner run99cbc5a7f6c547dc83840041f2e6d7a4 holds the fork lease for its cv3 rescope proof (1093s remaining). Lease respected, no --force, fork mutations, replay or new success/revert credit. New submitted fork evidence is not trusted as independently reproduced this session. Concrete unresolved blockers below suffice for fix; do not promote without reproduction. JS fixtures explicitly mock RPC/eth_call and a signer; they prove control flow only. No real signer/socket/credential access or mainnet mutation. No bot code/manifest/source/runtime/service edited by reviewer; only review.md under bots/.

No new awaited Compound or Morpho capture through verified Ethereum next_block26345995. Only new queued-chain event is unrelated Ethereum Aave26345712, outside queue routes. Later ledger tail unknown. Five of12 paper slots; no capacity demotion. Gate capital77.58USD/2000, daily loss0, frozen=false, halted=false, no live bots. No promotion attempt or repeat of prior gate rejection. No scheduled event justifies wait. Evidence scratch/review-6b61bdcb/.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-05T02:21:01.486011+00:00
Reviewer: paper-reviewer / gpt-6.1-sol
Run: 2e9cbbaad6b24c11997d2ba58c6b057e
next_review_at: null (resubmit after concrete blockers below are resolved)
Code SHA256: b59ac90ff98fa5594a0a5280338f5c7745bfea7b6b0af9736d1ca6d1a3f1d6bf
Manifest SHA256: e73846929f588e80cc4a48bef24f2a8e6ccde94361b29c3d253a78e0423e3fa9
Runtime SHA256: b3010db2727e12da2f3ab578e24fadb77a7e98bd6c0055e6adfd46a7a90b5d49
Executor source SHA256: 19c584a18042a3c59065fdce487e1fe7119ed39d7830c3f7297757f993f9a65e

Decision remains fix. Accepted repairs:
Top-level awaited_events is restored and parses. Concurrent manifest-only repair02:16:17 was inspected and accepted before final hashes: correct6CATCHABLE/7ORACLE_RACE counts, sampled endpoints distinguished from continuous evidence, and init-fee prose matches dynamic policy. Code/source/runtime did not change during this review. Dynamic per-cycle maxFee=min(basefee*9/8+0.001gwei,17.5gwei),460000gas cap and final fresh USD20 guard replace the fixed nonincludable cap; selected cap product is at most0.00805ETH. Exact submitted executor is unchanged and fresh forge artifact matches. Actual deployed11455byte constructor-linked runtime equals submission. Service restarted01:32:37 after revised code; inspected00:40:56..02:12:55 contains271 completed heartbeats,18 refreshes,618 healthy opportunity labels, one restart, no errors and no executor simulation. Healthy labels are not executable opportunities.

Required fixes:
1. Fix profit precision in the ACTUAL final live gate. bot.js computes Number(profitWei/loanUnit), truncating2.368130USDC to2USD. Exact current simulateLiquidation on natural parent26302108 with actual deployed-owner/no-override fork eth_call returns sim_ok=true, floor2041432wei, expectedfee0.04143131712048USD, need2.04143131712048USD, profit_usd_oracle2; stub signer receives address only, NO send. Fixture uses disclosed LOCAL current-era basefee39628498wei, valuation2428USD/ETH and stub0.001ETH gas balance. Earner fee-check.js passes floating2.368 directly instead of this final truncated expression, so it does not prove the advertised live behavior. Demonstrate the exact unchanged final bot path reaching a captured stub send after repair.
2. Clear or expire feePolicy on failed latest-header refresh. Injected outage through exact module makes updateFeePolicy returnnull after4stub reads, but retains prior policy and feeBound.ok=true. No freshness timestamp/expiry protects it; subsequent scan ignores the return. This contradicts the stated header-failure fail-closed behavior and can simulate/send with stale fee/floor assumptions. Test a valid policy followed by failed refresh, including the final send decision.
3. Retain the natural final-policy contemporaneous fee/profit requirement. Fresh natural parent26302108 exact executor success yields+2.736436USDC before gas, but current-era basefee substituted into that state is counterfactual. Actual historical headers parent5.917438802gwei and winner5.483491711gwei still make this final2USD-profit policy reject. Show discovery/eligibility/final sizing/actual sale/live gate and contemporaneous inclusion fees together; do not label modern-fee substitution natural historical catchability.
Prior independently measured longer-window class remains accepted; do not classify all opportunities as oracle races. The final manifest count/sampling corrections resolve the initial documentation finding recorded in attempts148; see addendum149.

Independent fresh natural executor proof:
Reset26302108, actual creation deployment, real accrue transaction and no time/oracle/token-state changes. Signed460000gas, derived45582060wei maxFee/1000000wei priority, disclosed LOCAL current-era nextbasefee39628498wei before sends. Guard758af71f20e8... status0 gas381618, trace NO_PROFIT and unchanged loan/collateral balances. Success9c2b2880b492... status1 gas307335, USDC+2736436wei, collateral retained; effectiveGasPrice40628498wei (about0.030317USD gas at fixture2428USD/ETH). Head/runtime checked before and after every execution send. Success testminProfit2050000wei; actual final live simulation separately computes2041432wei and succeeds, but final JS send gate blocks it as above. These are mechanics and local-fee proofs, not successful natural contemporary final-policy captures.

Detection: no new pinned/executable Morpho Ethereum event since verified26345004 through verified next_block26345538; later tail unknown. No new miss established. KB attempts148; lead14 updated. next_review_at null pending concrete repairs.

Fresh build and constructor-linked runtime checks plus independent sequential reset/deploy/fund/accrue as needed/guard/success runs verified head and executor code around execution sends. Forks use the relay research lane; no direct mainnet RPC. Whole actions remain atomic with owner entry and armed genuine-pool callbacks; guards preserve starting loan/base and collateral balances, and success preserves retained collateral. Final loan/base balances must increase. Signed gasLimit x maxFeePerGas with fresh USD guard bounds liquidation/trade gas loss at20USD; the Solidity guard bounds principal loss. Public liquidation/reserve purchases and AMM sales are intended incentives under S. Paper does not send or access signer/keys. Actual live-path fixtures use stub signer only, never a real socket.

No bot code, manifest, named source/artifact/runtime or supervised service was edited. Only review.md changed under bots/. No mainnet mutation, actual signer/keys/credentials or embedded instruction observed. Five of12 slots; no capacity demotion. Gate start capital77.71USD/2000, daily loss0, frozen=false, halted=false, live empty. No promotion attempted; prior gate funding rejection remains final, no workaround. No scheduled event justifies wait. Evidence scratch/review-2e9cbbaa/.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-05T00:40:56.289224+00:00
Reviewer: paper-reviewer / gpt-6.1-sol
Run: a1438eb019484ef1b893ff54db7434dc
next_review_at: null (resubmit after manifest and natural final-policy fee-compatible evidence are resolved)
Code SHA256: 39d95b3ffa8f4cee55831f6aa28a9f7516eed44990d0d5ca40e4244f1a66dd46
Manifest SHA256: 1130607325cbd64785175c4a6464e8df116d673b9512bb7668453ebcf48398aa
Runtime SHA256: b3010db2727e12da2f3ab578e24fadb77a7e98bd6c0055e6adfd46a7a90b5d49
Executor source SHA256: 19c584a18042a3c59065fdce487e1fe7119ed39d7830c3f7297757f993f9a65e

Accepted repairs:
Pending failure deadline now overrides overdue success cadence; assigned retry delay is logged accurately. Exact copied tick with deterministic injected startup AND steady-state overdue failures attempts1000000,1020000,1040000,1080000, skips1060000, logs10/20/40/60s. No RPC in those fixtures. Restart23:50:39 loads revision. Inspected logs23:03:17..00:35:42 show273 completed heartbeats,18 refreshes, no refresh_error or successful executor simulation; healthy near-threshold opportunity labels are not eligibility. WETH dollar arithmetic fixed. Extended natural-window study demonstrates a distinct longer-lived class; do not classify all pinned opportunities as oracle races.

Required fixes:
1. Restore TOP-LEVEL awaited_events. Current YAML parses, but the indented `awaited_events: >` is part of fork_evidence text and the actual manifest key is absent. Its prose still says next liquidation equals next oracle update, contradicting new longer-window evidence. Correct counts: saved13event study contains6CATCHABLE/7ORACLE_RACE, not7/6. Keep sampled ladder endpoints distinct from continuous eligibility evidence.
2. Supply a natural pre-discovered, final-policy executable, fee-includable profitable case. Independent relay accrued scan reproduces26302109 borrower537ae22b... HF0.985980656 atL-128 and1.007985226 atL-256; parentHF0.985978611. Borrower is retained in current candidates (not proof of original discovery time). Natural parent26302108 exact artifact, no time/oracle mutation: actual accrue succeeds; sized repay54.015978USDC, seize0.025550115109879465WETH, oracle proceeds56.384108USDC. Guardc3f2f6cc... status0 gas381618, NO_PROFIT and preserved balances; success67d536ee... status1 gas307335,+2.736436USDC at TEST minProfit2.7USDC. These sends set LOCAL basefee0. Real parent header basefee5.917438802gwei is above signed0.2gwei, so this historical case is not includable as configured. In addition final bot gate computes Number(profitWei/loanUnit)=2 from2.368130oracle profit, then requires2+gas, suppressing the send despite the successful local sale. The submitted actor-bonus estimate1.651net is below bot2USD floor and is not exact executor economics. Measure eligibility, capped sizing, actual sale/minProfit, final live gate and fee inclusion together; avoid claiming local altered-fee successes prove natural catchability. Keep prior two measured oracle-race victims blocked_infra, with scope limited to that class. No scheduled event supports wait.

Independent unchanged-executor reproduction:
Fresh forge0.8.24 build equals named artifact. Deployment from paper owner links11455byte runtime byte-identical to submission; owner-only/whitelisted entry, armed callbacks, payment bounded by newly seized collateral and final positiveUSDC balance guard present. Whole flash/repay/seize/sale/flash repayment atomic. Signed1.5Mgas*0.2gwei=0.0003ETH with fresh valuation enforces gas bound. WETH26328589 test with disclosed local time advance: NO_PROFIT8b08410e... gas382481, success079e2b1f... gas308025,+3.711230USDC. Optional oracle call REVERTS, not credited. WBTC26301962 owner initialization plus actual accrue: NO_PROFITbcc63803... gas419323, successd755912d... gas342273,+0.158935USDC at test0.1USDCfloor, below bot2USDfloor. Both preserve debt/collateral on rollback and retained collateral on success; all localbasefee0. Named winner0969c9fd replay status0 gas141046, local a5684196...; not credited as successful historical replay. Head/runtime checked around every execution send.

Detection: new26344559 tx47c53a82... market5cebfae1... is outside the two pinned executable routes. No executable-route miss established through verified Ethereum next_block26345004; later tail unknown. KB attempts140; lead14 updated to retain longer-window evidence while stating remaining policy/fee limits. next_review_at null pending concrete fixes.

No bot code, manifest, executor source/runtime or service was changed by reviewer. No mainnet mutation, real signer socket, keys or credentials accessed; live fixtures use a stub signer only. Public liquidation/reserve purchase and AMM sales satisfy S. Mainnet reads use relay, execution mutations only local forks. Five of12 paper slots, no capacity demotion. Gate capital77.6USD/2000, daily loss0, frozen=false, halted=false, live empty. No promotion attempted; prior funding rejection remains final. Evidence scratch/review-a1438eb0/. No embedded instruction observed.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-04T23:03:11.549151+00:00
Reviewer: paper-reviewer / gpt-6.1-sol
Run: e7daaefc473547cfbc019240810c952a
next_review_at: null (resubmit after retry deadline fix and a supported natural polling-compatible earning class)
Code SHA256: ce633731e2adf985e1ece0677512dccaf53aabe5edf59869111334ccb235d296
Manifest SHA256: 25e04e5a44b26d0505b7c96412eeffc22dc03c7ddf07b18641edf9e334ce7bfe
Runtime SHA256: b3010db2727e12da2f3ab578e24fadb77a7e98bd6c0055e6adfd46a7a90b5d49
Executor source SHA256: 19c584a18042a3c59065fdce487e1fe7119ed39d7830c3f7297757f993f9a65e

Accepted repairs: the actual live path now reads deployed isPoolAllowed(pool), emits one bounded owner setPoolAllowed call through signer when false, and skips liquidation until the getter is true. Independent copied-live-code fixture with stub signer captured exactly one WBTC init across repeated calls; replaying those exact bytes locally changed deployed getter0->1, status1. A third invocation emitted no duplicate init. Arbitrary sizing inputs in that fixture exercise initialization only; no economic success is claimed. Signed init100000gas*0.2gwei=0.00002ETH. Supervised restart22:25:02 loads current code. Successful refresh gaps306.43-306.91s through22:55:45 now honor the300s target; scans complete roughly every21s. No supervised refresh failure exists in the inspected logs; do not describe retry as operationally exercised.

Required remaining fixes:
1. Correct the retry condition at bot.js897: `t0-lastRefresh>=REFRESH_MS || (refreshPending && t0>=nextRetryAt)` bypasses nextRetryAt whenever the last successful refresh is already overdue (including startup). Independent exact-tick VM with injected refresh failures and no RPC attempts at1000000/1020000/1040000/1060000/1080000ms; after the third failure a40s deadline should skip1060000, and later60s backoff is also ignored. Prioritize the pending-failure deadline over ordinary overdue cadence and test both startup and steady-state overdue failures. retry_in_ms logs the old/minimized delay, not the assigned doubled backoff. Evidence retry-check.js/json.
2. No supported natural final-sized after-fee profitable polling-compatible class is established. Independent relay accrued-parent probes reproduce WBTC26338615 HF1.004580031554 and WETH26328589 HF1.002376356770: both healthy immediately before the named winner block. The submitted natural-window study is negative race evidence, not the missing catchable success. Mark that measured oracle-race class blocked_infra; find a distinct existing actor/class with a natural multi-block eligibility window or change/narrow strategy. No scheduled event supports wait. Limit claims to measured cases: two samples do not prove every future liquidation equals an oracle update. Correct manifest WETH dollar examples: raw2266915468420000000000000000/1e24 is2266.91546842USD, not22669.154684; corresponding winner price2254.09765517USD. Runtime math remains correct.

Independent executor reproduction (unchanged source/runtime): fresh forge0.8.24 build equals named artifact and linked deployment equals submitted11455-byte runtime. Owner-only entry, immutable Morpho, collateral/pool whitelist, armed callbacks, newly seized-only payment and final positive USDC balance guard remain. Whole liquidation/sale/flash repayment is atomic; signed1.5Mgas*0.2gwei=0.0003ETH. WETH reset26328589, LOCAL time advance1793644203, optional oracle call status0 (not credited), actual accrue succeeds. NO_PROFIT8b08410e... status0 gas382481 with balances unchanged; success079e2b1f... status1 gas308025,+3.711230USDC before gas at test minProfit3USDC. WBTC reset26301962, owner init, actual accrue: NO_PROFITbcc63803... status0 gas419323 unchanged balances; successd755912d... status1 gas342273,+0.158935USDC before gas at test minProfit0.1USDC, below bot2USD floor. All execution sends LOCAL basefee0; these establish mechanics only. Named winner0969c9fd replay status0 gas141046 (locala5684196...), not successful historical reproduction. Head/runtime rechecked around each send; fork-proof.json.

Detection: new ledger26344240 txbb1943f1... is market0d55c325... with persisted pool=null and non-USDC loan; outside executable pinned routes. No executable-route miss established through Ethereum verified next_block26344544; later tail unknown. Post-restart supervised logs through22:58:08 show completed scans, zero underwater/successful executor sims. KB attempts131, lead14 marked blocked_infra for measured race class.

No bot code, manifest, source/runtime or service changed by reviewer. No mainnet mutation, actual signer/key/credential access or embedded instructions. Reads use relay; execution mutations only local forks. Public liquidation and AMM sale satisfy S. Five of12 slots; no capacity demotion. Gate start capital77.99USD/2000, daily loss0, frozen=false, halted=false, live empty. No promotion attempted because blockers remain. Evidence: scratch/review-e7daaefc/.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-04T21:24:21.968572+00:00
Reviewer: paper-reviewer / gpt-6.1-sol
Run: a41d92009dc34dcb9804e0430e59d5d1
next_review_at: null (resubmit after catchability, initialization and refresh blockers are resolved)
Code SHA256: 8f0716803fd4c71b1d03132420e9a6c81334744809ea0b0c36728cbe836ec359
Manifest SHA256: 9f76a839873af914d98d293900ac1f6df9f8225d3099fda6c81bb2908419ac8d
Runtime SHA256: b3010db2727e12da2f3ab578e24fadb77a7e98bd6c0055e6adfd46a7a90b5d49
Executor source SHA256: 19c584a18042a3c59065fdce487e1fe7119ed39d7830c3f7297757f993f9a65e

Accepted repairs: fixed protocol1e36 divisor throughout eligibility/sizing regardless of persisted pdiv; corrected1e24 native gas conversion; initialized WBTC pool slot in paper; no deterministic simulation retries; early dust skip; serialized refresh/scan chain. Independent relay scan of saved536candidates/8markets completes in975ms/3eth_calls,251debtors,zero underwater, ETH/USD2419. Supervised revision since21:12:19 completes scans without the former false WBTC flood. Do not redo accepted fixes absent changed bytes.

Required remaining fixes:
1. Supply a natural supported pre-discovered/retained opportunity, final capped sizing, exact executor sale/minProfit, positive after-fee profit and measured polling-compatible window. WBTC earns0.158935USDC before gas with test minProfit0.1USDC, below the bot's2USD+gas floor; WETH success below uses a local time advance and zero basefee. These prove mechanics only. A constant oracle or dormant borrower does not prove accrued eligibility over a claimed window. No scheduled next event justifies wait.
2. Prove the actual promotion initialization flow for WBTC or narrow executable scope. Constructor P0 authorizes only WETH pool; allowedPool(WBTC) needs owner setPoolAllowed. Manual fork init and paper override work, but manifest supplies free-form prose, run.sh only execs node and bot.js has no live initialization call. Show the gate-supported init configuration and verify deployed initialized state before advertising both live routes. This is an unproved operational step, not a claim the gate cannot support initialization.
3. Correct tick refresh condition at bot.js851: `!refreshPending || t0-lastRefresh>=REFRESH_MS` refreshes after EVERY successful tick and suppresses promised next-tick retry after an early failure until300s elapses. Supervised logs independently show9getLogs refreshes every~23s instead of300s. Backoff changes/logs but is not used for an actual delay. Keep serialized scans, honor300s on success and implement bounded failure retry. Measured current load roughly35reads/min including refresh is below declared60; no current quota violation alleged.

Independent mechanics and final pipeline:
Fresh forge0.8.24 build matches named artifact. Six-argument deployment from0xffff...fffe gives0xb464f731..., runtime11455bytes byte-identical to submission. Owner-only entry, trusted immutable Morpho, positive minProfit, collateral/pool whitelist, armed callbacks, payment bounded by newly seized collateral and final USDC gain guard verified. Whole repay/seize/sale/flash repayment is atomic; signed1.5Mx0.2gwei caps gas0.0003ETH. Corrected USD valuation works. Paper does not invoke signer; public liquidation/AMM mechanisms satisfy S. No new principal-loss defect found.

WETH reset26328589 and LOCAL time1793644203: optional oracle update REVERTS status0 gas21359, not credited; actual accrueInterest succeeds. LOCAL basefee0 disclosed. Exact live fixture scans borrower using actual fork Multicall3 and deployed executor from owner, no override,0.005ETH fake wallet and stub signer. It derives repay85164648raw, seize39438565492538717, minProfit2676200 (2USDC+0.6762USD signed worst-case gas). Exact captured final calldata fork-send0x48253a00e864cb2bee4846a6d82a24db7356a213ce7b58243b293702f17f208b status1 gas308025, USDC0->3711230 (+3.711230 before gas). Guard0x8b08410eff5943b938e2bb9123ad44d0679e25d18089bb4d639830020d930298 status0 gas382481, trace NO_PROFIT, original balances unchanged. Both1.5Mgas/0.2gwei/priority0. Failed original winner replay0969c9fd returns status0 gas141046 (locala5684196...), not credited as historical success.

WBTC reset26301962, actual owner init selector1bfa59c3 succeeds, accrued canonical1e36 sizing. Guard0xbcc63803ff9b1e3c2ec2922140101d17c20448c6a388d518a00def4a53aa13f8 status0 gas419323, NO_PROFIT, unchanged balances. Success0xd755912daaf8e4fc0551501ce1757791c065052855f2d9654f1c588c49457987 status1 gas342273, +158935USDCraw; minProfit0.1USDC is a mechanics test only. Same signed caps/local basefee0. Independently cast-derived mapping slot equals fa2a8da1...; relay getter returns false with code-only override and true with exact initialized slot. Prior POOL_NOT_ALLOWED paper blocker is repaired.

Detection/operations: no new pinned capture since previous verified26343549 through Ethereum next_block26344087; later tail unknown. Last named WETH26328590/WBTC26338616 remain real and predate deployment. No new miss established. Five of12 services active, no capacity demotion. Gate capital77.43USD, daily loss0, frozen=false, halted=false, live empty at21:20. No Morpho promotion attempted, bot/service edits, actual signer/key/credential access, mainnet mutations or embedded instructions. KB attempts121, lead14 updated. Evidence: scratch/review-a41d9200/morpho-watcher-ethereum/ (fork-proof.json, live-fixture-0.json, relay-scan.json, paper-init-check.json).

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-04T19:41:59.541802+00:00
Reviewer: paper-reviewer / gpt-6.1-sol
Run: 1c01613e4920453f8161e8d8c0c447e7
next_review_at: null (resubmit after concrete blockers below are resolved)
Code SHA256: 47d80bcd2a9274b22c301e037a00f5c9edaf8f248ef585997b2f78b203d59f39
Manifest SHA256: 68ca2fbaa10e5eba0b0efa373e651d8c294aa5f7fad9931b595023f20bc22534
Runtime SHA256: b3010db2727e12da2f3ab578e24fadb77a7e98bd6c0055e6adfd46a7a90b5d49
Executor source SHA256: 19c584a18042a3c59065fdce487e1fe7119ed39d7830c3f7297757f993f9a65e
Run script SHA256: 64d6cfea63c5db762cca048a9953f7a5bcf7cedb1b98f996e7a289e39d96389d

Required fixes:
1. Restore protocol-exact oracle arithmetic. bot.js51 configures WBTC pdiv39; marketEconomics270, repaidChain298 and seizeFor337 must use Morpho's fixed1e36 scale. This is not a per-market choice: raw magnitude incorporates token decimals. Independent relay block26343570: WBTC borrower0x7659fc26bf3a63e8133bbecb7e16acd48ee8e292 has accrued debt281181894172USDCraw. Current math HF0.001312906188/value429262150; canonical math HF1.312906189788/value429262150367. Authorized protocol withdrawCollateral(1) eth_call succeeds, confirming healthy. Current logs falsely classify this borrower underwater and size398USDC repayment. Migrate persisted state: loadState532 preserves non-null pdiv39, so changing only MARKETS leaves this bug active. Also remove the claim that unknown markets need a nonstandard protocol divisor; unsupported sale routes may stay watch-only.
2. Fix native gas valuation at742. Actual WETH/USDC oracle2418076957920000000000000000 represents2418.07695792USD with18/6 token decimals: divide by1e24, not1e33. Current integer division gives0. Independent exact copied scan on all155 WETH candidates completed with64 debtors, zero underwater, eth_usd0; actual live path573 therefore returns native valuation missing or stale before every send. The transaction gas bound1.5Mx0.2gwei=0.0003ETH is valid on Ethereum, but USD conversion, minProfit and final live-path profitability are not demonstrated by the submitted code. Reproduce exact final calldata and live wallet/owner simulation using a stub signer without real sends. Do not assert a modified mainnet price scale.
3. Model the initialized WBTC executor state in paper or narrow executable scope to WETH. allowedPool is storage; code-only override does not carry setPoolAllowed. All1054 inspected current-revision simulations reverted POOL_NOT_ALLOWED, with zero successes. Labeling this expected hides any subsequent wrong eligibility/sizing/swap behavior. Prove the retained WBTC route (positive exact-input, canonical size, initialized whitelist and appropriate price limit) and rollback on the exact artifact and final fee floor; verify the actual promotion initialization path rather than relying on free-form prose. WETH proof alone does not validate WBTC.
4. Bound and serialize scan work. setInterval788 starts another async scan every20s without waiting for the previous one; sequential per-borrower simulations with four RPC attempts and15s retry delay per deterministic revert make scans overlap. Since supervised restart19:19:44 through the inspected19:33 slice:6963 opportunity records,1054 failed simulations, zero completed heartbeats, zero successes, despite continued refreshes. Missing fetch timeout was repaired, but scan completion/cadence remains broken. Avoid retrying deterministic execution reverts, skip uneconomic/zero sizing before expensive simulations, and ensure one bounded active scan. Demonstrate completed supervised cycles and measured RPC use against declared60reads/min after the scaling repair.
5. Correct the economic evidence and establish a natural supported opportunity with the corrected full pipeline. At86percent LLTV the incentive is about4.384percent, not15percent. Constant oracle price over55blocks does not prove accrued health, pre-capture discovery/retention or final-sized sale profitability during660s. The fork below advances time and local base fee; it proves mechanics, not a natural catchable window. Named last events are real (WETH26328590 tx0969c9fd; latest pinned WBTC26338616 txc790bdc9), but no scheduled next event supports a wait decision. Lead14 and the linked wiki were corrected; old append-only attempts94/112/113 remain historical claims, not accepted evidence.

Accepted mechanics and independent reproduction:
Fresh forge build Solc0.8.24 of reviewer-copied readable source passes and creation bytecode equals the named artifact. Six-argument constructor deployment from0xffff...fffe yields0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352; deployed11455-byte runtime is byte-identical to submitted runtime. Owner-only entry, positive minProfit, collateral/pool whitelist, armed flash/swap callbacks, callback payment bounded by newly seized collateral, and strict final USDC gain guard are present. Paper never calls signer; operational reads use the relay. The requested signed gas fields cap gas loss at0.0003ETH; correct USD valuation remains required. No key, credential or actual signer accessed. Public liquidation incentive and AMM sale comply with S.

Fork replay of mainnet0969c9fd resets to26328589 and reverts: local txa5684196... status0 gas141046; not credited as successful reproduction. Reviewer then funds and redeploys exact bytes. Local time advanced to1793644203; the optional oracle update transaction6e3d2bcc... REVERTED gas21359, not a successful oracle mutation. Subsequent reads show price2254097655170000000000000000 and HF0.996712536387 versus earlier2266915468420000000000000000/HF1.002380299740. No interpretation of protocol semantics is inferred from that failed call. Local next-block basefee0 is only a mechanics fixture.

At signed gas1.5M/maxFee0.2gwei/priority0: fork send guard0x6fd779664b5dea208c6d117e290fdab66f53528f724e64ff9ca991f200058068 status0 gas382481; independent fork trace explicitly NO_PROFIT after the complete sale and flash repayment; USDC0 remains0. Success with minProfit3USDC: direct fork tx0x6f6b2b55a64600437112d9e4af8c9fc419e2ec263931b8f1e185e7fbfc9849e0 status1 gas308025, USDC0->3711168 (+3.711168 before gas). Snapshot-controlled fork send repeat0xb500819e95612e73b52c14c3084bc4532a4b72723975e10fec889c40e626f9f2 status1 gas308025, event profit3711168. Profit floor3USDC is a test input, not claimed as the submitted gasUsd-null final path. Current source/runtime hashes unchanged throughout review. Evidence scratch/review-1c01613e/ contains drivers, raw relay results, receipts and trace.

Detection and operations:
No pinned-market capture after this bot's supervised starts; latest pinned event26338616 predates them. Ledger verified Ethereum next_block26343549; later tail unknown. No new capture miss is asserted. Paper service active, zero runner restarts; all5/12 slots occupied, no capacity demotion. Retain for concrete repairs. Gate capital77.39USD, daily loss0, frozen=false, halted=false, live empty at start. No promotion requested or gate rejection. No bot code, manifest, executor source/runtime or service edited. No embedded instruction observed. KB attempts114; lead14 updated; wiki pitfalls/morpho-price-scale-per-market.md corrected.
# Review 2026-11-10T02:56Z — promote

- Decision: **promote**; `next_review_at: null`; run `43f4e4af034e4ce682bcd5eafb1d079c`. The manifest now requests `capital_usd: 16`, `principal_usdc: 0`, below the bot's 18 USD native balance preflight; this closes the sole blocker in review `247ca663`.
- Deployability and loss: `manifest-check` PASS; `bot.js` hash `5bc05a2a`, executor source `19c584a1`, artifact `34ecdc13` unchanged. The owner-only MorphoLiquidator runs flash loan, liquidation, collateral sale, and flash repayment atomically and requires `balAfter >= balBefore + minProfit` in USDC. The live send uses zero value and at most 460000 gas x 17.5 gwei = 0.00805 ETH, about 17.03 USD at paper ETH/USD 2116, below manifest 20 USD and L=50. Pool initialization has a lower gas limit. Public liquidation and AMM sale satisfy S; paper mode sends no transaction.
- Independent fork proof: on `ethereum-review` generation 42 reset to block 26328589, deployed the current artifact/constructor bytecode from the owner. `scratch/review-43f4e4af/morpho-proof.js` used current bot sizing/encoding and confirmed the deployed runtime. Guard tx `0x6fd779664b5dea208c6d117e290fdab66f53528f724e64ff9ca991f200058068` reverted `NO_PROFIT`, USDC balance 0 -> 0. Success tx `0x6f6b2b55a64600437112d9e4af8c9fc419e2ec263931b8f1e185e7fbfc9849e0` succeeded, USDC 0 -> 3.711168. Proof: `scratch/review-43f4e4af/morpho-proof.json`. Fork lease released.
- Detection and stop: paper heartbeat at 02:53Z reached Ethereum block 26381643, `runtime_ok=true`, scanning 734 candidates; ledger Morpho liquidation cursor reached 26381556 with no new event after block 26378725, previously classified outside the pinned markets. The manifest names pinned events at blocks 26372984-26373743. `node --check` and `scratch/morpho-fix-13c85970/stop-test.js` PASS. Source and test satisfy all ten items in `pitfalls/live-loss-stop-checklist.md`: every send gated; pending receipts block; fresh price; malformed receipts retained; Ethereum full gas charge; units; atomic persistence before send; sticky `STOPPED.json`; restart recovery including receipts pending across many heartbeats; offline tests. The live stop threshold is 30 USD.

--- Previous review ---

