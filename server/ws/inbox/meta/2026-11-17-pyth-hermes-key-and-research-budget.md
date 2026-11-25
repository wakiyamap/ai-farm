# Pyth Hermes needs a key (lead 250); research lane ran out at ~18:47Z

From: builder-claude, run 70dc57b16e6d49148138a3372be5d72b, 2026-11-17.

1. **needs_human candidate, lead 250 (arbitrum flat_money_v2 executeOrder trial).** The entry needs a
   signed Pyth update published after the order becomes executable. `hermes.pyth.network` and
   `benchmarks.pyth.network` answer HTTP 401 `unauthorized` from this host (18:45Z). Ask: a Hermes
   key (Pyth's own or a third-party provider; I did not look up prices) behind a local keyless proxy
   like `relayapi`. Honest size: this lead alone pays about 0.89 USD/day gross for the whole class
   (45 executions / 7 d, one incumbent), so it justifies a free-tier key only; the wider value is
   that every Pyth pull-oracle keeper class is closed to the farm without it. Details: lead 250,
   wiki `pitfalls/pyth-hermes-needs-key.md`.

2. **Research lane budget.** `/health` at ~18:47Z: research 1,003,704 / 1,000,000 CU. My session
   added roughly 15 `eth_getLogs` over 400k-block arbitrum ranges, ~95 block reads, ~90
   tx/receipt reads, 45 small getLogs and one `debug_traceTransaction`; by my estimate that is
   under 15k CU, so the lane must already have been near the cap when I started (inferred: I did
   not read `/health` first, which I should have). Consequence:
   `fork reset arbitrum <historical block>` fails with `all providers failed: public: HTTP 403`
   until the UTC day rolls, so no builder can fork-prove against a past block for the rest of the
   day. Suggestion: show the research lane's remaining CU in the builder session context so a
   session can decide to scout less and keep budget for its fork proof.
