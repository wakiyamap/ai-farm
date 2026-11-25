# Race rule: by farm reaction time, not by block count (human, 2026-11-14)

Replaces the block thresholds of 2026-11-13-next-block-feed. The question is how fast farm can react, and that is seconds: Base has 0.2 s blocks since 2026-11-05, elysium 0.1-0.2 s.

## Definitions
- T = timestamp of the block in which the case became takeable.
- R = farm reaction time on that chain: seconds from T until a farm transaction can be included (feed notice + reads + signing + sending). Use R = 3 s on every chain until it is measured there.
- L = the first block whose timestamp is at least T + R. This is the earliest block a farm transaction can be in.
- Where blocks share a timestamp, use block count x measured block time.

## Classes (for a bot that waits on the feed)
- Out (speed race, blocked_infra): the winner was in a block before L.
- Trial only: the winner was in L, or in a block less than R seconds after L. Farm arrives, but it is a race for position in the same block. Not counted in EV; the next-block trial exception of 2026-11-13-blocked-infra-feed-retriage applies.
- Counted: the winner was in a block at least R seconds after L.
- Polling bots: as before, with R = poll interval + inclusion time.
- With R = 3 s this is unchanged on ethereum (same block out, next block trial only, 2 blocks or more counted). On Base: under 3 s out, 3 to 6 s trial only, more than 6 s counted.

## Work
- Earner: measure R per chain where farm has or plans a bot (feed notice delay, read time, send time; at least 20 samples) and record it in wiki infra/reaction-time.md with the date. Re-measure when the send path changes.
- Recount: Base and elysium cases that were classed by block count (attempts 1059-1071, lead 157 and others) get their class again by this rule, from recorded timestamps; no new chain reads unless a timestamp is missing.

Unchanged: census thresholds (slow = median 10 s or more, fast = under 3 s), EV per case = gross - gas, EV must exceed the CU cost.
Meta: replace the old wording in the role files, do not add to it; the earner prompt is 126 bytes below the 56,000 warning.
