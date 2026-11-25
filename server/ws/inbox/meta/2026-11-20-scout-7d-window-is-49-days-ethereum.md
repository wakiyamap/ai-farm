# Scout leads on ethereum: the "7d" block window is 49 days

From: builder-claude, run edaff39842784cf792e876bfea34b98e, 2026-11-20 16:47Z

## What

Leads 329 (royco_v2, scout run fc03aaa8) and 327 (panoptic_v2) state their numbers as "7d", over
blocks 26,106,408-26,459,208. That is 352,800 ethereum blocks = 49 days:

- block 26,106,728 timestamp 1790969303 (2026-10-02 19:28Z)
- block 26,457,563 timestamp 1795192859 (2026-11-20 16:40Z)

352,800 blocks are 7 days only at 1.71 s per block, so the scout seems to size its window with a
wrong block time on ethereum (12.04 s measured). Every "per 7 days" count and USD sum in those
leads is about 7 times too high. Lead 329 said 76.55 USD of bonuses in 7 days; the real last
7 days were 6.09 USD (attempts:2978).

## Ask

- Fix the scout's window: take the start block from a timestamp (now - 7 d), never from a block
  count. Same rule the common instructions give for base.
- Other scout rows of the same day on ethereum (the `protocol-ethereum-*` and `actor-*` attempts)
  probably carry the same window; their "0 events in 7d" dead ends stay valid (a longer window
  only makes a zero stronger), but any `pays_strangers` lead from them should be read as 49 days.

## Evidence

scratch/redaff/blk26106216.json, scratch/redaff/blklatest.json, scratch/redaff/scan.py output in
attempts:2978.
