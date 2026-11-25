# phase 15i: fork lane on Alchemy only with no cap, bigger research/scout budgets, feed filters, builder context (human, 2026-11-20)

Answers to `inbox/human/2026-11-19-meta-fork-budget-context-list.md` (ee059752) and
`inbox/human/2026-11-19-meta-15h-optrial-scout-usd.md` (f5e76c77). Read together with
`decisions/human/2026-11-20-trial-slots-45.md`: Farm closes on 11-24, the Alchemy month may be used up
to then.

## 1. Fork lane (your item 1: option a)

- You were right that 15h did not work as described. 15h sent a fork read to Alchemy only when the
  relay's `is_historical()` called the block old. For anvil's reads it did not, so within the budget a
  fork read went Alchemy, then public (Alchemy skipped while cooling down -> `public: HTTP 403
  Archive`, the 08:12Z arbitrum case), and past the budget it went to public nodes only (all day after
  09:43Z). Why `is_historical()` missed anvil's reads was not investigated: it no longer matters.
- Now **every fork-lane read goes to Alchemy only, whatever the block, with no daily cap**. Public
  nodes are never used by a fork. The fork entry in `/health` budget shows 95,200,000 (the month); the
  relay does not use it for the fork lane. Do not report "fork budget spent" any more.
- A fork call can still fail on Alchemy itself: code 429 (anvil retries) or an Alchemy error. If
  `public:` appears in a fork error after 15i, write time (UTC), chain and block in inbox/meta.
- You do not need to know what spent 600k before 09:40Z; report the fork lane's CU per day as usual.
- The workaround lines you added (`pitfalls/fork-past-state-public-nodes.md`, builder.md "recent block
  first, old block next UTC day") can go: an old-block fork works at any time of day now.

## 2. Read budgets

- research 700,000 -> 1,500,000 CU/day, scout 300,000 -> 1,200,000 CU/day (relay.json). Other lanes
  unchanged. Scouts should now get bsc getLogs and 7-day counts through Alchemy after the public node
  refuses. Tell the scouts (scout.md) that a 7-day count is expected again, not "unmeasured: lane spent".
- Watch `/health` `cycle`: tell inbox/human only if the month would run out **before 11-24**.

## 3. Feed

- `max_log_filters_per_chain` 8 -> 16 (feed.json; your base-feed-filters-full). Update `infra/feed.md`
  and the builder.md feed line: a new base bot can take a feed filter again instead of polling.

## 4. Builder session context (your item 2 and builder-queue-stale-entries 1-3)

- "Trial bots live: N / 45".
- "Paper bots waiting for a fix" takes the current decision from the first decision line or decision
  heading in the top 15 lines of review.md (`**Decision: fix**`, `decision fix stands`,
  `## <time> — fix`). Keep the paper-reviewer rule that line 1 is `**Decision: ...**`; both now agree.
- A fix-reviewed bot whose bot.py, *.sol or manifest.yaml is newer than its review.md is listed under
  "Paper bots resubmitted after a fix (waiting for the reviewer; not builder work)".
- "Measured leads without a bot" leaves out leads whose next_steps contain TRIAL BOT PLACED or NOT A
  BUILD TARGET, and leads named in a paper or live manifest as `lead: N`, `lead_id: N` or `leads:N`.
  If manifests use another form, ask builders to add `lead: N` to manifest.yaml.

## 5. Other answers

- OP Stack trial loss bound (your f5e76c77 item 4): the human accepts your reading: signed cap +
  measured L1 / operator fee estimate under 1 USD, wallet ≤ 18 USD bounds the rest. Keep
  paper-reviewer.md as you wrote it; the 12 live base/optimism trials stay.
- `gate promote` accepts a decimal `capital_usd` (0.75): it is read as a float since phase 9k.
- Avalanche read path for scouts (ee059752 item 3): no live-lane Alchemy for scouts. Keep the
  head-vs-7-days-ago state difference you wrote in the wiki; with the bigger scout budget, Alchemy
  getLogs (scout lane, 10k-block chunks) may also work now.
