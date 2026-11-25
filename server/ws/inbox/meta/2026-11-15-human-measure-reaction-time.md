# Measure the farm's reaction time R; it is still the 3 s placeholder (human, 2026-11-15)

Decision 2026-11-14-race-rule-seconds draws the speed line from R, the farm's reaction time on each chain, and says "3 s on every chain until measured". Nobody has measured it. 29 leads sit in `blocked_infra`, many of them cut by that placeholder. If the real R is shorter, some of them count again; if it is longer, we are counting cases we cannot take. Either way I want the number.

## What I ask

Put this on the board as a measurement request for the earner's measure lane. It does not jump the queue: the Relay cross-chain request (decision 2026-11-15-cross-chain-gap-relay) comes first, and this one fits in the hours that request spends waiting for its 24 h series.

Measure R in two parts, per chain, and write both down separately:

1. **Detection**: from the timestamp of the block that carries an event to the moment a process on this server has it in hand.
   - Through the feed (`/logs`): subscribe a paper process to one modest event per chain (a few per hour, not a busy one), log arrival time against the block timestamp for at least 30 events, report median and 90th percentile.
   - Through polling: the same for a relay poll at the interval our bots really use.
2. **Send to inclusion**: from the bot handing a transaction to the signer to the timestamp of the block that includes it.
   - Use what already happened first, no new transactions: the live bots' own logs (`bots/live/<id>/logs/`) against the chain for every send they have made, and the gate's deploy and fund transactions in `gate status` / the brief's gate log against their blocks. Say how many samples each chain has.
   - Where a chain has no sample, do not send anything to get one. Write "no sample" and give an estimate (detection + one block time) marked as an estimate.

R for a chain = detection (90th percentile, through the feed) + send to inclusion (median, or the estimate). Record the table in wiki `infra/reaction-time.md` with the date, the sample counts and which numbers are estimates.

## Then

- Where the measured R differs from 3 s by more than a second, list the `blocked_infra` leads closed for speed on that chain whose verdict would change (id, chain, old line, new line). Do not reopen them yourself: put the list in inbox/human.
- Until a chain has a measured R, 3 s stays.
- No change to any limit, and no new send path: this is a measurement.

## What I do not want

- Real transactions sent only to take a timing.
- A subscription to a busy event (the feed rules in TOOLS.md stand).
- A re-walk of the closed leads before the table exists.
