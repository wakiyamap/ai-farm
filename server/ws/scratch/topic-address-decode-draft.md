---
type: pitfall
chains: [base, arbitrum, ethereum]
protocols: [any]
---

# eth_getLogs topic addresses: slice from the end, not from a fixed offset

## Conclusion

An indexed `address` topic is 32 bytes: 12 zero bytes then the 20-byte address. In the
JSON-RPC hex string (`0x` + 64 chars) the address is the **last 40 hex characters**.
Extract it with `topic.slice(-40)`, never `topic.slice(24)`: slice(24) leaves 42 characters
(the final two padding zeros plus the address), which yields `0x00<addr>` — a string that
passes no address comparison and no `/0x[0-9a-f]{40}$/` check.

## Pitfall shape

The broken form fails **silently when it is only used as a comparison key**: if every
decoded value carries the same `00` prefix, started/settled pairing and calldata word
encoding (padStart to 64) keep working, and a `=== TOKEN_CONSTANT` filter silently skips
every event — so the watcher logs events forever but never executes. It looks like an
empty opportunity, not like a bug.

## Evidence

reserve-dutch-ethereum (run e76782b3, attempts 233): bot.js used `'0x' + e.topics[1].slice(24)`;
the seeded backfill logged the weETH->ETH+ pair as `trade 0x00527dc250...`, `sell 0x00cd5fe...`
(42 chars) — `t.sell === WEETH` (40-char constant) never held, so the simulate branch could
never run for the bot's only route. After `slice(-40)` the same backfill logs the 40-char
addresses and the filter matches. Fixed executor calldata encoding was unaffected
(padStart(64) of the 42-char value reproduces the correct 32-byte word), which is exactly why
the bug stayed invisible.
