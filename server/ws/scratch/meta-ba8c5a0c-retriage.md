---
type: method
chains: [ethereum, base, arbitrum, hyperevm]
protocols: [morpho_blue, aave_v3, compound_v3, aave_v4, moonwell]
---
# Re-triage of blocked_infra leads with the feed (decision 2026-11-13-blocked-infra-feed-retriage)

**Conclusion first:** while no fix bot, unfinished bot or unmeasured lead exists, an earner session takes the next 2-4 leads in the order below, classifies why each one was blocked, recounts the speed-blocked ones by blocks from trigger to capture, and writes one `attempts` row per lead. Source: `decisions/human/2026-11-13-blocked-infra-feed-retriage.md` (Japanese; it wins if this page disagrees).

## Where the work stands

Before you start, see which leads are done: `kb query "SELECT id, target, outcome FROM attempts WHERE target LIKE '%retriage%' ORDER BY id DESC LIMIT 50"`. Put `retriage lead <id>` at the start of every attempts `target` so this query finds it. Take the next lead nobody has done. Claim it (`claims/retriage-lead-<id>.json`) so parallel sessions don't take the same one.

## Order (fixed by the human on 11-13, not by id)

1. **Lead 14** (ethereum morpho, `dead_end`, included anyway): the ~3,111 USD gross miss on 11-12 was taken one block after the price update. Recount 30 days of the target markets' liquidations by the counting rule below.
2. **Ethereum:** 17 (aave), 5 (compound v3: its record says "+0 / +1 block"; give the +1 count and gross), 33, 35, 67.
3. **Held by the 2026-11-06 decision, block count never measured:** 1, 2, 6, 7, 9, 10, 12, 15, 21. Also for 13 and 10 (the "interest carries the position over the boundary between price updates" type): check whether the crossing time can be computed in advance. If it can, it is not a speed race.
4. **The rest of the speed-blocked leads:** 31, 41, 42, 44, 57, 72, 147, 157.
5. **Not speed** (18, 73, 91, 94, 103, 117, 129, 145): one attempts row with the class only.

## Step 1: classify (one attempts row per lead)

- **(a) speed**: the time from trigger (price update, auction start, event) to capture was too short
- **(b) permission**: the entry is restricted to certain senders (auctioneer, keeper registration...)
- **(c) capital**: too small at 400 USD, or principal cannot be sourced
- **(d) tooling**: no trace, unreadable contract, etc.
- **(e) other**: one sentence

Only (a) can change with the feed. For (b)-(e), record the class and leave the lead `blocked_infra`.

## Step 2: recount (a) leads by blocks

For every past occurrence in the ledger (at most 30 days): blocks from the trigger block to the capture block.

- **0 blocks** (same block): out of scope, as before
- **1 block**: a feed bot may try it; never counted in EV
- **≥2 blocks**: counts in EV for a feed bot

Also name the feed `/logs` filter (address + topic0) the bot would wait on, and price it: events/day x bytes of one real log x 0.04 CU (`infra/feed.md`). A lead whose only possible trigger is a busy event (Transfer, big-pool Swap) stays out of scope even with the feed.

**Base (~2 s/block) and arbitrum (~0.25 s/block):** write seconds as well as blocks, and don't count occurrences faster than the farm's real feed-notification-to-inclusion time (measure it and write the number). For base liquidations triggered by price updates, also check whether they are sold through an SVR auction (OEV recapture), which makes them unavailable.

Write the result into the lead's `next_steps` as: `0-block n / 1-block n / >=2-block n, gross total, feed CU/day`. Then:

- ≥2-block occurrences with sum(gross − gas) > the CU cost (1M CU ≈ 0.53 USD) → set the lead `unmeasured` and build a feed bot
- only 1-block occurrences, but one with gross > 50 USD → set `unmeasured`, a candidate for the next-block trial below
- neither → stays `blocked_infra`

## Step 3: next-block trial (exception to promote rule 6 of decision 2026-11-12)

A bot that targets only 1-block occurrences has zero counted EV, so it would normally fail the "EV must exceed CU cost" rule. To measure whether we can win them, the reviewer may promote it if **all** hold:

- waits on the feed `/logs`; confirmation poll every ≥5 minutes; total ≤50,000 CU/day
- `capital_usd` ≤ 20
- in the last 30 days at least one 1-block occurrence with gross > 50 USD
- every other check unchanged: fork success and revert reproduced, profit returned to the wallet in the same tx, send condition "expected gross > gas cap"
- at most 2 such bots live at the same time

The reviewer writes "next-block trial" in `review.md`. If after 14 days live it has 0 sends, or every send reverted, an earner or meta recommends its stop via `inbox/meta/` → `inbox/human/`.

## Step 4: report

When every lead is classified, an earner writes the table (lead id, class, (a) block breakdown, result) to `inbox/meta/`; meta translates it into Japanese for `inbox/human/`.
