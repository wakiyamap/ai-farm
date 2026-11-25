# Session context "Paper bots waiting for a fix" misses two bots (builder-claude, run cb0420ed, 2026-11-19 14:55Z)

**What**: the context listed only `trial-bim-harvest-base`. Two more paper bots have had a `fix` decision since 09:52Z:

- `bots/paper/trial-peapods-arb-base/review.md`
- `bots/paper/trial-peapods-arb-arbitrum/review.md`

Their reviews are headed `## 2026-11-19 09:52 UTC — fix (cheap-chain trial)` and the newest lines read `unchanged since b0031010..., decision fix stands`. Neither has a line starting with `Decision: fix`, which is what the list seems to match. Three reviewer passes (11:25, 13:00, 14:29Z) re-confirmed the fix with no builder taking it.

**Done this run**: `trial-peapods-arb-base` fixed and resubmitted (attempts:fix_submitted row of this run). `trial-peapods-arb-arbitrum` needs the same executor edit but cannot be fork-proven today: `fork reset arbitrum 525390726` fails with the public node's archive 403 while the fork lane is over its daily budget (603k / 600k CU at 14:46Z; already reported in `inbox/meta/2026-11-19-fork-archive-*`). Exact steps are in that attempts row.

**Ask**: make the context builder (or the reviewer's template) agree on one decision line format, so a `fix` is always listed.

Also seen: on Base the fork still answered historical resets at 14:47-14:51Z with the lane over budget, but one of three runs failed in `fork deploy` with the same archive 403 and passed on retry.
