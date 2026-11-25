---
type: pitfall
chains: [any]
protocols: [morpho_blue]
---
# Executor setup transactions: avoid them; if unavoidable, at startup, never on the first opportunity

**Default since 2026-11-15 (`decisions/human/2026-11-15-executor-no-baked-targets.md` item 2, `pitfalls/executor-no-baked-targets.md`): build executors that need no setup tx at all.** Pools, tokens, markets and approvals are arguments of the execution call; constructor args are the owner `{bot}` only. (This replaces the earlier advice on this page to do the setup in the constructor via `executor_args`.)

**Only if a setup tx is truly unavoidable (human note `inbox/meta/2026-11-15-morpho-nextblock-pool-init.md`):** the bot sends **all** of them at startup in `BOT_MODE=live`, logs each one (tx hash, gas), then logs one line `executor armed` (with the executor address). The README says in one line why the setup is needed and lists the txs with gas. Deferring setup to the moment an opportunity arrives = paper-review `fix`; so is a setup tx that could have been a call argument. After a promote the reviewer checks the live log for the `armed` line together with the executor-address line.

## Why: morpho-nextblock-ethereum, 2026-11-14

- 14:02:35 block 26413694: BTC/USD AnswerUpdated. 14:02:36.9 the bot got the feed event; 14:02:37.7 borrower `0xa709b849…` in market `0x3a85e619…` (WBTC collateral) was liquidatable.
- 14:02:38.9 `live_skip`: `isPoolAllowed(0x9a772018..)=false` on executor `0x514d9988…`. The constructor allowed only the WETH pool; bot.js sent `setPoolAllowed(WBTC pool, true)` only when the first WBTC-market opportunity arrived.
- The setup tx `0xdf25a9c7…` landed in block 26413695 (46,065 gas, ~0.022 USD) — the next block. The bot was fast enough (block timestamp to send ~3.9 s) but spent that block on setup. (Lead 14, run 9c972820: a taker had already liquidated the borrower in that same block, so the farm would have been too late anyway; the setup flaw stands.)

## What the reviewer checks

1. Grep the bot for owner-only executor calls (`setPoolAllowed`, `approve`, `setAllowed`, `register`, `whitelist`…). Could each be a call argument instead? If yes, `fix`. If not, it must be reachable from the startup path, not only from the opportunity handler.
2. Paper mode logs the setup it would send (simulated) and the `armed` line.
3. After promote: the first live log lines show the executor address (phase 11c) and `executor armed`. No `armed` line = write `inbox/human/` as for a wrong executor address.

`tools/manifest-check.py` warns when the executor ABI has setup-style state-changing functions (`set*`, `allow*`, `approve*`, `register*`, `whitelist*`, `enable*`, `add*`), since 2026-11-15 regardless of the `armed` line (which it notes when missing), and when `executor_args` has words other than `{bot}`. It cannot prove the setup is on the startup path; the reviewer still reads the code. Archive scan at introduction (meta c409, 11-14): the Morpho/Moonwell executor family's deferred-init block (`morpho-watcher-ethereum/bot.js` ~l.811-943) was copied into watcher2, watcher3 and nextblock. **Do not copy that block, nor those executors' constructor-baked pool/collateral lists.**
