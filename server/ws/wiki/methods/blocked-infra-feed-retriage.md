---
type: method
chains: [ethereum, base, arbitrum, hyperevm]
protocols: [morpho_blue, aave_v3, compound_v3, aave_v4, moonwell]
author: meta/opus
updated: 2026-11-15
---
> **Closed** by decision 2026-11-15-widen-beyond-liquidations: re-triage is no longer "no target left" work for earners; the content below is kept for reference (the race-rule counting in step 2 still applies wherever race-rule-seconds is used).

# Re-triage of blocked_infra leads with the feed (decision 2026-11-13-blocked-infra-feed-retriage)

**Conclusion first:** while no fix bot, unfinished bot or unmeasured lead exists, an earner session takes the next 2-4 leads in the order below, classifies why each one was blocked, recounts the speed-blocked ones by the farm's reaction time (decision 2026-11-14-race-rule-seconds, which replaced the block counts on 11-14), and writes one `attempts` row per lead. Source: `decisions/human/2026-11-13-blocked-infra-feed-retriage.md` (Japanese; it wins if this page disagrees, except where race-rule-seconds replaced it).

## Where the work stands

Before you start, see which leads are done: `kb query "SELECT id, target, outcome FROM attempts WHERE target LIKE '%retriage%' ORDER BY id DESC LIMIT 50"`. Put `retriage lead <id>` at the start of every attempts `target` so this query finds it. Take the next lead nobody has done. Claim it (`claims/retriage-lead-<id>.json`) so parallel sessions don't take the same one.

## Order (fixed by the human on 11-13, not by id)

1. **Lead 14** (ethereum morpho, `dead_end`, included anyway): the ~3,111 USD gross miss on 11-12 was taken one block after the price update. Recount 30 days of the target markets' liquidations by the counting rule below.
2. **Ethereum:** 17 (aave), 5 (compound v3: its record says "+0 / +1 block"; give the +1 count and gross), 33, 35, 67.
3. **Held by the 2026-11-06 decision, timing never measured:** 1, 2, 6, 7, 9, 10, 12, 15, 21. Also for 13 and 10 (the "interest carries the position over the boundary between price updates" type): check whether the crossing time can be computed in advance. If it can, it is not a speed race (taker type T, `methods/taker-types.md`).
4. **The rest of the speed-blocked leads:** 31, 41, 42, 44, 57, 72, 147, 157.
5. **Not speed** (18, 73, 91, 94, 103, 117, 129, 145): one attempts row with the class only.

## Step 1: classify (one attempts row per lead)

- **(a) speed**: the time from trigger (price update, auction start, event) to capture was too short
- **(b) permission**: the entry is restricted to certain senders (auctioneer, keeper registration...)
- **(c) capital**: too small at 400 USD, or principal cannot be sourced
- **(d) tooling**: no trace, unreadable contract, etc.
- **(e) other**: one sentence

Only (a) can change with the feed. For (b)-(e), record the class and leave the lead `blocked_infra`.

## Step 2: recount (a) leads by reaction time

For every past occurrence in the ledger (at most 30 days), from block timestamps (decision 2026-11-14-race-rule-seconds): T = timestamp of the block where it became takeable; R = the farm's reaction time on that chain (3 s until `infra/reaction-time.md` has a measured value); L = the first block with timestamp >= T + R. Where blocks share a timestamp, use block count x measured block time.

- **out** (taken in a block before L): speed race, out of scope
- **trial only** (taken in L, or less than R seconds after L): a feed bot may try it; never counted in EV
- **counted** (taken at least R seconds after L): counts in EV for a feed bot

With R = 3 s this equals the old block rule on ethereum (same block out, next block trial, 2+ blocks counted). On Base (0.2 s blocks): under 3 s out, 3-6 s trial, over 6 s counted. Recounts made by block count on Base or elysium before 11-14 (attempts 1059-1071, lead 157 and others) are reclassified from their recorded timestamps. Also give each case its taker type (`methods/taker-types.md`); for Base price-triggered liquidations check SVR / Atlas (type O = not copyable).

Also name the feed `/logs` filter (address + topic0) the bot would wait on, and price it: events/day x bytes of one real log x 0.04 CU (`infra/feed.md`). A lead whose only possible trigger is a busy event (Transfer, big-pool Swap) stays out of scope even with the feed.

Write the result into the lead's `next_steps` as: `out n / trial n / counted n (R=<s>), gross total, feed CU/day`. Then:

- counted occurrences with sum(gross − gas) > the CU cost (1M CU ≈ 0.53 USD) → set the lead `unmeasured` and build a feed bot
- only trial occurrences, but one with gross > 50 USD → set `unmeasured`, a candidate for the trial below
- neither → stays `blocked_infra`

## Step 3: trial-only bot (exception to promote rule 6 of decision 2026-11-12)

A bot that targets only trial occurrences has zero counted EV, so it would normally fail the "EV must exceed CU cost" rule. To measure whether we can win them, the reviewer may promote it if **all** hold:

- waits on the feed `/logs`; confirmation poll every ≥5 minutes; total ≤50,000 CU/day
- `capital_usd` ≤ 20
- in the last 30 days at least one trial occurrence with gross > 50 USD
- every other check unchanged: fork success and revert reproduced, profit returned to the wallet in the same tx, send condition "expected gross > gas cap"
- at most 2 such bots live at the same time

The reviewer writes "next-block trial" in `review.md`. If after 14 days live it has 0 sends, or every send reverted, an earner or meta recommends its stop via `inbox/meta/` → `inbox/human/`.

## Step 4: report

When every lead is classified, an earner writes the table (lead id, class, (a) out/trial/counted breakdown, result) to `inbox/meta/`; meta translates it into Japanese for `inbox/human/`.
