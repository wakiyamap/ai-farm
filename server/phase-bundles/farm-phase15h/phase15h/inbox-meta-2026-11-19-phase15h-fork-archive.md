# phase 15h: the fork lane no longer reads old state from public nodes (human, 2026-11-19)

Answer to `inbox/meta/2026-11-19-bsc-fork-missing-trie-node.md` and to item 3 of your note
`inbox/human/2026-11-19-meta-15g-direct-node-bsc-fork.md` (run 0facbcb2).

## Cause

There is no separate non-archive provider for the fork lane: its list was Alchemy first, then the
chain's public nodes (for bsc: bsc-dataseed.binance.org, bsc-dataseed.bnbchain.org). The relay keeps
one cooldown per upstream URL, shared by all lanes. When another lane's call on bsc made Alchemy time
out (30 s cooldown) or rate-limit (10 s), the fork's read of a 4-day-old block skipped Alchemy and went
to bsc-dataseed, which keeps recent state only: `missing trie node`. When the public node was cooling
down too, nothing was left: `no provider available`. A few seconds later Alchemy was back, so the same
call worked. The research lane looked healthy because it happened to ask outside a cooldown.

## What changed in rpc-relay

1. Fork lane, a state read pinned to a block older than about 800 blocks: Alchemy only, never a
   public node.
2. A fork's only archive provider is tried even while its URL is cooling down. The same applies to
   every send (eth_sendRawTransaction goes to Alchemy only), so a burst of reads on one chain can no
   longer make a live bot's send on that chain fail for 10-30 s.
3. Fork lane: when the call fails on a rate limit, the error comes back as JSON-RPC code 429
   ("rate limited, retry: ..."). anvil retries 429 with backoff; before, it got -32000 and failed the
   call.

Other lanes and methods are unchanged. A research or scout read of old state still goes Alchemy, then
public, so `missing trie node` can still appear there while Alchemy is cooling down. Treat it as
"retry later", not as a revert.

## What to do with the wiki

- `pitfalls/fork-past-state-public-nodes.md`: say this is fixed in the relay for forks (15h, 11-19).
  Keep the workaround of one retry on an RPC error for research-lane scripts.
- If a fork still shows `missing trie node` after 15h, write the time (UTC), chain and block in
  inbox/meta. That would mean Alchemy itself lacks the state, which is a different problem.
- Old-state reads on the fork lane always use Alchemy, even after the fork lane's daily budget is spent
  (as before 15h). If the fork lane's CU per day keeps rising, say so in your report.
