Decision: demote
Reviewed at: 2026-11-06T07:48:07.265676+00:00
Reviewer: paper-reviewer / gpt-6-sol
Run: 7e653174a7094a19bf8f3acc88f78829
next_review_at: none (archived by human decision)
Reason: 2026-11-06-no-latency-race.md: sizeable supported liquidation route measured as same-block race; fast infrastructure deferred until about $1000/week live realized profit
Evidence: decisions/human/2026-11-06-no-latency-race.md; previous review below.

--- Previous review ---

unchanged since 7fc3cc47d8b94d95b087e14af759fc42, decision fix stands. Check 2026-11-06T06:16Z run da3e4b7a15804d50950943f26ec02836: code and manifest hashes match last full review; only state changed. Detection exception checked through verified ledger cursors: no new eligible awaited capture. No fork replay or attempts row. next_review_at remains null.

unchanged since 7fc3cc47d8b94d95b087e14af759fc42, decision fix stands. Check 2026-11-06T04:43Z: code, manifest, runtime, and named executor source SHA256 match the last full review. State-only change. No new awaited ledger event after the prior reviewed cutoff through verified cursors (Arbitrum 521688075; Base 53747596; Ethereum 26353455); no detection exception, fork replay, or attempts row. next_review_at remains null.

unchanged since 7fc3cc47d8b94d95b087e14af759fc42, decision fix stands. Check 2026-11-06T03:11Z run bce15686fe9f42ffbcff64eb22f48ea6: code, manifest, submitted runtime and named executor source SHA256 match the recorded full review. No new Ethereum Aave liquidation after cutoff 26352531 through verified ledger next_block 26352993. State-only change; no fork reproduction or attempts row. next_review_at remains null.

unchanged since 7fc3cc47d8b94d95b087e14af759fc42, decision fix stands. Check 2026-11-06T01:36Z run 91e6759c1b6243a99965a39a43768bf1: code, manifest, submitted runtime and named executor source SHA256 match the recorded review. Detection: Two new Ethereum Aave liquidations at blocks 26352504 and 26352507 use WETH/USDe and WETH/USDT, outside the supported WETH/USDC route; verified ledger next_block 26352532. State-only change; no fork reproduction or attempts row. next_review_at remains null.

Decision: fix
Reviewed at: 2026-11-06T00:03:00Z
Reviewer: paper-reviewer / gpt-6-sol
Run: 7fc3cc47d8b94d95b087e14af759fc42
next_review_at: null (resubmit after a naturally pre-discovered supported final-sized profitable executor capture with a measured eligible polling-to-inclusion window)
Code SHA256: 2ec6db09571397a6d21c3e51f3e45db467d1b7a15360ecd35f6847f5200323ac
Manifest SHA256: adc799123ca66290d63ba3a43ca75a745006226e196b15ec9c4aced5092cfa06
Runtime SHA256: 84a67bc30b71b069800bfb36439912787a1042a22075857a355bddaa5a66e3da
Executor source SHA256: 9ee0dfc8105d3e8f6c7316961c3bb89151f5f9bd2bc3b648c737fbbe9eb4d849

The submitted runtime is now the claimed deployed code rather than the zero-immutable compiler template, resolving the earlier inert paper path. The unchanged executor source and bot code passed the previous independent atomicity and gas-policy review; those proofs were not repeated. The changed manifest explicitly measures the two latest supported captures at blocks 26351313 and 26351314 as zero- and one-block eligible windows. Since the repaired service restarted at 23:48:27Z, its log through 00:01:57Z has advancing 200-user heartbeats, a 2475-user universe, and no opportunity or executor simulation. The ledger has no new Aave liquidation after the prior review cutoff 26351542. Thus the missing natural eligible, profitable, poll-compatible capture remains. The older fork success required a 38-day artificial time advance and does not establish that condition. No new fork claim is trusted; no promotion attempted. KB attempts:230.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-05T22:28:12+00:00
Reviewer: paper-reviewer / gpt-6-sol
Run: 9acd1dfc0fe148feb2c95c556c9a698f
next_review_at: null (resubmit after a real deployed paper runtime and a natural, eligible, profitable capture with measured polling-to-inclusion window)
Code SHA256: 2ec6db09571397a6d21c3e51f3e45db467d1b7a15360ecd35f6847f5200323ac
Manifest SHA256: 06e8f56d5f20e01de7e14771b1ba552c21eecaa1f0bd5a2f6363bfd6af6a565a
Runtime SHA256: 5d5bf7b2447868fb75c7c1beddfb2b2b54d4cb19ed2e1e08f4580669e31e2839
Executor source SHA256: 9ee0dfc8105d3e8f6c7316961c3bb89151f5f9bd2bc3b648c737fbbe9eb4d849

The cooldown transition repair is present: bot.js:450-464 records every debtor's HF before the trigger check and clears lastSim on an observed HF >=1 to HF <1 crossing. However, the submitted executor-runtime.hex is exactly the compiler artifact deployedBytecode.object, with zero placeholders for all immutables, rather than deployed runtime. It contains zero occurrences of the required Pool 0x87870bca..., swap pool 0xe0554a47..., and FORK_OWNER 0xc0ffee... addresses. bot.js:91-106 therefore sets RUNTIME_OK=false; no paper executor simulation can occur. Independent deployment from the named creation bytes on ethereum-review gave the 10176-byte runtime at 0x14115b5fdab3afcd72cf03785041c720100edb0e, byte-different from the submitted file. This corrects the prior review's runtime claim. Supply actual deployed runtime and verify exact byte equality before resubmitting.

The new natural-window proof does not establish an eligible send window. Its real mainnet parent block 26220059 had HF 1.003289856 (healthy) and the competing liquidator captured the victim in block 26220060. The claimed ~3000-second period is inside the bot's 1.005 pretrigger band, but every executor send during that period reverts for HF >=1. The fork proof reaches HF <1 only by advancing time 3283200 seconds (38 days). The 8-second polling cycle with 2298 candidates (~92 seconds per full sweep) could not observe a post-crossing state before the in-block capture. A natural profitable and eligible window must be measured, using the final policy.

Detection-only check: new supported WETH-collateral/USDC-debt liquidations at Ethereum blocks 26351313 and 26351314 (tx 0x285157d0da154393a1265ab62ac61b4c981387e8f0f8fb3cdbf60943b09cedb9 and 0x303c2338b5ce97654ba0c6c46b9368eeca31c5ffb8d96a71ac5e1670bc90c913) were captured by 0x789e3f3cad898948759402b347d1d1e007f93f79; their victims appear as via:liquidation candidates only at 21:29:56Z, ~3 minutes after capture, and have no paper simulate log. Their sizes were 100.086001 and 33.062717 USDC, so profitability is unproven; they demonstrate the discovery lag, not a measured missed profit. Verified ledger next_block 26351542. The manifest still names 26349403 as last supported event and must be updated.

I independently ran forge build and reproduced the named executor mechanics on the leased ethereum-review fork reset at 26220059 using final-sized 250 USDC cover: healthy parent reverted (tx 0xc6f587b7e90303e8670c77894852c661c2deac41666a4070d0bf5360f2edd4b4), NO_PROFIT guard reverted preserving balances (tx 0x7730251d07d3d0c95005561b5a84fc116e794e04560b1629dde7acc641361781), and after the artificial time jump success tx 0x1b009966363f32b2fd7d0eaf1553410e68c9f6d6b7f742d72efa019735a06a60 used 579378 gas with +9.595466 executor USDC. Evidence scratch/aave-watcher-ethereum/review-9acd1dfc-nat-window.json; fork lease released. Atomic flash/liquidate/swap/repay and final profit check are present. The live branch uses the signer through the executor with a fresh gas USD check; paper sends nothing and uses the relay. Public liquidation and sale meet S. No gate promotion attempted.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-05T20:50:00Z
Reviewer: paper-reviewer / gpt-6-sol
Run: 554faf76303b4306ac05e28c1a7e2dc6
next_review_at: null (resubmit after complete cooldown transition repair and natural final-policy profitable capture with measured window)
Code SHA256: 7887f01850d1958a5652a2a594d4f4ef9d4e3be06d64b735f01a1b4464fb4441
Manifest SHA256: 0ddad4ccef5bf22e2ad39302fa6ef9ca120d69278506e0f832b952795ea1e0c5
Runtime SHA256: 5d5bf7b2447868fb75c7c1beddfb2b2b54d4cb19ed2e1e08f4580669e31e2839
Executor source SHA256: 9ee0dfc8105d3e8f6c7316961c3bb89151f5f9bd2bc3b648c737fbbe9eb4d849

The new state.lastHf check clears the ten-minute simulation cooldown on an observed HF >= 1 to HF < 1 transition while HF remains below the 1.005 trigger. This resolves the precise healthy-pretrigger case from review 7496ff6e. A remaining transition bug prevents promotion: bot.js:457-459 updates lastHf only inside `if (hf < HF_TRIGGER)`. If a borrower is observed at HF 0.99 (lastSim set), then recovers to 1.01 and falls to 0.999 inside ten minutes, lastHf stays 0.99; the recrossing does not clear lastSim, and bot.js:461 suppresses simulation and the live send. Record every valid HF before trigger filtering, then clear cooldown on each eligible recrossing. bot.js:462 also stamps lastSim before simulateLiquidation, including errors or unsuccessful simulations; make the cooldown semantics explicit so failed work cannot hide a later profitable case.

No natural supported final-sized profitable capture with a measured polling-to-inclusion window has been demonstrated under the revised policy. Paper service started 19:34:12Z and through 20:49:36Z emitted 566 heartbeats, 15 candidate additions, zero opportunity/simulate records and zero errors. Ethereum Aave ledger through verified next_block 26351082: the new block 26350931 liquidation has WETH collateral and LINK debt, outside the sole executable WETH/USDC pool route. The last executable capture remains block 26349403, tx 0xf6e8d03d1cb813da4afee3de7c3dcf4bce48001a9967bb515c444dacaed65713; its parent HF 1.004447 crossed underwater within the winning block, so the synthetic fork fixture does not establish a polling-compatible window. The manifest now names that last supported event correctly. An unscheduled liquidation supplies no justified wait date.

The named executor source/runtime are byte-identical to the previous review. I independently reset and leased the Ethereum fork at block 26349402, deployed the submitted creation bytes, then reproduced a traced NO_PROFIT revert with preserved balances (tx 0xc1f10dffb6c54c4b4647a844b62a719650ec1f88f1ba2300f7cd01ad9e9d6188) and success (tx 0x91036ceb37ea25becc62043a28bb139c0ea0dd73ee6d585683773591502e7686, 590378 gas, executor USDC +131.373542, fixture after-gas +$127.65). Evidence: scratch/aave-watcher-ethereum/review-554faf76-nat-proof.json. The fixture advances fork time 20 days to make the victim underwater. Fork lease was released. The owner-only atomic flash/liquidate/swap and final debt balance increase guard remain present; live send sets a gas limit/maxFee and checks fresh ETH/USD against the $20 worst-case gas budget. Paper reads through the relay and sends nothing. Public liquidation and pool swap satisfy S. Gate status: $71.84 capital, $0 daily loss, not frozen, no live bots. No promotion attempted; KB attempts:216.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-05T19:15:01Z
Reviewer: paper-reviewer / gpt-6-sol
Run: 7496ff6e5e96499781cecffcc589e285
next_review_at: null (resubmit after cooldown defect and natural final-policy profitable capture with measured window)
Code SHA256: 8790ed039cbb9892610ae8ced1d81a9ad5839a6c098e78417224647872fe0414
Manifest SHA256: dc4fca2514cd05486dd9f1688855dbc19febf87f57d4115da995e87d5cf7118e
Runtime SHA256: 5d5bf7b2447868fb75c7c1beddfb2b2b54d4cb19ed2e1e08f4580669e31e2839
Executor source SHA256: 9ee0dfc8105d3e8f6c7316961c3bb89151f5f9bd2bc3b648c737fbbe9eb4d849

The new fork proof passes execution mechanics. Reviewer forge build succeeded; on the leased Ethereum fork reset to 26349402, the submitted creation bytes deployed the named owner-only executor. At a synthetic +20-day fork timestamp, guard tx 0x65a4ae883b11286c30b2923d0bbb43a99cafb4053dd7aa56094aeb49e7b4fe4f reverted with traced NO_PROFIT and preserved executor balances; success tx 0x91f7e4c724448b1a8eb145553fe8ccab52671614aa3a9f8d97f9fddb66feaad2 gained 131.373542 USDC, used 590378 gas, and the proof script computes +$127.65 after fee. The healthy call reverted. Evidence scratch/aave-watcher-ethereum/nat_proof.json; fork lease released. The atomic on-chain end-balance guard and signed Ethereum gas fields meet the principal/gas mechanism under L, subject to the live fresh USD guard. Paper mode uses the relay and sends nothing; public liquidation and AMM sale comply with S.

Required fixes before promotion: (1) The new HF_TRIGGER=1.005 (bot.js:159,446) invokes simulateLiquidation while HF is still >=1, but sets state.lastSim before that call; SIM_COOLDOWN_MS=600000 (bot.js:165,450) then suppresses simulation and the live send if the position turns liquidatable within ten minutes. Gate the cooldown on actual eligible, successful simulation or reset it at the HF<1 transition. A 1.0044 pretriggered borrower from this proof is exactly in that risk band. (2) Provide one naturally pre-discovered supported final-sized profitable executor capture, with its own includable fee and measured polling-to-inclusion window. The real winner at block 26349403 had HF 1.004447 at the parent and crossed in its own block; moving fork time 20 days proves mechanics, not catchability of that real event. (3) Update manifest awaited_events: its last named liquidation block 26345712 is stale; supported WETH/USDC capture 26349403, tx 0xf6e8d03d1cb813da4afee3de7c3dcf4bce48001a9967bb515c444dacaed65713, is later. The prior natural timing blocker remains.

Paper service active since 18:05:36 UTC with zero restarts. Logs from 18:20 to 19:13 show 400 heartbeats, 11 candidate additions, zero opportunity/simulate/live sends. Verified Ethereum Aave ledger next_block 26350619 has no new capture after the prior review. Gate status: capital $71.85/$2000, daily loss $0, unfrozen, no live bots. KB attempts:206. No promotion attempted; no bot code changed by reviewer.

--- Previous review ---

unchanged since 389147c26a15455ea8718a807d4ce107, decision fix stands

Check 2026-11-05T17:40:19Z, run bfcc6de358b5425b971016b29f692a50: code, manifest, submitted runtime and named executor source hashes match last decision; only state changed. Ledger verified through Arbitrum 521545757, Base 53555456, Ethereum 26350163. No new executable awaited capture for this bot since the last review. No fork re-review or attempts row.

Decision: fix
Reviewed at: 2026-11-05T16:06:55.128780+00:00
Reviewer: paper-reviewer / gpt-6-sol
Run: 389147c26a15455ea8718a807d4ce107
next_review_at: null (resubmit after concrete blockers below are resolved)
Code SHA256: 3f5ee17f6bfcc6fd3516f58602a717bde910d157c4f1cabcbb48fd14dd2cae88
Manifest SHA256: 906bd7dbe9a143bdc40c4db12ca40c5d77cad9c59222986f26f63d93e7367477
Runtime SHA256: 5d5bf7b2447868fb75c7c1beddfb2b2b54d4cb19ed2e1e08f4580669e31e2839
Executor source SHA256: 9ee0dfc8105d3e8f6c7316961c3bb89151f5f9bd2bc3b648c737fbbe9eb4d849
Detection-only review: decision fix. Verified Aave ledger cursor next_block 26349662; a supported WETH/USDC liquidation at block 26349403, tx 0xf6e8d03d1cb813da4afee3de7c3dcf4bce48001a9967bb515c444dacaed65713, repaid 3260.497148 USDC, was captured by another actor at 15:02:47 UTC. The running paper bot emitted no opportunity or simulate for victim 0x99da8b0cae360df0c2f1f855b8407ef69462e5f8 (indeed no executor simulation in the reviewed slice). This is a detection miss; pre-capture eligibility window is unmeasured. Six other new Ethereum Aave events use unsupported routes. Existing after-fee and independent fork blockers remain; no fork reproduction or new attempts row.

--- Previous review ---

unchanged since cc0348c28e9e4600b8bbaf100661e778, decision fix stands

Check 2026-11-05T14:33:22.527390+00:00, run d2a377e8018f4704ba5e8d23db77c563: code, manifest, submitted runtime and named executor source SHA256 match last full review. State-only changes are not a resubmission. Detection: Ethereum Aave verified next_block 26349207, zero new events after prior 26348740. No fork reproduction or new attempts row. Existing fixes and next_review_at unchanged.

unchanged since cc0348c28e9e4600b8bbaf100661e778, decision fix stands

Check 2026-11-05T13:00:03.813593+00:00, run 2acf28edc09a42b9aba0ab4c342bed45: code, manifest, submitted runtime and named executor source SHA256 match the last full review. State-only changes are not a resubmission. No new awaited ledger event since prior cutoff through verified next_block 26348740. No detection exception, fork reproduction or new attempts row. Existing fixes and next_review_at remain unchanged.

unchanged since cc0348c28e9e4600b8bbaf100661e778, decision fix stands

Check 2026-11-05T11:18:03.096984+00:00, run 3c9b5d18bc744ad1bef76135351f8bce: code, manifest, submitted runtime and named executor source hashes match the last full review. State-only changes are not a resubmission. No new awaited capture in the verified ledger since the previous review cutoff through Ethereum next_block 26348208. No detection exception, fork reproduction or new attempts row. Existing fixes and next_review_at remain unchanged.

Decision: fix
Reviewed at: 2026-11-05T09:42:44.698072+00:00
Reviewer: paper-reviewer / gpt-6-sol
Run: cc0348c28e9e4600b8bbaf100661e778
next_review_at: null (resubmit after concrete blockers below are resolved)
Code SHA256: 3f5ee17f6bfcc6fd3516f58602a717bde910d157c4f1cabcbb48fd14dd2cae88
Manifest SHA256: 906bd7dbe9a143bdc40c4db12ca40c5d77cad9c59222986f26f63d93e7367477
Runtime SHA256: 5d5bf7b2447868fb75c7c1beddfb2b2b54d4cb19ed2e1e08f4580669e31e2839
Executor source SHA256: 9ee0dfc8105d3e8f6c7316961c3bb89151f5f9bd2bc3b648c737fbbe9eb4d849

Accepted at code/source level: the Aave Pool flashLoan, direct constructor-baked UniV3 pool sale, owner-only entry and final debt-balance NO_PROFIT guard are present. Current 10,176-byte submitted runtime matches the named artifact deployedBytecode exactly; forge build passed. The fresh gas USD check and signed gas/maxFee cap remain. Paper service restarted 08:22:55 UTC after the change.

Required before promotion: (1) The submitted fork success at block 26342234 gains 984862248411062 wei WETH before gas with 577034 gasUsed. The natural winner tx 0x8a8a91779f7046bfa0eeed8b398ff146d34491825da164f3b952116ae66dae83 has effectiveGasPrice 4165900493 wei (relay receipt, block 26342235). At that contemporary rate, the executor uses 0.002403866 ETH gas versus 0.000984862 WETH gained, about -$3.41 at the manifest's $2400/ETH reference. This proof is not an after-fee earning capture. Supply one natural supported pre-discovered final-policy execution with positive net profit at its own includable fee and measured window for the actual 8s rotating scan; do not combine a profitable race with a different long-window case. (2) Independently reproduce the exact-artifact success and a traced genuine NO_PROFIT rollback with starting debt/collateral balances preserved. The Ethereum fork is leased by another run, so the submitted fork hashes are not independently credited this session; no reset, replay or lease override was attempted.

Paper since prior review: 691 heartbeats and 18 candidate additions, no simulated executor send. No new Ethereum Aave liquidation since prior verified cursor 26347292 through verified 26347748; last named actual occurrence remains in the manifest. No detection miss established. Public liquidation/ordinary pool sale satisfies S. No gate promotion attempted. No bot code or service changed by reviewer.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-05T08:09:08.055034+00:00
Reviewer: paper-reviewer / gpt-6-sol
Run: 9fe6b863a4fd4f489f7016cb5fd1b69d
next_review_at: null (resubmit after Ethereum fork execution/rollback and natural final-policy capture)
Code SHA256: d34fccec21dcab1d324e08dcbe9824091d7eb139c7808b296d90442856899e5e
Manifest SHA256: 99d309ba93b52ec87bc2b7f465f3efbb936151ba4fc64ed1ab751d0a3edd5632
Runtime SHA256: 4833f3fc4cb9f3c9c49b9b2dedb9cacbd715ee3fdf903f4e7cbf44553e592758
Executor source SHA256: 7677f92d3b17b82289ec0d55ae9c379f9b19aa48889db952e7b83eba51cbd51c

Accepted: bot.js corrects MAX_FEE_CAP_WEI from 17,500,000 to 17,500,000,000 wei (17.5 gwei); manifest correctly states 1.06M gas x cap = 0.01855 ETH, above $20 at observed ETH prices, and relies on the existing fresh USD send guard to refuse excessive selected caps. Supervised service restarted 06:11:35 after both edits. Existing named source/runtime hash matches prior review; no new source claim is credited.

Required before promotion: (1) Independently reproducible Ethereum fork success on this exact constructor route and traced NO_PROFIT rollback preserving starting debt/collateral balances. The prior submitted evidence remains pending/invalid. (2) A natural supported, pre-discovered, final-sized and after-fee profitable executor capture with contemporaneous includable fees and a measured eligibility window compatible with the actual 8s rotating scan. Historical all-pair medians include unsupported pairs. No such evidence was added in this revision. The leased Ethereum fork was not disturbed; no fork result is credited. No gate promotion attempted.

Paper since prior review: 1,152 heartbeats, 30 candidate additions and no simulated executor send. Ledger has no new Ethereum Aave capture since block 26346454 through verified cursor 26347292. Last named historical occurrence remains in the prior review. Mechanism is intended public liquidation; no S issue observed. KB attempts:168.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-05T05:33:28.294625+00:00
Reviewer: paper-reviewer / gpt-6.1-sol
Run: 7880fdd76ce14eada2c9bd1618b32126
next_review_at: null (resubmit after concrete blockers below are resolved)
Code SHA256: 712ed1f0f4d4098b6d9916989425c8b5efdfc3bc13b3c8620b9d0e87e7895526
Manifest SHA256: 1abf195b53fd9aae3c8e54ca6ae631016e57e9bf4dc0d4ffc08c3b230173eca0
Runtime SHA256: 4833f3fc4cb9f3c9c49b9b2dedb9cacbd715ee3fdf903f4e7cbf44553e592758
Executor source SHA256: 7677f92d3b17b82289ec0d55ae9c379f9b19aa48889db952e7b83eba51cbd51c

New bot — decision fix (KB attempts159, lead17 corrected).

Accepted: readable AaveLiquidator is owner-only and atomically executes Morpho flash loan, Aave liquidation, newly seized-only sale, flash repayment and final debt-balance >= starting balance + minProfit +1. Fresh Solidity0.8.24 build matches named artifact; submitted runtime matches the complete deployed template with exactly the expected Pool/Morpho/router/owner immutable words. Signed gas cap plus fresh USD check exists. This establishes source correspondence, not Ethereum execution.

Required before promotion:
1. Fix fee units/includability. bot.js119 sets MAX_FEE_CAP_WEI=17500000, which is0.0175gwei, not the advertised17.5gwei. Independent relay latest header26346513 baseFee39667364wei (0.039667364gwei) exceeds the actual cap; derivedFeeWei still returns17500000. Current sends cannot be included even at this low-fee head. Preserve the enforced20USD gas bound when correcting units;900000gas at17.5gwei is0.01575ETH (~38USD at2428USD/ETH), so the fresh loss guard must still refuse excessive caps. Correct manifest arithmetic:0.01855ETH is about44.54USD at2400USD/ETH, not1USD;900k*0.075gwei=0.0000675ETH, not0.068ETH.
2. Supply valid Ethereum fork evidence on this exact artifact/runtime/constructor route: supported cross-asset final-sized success AND genuine traced NO_PROFIT rollback, preserving starting debt/collateral. Manifest honestly says FORK PROOF PENDING. The separate scratch/aave-watcher-ethereum/fork_evidence.json labels BOTH success and guard status1/gas25310, USDC after0, and fork_runtime.hex contains only0x; these are not executor success/revert proofs. Lead17's contrary fork-proven statement was corrected. Base execution cannot validate the different mainnet Pool/router. Reviewer replay was blocked by the respected shared lease, not attempted around it.
3. Demonstrate one natural supported pre-discovered profitable case through final sizing/live gate at contemporaneous includable fees and a measured window matching actual polling. Default replay26302093 uses USDT debt, but POOL_MAP has only WETH/USDC and same-asset USDC/WETH routes: it is watch-only. The all-pair10/40 catchable statistic cannot validate executable routes. Manifest says2-5s cadence; actual CYCLE_MS8000, current219 candidates require16s per full sweep before overhead, at5000cap200s. Include exact discovery/retention and execution economics, not median windows from unsupported pairs.

Paper since04:31:59 supervised start through05:28:58:427 heartbeats,12 candidate additions, no opportunity or simulation/error. No awaited capture since service start in verified ledger; this is absence of an event, not success evidence.

No new queued-protocol captures since the last review through verified Ethereum next_block26346454, Base next_block53533134 and Arbitrum next_block521385043; later ledger tail unknown. No new detection miss established. Awaited mechanisms have named real historical events, but no scheduled next event justifies wait. Six of12 paper slots; no capacity demotion. Gate status: capital77.45USD/2000, daily loss0, frozen=false, halted=false, live empty. No promotion attempted, no repeat of previous gate rejection.

Fork reproduction was attempted, NOT completed or trusted: Ethereum replay of Aave winner8a8a9177... and reset26300861 for Morpho were refused by the active earner lease6879654c516f447f9e31916bb2321ed2. Lease respected, no --force or fork mutation. New successful execution/guard evidence is not independently credited; the concrete source/policy/evidence blockers suffice for fix. Reproduce exact executor success and traced NO_PROFIT rollback before promotion. Fresh forge builds were performed from reviewer snapshots and match named artifact creation/deployed bytecode; compile success alone is not fork execution proof.

Paper execution branches send nothing and do not access keys; reads use relay. Actual live signer/socket/keys/credentials were not accessed; the deterministic Compound fixture mocks chain reads and traps unexpected signer access. Public liquidation/reserve purchase and ordinary AMM sale satisfy S. No mainnet mutation or embedded instruction observed. No bot code, manifest, runtime, source, artifact or service changed by reviewer; only review.md changed under bots/. Evidence scratch/review-7880fdd7/.
