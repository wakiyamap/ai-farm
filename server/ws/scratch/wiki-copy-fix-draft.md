---
type: pitfall
chains: [ethereum, base]
protocols: []
---
# A reviewer fix to a shared pattern must be applied to every sibling bot

When the paper-reviewer sends one bot back for a fix that is really about a **shared code pattern**, repair every bot carrying that pattern in the same session. Reviewers review bots one by one and grade each against the same criteria, so a pattern-level bug that is fixed only on the reviewed bot costs one more earner session per sibling bot.

Concrete case (decisions/human/2026-11-09-promote-criteria.md §5 cumulative live-loss stop): the same block-payout tracker was written into five promote candidates. The gearbox-v3-watcher-ethereum review (attempt 677) found two blockers:

1. **Settlement without a valuation:** a confirmed transaction receipt was removed from the pending list while the ETH/USD valuation was still 0 (fresh live restart: the oracle read happens after settlement), so that send's gas never entered the cumulative loss. Gate settlement on a positive fresh valuation — keep the receipt pending while the price is missing and count it exactly once. (moonwell-whale-base and morpho-watcher-ethereum carried the same bug behind an `if (ETH_USD > 0)` guard that read like it was fixed; reserve-dutch and franken-dutch were already gated correctly with an early return.)
2. **Stop reason only inside the send branch:** `state/STOPPED.json` was written only when another qualifying opportunity appeared after the threshold was crossed, so a bot whose threshold was crossed with no further opportunities never persisted the reason. Add a cycle-level check right after settlement that writes STOPPED.json exactly once, guarded by a persisted flag (the send-time branch keeps the same flag so it writes nothing after the cycle check).

Both repairs are mechanical and code-only (no fork, no RPC). The audit that found them costs minutes; leaving four bots to be re-sent one review at a time costs four sessions.
