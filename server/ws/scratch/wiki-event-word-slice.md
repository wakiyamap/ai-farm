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

The same off-by-two applies to non-indexed **event data words**: with the `0x` prefix,
word `i` of `data` spans characters `2 + 64*i .. 2 + 64*(i+1)`, i.e. word 1 is
`data[66:130]`, not `data[64:128]`. A misaligned slice still parses as an int and is a
garbage number, so the tracker never finds the entity it indexes and the opportunity is
classified as gone forever, without an error.

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
never run for the bot's only route. After `slice(-40)` the same backfill logged the 40-char
addresses and the filter matches. Fixed executor calldata encoding was unaffected
(padStart(64) of the 42-char value reproduces the correct 32-byte word), which is exactly why
the bug stayed invisible.

franken-dutch-ethereum (run 53a1754f, attempts 484): bot.py read the ChallengeStarted
challenge number as `data[64:128]` — the last two characters of word 0 plus the first 62 of
word 1. On the real log at block 26327471 (true number 10, `...000a` tail) the misaligned
slice decodes to a huge integer, the hub array getter then returns the uninitialized
(all-zero) slot, `challenger == 0` marks the challenge settled, and the bot bids on nothing
forever. Correct: `int(data[66:130], 16)` for word 1, `int(data[2:66], 16)` for word 0 —
the same alignment the getter return values already used (`(2, 66, 130, 194)`).
