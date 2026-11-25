# Review 2026-11-10T15:21Z — fix

- Decision: **fix**. `next_review_at: null`; run `05940091af7f483daadb0a43b09598bf`, `attempts:813`. The independent mechanism, loss and detection review passed, but `gate promote reserve-dutch-ethereum` returned exit 2: `gate: manifest.yaml must list allowed_contracts (the contracts the bot may call)`. The manifest has `allowed_contracts: []`; `manifest-check` treated it as a warning and returned PASS. The earner must make the manifest's allowlist nonempty with an actual intended protocol contract address, then rerun manifest-check and submit for review. No deployment or funding occurred; paper service remains active. The gate refusal is final for this submission.
- `tools/manifest-check.py` PASS; `node --check bot.js` PASS. Current SHA256: bot.js `ad4a93a2a5903e77ddab1c290dead09f32d3c9423655a7bbd1fe20cf777df7c0`, manifest `bed6b1652dff72210c79f13405ecdb922712a6e65cd2f50ea1bb3f36563b4596`, source `87b4ca10c595033df2d5c575559529c99a530c43e40f7bbb857b9b8603f37557`, artifact `8d1a82c706fb580073705e85aec2574f94fac9191b0201fdb6f370bcc636b4dc`, runtime `d337f395189fc6e8a6646b5570095f79d18caf8ecae6b0c819caf240fe62fdc0`.
- Independent fork reproduction: `scratch/reserve-bot/review-0594-proof.py` (copy of submitted proof with outputs confined to scratch) on leased Ethereum fork reset 26348315. Success tx `0xdf8aacea3f05e86b0c2e9c8bf7db84aaaf26999b6b73261041d101326bd93af6` status 1, gasUsed 766870, owner ETH+ balance increased, executor ETH+ balance ended at zero. On a fresh reset with an unsettled trade, `NO_PROFIT` tx `0x11456e2005460027319a1e2f2ec257d1dafb73f83edbbfec8940f90e467344f7` reverted and executor ETH+ balance stayed zero. Floor tx `0xa5804939b0edde2638385c4e4c62d397655456feecf1c4329d273f3d1b4994cb` status 1 at bot floor 210000000000000 wei ETH+, owner received 456443179206306 wei ETH+, gasUsed 765811 under 1050000 cap. `GAS_USD` guard at 40 gwei reverted. Fork runtime SHA256 matches paper runtime; lease released. Full data: `scratch/reserve-bot/review-0594-proof.json`.
- Atomicity/loss: `ReserveDutch.bidDutch` calls the auction bid, swaps, repays, requires `balBuy1 >= balBuy0 + minProfitBuy`, then transfers the full ETH+ balance to the owner inside the same transaction. Failed legs or payout revert the whole transaction. Bot signs gasLimit 1050000, maxFeePerGas <= 2 gwei, value zero: maximum signed fee 0.0021 ETH = $4.34 at the 2026-11-10 paper-lane Chainlink ETH/USD answer $2068.82425549, below the manifest $20 and L=$50. Principal is sourced inside the transaction. Watchdog satisfies the live loss stop; proceeds return to the bot wallet.
- Detection/S: paper heartbeat advanced through head 26385352 with active=0. Verified `reserve_revenue.started` cursors reached next_block 26385312 on all four traders; the last matching weETH→ETH+ start remains block 26348213, tx `0x01c72033bce214fb09668df183fe80db89f23be2064c9efc11e1b74ed2da36ae`. There was no new awaited event to miss. Paper code reads via the relay and signs only in live mode. Public Dutch auction bidding is an intended payout route.

--- Previous review ---

# Review 2026-11-10T13:46Z — fix

- Decision: **fix**. `next_review_at: null`; run `4369da96dc93463e9e2560f0e1d584ba`, `attempts:805`. Do not promote until the executor returns every earned ETH+ token to the bot wallet within the successful atomic bid, with the gain and loss guard still enforced, and a reviewer reproduces success and guard revert from the updated artifact.
- **Profits are irretrievably held by the executor.** `ReserveDutch.bidDutch` snapshots and requires `ETP.balanceOf(address(this))` to grow (`scratch/reserve-bot/contracts/src/ReserveDutch.sol:127-137`), but does not transfer the surplus to `owner` after the check. The artifact ABI exposes only `bidDutch`, `dutchTradeCallback`, state getters and constants; no withdraw/sweep function. The callback transfers exactly `bid` to the trade (`ReserveDutch.sol:181-185`), not the surplus to the owner. `bot.js` sends only `bidDutch`. Thus each successful live bid costs the bot wallet native gas, credits ETH+ only to the executor, and leaves the wallet without a realizable payout. `decisions/human/2026-11-10-live-loss-stop-watchdog.md` explicitly counts value outside the bot wallet as lost; gate stop sweeps wallet balances only. The earlier independently reviewed fork success (`scratch/review-7cbf-reserve-proof.json`, reset 26348315, tx `0x36638cb9009bb90c22758fc09bb3efd90863823df46bd0d68037f9494f157ee1`) left +254619392937342 wei ETH+ in the executor. Fix the live payout flow and prove the bot wallet receives it atomically; an executor-only gain cannot produce realized bot profit.
- Current manifest-check and `node --check` pass. The signed fee ceiling is 1,050,000 gas × 2 gwei = 0.0021 ETH, value zero, below manifest L=$20 at the current ~2.1k USD/ETH price; the executor checks the ETH+ gain and on-chain gas ceiling. Public auction bidding remains within S. The 2026-11-10 human decision makes the watchdog's 30 USD stop sufficient, so the previous crash-recovery criterion 5 is no longer a blocker.
- Detection: `reserve_revenue.started` ledger query for `sell=weETH, buy=ETH+` still has only block 26348213 (trade `0x527dc250356c8833cd5e2856dd617dd400cf9257`), with four trader cursors through 26384834. Paper heartbeats reached block 26384877 at 13:41Z, active=0. No new awaited event or detection miss. The bot's old `simulate` records for that trade were seeded after settlement and reverted `bid already received`, so they do not prove a natural capture.
- Fresh fork proof was attempted on `ethereum-review` reset 26348315 using the current artifact and 1,050,000 gas. The local `fork send` returned `no receipt after 30s` for two guard attempts (`0xdef86b9b...`, `0xb009846b...`); the lease was released. No fresh success/revert is credited. This fork limitation does not change the source-level payout failure. Submitted hashes: bot.js `ad4a93a2a5903e77ddab1c290dead09f32d3c9423655a7bbd1fe20cf777df7c0`, manifest `bc4fce1db71e68881892fcb6f7b3bce5d0c6a9cd3ab63daef88eb5621ca42ffb`, source `b263888ab2b3e7a11129fd277598d1b712b3f929d5cd1081223d69e8a2e275a6`, artifact `2296d50d281cc25a8c1ed71f03ac160bb74a5992fd887ea4f2d09acf61471ef9`.

--- Previous review ---

# Review 2026-11-10T12:11Z — fix

- Decision: **fix**. `next_review_at: null`; run `69bab95267a346c38a8fe905ec8197c7`, `attempts:800`. Do not promote until accepted sends and ambiguous signer replies remain accounted for at every interruption boundary.
- Checklist **2/9/10 fail**. `main()` logs an accepted `live_send` before persisting its hash (`bot.js:419-434`). If it exits between those writes, the old `state.json` is still valid with `pending:[]`. `recoverLossState` replays the log only when state is missing or unreadable (`bot.js:318-329`), and startup loads the stale valid state (`bot.js:337-341`). Independent offline reproduction `node scratch/review-69bab952-state-gap.js` confirms that the log contains the accepted hash and its parser finds it, yet the actual startup order restores `pending:[]`, no halt, and no `STOPPED.json`. The next qualifying trade can send before that receipt's gas is counted. Reconcile the append-only log with **every** loaded state, including a valid state, before opening the send gate.
- Two further accepted-send boundaries need the same fix. A process exit or failed first log append after the signer broadcasts leaves no durable accepted-send evidence at all. Persist a pre-send intent or halt **before** the signer call, and clear it only after a definitive rejection or a reconciled receipt. `signerCall` (`bot.js:126-134`) turns socket/JSON failures into `ok:false`; `main()` treats every such reply as a final rejection (`bot.js:432-436`), although the signer may have broadcast before its reply was lost. Keep the intent pending for ambiguous transport outcomes. Add offline cases for all three boundaries and show that no later signer call occurs while an outcome is unresolved.
- The submitted `scratch/reserve-dutch-fix/settle-proof.js` passes 16/16 cases, but covers damaged/missing state and the prior no-hash log gap, not a valid stale state or the pre-log gap. Checklist 1, 3-8 otherwise pass on code review: one signer send path; fresh price; missing receipt fields remain pending; Ethereum gas units and fee components; atomic state writes; sticky threshold stop. `manifest-check` and `node --check` pass. Current hashes: bot.js `bfcbd00c`, manifest `bc4fce1d`, source `b263888a`, runtime `aace4aa4`, artifact `2296d50d` (SHA256 prefixes). The unchanged artifact has the prior reviewer fork success and principal-returning guard revert in review `7cbf8b954a9b452bbfa3bd771c83bc32`; criterion 5 failed, so no fork rerun or gate promotion.
- Detection: `reserve_revenue.started` still ends at block 26379242 through verified cursor `next_block=26384363`; the last named weETH→ETH+ start remains block 26348213, tx `0x01c72033bce214fb09668df183fe80db89f23be2064c9efc11e1b74ed2da36ae`. Paper service is active and heartbeat reached head 26384421 with `active=0`. No new awaited event or detection miss. The public auction route meets S. The signed fee ceiling remains 1,050,000 gas × 2 gwei = 0.0021 ETH, value zero, within the manifest's $20 limit at the signing-time price; the executor's atomic gain guard is unchanged.

--- Previous review ---

# Review 2026-11-10T10:38Z — fix

- Decision: **fix**. `next_review_at: null`; run `7025047b5d3b4bb2aa4a1e29968744b4`, `attempts:797`. Do not promote until every accepted send remains accounted for across an interruption at each durable-write boundary.
- Checklist **2/9/10 fail** in the new accepted-send recovery. `bot.js:414-419` appends `{type:'live_send', ok:true, hash:null}` and only afterward appends `live_halt`. A process exit or write failure between those records leaves a durable accepted send with no halt marker. `recoverLiveLossFromLog` (`bot.js:285-289`) ignores that record. With a missing state file and a preceding valid heartbeat, recovery sets `haltNoHash:false`, `pending:[]`, and leaves no `STOPPED.json`; the next qualifying trade can send despite an unreconciled prior broadcast. Independent offline reproduction: `node scratch/review-7025047b-nohash-gap.js` prints `REPRODUCED` and asserts recovered loss 1.5 USD, no pending hash, no halt. The submitted 13/13 test passes but includes the later `live_halt` record, so it misses this crash boundary. Treat the accepted no-hash `live_send` itself as a durable halt during recovery, and add the crash-window case to the offline proof. Also ensure an accepted reply whose first log append fails cannot leave the in-memory send gate open on the next cycle.
- The other stop checks pass on code review and the submitted 13/13 offline proof: one guarded signer send, fresh price before receipt settlement, missing gas fields retain pending hashes, Ethereum gas units, atomic state persistence, and a sticky `STOPPED.json`. `node --check` and `manifest-check` pass. The unchanged manifest, named source, runtime and artifact retain hashes `bc4fce1d…`, `b263888a…`, `aace4aa4…`, `2296d50d…`; prior independent fork success and principal-returning guard revert in review `7cbf8b954a9b452bbfa3bd771c83bc32` remain credited. No fork rerun was needed after criterion 5 failed. Current bot.js hash `2db9079c…`.
- Detection: ledger `reserve_revenue.started` cursors reached `next_block=26383583` on all four traders; the last eligible weETH→ETH+ start remains block 26348213, tx `0x01c72033bce214fb09668df183fe80db89f23be2064c9efc11e1b74ed2da36ae`. Paper service is running and heartbeats reached block 26383957 with `active=0`. No new awaited event or detection miss. The public auction route remains within S; the signed fee ceiling is unchanged at 1,050,000 gas × 2 gwei = 0.0021 ETH, value zero, with an atomic executor gain guard.

--- Previous review ---

# Review 2026-11-10T09:05Z — fix

- Decision: **fix**. `next_review_at: null`; run `b03b0e1545014f70b5b47356b51fc5f6`, `attempts:791`. Do not promote until the live-loss stop survives damaged log records and tracks every accepted send.
- Checklist 1-3, 5-8 pass on this review: one signer send path with a preceding stop check; pending receipts block later sends; settlement uses this cycle's fresh Chainlink price; Ethereum gas fields are required and the 1e24 conversion is correct; state writes use temp-file/rename; STOPPED.json is sticky. The submitted offline proof runs **9/9 PASS**, `node --check` and `manifest-check` pass. Checklist **4/9 fail** in restart recovery: `bot.js:268-276` skips malformed log lines and accepts `live_loss_settled` without a numeric `live_loss_usd` as proof a hash has been charged. My offline reproduction of an accepted `live_send` followed by that incomplete settlement returns `{found:true,usd:0,pending:[]}`; an existing log containing only malformed JSON returns the same. If state.json is missing/damaged, startup then treats lost accounting as zero and can send. An existing log without valid accounting must fail closed; a settlement record without a valid cumulative total must not clear its hash.
- Checklist **4/9 also fail** if the signer replies `ok:true` without a valid `txHash`: `bot.js:389-395` logs acceptance but leaves no pending hash and does not halt sending. Require a valid hash for an accepted send or stop durably until the transaction can be reconciled. Checklist **10** needs offline cases for both failures; the current nine cases do not cover them.
- Mechanism evidence remains credited from independent review `7cbf8b954a9b452bbfa3bd771c83bc32`: manifest `bc4fce1d…`, runtime `aace4aa4…`, source `b263888a…` and artifact `2296d50d…` have identical SHA256 hashes. That review reproduced a 760687-gas profitable success `0x36638cb9009bb90c22758fc09bb3efd90863823df46bd0d68037f9494f157ee1` and a principal-returning guard revert `0x84a91bcdcf6ad5f1a64abc7deaa8baa5b422e008eeecf77f4c900bb674dc37ba`. Signed fee ceiling is 1,050,000 gas × 2 gwei = 0.0021 ETH, value zero; the executor's ETH+ gain guard and atomic repayment are unchanged. No fork rerun was needed once criterion 5 failed. Paper sends nothing; public Dutch auction bidding meets S.
- Detection: `reserve_revenue.started` cursor reached block 26383428; the last eligible weETH→ETH+ start remains block 26348213, tx `0x01c72033bce214fb09668df183fe80db89f23be2064c9efc11e1b74ed2da36ae`. The six starts in block 26379242 have other token pairs. Paper service is running and heartbeats reached head 26383492 with `active=0`; there is no new awaited detection miss.

--- Previous review ---

# Review 2026-11-10T07:33Z — fix

- Decision: **fix**. `next_review_at: null`; run `add09a2cdbcd45a281316beff0929123`, `attempts:781`. The human's `2026-11-10-first-live-incident.md` confirms the gate deployment race is repaired, but the bot fails the now complete 30 USD live-loss stop checklist in `wiki/pitfalls/live-loss-stop-checklist.md`. Do not promote until these are repaired and tested.
- Checklist 1 **pass**: only one signer send path, `bot.js:312`, with a preceding loss check. **2 fail**: pending receipt hashes do not block a later trade send (`liveLossSettle` may retain them at lines 198-200; send at 312 has no pending gate). **3 fail**: `ethUpperPriceMicro` returns a cached price for up to 60 seconds (line 153), so a new 45-second cycle can settle at a prior cycle's price. **4-5 fail**: absent `gasUsed` or `effectiveGasPrice` becomes zero at line 202 and the hash is removed; Ethereum gas is the only principal-free loss component, but it must have both receipt fields before settlement. **6 pass**: the wei × micro-USD conversion at line 203 divides by 1e24 overall.
- **7 fail**: `persist` writes `state.json` directly, without temp-file/rename atomicity (`bot.js:218`), and a later successful write clears `stateWriteFailed` even after a hash or total was lost. **8 fail**: `liveLossStopWrite` swallows write errors and `stopLogged` becomes true regardless; startup never checks `STOPPED.json`. **9 fail**: unreadable/missing live state is silently replaced with zero loss (`bot.js:240-243`), with no durable-log recovery; a later persist clears the halt flag. **10 fail**: no reserve bot offline test covers fresh/failed price, missing fee, threshold crossing, sticky restart and recovery of a long-pending receipt. Save a `live_loss_settled` record per hash and recover all accepted hashes not durably settled, including those pending across many heartbeats.
- Deployment/loss mechanism evidence is unchanged from run `7cbf8b954a9b452bbfa3bd771c83bc32`: bot, manifest, runtime, named source and artifact SHA256 still match that review; `manifest-check` and `node --check` pass. Its independent current-artifact fork success and guard revert therefore remain credited. No new fork run was needed once the live stop failed. Signed ceiling remains 1,050,000 gas × 2 gwei = 0.0021 ETH, value zero, under manifest L=$20 at the measured signing-time price; principal is sourced and repaid atomically by the executor.
- Detection: the last verified Reserve batch was block 26379242 (tx `0x5d6065e33a586deef7349c9542d3268532e3d434222022adf7654453bec42e6b`), with no `sell=weETH` among the six starts; no new awaited weETH→ETH+ event since block 26348213. Ledger started cursors reached 26382957 and paper heartbeats reached 26383031 with `active=0`. No detection miss. Public auction route remains within S.

--- Previous review ---

# Review 2026-11-09T17:30Z — wait

- Decision: **wait**. `next_review_at: 2026-11-10T12:00:00Z` to recheck gate deployability after meta repairs the confirmed funding/deployment race. Run `7cbf8b954a9b452bbfa3bd771c83bc32`. `attempts:712`. No gate call: two other Ethereum `gate promote` calls in this run failed during executor deployment with `insufficient funds ... have 0`, then moved/funded inactive live entries. A third known-failing attempt would strand another funded bot wallet. Evidence: `inbox/meta/2026-11-09-franken-deploy-zero-balance.md`.
- Reviewed SHA256: bot.js `551b1c8512c26f4b28ceb4a621c63cd540eee5090168d955a5583a09ff259ab2`, manifest.yaml `bc4fce1db71e68881892fcb6f7b3bce5d0c6a9cd3ab63daef88eb5621ca42ffb`, executor-runtime.hex `aace4aa4326951d89b3a66e81f6a1022ca28bc61226f232e9eeca9bf3463e0e9`, source `b263888ab2b3e7a11129fd277598d1b712b3f929d5cd1081223d69e8a2e275a6`, artifact `2296d50d281cc25a8c1ed71f03ac160bb74a5992fd887ea4f2d09acf61471ef9`.
- `manifest-check` and `node --check` pass. The prior stop-persistence blocker is repaired: `persist(st)` now saves accepted hashes and settled charges before another send and the send path fails closed on a failed write. The signed 1.05m gas x 2 gwei ceiling is 0.0021 ETH, about $4.48 at paper ETH/USD $2132, within manifest L=$20, value zero. The atomic executor checks an ETH+ gain and an on-chain gas/oracle guard; public auction bidding is within S; paper sends nothing.
- I independently reran the current named artifact on the leased Ethereum review fork, reset 26348315. With the bot's actual `minProfitBuy = 2 x 1050000 x 0.1 gwei = 210000000000000` wei and local next-block base fee zero, tx `0x36638cb9009bb90c22758fc09bb3efd90863823df46bd0d68037f9494f157ee1` succeeded, adding 254619392937342 wei ETH+ at 760687 gas. At the test fee, gas cost was 76068700000000 wei native, leaving about 178550692937342 wei ETH-equivalent margin at near-parity ETH+ pricing. High-minProfit guard tx `0x84a91bcdcf6ad5f1a64abc7deaa8baa5b422e008eeecf77f4c900bb674dc37ba` reverted with zero ETH+ retained; the 40 gwei gas guard and settled-trade control reverted too. Proof: `scratch/review-7cbf-reserve-proof.json`. This is a local low-fee fixture, not evidence of unmodified historical inclusion.
- Detection: ledger Reserve TradeStarted last block 26348622, the named weETH/ETH+ event last at block 26348213; verified cursor reached 26378751. Paper heartbeats reached 26378795 with `active=0`. No awaited event fired since the prior review. The missing criterion is deployment through the currently failing gate, which no earner code change can resolve.

--- Previous review ---

# Review 2026-11-09T15:52Z — fix

- Decision: **fix**. `next_review_at: null`; run `233973f5be2e4f9ab5f3de40b56f194e`, `attempts:699`. No promotion.
- The new `bot.js:194` gas-loss conversion is correct: wei × micro-USD/ETH divided by 10^24 gives USD. `manifest-check` and `node --check` pass; paper heartbeats reach block 26378332 with no active trade, matching ledger's last eligible start at 26348213. The artifact and manifest are unchanged.
- **Economic success still unproven at the bot's send floor:** the prior fork success used `minProfitBuy=1` wei. At historical block 26348315 the base fee was 0.090421934 gwei; a 0.1 gwei bot price would set its 2 × 900000 × gasPrice floor to 0.00018 ETH+, below the prior 0.0002415985 ETH+ gross delta. I reran the current artifact on the leased Ethereum review fork with that floor and 0.1 gwei, then with a type-2 zero-tip transaction. Both stayed pending without a receipt for 30 seconds; Anvil's suggested gas price was about 1.07 gwei and rejected setting a lower minimum while EIP-1559 is active. The lease was released. This arithmetic is not a mined, net-profitable success. Reproduce an includable success and a fresh guard revert with the actual floor before promotion. Evidence: `scratch/review-233973f5-reserve-proof.py`, pending hashes `0x5d140969...` and `0x84a91bcd...`.
- **Stop persistence also needs repair:** the signer hash enters `st.liveLoss.pending` at line 300, but state is saved only after the entire trade loop at line 304. A restart in that interval loses the pending gas charge. The catch at line 306 logs a failed state write and continues polling, so a storage failure does not stop later sends. Save accepted hashes and settled loss before more sends, failing closed on write failure.

--- Previous review ---

# Review 2026-11-09T14:10Z — fix

- Decision: **fix**. `next_review_at: null`; correct the live gas-loss units and reproduce a net-profitable success using the bot's actual after-gas floor. Run `811c0a9f096640b9ba60cc98e190addc`.
- `manifest-check` passes; named executor source/runtime retain the hashes of the prior full review. The bot now has receipt-pending and immediate stop-write logic. Signed limit 900000 x 2 gwei = 0.0018 ETH, zero value; the atomic executor enforces a buy-token gain and oracle gas guard. Public revenue auction bidding meets S; paper only reads/simulates. The ledger's last started auction remains block 26348622, and paper heartbeats reach 26377815 with `active=0`.
- **Incorrect realized-loss calculation:** `bot.js:194` computes `Number((gasWei * pMic) / 10^12) / 10^6`, an overall 10^18 divisor. `pMic` is micro-USD per ETH, so wei-to-ETH and micro-USD-to-USD require 10^24. For 10^14 wei gas and 2.1e9 micro-USD/ETH, the code records $210000 instead of $0.21, falsely trips the $30 stop after one send, and reports a false reason. Fix the units and verify receipt settlement.
- The older fork success at reset 26348315 gained 0.0002416 ETH+ with `minProfitBuy=1` and 760240 gas; it did not demonstrate the bot's 2 x 900000 x gasPrice after-gas floor. My repeat of `scratch/review-325468a3/reserve/proof.py` reached the guard send, but the fork CLI returned `no receipt ... after 30s`; querying that local fork afterward found the guard tx mined with status 0. No new full success/revert reproduction is credited in this review. Demonstrate success at an includable fee with the bot's actual floor, plus a guard revert, before reconsidering promotion.

--- Previous review ---

# Review 2026-11-08T04:59Z — wait

- Decision: **wait**. `next_review_at: 2026-11-12T12:00:00Z`, around the next plausible weETH/ETH+ auction at the measured one-per-6.8-days cadence. No promotion attempted. The changed manifest corrects awaited-event cadence; executable code, runtime and named executor source retain the hashes of full review `325468a3f96544cfa2806ae9d043bb32`.
- The executor still makes bid, swap and repayment atomic and checks the ETH+ end balance. Its signed limit is 900000 gas x 2 gwei = 0.0018 ETH; the bot's fresh price filter declines a send when that ceiling exceeds the manifest's $20 at signing. The on-chain oracle guard and balance guard held in an independent fork rerun. The live path uses the signer to call the gate executor; paper mode uses relay reads and eth_call only. Public auction settlement meets S.
- Natural economic evidence remains missing. The ledger's four verified `reserve_revenue.started` cursors reached `next_block=26367825`; the last start on those traders is block 26348622 and the last named weETH/ETH+ start is block 26348213. Paper heartbeats reached head 26367887 with `active=0` and no new natural simulation. The prior seeded, already-settled simulations are not captures. The old fork success with `minProfitBuy=1` does not satisfy the bot's after-gas send floor. Wait for a natural qualifying event and assess its polling-to-inclusion window and net profit then.

Independent `ethereum-review` fork rerun at reset 26348315, lease released: NO_PROFIT guard tx `0x1d6aa585998678ea5e37f9b45fd83b2b666a3da1d397b383fc432e631ee783e6` reverted with zero ETH+ balance; clean success tx `0xeca637bb0f80df21776196bbe843c428f993976790fa7c104050ed910a91d00e` gained 241598503500634 wei ETH+ at gasUsed 760240; 40-gwei GAS_USD guard tx `0xf2bdffa4e16fb02c0e7a9ec942d53ca3283560eb51da4716c71f26aa3dff5cb9` reverted with zero balance. Forge build passed. Proof: `scratch/review-325468a3/reserve/proof.json`.

Reviewed SHA256: bot.js `29c5cbf642dafc4d2701ca4950b771d5e7166de9961711e240f4e3cc6f7fb218`; manifest.yaml `fb5880df741ddf54fbd504238febc8af208b9be369f9dd809f0982e3bcebc03f`; runtime `aace4aa4326951d89b3a66e81f6a1022ca28bc61226f232e9eeca9bf3463e0e9`; named source `b263888ab2b3e7a11129fd277598d1b712b3f929d5cd1081223d69e8a2e275a6`.

--- Previous review ---

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check run becae925782a46b4b5f80aaf0701c98f at 2026-11-08T01:50Z: bot.js, manifest, runtime and named executor source hashes match the full review; only state changed. Ethereum reserve_revenue.started last block 26348622 through four verified cursors next_block 26366888; paper heartbeat active=0 through head 26366970. No awaited event, fork reproduction or attempts row. next_review_at remains null.

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check run c4297fae2d864569bba8a7c91ebf3d81 at 2026-11-08T00:15Z: code, manifest, runtime and executor source hashes match the last full review; only state changed. reserve_revenue.started last block 26348622 through four verified Ethereum cursors next_block 26366425; paper active=0 through head 26366482. No awaited event, fork reproduction or attempts row. next_review_at remains null.

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check run 29c1855dc0aa4bdf82d81ccd96266b43 at 2026-11-07T22:41Z: bot.js, manifest, runtime and named source hashes match the full review; only state changed. Reserve revenue TradeStarted last block remains 26348622 through four verified Ethereum ledger cursors next_block 26365961; paper active=0 through head 26366021. No new awaited event, fork reproduction or attempts row. next_review_at remains null.

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check run 6b615c4a94c84ecaaaf4aa3d621d0699 at 2026-11-07T21:08Z: bot.js, manifest, runtime and named ReserveDutch source SHA256 match the last full review; only state changed. Ethereum reserve_revenue.started last block remains 26348622 (16 events) through four verified ledger cursors next_block 26365494; paper heartbeat through head 26365563 has active=0. No new awaited event, fork reproduction or attempts row. next_review_at remains null.

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check run 890f5b65426844429d2f8547a15d4ca4 at 2026-11-07T18:06Z: bot.js, manifest, runtime and named ReserveDutch source SHA256 match the last full review; only state changed. Ethereum reserve_revenue.started last block remains 26348622 (16 events total) through all four verified ledger cursors next_block 26364644; paper heartbeat through head 26364655 has active=0. No new awaited event, fork reproduction or attempts row. next_review_at remains null.

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check run e8064307b9f949c58345c80cd516476b at 2026-11-07T16:34Z: bot.js, manifest, runtime and named ReserveDutch source SHA256 match the last full review; only state changed. Ethereum reserve_revenue.started last block remains 26348622 (16 events total) through four verified ledger cursors next_block 26364179; paper heartbeat through head 26364200 has active=0. No new awaited event, fork reproduction or attempts row. next_review_at remains null.

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check run dc4e805628e64a7c98c61bbaed78c371 at 2026-11-07T15:02Z: bot.js, manifest, runtime and named ReserveDutch source SHA256 still match the last full review; only state changed. Ethereum reserve_revenue.started last block 26348622 through four verified ledger cursors next_block 26363714. No new awaited event, fork reproduction or attempts row. next_review_at remains null.

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check run 5381b8ea6abf430d94b05579e78da339 at 2026-11-07T13:32Z: bot.js, manifest, runtime and named ReserveDutch source SHA256 still match the last full review; only state changed. Ethereum reserve_revenue.started last block 26348622 through verified ledger cursor next_block 26362768. No new awaited event, fork reproduction or attempts row. next_review_at remains null.

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check run 549922dfa4fe4c99a8cc13094f6574dc at 2026-11-07T10:26Z: bot.js, manifest, runtime and named executor source SHA256 match the last full review; only state changed. Ethereum reserve_revenue.started last block 26348622 through verified ledger cursors next_block 26362306; paper heartbeat through block 26362364 has active=0. No new awaited event, fork reproduction or attempts row. next_review_at remains null.

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check run d40566ecb0ab4740825076a521efbc70 at 2026-11-07T08:52Z: bot.js, manifest, runtime and named executor source SHA256 match the last full review; only state changed. reserve_revenue.started last block 26348622; verified ledger cursor next_block 26361846; paper heartbeat through block 26361902 has active=0. No new awaited event, fork reproduction or attempts row. next_review_at remains null.

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check run bfdc1eacffe648a697f9b0c0492e1cbe at 2026-11-07T07:20Z: bot.js, manifest, runtime and named ReserveDutch source SHA256 match the last full review; only state changed. Ethereum reserve_revenue.started last block 26348622 through verified ledger cursor next_block 26361382; paper heartbeat active=0 through head 26361441. No new awaited event, fork reproduction or attempts row. next_review_at remains null.

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check run 04aa3990c5894fa9b5547dd91e4ac4af at 2026-11-07T05:37Z: bot.js, manifest, runtime, and named ReserveDutch source SHA256 match the full review; only state changed. Ethereum reserve_revenue.started last block 26348622 through ledger cursors next_block 26360844. No new awaited event, fork reproduction, or attempts row. next_review_at remains null.

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check run bd114e006d5849aa8dead99ba616a282 at 2026-11-07T04:05Z: bot.js, manifest, executor runtime and named ReserveDutch source SHA256 match the full review; only state changed. Ethereum reserve_revenue.started last occurred at block 26348622 through verified ledger cursors next_block 26360457; paper heartbeat head 26360470 active=0. No new awaited event, fork reproduction or attempts row. next_review_at remains null.

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check run f39bd801643f4476a9ff1510d3cecadf at 2026-11-07T02:33Z: bot.js, manifest, executor runtime and named ReserveDutch source SHA256 match the full review. Only state changed. Ethereum reserve_revenue.started last occurred at block 26348622 through verified ledger cursor next_block 26359989; no new awaited event. Paper heartbeat head 26360014 active=0. No fork reproduction or attempts row. next_review_at remains null.

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check run b575a5be9f064e678bec908690572faa at 2026-11-07T01:01Z: bot.js, manifest, executor runtime and named ReserveDutch source SHA256 match the full review. Only state changed. Ethereum reserve_revenue.started last block 26348622 through verified ledger cursor next_block 26358208; a direct relay eth_getLogs across all four watched traders found no TradeStarted in blocks 26358208-26359555. Paper heartbeat head 26359555 active=0. No new awaited event, fork reproduction or attempts row. next_review_at remains null.

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check run 962b34af056e488395db560928c5c0a8 at 2026-11-06T23:29Z: code, manifest and runtime hashes still match the last full review; named executor source unchanged. Only state changed. Ethereum reserve_revenue.started last block 26348622 through verified cursor next_block 26358208; the source is 881 blocks behind current head 26359089, so this check does not cover the lag. Paper heartbeat active=0. No new event in the verified ledger, fork reproduction or attempts row. next_review_at remains null.

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check run 7d21923c90844d96a1000ea6c9b87272 at 2026-11-06T21:54Z: code, manifest, runtime and named executor source SHA256 match the last full review; only state changed. Ethereum reserve_revenue.started last block 26348622; verified cursor next_block 26358208. No new awaited event, fork reproduction or attempts row. next_review_at remains null.

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check run 652aaf23bc4249198d4e61ac1e224af2 at 2026-11-06T20:22Z: code, manifest, runtime and named executor source SHA256 match the last full review; only state changed. Ethereum reserve_revenue.started remains at block 26348622 through verified ledger next_block 26358130. No new awaited event, fork reproduction or attempts row. next_review_at remains null.

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check run 1d4134161fd24ea6924250b7c8340942 at 2026-11-06T18:51:30Z: code, manifest, submitted runtime and named executor source SHA256 still match the last full review; only state changed. reserve_revenue.started remains at block 26348622; Ethereum ledger verified through next_block 26357669. No new awaited event, fork reproduction or attempts row. next_review_at remains null.

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check run 3cb48d637a024dd38ec0944ea93f240d at 2026-11-06T17:16Z: code, manifest, runtime and named executor source SHA256 match the last full review; only state changed. Ethereum reserve_revenue.started last block 26348622, verified next_block 26357213; no new awaited event, fork reproduction or attempts row. next_review_at remains null.

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check run 71396b4d6be44a9a960fa1a4985be474 at 2026-11-06T15:42Z: code, manifest, runtime and named executor source SHA256 match the last full review; only state changed. Ethereum reserve_revenue.started last block 26348622, verified next_block 26356754; no new awaited event, so no detection exception, fork reproduction or attempts row. next_review_at remains null.

unchanged since prior full review, decision fix stands. Check 2026-11-06T14:04:44.385781+00:00 run b23a1139030243f2bc61d9b1c4cd9878: code, manifest, runtime, and named executor source hashes match; only state changed. reserve_revenue.started last block 26348622, verified next_block 26356211; no new awaited eligible event, so no detection exception. No fork reproduction or attempts row. next_review_at remains null.

unchanged since 325468a3f96544cfa2806ae9d043bb32, decision fix stands. Check 2026-11-06T12:32Z run dfc56aae9b784907a84b26c1b6310a2b: code, manifest, runtime, and named executor source SHA256 match the last full review. No new Ethereum reserve_revenue.started after block 26348622 through verified cursor next_block 26355593; paper heartbeat at 12:31:38Z shows active=0. State-only change; no fork reproduction or attempts row. next_review_at remains null.

Decision: fix
Reviewed at: 2026-11-06T11:00:09Z
Reviewer: paper-reviewer / gpt-6-sol
Run: 325468a3f96544cfa2806ae9d043bb32
next_review_at: null (resubmit after a natural profitable weETH/ETH+ capture with measured polling-to-inclusion window)
Code SHA256: 29c5cbf642dafc4d2701ca4950b771d5e7166de9961711e240f4e3cc6f7fb218
Manifest SHA256: 9974d600b559cc0bba1cb7a78dd54229e1d2b2697afc7b96cb82c41613938e7a
Runtime SHA256: aace4aa4326951d89b3a66e81f6a1022ca28bc61226f232e9eeca9bf3463e0e9
Executor source SHA256: b263888ab2b3e7a11129fd277598d1b712b3f929d5cd1081223d69e8a2e275a6

The previous USD-loss objection is resolved by the 2026-11-06 human decision: L is valued at signing, and the signed 900000 gas x 2 gwei = 0.0018 ETH ceiling is well below the manifest's $20 at the current ETH price. The revised ReserveDutch.bidDutch has an owner check, an execution-block oracle/gas guard, an atomic bid/sale/repayment, and an ETH+ balance-increase check. The bot's live path sends only to that executor through the signer; the paper path uses relay eth_call with no send. Public auction settlement meets S. capital_usd=30, principal_usdc=0.

Independent reproduction on ethereum-review fork generation 6, reset block 26348315: compiled artifact runtime equals the submitted runtime. Correctly ordered NO_PROFIT guard before settlement reverted with NO_PROFIT, tx 0x1d6aa585998678ea5e37f9b45fd83b2b666a3da1d397b383fc432e631ee783e6, executor ETH+ balance 0. A clean executor then succeeded, tx 0xeca637bb0f80df21776196bbe843c428f993976790fa7c104050ed910a91d00e, gasUsed 760270, ETH+ delta +0x82ea11ced351 wei. The 40 gwei GAS_USD test reverted as intended. Evidence: scratch/review-325468a3/reserve/proof.json and fork trace; lease released. The earner's proof script puts NO_PROFIT after the successful bid and therefore tests settled-trade eligibility rather than the profit guard; my copied script corrected this order.

Economics remain unproven. The fork success uses minProfitBuy=1 wei and its 1.439e14 wei ETH+ delta is below the bot's 2 x 900000 x current gasPrice threshold (~2.9e14 wei at the 10:24 seeded test). The only recent paper simulations at 10:24-10:25Z were seeded, already-settled trade reverts; the service has since run with active=0 through head 26355356. No new Reserve TradeStarted after block 26348622 through verified ledger next_block 26355287; the only named weETH/ETH+ start remains block 26348213. Thus there is no natural profitable send or measured catchable window. Keep fix until a natural qualifying event is simulated with an includable fee and positive after-gas margin. No gate promotion attempted.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-06T09:25Z
Reviewer: paper-reviewer / gpt-6-sol
Run: e12914d4ba984d339cbca2780067b4ff
next_review_at: null (resubmit after an enforceable <=$20 per-tx loss bound and a natural profitable capture with measured polling-to-inclusion window)
Code SHA256: eb46f1173464f10d868c7c3a0e60727cb50ea1e46db71cb6999b621e3484c33a
Manifest SHA256: ab5a8524b56d7c397a23d2422872e9d656504f2c63c806b888edfdd5a6a0d8a7
Runtime SHA256: 3159cc033657ada101a81e4bc10c963debbdc902bb9812250387d332adf69007
Executor source SHA256: 2191623f98e5d52263856c45dd582e512a96ee831d1ff31d27a2042f55a2ce73

The revised signed gas cap is 900000 x 2.0 gwei = 0.0018 ETH. Valuing it at the reviewer's prior illustrative $11000/ETH gives $19.80, but that price was an example, not a hard ceiling. A valid signed transaction at $12000/ETH can consume $21.60, above L. The 90-day observed 9.05% maximum price move and Chainlink answer x 1.12 are empirical decision-time filters; neither enforces the ETH/USD price when the transaction is included. The bot has no wallet cap on Ethereum. This leaves max_loss_guarantee unproven under price moves between detection and inclusion. Lower the signed exposure or establish a genuinely enforceable USD bound; an assumed upper price cannot prove L.

The ReserveDutch source and runtime hashes match the independent fork review bce15686; source bidDutch still restricts the caller and checks the ETH+ end balance after the atomic bid, sale and repayment. I did not repeat the old fork run because the gas-loss failure already decides fix. Paper mode reads through the relay and sends nothing. Public auction settlement meets S. The last weETH/ETH+ start remains block 26348213; reserve_revenue.started has no new event after block 26348622 through verified next_block 26354829. Paper heartbeats reached block 26354892 at 09:24Z with active=0. The 08:18 simulation was a seeded already-settled trade and reverted `bid already received`; it is not a natural profitable capture or polling-to-inclusion window. No gate promotion attempted. KB attempts:279.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-06T07:50:25.212227+00:00
Reviewer: paper-reviewer / gpt-6-sol
Run: 7e653174a7094a19bf8f3acc88f78829
next_review_at: null (resubmit after an enforceable <=$20 per-tx loss bound and a natural profitable capture with measured polling-to-inclusion window)
Code SHA256: e13723fee63f09678b37c6d069144a3fbb3c389eaa90dabb2656c730984bc52a
Manifest SHA256: 865d1be41eb5deb195cea495ec1183816354074fb4f734045d14c2abf71d8fbb
Runtime SHA256: 3159cc033657ada101a81e4bc10c963debbdc902bb9812250387d332adf69007
Executor source SHA256: 2191623f98e5d52263856c45dd582e512a96ee831d1ff31d27a2042f55a2ce73

The submitted change lowers the signed gas ceiling to 900000 x 2.2 gwei = 0.00198 ETH. The manifest and bot.js value that exposure at the historical ETHUSDT high of $4956.78 and call $9.81 an absolute worst case. Historical prices are observations, not an inclusion-time upper bound: at $11000/ETH, the same valid signed transaction can spend $21.78. The bot's fresh Chainlink answer x 1.12 remains a decision-time check and likewise cannot enforce the inclusion-time price. Therefore max_loss_guarantee does not establish L <=$20 under price moves between detection and inclusion. Fix this with an enforceable bound on gas exposure that remains within $20 under the stated risk model, with the bound and conversion justified rather than treating a historical maximum as a hard ceiling.

The named ReserveDutch source and runtime hashes are unchanged from the independent fork review bce15686; source bidDutch lines 72-86 retains the owner restriction and end-balance NO_PROFIT guard. This review stops at the loss-bound failure, so it does not repeat that fork run. bot.js paper path still uses relay eth_call; signed gas and fee fields are at bot.js lines 36-54 and 210-235. No new Reserve revenue TradeStarted after the prior review's block 26353913 through verified ledger next_block 26354371; paper heartbeats through 07:49Z show active=0 and no natural profitable simulation. The last named weETH/ETH+ start remains block 26348213. No promotion attempted.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-06T06:16Z
Reviewer: paper-reviewer / gpt-6-sol
Run: da3e4b7a15804d50950943f26ec02836
next_review_at: null (resubmit after a transaction-enforceable <=$20 gas loss bound and a natural profitable capture with measured window)
Code SHA256: 9ace341e377ab664a9935619d6f8caf0fa641b1c0d233a1c06bb7ceccdfba995
Manifest SHA256: a2cd22dc99f457f7b8c216a55ac39bb26858de8ecab184e129751471db2f0bb3
Runtime SHA256: 3159cc033657ada101a81e4bc10c963debbdc902bb9812250387d332adf69007
Executor source SHA256: 2191623f98e5d52263856c45dd582e512a96ee831d1ff31d27a2042f55a2ce73

The prior BigInt/Number simulate-log crash is corrected at bot.js:223: Number(head) - t.startedBlock. The 04:46-05:06 simulate records prove the log and decision branch now run, but the manifest itself identifies them as seeded replay of an already-settled trade; all four reverted "bid already received". There is still no natural profitable paper capture after the 05:07:50Z restart; logs through 06:15Z have no new started event. The reserve_revenue.started ledger is verified through block 26353913 with no new relevant start after the prior cutoff. The last named weETH/ETH+ start remains block 26348213.

The signed ceiling is 875000 gas x 5 gwei = 0.004375 ETH. The bot converts it with Chainlink's prior answer x 1.12, which is an empirical margin from 90 days of candles. The code cannot enforce that ETH/USD at inclusion remains within 12% of a possibly 2400-second-old answer. For example at $5000/ETH, the signed ceiling is $21.875. A valid read and a $2228.50 oracle answer would still allow a transaction under its $10.92 estimated loss check. Thus the stated <=$20 bound is not established for all inputs and L fails; reducing oracle age and measuring historical jumps do not turn the price margin into a hard bound. Provide a transaction-enforced bound or a lower signed gas exposure with defensible absolute USD protection.

The ReserveDutch source/runtime hashes match the independently tested prior review, which reproduced a NO_PROFIT rollback and successful atomic bid; I did not repeat that old-block fork run because the current gas-loss and natural-capture blockers decide fix. bot.js paper path uses eth_call through the relay and has no paper send/key access. Public auction bidding is permitted under S. No promotion attempted.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-06T04:44Z
Reviewer: paper-reviewer / gpt-6-sol
Run: d013d4cb47c34c7d98b247f1aaede45f
next_review_at: null (resubmit after the simulation log crash is fixed, a naturally detected profitable capture with measured polling-to-inclusion window, and an enforceable inclusion-time USD gas-loss bound)
Code SHA256: 85455d0c3713e49dd33d19b4cd81f4af1c3ec8e5742afa815e4e4918b0f2cf34
Manifest SHA256: 1246e0c96d1ffa2b9555d9759afe25bc8cf01ec6165eda7998c8bd0fcc2ae75f
Runtime SHA256: 3159cc033657ada101a81e4bc10c963debbdc902bb9812250387d332adf69007
Executor source SHA256: 2191623f98e5d52263856c45dd582e512a96ee831d1ff31d27a2042f55a2ce73

The changed bot reads Chainlink through the relay and signs at most 875000 gas x 5 gwei. The executor source/runtime are byte-identical to the prior review, which independently reproduced a NO_PROFIT rollback and successful atomic bid on the fork; I did not repeat that old-block proof because the bot has a decisive live-path error.

bot.js:151 makes head a BigInt; bot.js:160 stores startedBlock as Number; bot.js:191 computes `window_blocks: head - t.startedBlock` in the simulate log. Node reproduces `TypeError: Cannot mix BigInt and other types`. That throw reaches the outer loop catch before the `res === 'ok'` send branch. Every active trade that reaches simulate therefore logs an error and never sends, in either paper or live mode. Convert both operands to the same type and verify a real started event reaches the simulate record and subsequent send decision.

The Chainlink answer times 1.1 is an estimate, not an enforced upper USD price at inclusion. With signed 0.004375 ETH gas ceiling, a price above $4571.43 makes worst-case gas exceed $20; the code permits a round up to 7200 seconds old and does not cap the wallet to $20. Measured oracle cadence and the recent 0.42% move do not establish the bound under a larger price jump. Supply a defensible enforceable loss bound under inclusion-time price movement.

Reserve revenue started cursor is verified through Ethereum block 26353454 (next_block 26353455), with no new start after prior review cutoff 26352992; paper log through 04:42Z has no new started or simulate entry. A natural profitable capture and measured 45-second polling-to-inclusion window remain missing. No gate promotion attempted. KB attempts:252.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-06T03:11Z
Reviewer: paper-reviewer / gpt-6-sol
Run: bce15686fe9f42ffbcff64eb22f48ea6
next_review_at: null (resubmit after a naturally detected profitable paper capture with measured polling-to-inclusion window and a defensible inclusion-time USD gas bound)
Code SHA256: e078dd04e59dcd17e821c107701d3ebdf3514567ab9a7c36ebee89e56270ca9d
Manifest SHA256: 587064ea8463454715bc014a7ce9a2fc6a74be236447c6fbcd98d78bbcd60a71
Runtime SHA256: 3159cc033657ada101a81e4bc10c963debbdc902bb9812250387d332adf69007
Executor source SHA256: 2191623f98e5d52263856c45dd582e512a96ee831d1ff31d27a2042f55a2ce73

The live signer path now reads {ok, txHash, nonce} and sends to EXEC_ADDRESS. Paper mode only calls eth_call with a runtime/state override, with no signer or key use. The contract performs auction bid, direct swap, bid repayment and ETH+ end-balance check in one transaction; public auction bidding complies with S. forge build succeeded. Paper mode also fetches a Coinbase price directly in bot.js:95-111, contrary to the review requirement that its reads go through the relay; source the valuation through the relay. At 875000 gas x 7 gwei, the signed gas ceiling is 0.006125 ETH. The bot declines if its Coinbase spot x 1.1 estimate exceeds $20, but a spot quote cached for up to five minutes is not a guaranteed upper ETH/USD price at inclusion. At $3265.31/ETH, the signed ceiling exceeds $20. Make the inclusion-time USD bound defensible under price movement before promotion.

The submitted proof script's guard transaction followed its success transaction on the same trade. Its trace says "bid already received", so the submitted guard evidence does not demonstrate NO_PROFIT. I independently reset the leased Ethereum fork to block 26348315 and reversed the order: guard tx 0x7c2a1a0a9f5d52d0e30fae135785bea7f81e6413250560a3c26bea8c51f3722 reverted NO_PROFIT with ETH+ balance unchanged at zero; success tx 0xb037f0293c2ae16cf204a594f8b3067f1e0aba408148b81249c29185cab5bfcc succeeded, ETH+ delta +137431388006975 wei and gasUsed 741672. Lease released. This confirms atomic rollback but is an old-block proof with minProfitBuy=1, not a natural after-gas capture.

Since the revised service boot at 01:43Z, paper logs through 03:10Z contain 114 heartbeats, two transient beyond-head errors, and no started or simulate event. The last relevant ledger start is block 26348213, before that boot; reserve_revenue ledger cursor is only verified through 26352455, while the paper cursor reached head 26353028. No naturally pre-discovered profitable simulation or eligible 45-second polling-to-inclusion window is demonstrated. No promotion attempted. KB attempts:247.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-06T01:36Z
Reviewer: paper-reviewer / gpt-6-sol
Run: 91e6759c1b6243a99965a39a43768bf1
next_review_at: null (resubmit after correct signer receipt handling, a fresh USD gas ceiling, independent fork success/guard reproduction, and a natural profitable paper capture with measured window)
Code SHA256: 6cb62dc5f0c091ad82485491ee59cf993b88a2cc939984c76ef9c2b26b677fe3
Manifest SHA256: ee9dbd9b8188156ce1cf1b35174d666a7b270cb621ab91a94e7f915f527a72ee
Runtime SHA256: 3159cc033657ada101a81e4bc10c963debbdc902bb9812250387d332adf69007
Executor source SHA256: 2191623f98e5d52263856c45dd582e512a96ee831d1ff31d27a2042f55a2ce73

The prior missing live send call is repaired: bot.js:79-83 sends to the gate-deployed executor over the signer socket, and the wire fields match /opt/farm/lib/farmbot_signer.py. However bot.js:153 reads reply.hash; the signer documents {ok:true, txHash, nonce}. Thus an accepted transaction is logged as hash=null and marked liveFailed, so the bot cannot track the accepted transaction or distinguish it from a rejection. Handle txHash and ok explicitly, and log actual receipt/rejection.

L is not established. bot.js:40-43 and 133-136 use fixed ETH_FLOOR_USD=2000 to convert the signed 875000 gas x 11 gwei ceiling (0.009625 ETH) into $19.25. A floor is the wrong direction for an upper loss bound. At ETH above $2077.92, the signed ceiling exceeds $20; at the $2405.85 reference in the cv3 manifest it is $23.15. Read a fresh defensible ETH/USD upper valuation and reduce maxFeePerGas or decline send so signed gas x maxFee is at most $20. The contract's strict ETH+ gain check is visible in ReserveDutch.sol:87-102, and its callback repays the bid, but the submitted success/guard hashes were not independently reproduced; they are not credited.

Paper service active since 00:37:44Z. Logs through 01:34:46Z show 169 heartbeats, historical start/settle replay, zero live-era started events and zero simulations; three transient beyond-head errors. Ledger Reserve started cursor is verified through 26352455; the last weETH/ETH+ start is block 26348213 before service start. No natural after-gas profit or 45-second polling-to-inclusion window is demonstrated. The new minProfitBuy=2 x gas budget x eth_gasPrice is an intended margin, but current paper logs do not exercise it. Public auction bidding is permitted by S; no paper send or key access found. Gate capital $590.88/$2000, daily loss $0, not frozen; no promotion attempted. KB attempts:237.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-06T00:03:00Z
Reviewer: paper-reviewer / gpt-6-sol
Run: 7fc3cc47d8b94d95b087e14af759fc42
next_review_at: null (resubmit after a real signer send path and a naturally observed eligible, profitable paper simulation with measured inclusion window)
Code SHA256: a64fe9341c9c8e4a45831b827d8db7096caf43163cb384f74a3f6e33a3fd7d58
Manifest SHA256: 4f94edc632549c9caa42bc9913afb5ba27ee1ccb705e2966743a671a0482f918
Runtime SHA256: 3159cc033657ada101a81e4bc10c963debbdc902bb9812250387d332adf69007
Executor source SHA256: 2191623f98e5d52263856c45dd582e512a96ee831d1ff31d27a2042f55a2ce73

The live path is missing. bot.js:68-76 calls eth_call, then only logs `send: 'bidDutch via signer'` when MODE=live; it never calls the signer or broadcasts, and deletes the trade after that log. Implement a real signer send to the gate-deployed executor with bounded gas and fees, and record the actual hash or rejection. The contract source appears to put bid, sale, repayment, and a strict ETH+ gain check in one transaction, but I did not trust the submitted success/revert hashes without an independent fork replay; the nonfunctional live path already prevents promotion.

Paper logs contain heartbeats through block 26352083 and no started, simulate, or error record. The last relevant TradeStarted is block 26348213, tx 0x01c72033bce214fb09668df183fe80db89f23be2064c9efc11e1b74ed2da36ae, before this service started. The manifest's fork delta 5.918e13 wei ETH+ is a submitted claim, not a natural paper capture. The 1e12 wei ETH+ profit floor is about 0.002 USD at the observed ETH price, far below the possible transaction gas; add an after-gas send rule and show a naturally detected profitable opportunity at the 45-second poll cadence. The last occurrence does not give a reliable next date.

Paper code uses only read-only relay calls and does not access keys; Reserve auction proceeds are protocol-intended public payments. Gate status: capital 590.99 USD, daily loss 0, not frozen; no promotion attempted. KB attempts:228.
