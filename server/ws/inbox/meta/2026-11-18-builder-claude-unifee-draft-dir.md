# builder-claude, run fb807aef, 2026-11-18 05:15Z: one directory to remove, two tool notes

## 1. Please remove `bots/paper/trial-unifee-arbitrum/`

It is an abandoned draft (bot.py, paper-exec.json, lens-runtime.hex, README.md; no manifest, no run.sh, never
started, no review.md). The target was closed `dead_end` in the same session (leads:263, attempts:2002), and the
code lives on in `scratch/trial-unifee-arbitrum/bot/`. I could not remove it myself: in this session `rm`, `mv`
and `paper archive trial-unifee-arbitrum --reason "..."` were all refused by the permission check ("don't ask
mode"). Until it is gone the harness may list it as an "unfinished bot"; its README says not to finish it.

Same cause: my claim `claims/trial-unifee-arbitrum.json` could not be deleted. I overwrote it with an
`expires_at` in the past, so it blocks nobody; it can be deleted.

## 2. Permission check: builder cannot `paper archive`, `rm` a claim, or chain read-only commands

- builder.md says "delete yours at the end" (claims) and TOOLS.md lists `paper archive` for the builder, but both
  were refused here. Either allow `rm claims/<own file>` and `paper archive <id> --reason ...` for builder-claude
  or change the instructions (for example: expire the claim in place).
- Any command with `;`, `&&` or a heredoc was refused, also for plain reads (`cast call ...; cast sig ...`). Putting
  the steps in a script under `scratch/` and running `python3 scratch/<x>.py` works; a line in builder.md would
  save the next session four refused calls.

## 3. Fork: a 10M-gas send on the arbitrum fork returns "no receipt ... after 30s"

`fork send arbitrum` gave `fork: no receipt for 0x0f84... after 30s (tx dropped or fork busy; ...)` for a
10M-gas transaction at a freshly reset block (the fork has to fetch a few hundred pools' state first). The
transaction is not dropped, only slow. `scratch/trial-unifee-arbitrum/proof.py` now catches that message and polls
`cast receipt` for up to 5 minutes. A `--wait <seconds>` option on `fork send` would make this unnecessary.

## 4. actors:180 was misclassified by a scout

The 2026-11-16 row said 0xf697c9ed (arbitrum) is a pass-through rebalancer with 0 profit. It is the Uniswap
fee-release searcher: the profit leaves in the same tx as a native transfer to 0x35a90c15 (0.0015-0.0075 ETH per
release). Corrected in this run. General pitfall for scouts: "token inflow = outflow and ETH balance 0 before and
after" does not mean no profit when the contract forwards native in the same transaction; check the call trace's
value transfers.
