# morpho-nextblock-ethereum: its first live send was a pool init, and it skipped the opportunity it was waiting for (human, 2026-11-15)

Facts, read from signer.log, the bot's own log and the receipt. Nothing is broken now; this note asks for one measurement and one rule.

## What happened (UTC, 2026-11-14)

- 14:02:35 block 26413694: BTC/USD AnswerUpdated (round 26031).
- 14:02:36.892 the bot received the feed event (about 1.9 s after the block timestamp).
- 14:02:37.687 heartbeat: `underwater_now: 2`. Besides the known dust row, borrower `0xa709b849be7daf1716fdb2d05655621fd1d17730` in market `0x3a85e619751152991742810df6ec69ce473daef99e28a64ab2340d7b7ccfee49` was liquidatable.
- 14:02:38.942 `live_skip`: "pool not initialized on deployed executor (isPoolAllowed(0x9a772018..)=false)", and `pool_init_sent`.
- The init tx `0xdf25a9c72f6b85c61de693eadf9b573fd5f395a348079ea9c5f5af2e4239a918` landed in the next block, 26413695: status 1, 46,065 gas, about 0.022 USD. It is `setPoolAllowed(0x9a772018fbd77fcd2d25657e5c547baff3fd7d16, true)` on the deployed executor `0x514d99889ecb37a45ae345744c28bc26e76cf87c`.

So the bot was fast enough to make the next block (block timestamp to send: about 3.9 s; feed event to send: about 2.05 s), but the transaction it sent was setup, not the liquidation. The executor's constructor allows only the WETH pool; the WBTC pool needs an owner transaction, and bot.js sends that transaction only when the first opportunity in that market arrives (bot.js around lines 920-943). The pool is allowed now, so the next opportunity in that market will be attempted.

This is also the first transaction a live bot of this farm has sent on its own, and the path after phase 11c (deployed executor address, signer policy, relay send, watchdog nonce record) worked with real funds.

## Asked of the earner

1. Measure the skipped opportunity and record it on lead 14: who liquidated `0xa709b849…` in that market, in which block and transaction, gross and gas; and replay on a fork at the parent of block 26413695 what the farm's executor would have netted with the pool already allowed. Say whether the farm's transaction in block 26413695 would have been first, behind the taker, or too late. This is the first real data point for the next-block trial (decision 2026-11-13-blocked-infra-feed-retriage, item 3).
2. Read `isPoolAllowed` on the deployed executor for the pool of every market the live bot watches (4 markets) and write the result in the same attempt. If any pool is still not allowed, report it in inbox/meta; do not try to fix the live bot yourself.
3. Record the measured reaction time for ethereum in wiki `infra/reaction-time.md` (feed event 1.9 s after the block timestamp; send 3.9 s after; landed in the next block).

## Rule (earner.md and paper-reviewer.md, short)

- A bot whose executor needs any owner or setup transaction after deployment (pool allow-lists, approvals, registrations) sends all of them at startup in live mode, logs each one, and logs one line when the executor is fully armed. It must not leave setup for the moment an opportunity arrives.
- The README lists these setup transactions and their gas.
- paper-reviewer: a bot that defers setup to the first opportunity is `fix`. After a promote, check the live log for the "armed" line together with the executor address check you already do.
- meta: if `tools/manifest-check.py` can warn about a setup call that is only reachable from the opportunity path, add it; if that is not practical, leave it to the reviewer.

Keep the role files within 56,000 bytes; the details can go to the wiki.
