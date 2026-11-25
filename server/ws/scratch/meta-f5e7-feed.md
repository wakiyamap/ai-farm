---
type: infra
chains: [any]
protocols: []
---
# farm-feed: wait for an event instead of polling (`/logs`)

**Conclusion.** `http://127.0.0.1:8546` (service `farm-feed`, phase 11a, decision `decisions/human/2026-11-13-next-block-feed.md`) holds one Alchemy WebSocket subscription per filter and hands events to local callers as HTTP long-polls. Read-only. Use `/logs` to wait for one specific event; `/head` (every block) is **switched off** (400 on every chain) because one ethereum head is ~3,855 bytes = 154 CU, ~1.1M CU/day, dearer than polling. Measured delivery: a log arrives ~1.0 s after its block timestamp (attempts:1029), so a feed bot can act in the next block. **At most 8 filters per chain** (all bots together): check `/health` before you build a feed bot (section Cost).

## Wait for an event

    GET /logs/<chain>?address=<a>[,<a>...]&topic0=<event hash>[&topic1=..]&timeout=<s>
    -> {"cursor":"1731450123.0","logs":[]}         first call: subscribed from now on
    GET /logs/<chain>?address=...&topic0=...&after=<cursor>&timeout=<s>
    -> {"cursor":"1731450123.2","logs":[{..eth_getLogs shape..}]}
    -> {"timeout":true,"cursor":"<same>","logs":[]}
    -> {"gap":true,"cursor":"<new>","logs":[]}     stream interrupted

- `address` and `topic0` are required (up to 20 addresses, up to 4 values per topic); topic-only → 400 `address is required`. Send exactly the same address list and topics on every call: that identifies the filter.
- Logs have the `eth_getLogs` keys plus `blockTimestamp` (no `timestamp` key; a recorder reading `timestamp` dies on KeyError, attempts:1029). `blockTimestamp` vs arrival time gives the eligibility-to-capture column without another read.
- A subscription is released 180 s after its last call, so a stopped bot stops costing.

## Rules for a bot that uses the feed (reviewer checks these in code)

- `gap: true`, HTTP 429 / 503 or a connection error = "you may have missed something": read the current state through the relay once (the read the polling version did), then continue with the cursor you were given. Silence is never proof that nothing happened. Missing re-read = reviewer `fix`.
- Keep a slow safety poll through the relay every 5-10 min next to the feed (event cadence is lumpy: 0 events in 35 min, then one 170 s after re-subscribing, attempts:1029).
- The feed says *when* to look. Act on state read through the relay and simulated (`eth_call`) right before sending.
- `"removed": true` = reorg: re-read state instead of trusting the earlier log.
- Never subscribe to busy events (token `Transfer`, `Swap` on big pools, oracle updates you don't need): a ~4,300/day Transfer filter would eat ~430k CU, 61 % of the feed's daily budget. Reviewer `fix`.
- Need "every block"? Poll `eth_blockNumber` through the relay (10 CU), not `/head`.

## Cost and limits (same Alchemy bill)

- 0.04 CU per delivered byte; one 886-byte single-log response ≈ 35 CU. Measured delivery + maintenance is O(10-100) CU per event, plus ~3-4 CU/min per live subscription even with no events (attempts:1029).
- Per-filter cap 150,000 CU per UTC day (then 429 until next day); whole feed 700,000 CU/day (then 429 everywhere: bots poll as before).
- **At most 8 log filters per chain**, all bots together. Filter number 9 gets `429 {"error":"base already has 8 log filters; share one filter (several addresses) or poll the relay"}`. Base was full on 2026-11-19 07:50Z (with two overlapping pairs of filters from different bots; builder-claude 93ed4a84, inbox/meta/2026-11-19-base-feed-filters-full.md). If the chain is full, the new bot polls the relay on a timer and states its CU/day in the README; its code treats this 429 like any other (re-read, keep going). A slot frees 180 s after a bot stops calling.
- README CU estimate: events/day x bytes measured on a real log x 0.04, plus the safety poll's relay reads.
- `curl -s http://127.0.0.1:8546/health` shows `cu_today` and subscriptions per chain and per filter. On 11-12 the per-filter counter stayed 0 while the chain-level one moved: use the **chain-level** number. Daily CU reports add the feed's `cu_today` to the relay's number (the relay dashboard excludes it).

## Counting rule (decision 2026-11-13, blocks from trigger to capture)

- 0 blocks (same block as price update / auction start): latency race, out of scope, `blocked_infra`.
- 1 block: a feed bot may try it, but it is **not counted in expected revenue**; list it in the README table, add live hit/miss counts when they exist.
- ≥2 blocks: counts for a feed bot. A polling bot still counts only occurrences slower than poll interval + send-to-inclusion.
- Unchanged: send path (signer, executor that reverts without profit), L, 400 USD per bot; no mempool watching, bundles or builder submission.
- Superseded for timing by `2026-11-14-race-rule-seconds.md` (seconds, not blocks; common instructions principle 2).

## Example price

franken-dutch-ethereum waits for one `ChallengeStarted` (~1 per 43 days); its log is ~760 bytes = ~30 CU per event, i.e. under 1 CU/day plus the safety poll, against ~0.32M CU/day for its 60 s poll (inbox/meta/2026-11-12-waiting-watchers-feed-cheaper.md). State-read legs (gearbox's 21 credit-account re-reads) cannot be replaced by a feed.

Probe script for a first feed bot: `scratch/feed-probe/feed_probe.py` (run 35731076).

`/head` reference, for the day it is re-enabled (`heads_offered_on` in `/health` is empty today): `GET /head/<chain>?after=<last handled block>&timeout=<s, max 60>` → block header JSON with `age_ms`, or `{"timeout":true,"number":N}`.
