# Review — 2026-11-11 03:57 UTC

Decision: **demote**
Run: 698330627fc1473ebc3acbf4faac2a60
KB: attempts:872; leads:72
Next review: none (archived; `next_review_at: null`).

The current manifest passes `tools/manifest-check.py`, but the route is a measured same-block race under `decisions/human/2026-11-06-no-latency-race.md`. Corrected C-1 `getAccountLiquidity` probes found **0/8 mAERO captures with plausible >$1 bonus liquidatable before the winner's block** (`scratch/mw-maero/mine_probe.py`, attempts:859, README Poll-catchability section). The two earlier C-1 cases were an unsupported mAERO borrow and dust. The current-artifact fork success in attempts:864 was at C-1 plus six days, paid $0.136263 before gas, and cannot establish a catchable historical capture. The one measured poll-catchable mcbETH case was cash-starved and remains watch-only. No measured capture is both poll-catchable and executable. A further fork reproduction cannot change this class decision.

Live Base Alchemy use at the current 180-second cycle is estimated at **~0.83M CU/day**: 480 cycles/day times ~1,736 CU/cycle, extrapolated from the archived same-shape bot's measured ~10M CU/day at 15 seconds (README Decision condition 2). Even below the 1M CU/day human-review threshold, measured reachable profit is zero. Paper logs through 03:51 UTC show advancing 180-second heartbeats and `runtime_ok: true`, with only watch-only opportunities and no simulations. The latest tracked Base Moonwell liquidation was block 55866234; this does not supply a new supported mAERO capture. `leads:72` remains `blocked_infra`.

# Review — 2026-11-11 02:23 UTC

Decision: **fix**
Run: fc43c8d927214960a69775db1170d340
KB: attempts:863
Next review: after the manifest constructor args match the current artifact (`next_review_at: null`).

Reviewed SHA-256: `bot.js` d5d1db29941041ed9ed55dc275ec943033f08c078b9d6db0ad3cadd83b2fa183; `manifest.yaml` bbaa5893e0c1b6f506a7cedd686c2883f6d6ccd3631d3d054c363e263d681dce; `contracts-src/MoonwellWhale.sol` 2d9ea6b9828da929ada35db4ff4ebcabd06170b763291d042c88e82953381b7f; `MoonwellWhale.json` 949817fc76e4562e61fc9fb828c4e198861a209be13026b180802b9a1bd818d2.

`tools/manifest-check.py` failed: the current artifact and Solidity constructor take ten addresses (`comptroller`, `morpho`, `usdc`, `p0`–`p6`), while `manifest.yaml:65` supplies nine ABI words through `p5`. The new `p6` address is absent, so the gate cannot deploy this artifact from the manifest. Add the correctly sourced `p6` word in constructor order, update the explanatory manifest text, and rerun the static check. Lead 18 remains `measured`; lead 72 is `blocked_infra`, not `dead_end`, so the closed-class demotion rule does not apply. Following review step 1, I stopped before fork reproduction or a new detection judgment. Prior review findings remain open pending a deployable manifest and independent current-artifact review.

# Review — 2026-11-11 00:51 UTC

Decision: **fix**
Run: eb077fe87c1c4e42bd1f417943fd66b9
KB: attempts:858
Next review: after a current-artifact profitable fork success, corrected mAERO evidence, and measured RPC economics (`next_review_at: null`).

Reviewed SHA-256: `bot.js` 79ec6ce46db42ee32cc0fb9cab566831995ad9e13fa6b79c8a915c0d9f9e4c61; `manifest.yaml` 34eb643b295c3632a095bdb6a821906c34a7adae3d93a91fe49365efcf7d1533; `contracts-src/MoonwellWhale.sol` cc82087353a0e7f5e77250330669d683faa304b2d5c5368e999ff4a8ebdda03f; `MoonwellWhale.json` 50eca77a1f79f3671c869effc2113ca3df09b7ba608421db8733f2aa9609c679.

1. **Profitable execution is still unproved on this artifact.** The corrected Solidity now binds `getAccountLiquidity` as `(error, liquidity, shortfall)` and has the expected USDC balance guard and wallet payout. But the earner's newest current-artifact fork runs in `scratch/mw-maero/sweep24.json`, `sweep25.json`, and `sweep26.json` all record `status: 0`, `NO_PROFIT`, and zero OWNER USDC payout (for example tx `0x6c2f69b761fee8aa54c21a293f59a0acdd0e8073b83162d0d1908ef17559747a`). The `fix_submitted` row attempts:857 also says the earlier route reached `SELL1_FAILED`. These are failure diagnostics, not a reproducible profitable success. Provide a fresh-deploy, current-artifact fork success with the bot's exact calldata, USDC credited to OWNER, and an independent `NO_PROFIT` guard revert. A historical proof from a different artifact does not close this criterion.
2. **The mAERO poll-catchable case remains unmeasured.** The prior independent fork read at block 55697122 returned `(0, 1.818657 USD liquidity, 0 shortfall)` for the holder captured at 55697123; the manifest still calls its middle word a shortfall. README's two older C-1 mAERO captures are an unsupported mAERO borrow (55297693) and dust (55381952). Recalculate reachable mAERO captures from the third tuple word and show one profitable, poll-catchable mAERO route on the current artifact. The manifest and README should stop counting 55697123 as a C-1 default.
3. **RPC spend lacks a profit case.** The 60-second cycle is estimated at 2.5M Base Alchemy CU/day from the archived same-shape bot's measured 10M/day at 15 seconds. `decisions/human/2026-11-11-moonwell-stopped.md` requires a rationale before promotion above 1M CU/day. With no reachable mAERO payout demonstrated, reduce the reads/cadence below that level or supply measured gas-net profit and a rationale through the live-operator for the human.

Detection: `manifest-check.py` PASS. The paper log had 474 advancing heartbeats, 31 seed scans, seven `opportunity` lines, and zero `simulate` lines through 00:50 UTC. The latest ledger liquidation, Base block 55828068 at 00:13:09 UTC (tx `0x04dfa747208381ad7c2e3631dadae3e42a7cf9173cd3c6c53c1291facbf7d980`), was a 1.834885 USDC repay with collateral `0x3bf93770f2d4a794c3d9ebefbaebae2a8f09a5e5`; the bot logged that holder as watch-only because it has no sale route. This does not establish a supported-route detection miss. `allowed_contracts: []`, `EXECUTOR_ADDR`, and the 18 USD Base gas-wallet cap satisfy the deployment and loss-field checks; 2.2M gas × 2 gwei = 0.0044 ETH, about $9.02 at the paper log's $2050.87/ETH. The watchdog supplies the cumulative live-loss stop. No fork success is accepted for promotion in this review.

# Review — 2026-11-10 23:18 UTC

Decision: **fix**
Run: 872998e4494e4998b2cd87944e631f82
KB: attempts:855
Next review: after executor, artifact, and evidence change (`next_review_at: null`).

Reviewed SHA-256: `bot.js` 7a61882ecb7748ad77fdeeed9ac93b92808e6b86714d49a47ea65af635b96077; `manifest.yaml` 34eb643b295c3632a095bdb6a821906c34a7adae3d93a91fe49365efcf7d1533; `contracts-src/MoonwellWhale.sol` de8e43b80ff2d02b7708b5a3f78f79cf9d02f9c85760926ebc4778131aaaa385; `MoonwellWhale.json` e57c8236f0941d536eef715253300010f0601e12b56af26fc2eec0ef12592031.

1. **Executor decodes `getAccountLiquidity` incorrectly and cannot reach the flash loan for an underwater holder.** The real tuple is `(error, liquidity, shortfall)`. `MoonwellWhale.sol:197-226` binds the first word to `liquidity` and the second to `shortfall`. My fresh deployment from the current artifact at Base fork reset 53265094, followed by two mined transactions, called the WADO capture holder `0x1a7c950a8fff56a7cc679b4cbd085f910c1e7234` with the bot's `maxRepay=400e6` and `minProfit=1e6`. Tx `0x05e900c0a9fda60530c87b7539cd63717fc22bd19bc3d41c4b592b44fc22de4d` reverted `NOT_LIQUIDATABLE` after 442,567 gas. The comptroller then returned `[0, 0, 593690901024254531217]`: error 0, liquidity 0, shortfall $593.69; the executor reads its middle zero as shortfall, computes repay zero, and reverts. `bot.js:780-790` already decodes `(error, liquidity, shortfall)` correctly. Correct the Solidity tuple, rebuild the artifact and paper runtime, then reproduce a profitable success paying USDC to OWNER and a `NO_PROFIT` revert from the current artifact. The independent reproduction script is `scratch/review-872998e4494e4998b2cd87944e631f82/repro.py` (its first assertion fails on the revert).
2. **The mAERO opportunity evidence needs correction and an executable payout.** My independent fork read at reset 55697122 for holder `0x48768c348525b888e53232bc2d020eba94741255` returned `[0, 1818657008811822247, 0]`: $1.818657 of *liquidity*, zero shortfall. The manifest, README, and `proof22.json` label that middle word as shortfall and call capture 55697123 poll catchable; it was healthy at C-1. The other two claimed C-1 mAERO opportunities are a borrow market the bot cannot repay (55297693) and dust (55381952). Recalculate the reachable mAERO capture count and gas net value using the third word, and demonstrate a natural, poll catchable mAERO route success before promoting this extension. `proof22.json` had no profitable success (`phaseB_success` reverted `LIQUIDATE_REJECTED`); paper logs through 23:10 UTC have 374 heartbeats, 3 `opportunity` lines, 727 watch only lines, and zero simulations or sends.
3. **RPC cost remains above the human review threshold.** The 60 second cycle is estimated at about 2.5M Base Alchemy CU per day from the archived bot's measured 10M/day at 15 seconds. That is above the 1M/day threshold in `decisions/human/2026-11-11-moonwell-stopped.md`, while no reachable mAERO profit has been shown. Reduce the read cost or provide measured gas net capture value sufficient to justify it through the authorized route before promotion.

Other checks: `manifest-check.py` PASS; source and artifact match the existing Forge build; fresh deployment includes P5 in `isPoolAllowed`; `liquidate()` transfers measured USDC profit to OWNER after its balance guard; `allowed_contracts: []` and `EXECUTOR_ADDR` are correct. The 18 USD Base wallet cap bounds the transaction's worst loss, and 2.2M gas × 2 gwei is 0.0044 ETH (~$8.99 at the 23:10 paper ETH price $2042). The watchdog supplies the live cumulative loss stop. No new tracked Moonwell liquidation appeared after the prior review; detection is not the reason for this fix.

# Review — 2026-11-10 21:42 UTC

Decision: **fix**
Run: a50ef67474174664bd70d0bb33eca025
Next review: after code and manifest change (`next_review_at: null`).

Reviewed SHA-256: `bot.js` 13e067ce4d72fe6e37a9c07817d6e5221c1f107cacfc1c4950d5330ba9f201b2; `manifest.yaml` 0b54833b05c86e77d34ecef848f1ae20d821c2c566952a0f6f486d2c86f19c08; `contracts-src/MoonwellWhale.sol` a700622f1e1565941b79cce7976dc95ea5458ff85ed4ea7e761515fcc14abc96; `MoonwellWhale.json` 0a85312eab4ef262fd3927d64b208415bf417f18cc02f533e4b704923439d243.

1. **mAERO live route cannot execute on a fresh gate deployment.** `MoonwellWhale.sol:137-145,237-239` allows only constructor pools P0–P4 or an owner-approved pool. The mAERO leg-one pool `0xdfe5f275020def30993f042174fc2d335678b626` is not a constructor arg; the earner approved it only on a fork instance (README step 3, fork tx `0x96fbc4983523f9e7632dc0c090f1878d19019e467e33632bfc63ae40e9881e8c`). `bot.js` has no `setPoolAllowed` send. On a fresh deployment its mAERO liquidation reverts `SELL_POOL`. Include this pool in the constructor whitelist or arrange an authorized, reviewed initialization. Reproduce the complete fresh-deploy path on the fork.
2. **Profit is retained in the executor.** `MoonwellWhale.sol:245-259` checks the executor's USDC increase and returns the amount but does not transfer it to the bot wallet. `bot.js` sends only `liquidate`, never `sweep` (`bot.js:740`). The watchdog and gate sweep count the bot wallet's native/USDC balances, so captured profit would remain outside accounting and stop sweep. Return USDC to OWNER inside the successful liquidation transaction, with the guard still covering the complete action; then reproduce success and guard revert on the current artifact.
3. **mAERO success proof is absent.** The manifest/README explicitly await a natural mAERO capture liquidatable at C-1. The known 323.81 USDC whale at block 55297682 was healthy at C-1 and is a same-block race (lead 72). Paper logs from 20:10–21:39 UTC have 105 heartbeats, 2 historical `opportunity` lines, 179 `opportunity_watch_only` lines, and zero `simulate` or paper send lines. The bot currently watches 37 candidates, with two underwater candidates excluded for unsupported collateral/borrow routes. Show a current-artifact fork success and NO_PROFIT guard revert, plus detection of a reachable awaited event.
4. **Live RPC cost exceeds the human threshold.** README estimates roughly 10M Alchemy CU/day at the current 15-second cadence, and roughly 2.5M/day even at 60 seconds. Decision `decisions/human/2026-11-11-moonwell-stopped.md` requires a rationale to the human before promoting any bot above 1M CU/day. The only known mAERO whale was a same-block race and no mAERO payout is reproduced; this does not yet justify the cost. Reduce reads/cadence and measure the revised daily cost and reachable net earnings, or submit the required rationale through a role authorized to write `inbox/human/`.

Other checks: `manifest-check.py` PASS; `allowed_contracts: []` is correct for an executor bot; `liquidate()` is owner-only and has `NO_PROFIT` on the executor USDC balance; signed gas fields are capped at 2.2M gas × 2 gwei and Base's native wallet cap is 18 USD. No fork reproduction was accepted as promotion evidence in this review because the fresh-deploy mAERO route and wallet payout are missing.
# Review — 2026-11-11 03:57 UTC

Decision: **demote**
Run: 698330627fc1473ebc3acbf4faac2a60
KB: attempts:872; leads:72
Next review: none (archived; `next_review_at: null`).

The current manifest passes `tools/manifest-check.py`, but the route is a measured same-block race under `decisions/human/2026-11-06-no-latency-race.md`. The corrected C-1 `getAccountLiquidity` probes found **0/8 mAERO captures with plausible >$1 bonus liquidatable before the winner's block** (`scratch/mw-maero/mine_probe.py`, attempts:859, README Poll-catchability section). The two earlier C-1 cases were an unsupported mAERO borrow and dust. The current-artifact fork success in attempts:864 was at C-1 plus six days, paid $0.136263 before gas, and cannot establish a catchable historical capture. The one measured poll-catchable mcbETH case was cash-starved and remains watch-only. No measured capture is both poll-catchable and executable. A further fork reproduction cannot change this class decision.

Live Base Alchemy use at the current 180-second cycle is estimated at **~0.83M CU/day**: 480 cycles/day times ~1,736 CU/cycle, extrapolated from the archived same-shape bot's measured ~10M CU/day at 15 seconds (README Decision condition 2). Even below the 1M CU/day human-review threshold, measured reachable profit is zero. Paper logs through 03:51 UTC show advancing 180-second heartbeats and `runtime_ok: true`, with only watch-only opportunities and no simulations. The latest tracked Base Moonwell liquidation was block 55866234; this does not supply a new supported mAERO capture. `leads:72` remains `blocked_infra`.

