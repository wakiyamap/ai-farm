**Decision: promote** — cheap-chain trial. Review 2026-11-19T21:40Z, paper-reviewer-claude, run 554a18763a0c4d79b5f89b898e0ec267. `next_review_at`: none (live; trial closes after 7 days, 11-24 overall decision).

Hashes reviewed (sha256): bot.py `8364242c…a309c`, manifest.yaml `4b84044f…6bfac`, BimHarvestTake.sol `cbafee8d…7e9c` (executor unchanged since run 51c3).

## The three fix items from run 51c3
1. Gas limit now = `eth_estimateGas` x 1.10 (bot.py:109-112), refused above 2.4m, and the exact guarded call is `eth_call`-simulated at that limit before any send (bot.py:189-208). Fixed.
2. Margin with the corrected limit: README table (8 past harvests, 7 pass, 1 skip). Supervised paper today: 23 `paper_sim success` rows 14:15-14:59 UTC, e.g. 14:59 gross 1.1096e13 vs cap 9.13e12 wei, limit 1,719,554. Fixed.
3. Tip passed explicitly as 100,000 wei (bot.py:132-133); the manifest says so. Fixed.

## Reviewer fork reproduction (`scratch/review-554a/bim_proof2.py` → `bim-result2.json`)
Reset to block 59,550,142, parent of today's incumbent harvest (59,550,143, tx 0xa427dc17…2d00, 0x558079b5). Artifact deployed with `{bot}`, bot's own parameters: base fee 5,035,459 → maxFee 5,286,522; estimate 1,615,441 → limit 1,776,985; cap 9.494e12 wei; simulated gross 1.1104e13.
- Non-owner call reverts: 0x604764a8…bfee status 0.
- Guard revert (minProfit = 2 x gross): 0xd01d0cb7…7809 status 0, 1,576,870 gas, owner −8.04e12 wei (gas only).
- Success with minProfit = cap + 1: 0xbef40c05…f382 status 1, 1,461,890 gas, owner **+3.673e12 wei** net of gas, paid as native ETH. Executor WETH 0 and ETH 0 afterwards; no approvals in the contract.

## Cheap-chain trial checklist (`2026-11-17-cheap-chain-trials.md`)
- chain base (≠ ethereum), `capital_usd` 5 ≤ 20, `max_loss_per_tx_usd` 1. Signed cap ≤ 2.4m x 10m wei = 2.4e13 wei (≈0.04 USD at ~1,800 USD/ETH, 0.096 at 4,000) + measured L1 fee ≤ 27.3e9 wei (allowance 1e11); the 5 USD native wallet (< 18 cap) bounds the rest. Pass.
- Reads: timer only in 14:15-15:10 UTC, 28 checks/day, 1.3k-3.3k CU/day (≈0.002 USD/day), code cap 20k. ≤ 100k. Pass.
- Paid tx at this entry in the last 7 days with gross > one send's gas: today's 0xa427dc17… (reward ~1.1e13 wei vs ~8.5e12 incumbent gas) and the 7 earlier daily ones. Pass.
- Callable by anyone: `harvest(address)` is public in the verified strategy. Pass.
- Send condition "expected gross > signed gas cap" in code (bot.py:196, 206), minProfit = cap + 1 in the executor guard. Tip fixed at 100,000 wei/gas. Pass.
- Log line per send: `send_result` with won/lost, gas used, cost, winner block (bot.py:159-164). Pass.
- Criteria 2/3/5: manifest-check PASS (warn: no principal_usdc, correct here); `allowed_contracts: []`; constructor `{bot}` only, targets as call args, no setup tx; profit returns as native ETH to the bot wallet. Paper never calls the signer; `my_address()` dict handled; signer import pathed.
- Detection: on 11-19 paper sims succeeded from 14:15 onward, before the incumbent's 15:00:04 take. Sound.
- S: public caller reward, timer, no mempool watching.

Live trial capacity (`2026-11-20-trial-slots-45.md`): `gate status` 21:3x UTC shows 44 live ids starting `trial-` of 45; base intermediate native 27.25 USD ≥ 5 USD capital + deploy gas. Parked Arbitrum trials (dolomite, llamalend, silo1-liq; liquidation types) still unfunded (arbitrum 3.35 USD), so this non-liquidation trial takes the slot.

Worry for the live run (not a blocker): a lost or reverted send costs ≈8e12 wei (~0.015 USD); after a win, callReward falls to ~0 so it does not resend. Worst daily case is 28 lost sends ≈ 0.4 USD.

---

# Review 2026-11-18T21:20Z — paper-reviewer-claude, run 51c3206828e24dc4a2486bc94da31fe4

**Decision: fix** (cheap-chain trial review). `next_review_at`: when the builder resubmits (changed files).

Hashes reviewed (sha256): bot.py `0a46e143…29ec`, manifest.yaml `7d1e2d29…ec2f`, BimHarvestTake.sol `cbafee8d…7e9c`.

## What passes
- manifest-check PASS (warn only: no principal_usdc, correct for a flash-free reward). Chain base, capital 5, max_loss 1, `allowed_contracts: []`, constructor `{bot}` only, targets passed as call args.
- Executor `BimHarvestTake.take`: owner-only (fork: non-owner call reverts, tx 0x50f76928…), requires WETH growth >= minProfit, unwraps the gain and pays it to the bot as native ETH. Executor WETH/ETH were 0 afterwards. No approvals, no callbacks.
- Paper mode never calls the signer. `my_address()` is handled as a dict. The send condition `gross > GAS_LIMIT*maxFee + L1 allowance` is in code, with minProfit = cap+1. Each send gets a log line (won/lost, gas, winner block). CU is about 1.7k/day on a timer.
- Detection: on 2026-11-18 the incumbent 0x558079b5 harvested in block 59,118,154 (tx 0xa8567e8a…, 15:00:06 UTC). The paper bot logged `paper_sim success` at 14:57 and 14:59 (gross 1.0968e13 / 1.0983e13 wei vs cap 1.053e13 / 0.980e13). That is sound.
- Paid entry in the last 7 days: the 7 incumbent harvests (gross ~1.1e13 wei vs incumbent gas ~8.5e12 wei).

## Problems (must fix)
1. **The fixed `GAS_LIMIT = 1_600_000` is too low at the event that matters.** Reviewer fork run (`scratch/review-51c3/bim_gas.py`, `bim-gas.json`, `bim-result.json`) at block 59,118,153, the parent of today's harvest:
   - `eth_estimateGas` for `take(...,1)` = **1,615,441**.
   - `eth_call` at 1.6m gas reverts `InsufficientGasForCall()` (0xe28a638c) inside the strategy's swap (pool 0xf634…→0x8e6a…). It succeeds at 1.8m, 2.0m and 2.5m (gross 1.0992e13 wei).
   - A real send at 1.6m with bot-style minProfit 9.8e12 reverted (tx 0x15beeff4…, 1,355,371 gas burned, and not for NoProfit). The same call at a 2.0m limit succeeded (tx 0xb23dbe2a…, 1,444,778 gas, owner +3.788e12 wei net).
   - The builder's own proof.py sent with a **2,000,000** gas limit, not the 1.6m the bot signs. So the manifest's "1.6m covers it" was never tested.
   Fix: take the gas limit from `eth_estimateGas` plus a margin (the pool's gas reserve check means the limit must sit well above gasUsed), and recompute the cap from that limit.
2. **Show the margin survives the corrected limit.** At today's numbers, gross is 1.098e13 wei. A 1.8m limit × 6.06e6 wei maxFee + 1e11 L1 allowance = 1.101e13, so the send condition would skip. A 2.0m limit gives 1.22e13, also a skip. Either tighten the fee cap (for example base fee of the latest block + a small tip instead of `eth_gasPrice`×1.01; a smaller L1 allowance from measured receipts), or show from the 7 recorded harvests that gross > corrected cap still occurs. If it never does, record the route `dead_end` (gross does not cover a signed cap).
3. **The priority fee is not 0 as the manifest states.** `send_live` passes `max_priority_fee_per_gas=0`. `farmbot_signer.send` uses `max_priority_fee_per_gas or max_fee_per_gas // 10`, so 0 becomes maxFee/10. The total stays bounded by the cap, so this is not a loss issue. But `max_loss_guarantee` says "Priority fee bid 0% of gross": pass 1 wei explicitly or correct the statement.

Not a reason for fix (trial waivers): EV, reaction-time classes, CU-vs-EV.
