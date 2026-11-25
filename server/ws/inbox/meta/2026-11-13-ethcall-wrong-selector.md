# ethereum eth_call "incident" of 2026-11-13: wrong selector, not the relay (human)

- The request in scratch/aave-eth-revive/INCIDENT-eth-call-revert.md sends data 0xed42883a as decimals(). The selector of decimals() is 0x313ce567. Calling a function that does not exist reverts, on every node, so the relay answered correctly. cast computes selectors itself, which is why cast succeeded in the same minute.
- The fork reverted for the same reason (same wrong selector), not because of bad state.
- The 30-day window recount for lead 17 (recount.log, 15/15 reverted_at_parent) is probably hit by the same error and must be redone.
- meta: find where 0xed42883a came from. If tools/rpc.py (or any helper) computes selectors, test it against known values (decimals() 0x313ce567, balanceOf(address) 0x70a08231, totalSupply() 0x18160ddd) and fix it; if it was typed by hand, add one line to earner.md: take selectors from cast sig or the helper, never from memory, and check one known getter before concluding that a node is broken.
