Decision: demote
Reviewed at: 2026-11-06T07:48:07.265804+00:00
Reviewer: paper-reviewer / gpt-6-sol
Run: 7e653174a7094a19bf8f3acc88f78829
next_review_at: none (archived by human decision)
Reason: 2026-11-06-no-latency-race.md: GMX liquidation requires LIQUIDATION_KEEPER role grant; route is out of scope
Evidence: decisions/human/2026-11-06-no-latency-race.md; previous review below.

--- Previous review ---

Decision: fix
Reviewed at: 2026-11-06T06:16Z
Reviewer: paper-reviewer / gpt-6-sol
Run: da3e4b7a15804d50950943f26ec02836
next_review_at: null (resubmit after an actual atomically guarded own executor and natural pre-capture detection with a profitable simulation)
Code SHA256: 3af78e91ccd6217d00f1332d2272cf84efc5a2c8aac37f8b88c1376110c2d84a
Manifest SHA256: 7dc668d61a29dbb5d0f752522db87459b083f5b614c7b65cf33f59629763abb0

The manifest says executor: none and fork proof pending. bot.js has no signer send, no contract artifact, and no fork success/revert. It only calls eth_blockNumber, eth_getLogs, and eth_getBlockByHash through the relay and logs completed OrderCreated events. There is no live transaction path, no atomic principal repayment and profit guard, and therefore no enforceable L proof. I did not use the incumbent wrapper as proof of a bot-owned executor. Public GMX liquidations are protocol-intended keeper work under S.

The service started at 05:52:42Z with head 521704322 and a 100000-block backlog. Through 06:15:37Z, logs show 125 type-2 captures, all at blocks <=521702845, hence historical; none was pre-discovered. Cursor 521703322 still trails head 521708984 by 5662 blocks. Universe stays zero because bot.js creates a Set from state but never adds accounts to it. The code does not decode the candidate account, size or fee, and does not simulate an eligible liquidation. A type-2 OrderCreated after a competitor liquidation is evidence of a completed capture, not an advance opportunity by itself. There is no measured after-gas candidate or inclusion window.

Fix: build and name a Solidity executor that performs the entire liquidation and fee collection in one transaction, with a checked end-balance gain and bounded gas; demonstrate success and correct rollback on the fork. Decode and persist candidate positions, detect them while still eligible, and log a natural profitable executor simulation before another keeper captures them. Demonstrate the claimed polling-compatible window. No promotion attempted.
