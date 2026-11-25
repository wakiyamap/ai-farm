# Phase 11a (human, 2026-11-13): the feed - wait for the chain instead of polling it

New service `farm-feed` on `http://127.0.0.1:8546` (earner, paper bots, live bots and harness roles
can reach it). It holds one WebSocket subscription per need at Alchemy and hands the events to local
callers as HTTP long-polls. It is read-only. Decision: decisions/human/2026-11-13-next-block-feed.md.

Please do three things, within the prompt size limit (56,000 bytes):

1. Create wiki `infra/feed.md` with the reference below (common.md points there).
2. TOOLS.md: one row only, e.g. "feed: `curl -s 'http://127.0.0.1:8546/head/ethereum?after=<n>'` /
   `/logs/<chain>?address=&topic0=&after=` - wait for a block or an event instead of sleeping; details
   in wiki infra/feed.md".
3. earner.md / paper-reviewer.md: the counting rule of the decision (items 2 and 3).

## Reference for wiki infra/feed.md

**Wait for the next block** (only on chains listed in `heads_offered_on` of `/health`; today: ethereum)

    GET /head/<chain>?after=<last block number you handled>&timeout=<seconds, max 60>
    -> {"chain":"ethereum","number":21000001,"hash":"0x..","parentHash":"0x..","timestamp":1731450000,
        "baseFeePerGas":"0x..","age_ms":35,"epoch":1731450123}
    -> {"timeout":true,"number":21000000}          nothing new yet: call again

Without `after` it returns the newest head it has. Loop: call with `after=<number>`; on a head, read
what you need through the relay at `latest` and act; repeat.

**Wait for an event**

    GET /logs/<chain>?address=<a>[,<a>...]&topic0=<event hash>[&topic1=..]&timeout=<s>
    -> {"cursor":"1731450123.0","logs":[]}         first call: subscribed from now on
    GET /logs/<chain>?address=...&topic0=...&after=<cursor>&timeout=<s>
    -> {"cursor":"1731450123.2","logs":[{..eth_getLogs shape..},{..}]}
    -> {"timeout":true,"cursor":"<same>","logs":[]}
    -> {"gap":true,"cursor":"<new>","logs":[]}     the stream was interrupted

`address` and `topic0` are required (up to 20 addresses, up to 4 values per topic). Use exactly the
same address list and topics on every call: that is what identifies the filter.

**Rules for a bot that uses the feed**

- `gap: true`, any HTTP 429 / 503, or a connection error means "you may have missed something":
  read the current state through the relay once (the same read the polling version did), then
  continue with the cursor you were given. Never treat silence as proof that nothing happened.
- Keep a slow safety poll through the relay (every 5-10 minutes) next to the feed.
- The feed says *when* to look. What you act on is still the state you read through the relay and
  simulate (`eth_call`) right before sending.
- A log can arrive with `"removed": true` (reorg). Re-read state instead of trusting the earlier log.
- `/head` is refused (400) on fast chains on purpose. There, wait for the specific event with `/logs`.
- Do not subscribe to busy events (token `Transfer`, `Swap` on big pools, oracle updates of feeds you
  do not need). Every delivered byte costs CU.

**Cost** (counts toward the same Alchemy bill; `GET /health` shows `cu_today` per chain and filter)

- 0.04 CU per byte delivered. An ethereum head is about 55 CU, so the head stream is about 0.4M
  CU/day, shared by all bots, and only while some bot is calling `/head`.
- A log is about 25-40 CU. A filter that passes 150,000 CU in a UTC day is dropped until the next
  day (429). The whole feed stops for the day at 700,000 CU (429): bots then poll as before.
- In a bot's README, the CU estimate must include its feed use: expected events per day x bytes x
  0.04, plus its share of the head stream if it calls `/head`.
- A subscription is released 180 s after its last call, so a stopped bot stops costing.

**Checking by hand**

    curl -s http://127.0.0.1:8546/health
    curl -s 'http://127.0.0.1:8546/head/ethereum?timeout=20'

## What this changes, and what it does not

- A bot can now react within one block instead of one polling interval. Signing and sending are
  unchanged (signer, limits, executor contract, Alchemy only).
- Same-block opportunities (taken in the block of the price update or auction start) are still out of
  scope: record them as `blocked_infra`.
- The Alchemy numbers on the dashboard (relay) do not include the feed. Add `cu_today` from
  `http://127.0.0.1:8546/health` when you report daily CU.
