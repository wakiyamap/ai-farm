# Review 2026-11-09T15:52Z — fix

- Decision: **fix**. `next_review_at: null`; run `233973f5be2e4f9ab5f3de40b56f194e`, `attempts:698`. No promotion.
- The submitted `bot.js` fixes the prior stale ETH/USD finding: the current-cycle oracle result gates sends (`priceFreshCycle` at lines 335-351, 385), and receipts remain pending when that read fails. `manifest-check` and `node --check` pass. Paper heartbeats reach block 26378333 with 21 accounts, fresh price, zero liquidatable; ledger Gearbox cursor is 26378283 with no new capture after block 26287070. Atomic executor and signed fee limit were independently reproduced in the previous review; the artifact and manifest are unchanged, so no new fork run was needed to identify the open code defect.
- **Live stop is not restart-safe:** `saveState` at line 113 catches and ignores every write error. A signer-accepted hash is appended only in memory at line 418 and settled loss changes only in memory at line 137; neither is persisted until line 439, after the whole scan and any other sends. A restart or failed write in that interval loses an accepted transaction or its gas loss, allowing the persisted cumulative loss to stay below $30. Persist each accepted hash and settlement before another send, fail closed on persistence failure, and keep `STOPPED.json` consistent with the state total.

--- Previous review ---

# Review 2026-11-09T14:10Z — fix

- Decision: **fix**. `next_review_at: null`; require a fresh ETH/USD value in the live send gate and loss settlement. Run `811c0a9f096640b9ba60cc98e190addc`.
- The submitted code fixes the two previous stop findings: a receipt stays pending when ETH_USD is zero, and settlement invokes the stop writer without waiting for another eligible account. `manifest-check` passes. I reran `scratch/gearbox-v3/proof-flash5.py` on leased Ethereum fork generation 326 at reset 26287069; success tx `0x4e66dcf112b147a0b3930cdd4b6031b9c085ce98ae9781d87c54a6972e63d85f` used 1347729 gas and paid owner 3.222826613365578920 WETH, executor WETH zero. Healthy-account tx `0xa186843f8c78a6c20edf877b6a7fcf8731914aea7836add3d88acf5deb9f00c5` reverted with both WETH balances unchanged. Lease released. Atomic executor and signed 1.5m x <=10 gwei, value zero, are otherwise sound. The live path calls only the executor; paper only reads the relay. Public liquidation meets S.
- **Open L/stop issue:** `bot.js:333` leaves the prior ETH_USD and ETH_USD_AT untouched if the oracle slot is absent or fails. `bot.js:367,383-384` can then send using that old price to check the manifest $35 bound; `bot.js:286` also settles receipts with the old price before the current cycle's oracle read. A price rise during a read failure can make 0.015 ETH exceed $35 at signing while the bot still sends, and can undercount cumulative gas loss. Fail closed on a failed/stale price refresh, and settle receipts only with a fresh positive price. Current paper heartbeats through block 26377806 show 21 accounts, header lag zero, no new liquidatable account; ledger source has no newer qualifying event than block 26287070.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-09T12:31Z
Reviewer: paper-reviewer / gpt-6-sol
Run: ece30d8080914650b0db7985f5bcce3d
KB attempt: 677
next_review_at: null (resubmit after cumulative live-loss accounting and stop-state persistence are repaired)
Code SHA256: b2f2cbbbcd7abd321dd0952be7693c6cd56d74740a65e2899a02056ca811903b
Manifest SHA256: 8b3016cdf90b44cfa074b54d1876d4e8982c5eb5fb5cd16839aceb2dc2685653
Runtime SHA256: 6fd4851edf00e261ae922163465bdebcd3565c54240585893b4560ca20632187
Executor source SHA256: 4b2aadc1733f12e30296bae653ced3669494828257865a9d3edefbe9097624e9

Required fix under decisions/human/2026-11-09-promote-criteria.md §5: In bot.js liveLossSettle (lines 123-134), a confirmed pending transaction is removed from pending even when ethUsd is 0. On a live service restart, ETH_USD initializes to 0, and scanCycle calls liveLossSettle before reading the oracle price in that first cycle. If a pending tx receipt is available then, its gas is permanently omitted from liveLoss.usd, so cumulative realized loss can cross $30 while the bot continues sending. Keep that receipt pending until a positive fresh valuation exists, then count it exactly once. Also trigger and persist the STOPPED.json reason immediately when settlement reaches $30; the current stop check and write are inside the fresh eligible-account branch (lines 352-354), so the reason is not written until another qualifying opportunity appears. Verify the restart-with-confirmed-receipt path and the no-new-opportunity threshold path before resubmitting. No gate promotion attempted.

Independent safety and detection checks passed. manifest-check: OK 1/1; forge build succeeded for the named artifact. Reviewer ran scratch/gearbox-v3/proof-flash5.py against the leased ethereum fork reset to 26287069, generation 319, and verified the current artifact deploys with no constructor args and owner=0xc0ffee...01. Success tx 0x4e66dcf112b147a0b3930cdd4b6031b9c085ce98ae9781d87c54a6972e63d85f used 1,347,729 gas, owner WETH increased 3.222826759268905135, executor ended at 0 WETH; healthy-account tx 0xa186843f8c78a6c20edf877b6a7fcf8731914aea7836add3d88acf5deb9f00c5 reverted with owner/executor WETH unchanged. Proof: scratch/review-ece30d80-gearbox-proof.json; lease released. The freshly deployed runtime SHA256 matches the paper runtime. The executor takes a Morpho flash loan, liquidates through the Gearbox facade, repays and sweeps in one transaction, reverting on WETH below principal + minProfit. The live path sends only to that executor with signed gas 1.5m x at most 10 gwei = 0.015 ETH and value 0; at logged $2110/ETH the full signed cap is $31.65, below manifest L=$35, and the bot checks the USD bound at send time. Paper mode uses relay eth_call only; public Gearbox liquidation compensation is within S.

Paper logs: 9,845 heartbeats through block 26377333, 21 enumerated accounts, header_lag 0, four RPC reads/cycle, zero liquidatable and zero sims; no new gearbox_v3.liquidate_credit_account event through verified ledger cursor next_block 26377258. The last historical occurrence remains block 26287070, tx 0x906b3d51233d9538bdcfbc583ca91fd0eda77102b8d85b1abb9d5f1941b8d847. The new human promotion criteria remove the natural-capture prerequisite, so the missing event is not a fix reason. No embedded instructions observed.

--- Previous review ---
Decision: wait
Reviewed at: 2026-11-08T12:51Z
Reviewer: paper-reviewer / gpt-6-sol
Run: 8222f536141845838c6a5996934ae2d5
next_review_at: 2026-11-09T12:00:00Z (check for the next natural eligible liquidation; historical cadence 0.31/day)
Code SHA256: 2f967fd44f2c869d1c46266933e2a571a689fbf09f22415f897cad7df7e13815
Manifest SHA256: f3f4bd49d4fc63e0ccb2708366414bb5d305a4a71861b0eec614196cd4322038
Runtime SHA256: a3a15cbb1e64d712ebf0e33d2954a153ff5fff9ada55d117502b5a51a7d96187
Executor source SHA256: 81d59ed14224983b020947816128911e5206b401d19e77c40d1f53fb0a82fe1b

Unchanged code, manifest, runtime and named executor source. Independent ethereum-review fork reset 26287069, generation 32, reproduced the profitable liquidation (tx 0xf30db5c79749c9b63af9575085dd770d489b3dcf62c95b59aab60f1c9f7175e4, owner +3.222826613365578920 WETH, 1,350,704 gas, executor ending WETH zero) and a guard revert with balances unchanged (tx 0xda173dde3d6ab18dc2685fd70ed039ff7b62cc42dddfd17eb407d17e26f87f99). Proof: scratch/review-8222f536-gearbox-proof.json; lease released. The signed maximum remains 1.5m gas x 10 gwei = 0.015 ETH, worth $33.54 at paper price $2236, under manifest L=$35 at signing; value zero. The executor performs flash loan, liquidation, conversion, repayment and owner payout atomically; paper sends no transactions. Public liquidation reward is within S.

Ledger gearbox_v3.liquidate_credit_account still has zero events through verified cursor next_block 26370234, versus last named mainnet occurrence block 26287070. Paper heartbeat reached block 26370264 with 21 accounts, zero liquidatable, zero simulations, runtime_ok true and header_lag zero. Seven isolated cycle errors across about 5,019 heartbeats since the prior review did not stop its progress. There is no natural capture to assess net after gas or polling window, so wait. No gate promotion attempted.

--- Previous review ---

Decision: wait
Reviewed at: 2026-11-07T08:55Z
Reviewer: paper-reviewer / gpt-6-sol
Run: d40566ecb0ab4740825076a521efbc70
next_review_at: 2026-11-08T12:00:00Z (check for a natural eligible liquidation; historical cadence about 0.31/day)
Code SHA256: 2f967fd44f2c869d1c46266933e2a571a689fbf09f22415f897cad7df7e13815
Manifest SHA256: f3f4bd49d4fc63e0ccb2708366414bb5d305a4a71861b0eec614196cd4322038
Runtime SHA256: a3a15cbb1e64d712ebf0e33d2954a153ff5fff9ada55d117502b5a51a7d96187
Executor source SHA256: 81d59ed14224983b020947816128911e5206b401d19e77c40d1f53fb0a82fe1b

The manifest's executor is now an exact scalar artifact path. YAML parsing resolves it to scratch/gearbox-v3/contracts/out/GearboxFlashLiquidator5.sol/GearboxFlashLiquidator5.json and the file exists. The constructor and paper-runtime explanation moved to executor_note. Bot code, runtime and named Solidity source are byte-identical to the previous independent review. The source runs the Morpho flash loan, Gearbox liquidation and adapter conversions in one transaction, checks WETH >= principal + minProfit, repays principal and sweeps the premium to the bot owner; a revert rolls back all legs. Live sends go only to the executor, and paper uses relay eth_call with a runtime override. The signed limit is 1,500,000 gas x at most 10 gwei = 0.015 ETH, worth $33.63 at the paper price $2242/ETH, under manifest L=$35 and common L=$50. capital_usd=100, principal_usdc=0. Public liquidation premium is an intended protocol reward under S.

Independent reproduction on ethereum-review fork generation 12, reset at block 26287069: high-minProfit guard reverted with balances unchanged (tx 0xda173dde3d6ab18dc2685fd70ed039ff7b62cc42dddfd17eb407d17e26f87f99); the measured liquidation succeeded (tx 0xf30db5c79749c9b63af9575085dd770d489b3dcf62c95b59aab60f1c9f7175e4), used 1,350,704 gas and swept 3.222826175655600209 WETH to the owner, leaving executor WETH zero; a healthy-account call reverted with balances unchanged. Evidence: scratch/review-d40566ec-gearbox-proof.json. The proof script's cm_accounts_n=192 uses its obsolete decoder and is not a count of real accounts; the prior independent historical relay check established 20 genuine accounts including the target at the parent block. Lease released.

The ledger has no gearbox_v3.liquidate_credit_account event through verified next_block 26361846; last measured occurrence remains mainnet tx 0x906b3d51233d9538bdcfbc583ca91fd0eda77102b8d85b1abb9d5f1941b8d847 at block 26287070. Paper heartbeats through block 26361898 show 21 accounts, zero liquidatable, zero simulations, header_lag=0 and four RPC reads per cycle. Thus there is no new awaited event to test detection and no natural paper capture establishing a polling-to-inclusion window or after-gas profit. The only missing evidence is a naturally occurring qualifying event; wait until the stated time. No promotion attempted.

--- Previous review ---
Decision: fix
Reviewed at: 2026-11-07T07:19:48Z
Reviewer: paper-reviewer / gpt-6-sol
Run: bfdc1eacffe648a697f9b0c0492e1cbe
next_review_at: null (resubmit with executor set to the exact artifact path; then review a natural eligible paper capture)
Code SHA256: 2f967fd44f2c869d1c46266933e2a571a689fbf09f22415f897cad7df7e13815
Manifest SHA256: dfb5605d544e36b396133902eb6e74c81f93f9b4891bdd568b2980aeeb71bd3b
Runtime SHA256: a3a15cbb1e64d712ebf0e33d2954a153ff5fff9ada55d117502b5a51a7d96187
Executor source SHA256: 81d59ed14224983b020947816128911e5206b401d19e77c40d1f53fb0a82fe1b

Required fix: Set manifest.yaml `executor` to exactly `scratch/gearbox-v3/contracts/out/GearboxFlashLiquidator5.sol/GearboxFlashLiquidator5.json` (a single scalar path); put the constructor and paper-runtime explanation in another field. YAML currently parses the folded `executor` as that path followed by several sentences; os.path.isfile(manifest["executor"]) is false, although the artifact at the path prefix exists. The deploy gate consumes the manifest field as the artifact name, so this submission is not deployable as written. This is the sole remaining code/manifest blocker found in this review.

The prior decoder, fee-header and arithmetic issues are corrected. Independent historical relay check at block 26287069 returned 20 compressor accounts including the next-block liquidated account 0x56631dcb1ea548d2629e82e01375090ed1f81b7e, with isLiquidatable=1 (scratch/gb-enum-verify.py). Current paper logs show 21 accounts, header_lag=0 and four RPC reads/cycle at 07:16Z; no simulations or sends. Fork-measured economics recompute correctly: 3.222825835 WETH x $2239.78 = $7218.42 gross; 1,350,704 gas x 0.0396 gwei x $2239.78 = $0.12 gas. This is one measured large debtor, not a measured distribution.

Independent executor reproduction: ethereum-review fork generation 11 reset to 26287069, lease released. The unchanged source was deployed with constructor owner; high-minProfit call reverted with owner/executor WETH unchanged (tx 0xda173dde3d6ab18dc2685fd70ed039ff7b62cc42dddfd17eb407d17e26f87f99). The clean liquidation succeeded (tx 0xf30db5c79749c9b63af9575085dd770d489b3dcf62c95b59aab60f1c9f7175e4), gasUsed 1350704, owner WETH +3.222825932483389864 and executor final WETH 0. A healthy-account call reverted with balances unchanged (tx 0xcff87bf41778eb8ced475b554ed17c6a8fc25916c494a7745cbbc96d0360d594). Evidence: scratch/review-bfdc1eac-gearbox-proof.py and .json. The proof script retains its old compressor decoder for finding a healthy control and reports 192 pseudo-accounts; that number is not evidence for enumeration. The separate historical relay check above validates the corrected bot decoder. Live sends target the executor; paper mode uses relay eth_call with the fork runtime override. Its signed 1.5m gas x 10 gwei maximum is 0.015 ETH, or $33.65 at the paper price $2243, within manifest L=$35; capital=$100, principal_usdc=0. Public liquidation premium is an intended mechanism under S.

Detection: gearbox_v3.liquidate_credit_account has zero ledger events since installation, verified through cursor next_block 26361382; the last historical occurrence remains tx 0x906b3d51233d9538bdcfbc583ca91fd0eda77102b8d85b1abb9d5f1941b8d847 at block 26287070. No natural eligible paper capture or measured polling-to-inclusion window yet, so promotion is not justified even after the path is repaired. No gate promotion attempted. No embedded instructions observed.

--- Previous review ---
Decision: fix
Reviewed at: 2026-11-07T05:44:00Z
Reviewer: paper-reviewer / gpt-6-sol
Run: 04aa3990c5894fa9b5547dd91e4ac4af
next_review_at: null (resubmit after the account decoder, manifest artifact path, and economics are corrected; then observe a natural eligible paper capture)
Code SHA256: f0f8e6c597199542ad41aafd82bbb8659d35239905f1e100c7dda50162c8d081
Manifest SHA256: 6b407f2f57af10c54a27cf430d0b3587cfbe1786646a3450c5b0ac72cca45569
Runtime SHA256: a3a15cbb1e64d712ebf0e33d2954a153ff5fff9ada55d117502b5a51a7d96187
Executor source SHA256: 81d59ed14224983b020947816128911e5206b401d19e77c40d1f53fb0a82fe1b

Required fixes:
1. Correct CreditManagerCompressor.getCreditAccounts decoding in bot.js scanCycle. The return is a dynamic array: word 0 is offset 0x20, word 1 is the length, followed by element offsets and structs. The bot treats word 0 as the count (always 32) and takes every second offset as an account address. Independent relay eth_call at historical block 26287069 returned 20 accounts and included the next-block liquidated account 0x56631dcb1ea548d2629e82e01375090ed1f81b7e; the bot's extraction returned 32 pseudo-addresses beginning 0x...14, 0x...0300, 0x...0400 and omitted that account. At current head 26360944 the true length was 21, while paper heartbeat logged accounts=32 and liq=0. Decode the returned ABI tuples, then demonstrate that the actual known eligible account is enumerated at block 26287069, not merely that the count is nonzero. This is a deterministic detection miss for the measured route.
2. Repair the executor artifact reference in manifest.yaml. YAML folds the line break inside the filename to a space: parsed executor begins scratch/gearbox-v3/contracts/out/GearboxFlashLiquidator5.sol/GearboxFlashLiquidator 5.json. That file does not exist; the actual artifact is GearboxFlashLiquidator5.json. The source path in max_loss_guarantee is similarly split. Keep both paths whole so gate deployment can use the named artifact and reviewers can follow the named source.
3. Correct the economics in manifest expected_value and fork_evidence (and bot/source comments if retained). 3.222825835 WETH x the cited 2239.78 USD/WETH = 7218.42 USD gross, not 7.22 USD. The stated 0.053 USD gas estimate repeats the unit error: 1,350,704 gas x 0.0396 gwei = 0.00005349 ETH, about 0.12 USD at 2239.78 USD/ETH. Recompute the after-gas expected value and distinguish the measured large debtor from the unmeasured debtor distribution. The wrong unit affects the case for allocating a slot and for future promotion.


4. Read the current head before deriving fees or claiming a 20-second poll. The paper bot repeatedly received eth_getBlockByNumber("latest")=26360944 (timestamp 05:39:35Z) from 05:41:42 through at least 05:44:35Z, while an independent eth_blockNumber at 05:44:35 returned 26360969. eth_getBlockByNumber("0x1923c89") returned the fresh explicit header. At that moment the bot's fee policy was 25 blocks behind, and its heartbeat still advertised 26360944. Derive the header from an explicit fresh block number, verify the lag is bounded, and show polling-to-inclusion at an eligible event. This may be a relay cache problem; see inbox/meta/2026-11-07-paper-header-latest-stale.md.

Accepted safety evidence: I read GearboxFlashLiquidator5.sol and independently ran forge build and a copied one-script proof on the dedicated ethereum-review fork, reset 26287069, generation 10, with lease released. The exact route completed atomically: success tx 0xf30db5c79749c9b63af9575085dd770d489b3dcf62c95b59aab60f1c9f7175e4 status 1, gasUsed 1350704, owner WETH delta +3.222825883848947772, executor final WETH 0. Before it, the same liquidatable account with minProfit 4 WETH reverted (tx 0xda173dde3d6ab18dc2685fd70ed039ff7b62cc42dddfd17eb407d17e26f87f99, status 0) with owner/executor balances unchanged; a healthy-account call also reverted with balances unchanged. Evidence script/output: scratch/review-04aa3990-gearbox-proof.py and scratch/review-04aa3990-gearbox-proof.json. The Solidity calls Morpho flashLoan, Gearbox liquidation and three registered adapter legs, checks WETH balance >= principal+minProfit, sweeps premium to the immutable owner, and repays in one transaction. The bot's live send targets EXECUTOR_ADDR, not the facade; paper mode only calls the relay with a code override and never invokes the signer. Signed gas=1500000 x maxFeePerGas capped 10 gwei, value=0, native worst case <=0.015 ETH. Its live valuation check refuses when this exceeds manifest L=35 USD; the signer also enforces L at signing. Capital=100 USD, principal_usdc=0. Public Gearbox liquidation is intended protocol compensation, consistent with S.

Detection/operations: The supervised paper service began 05:41:41Z and logged 20-second heartbeats, no simulations or captured events yet. The ledger source gearbox_v3.liquidate_credit_account has next_block 26360921 and zero ingested events because it was just installed, so the independently measured last occurrence remains tx 0x906b3d51233d9538bdcfbc583ca91fd0eda77102b8d85b1abb9d5f1941b8d847 at block 26287070. The new service cannot be credited with a natural capture. Independent relay first showed 17-block header lag at 05:42:55Z, growing to 25 blocks by 05:44:35Z; explicit-number header reads were fresh. No gate promotion attempted. No bot code or manifest edited by reviewer. No embedded instructions observed.
