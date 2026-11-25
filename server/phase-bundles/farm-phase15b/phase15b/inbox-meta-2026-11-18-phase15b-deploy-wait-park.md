# phase 15b: executor deployment waits for the bot's funds; approved trials are parked off paper (human, 2026-11-18)

Applied by the human. Two changes:

1. **gate-ctl `send_deploy()`** (executor deployment, in `promote` and `deploy`). On 2026-11-17 20:21Z the promote of trial-aave-optimism funded the bot wallet and saw the funding receipt (9f), but the node that took the deployment still read the old balance: `insufficient funds ... have 0`. The gate now waits until the bot wallet reads at least the deployment's worst-case gas, and resends the same signed bytes while the node answers "insufficient funds" (the tx was not accepted, so the nonce is unused). After one minute it gives up with nothing sent from the bot key: gate.log `deploy_executor_not_sent`, exit 2, and the bot is a partial promotion as before (`gate-ctl deploy <id>` finishes it; report it in `inbox/human/` as before). Any other send error is raised as before. Please add the pitfall to the wiki (relay-reference or pitfalls page).
2. **Parking approved trials**: `decisions/human/2026-11-18-park-approved-trials.md`. A trial bot that passed technical review and only waits for a live trial slot is `paper stop`ped by the reviewer, keeps its directory and review.md, does not count against the 12 paper slots, and is promoted from there when a slot opens (oldest approval first). Please fold this into:
   - `paper-reviewer.md` (Capacity section, and the "wait" decision wording `wait (parked: approved, waiting for a live trial slot)`)
   - `builder.md` (do not `paper start` a parked bot; a free paper slot is for new bots; trial-euler-base is already approved and parked)
   - `TOOLS.md` (paper runner row: paper-reviewer uses `archive` and `stop`)
   run-role now allows `Bash(paper stop *)` for paper-reviewer-claude; the codex reviewer ignores that list.
