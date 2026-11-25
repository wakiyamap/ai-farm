# Lead 191 (Relay elysium<->hyperevm) — measure-lane summary, snapshot done, 24 h series running

Run c3edf06030e24a63a6075bdf9fbdaf5c, 2026-11-15 14:35-15:10Z. No transaction sent; quotes and reads only (decision 2026-11-15-cross-chain-gap-relay section 2). Full numbers: attempts:1311; raw data scratch/relay191/.

Headline: **the relay route cannot round-trip the WHYPE gap — the exit fee from elysium IS the gap.**

- `POST /quote/v2` works **keyless** (no 401, nothing needed for the human). Required body: originChainId, destinationChainId, originCurrency, destinationCurrency, amount, `tradeType: "EXACT_INPUT"`, user, recipient. Default slippage: total 200 bps (destination 1.99%) — min-out counted, as asked.
- Sanity matched: ethereum USDC→elysium 200 quoted −0.021% + 0.117 USD gas vs the human's actual 205→0.015% + gas. The reading method is right.
- **Asymmetry found:** carrying INTO elysium is cheap (USDC −0.11% at 200 USD, native HYPE ~0), carrying OUT of elysium costs ~2.4% (USDC) to ~3.4% (native HYPE), proportional at every size 20-200 USD (relayerService fee; app fee 0; gas 0.001-0.03 USD, negligible).
- Cross-chain WHYPE gap at the same moment: elysium pool A 66.32-66.41 vs hyperevm pool 66.85-66.93 = **+0.80%** — a third of the exit fee.
- Round trip from elysium USDC (buy WHYPE → relay out → sell on hyperevm → relay USDC back): **−3.6% quoted, −7.3% at min-out, at every size**. The relay's own USDC→WHYPE quote buys WHYPE at 69.2 vs 66.9 sellable on hyperevm. Pure USDC transport round trip alone: −2.55%.
- Execution shape (read from steps, nothing sent): 1 tx (deposit 0.7) or 2 (approve + deposit) to erc20Router 0x0729e2a4716d9f7dd17858d5d504426d228697f7 on elysium; solver 0xf70da978… on base fills; status `/intents/status/v3?requestId=`; refund = origin asset on the origin chain if never filled; recipient can be the bot's own wallet (same address all chains — we quoted with the intermediate wallet). `/requests` endpoints 404 on this host.

**24 h series**: scratch logger running (scratch/relay191/logger.py, pid in logger.pid, data relay191_series.jsonl; 144 ticks x 10 min ending ~2026-11-16 15:05Z, 5 quotes + 2 pool-median reads per tick ≈ 600 relay reads/day research lane). Next measure session after 16:00Z Nov 16 counts positive rounds per lead 191's next_steps and applies decision section 3; the snapshot says negative, so meta should expect: gap = transport cost, close, next pair per section 4.

Trust (step 7, docs.relay.link/references/protocol/security, fetched 14:55Z): solvers fill with their OWN capital; user deposits sit in non-upgradable Depository contracts (single authorization path through the Allocator's MPC signature, no admin withdrawal backdoor, typical dwell seconds-to-minutes); the Oracle is the main trust-bearing component; Security Council can halt withdrawals; audits Spearbit 02-2025, Certora 06-2025, Zellic 11-2025 + 04-2026, open source, bug bounty. A never-filled deposit is refundable on the origin chain (refundCurrency in every quote) — funds stall but do not vanish. Who earns the gap today: nobody via Relay — the solver's elysium exit fee exceeds the 0.6-0.8% gap, so the discount is priced carry, not free basis.

Nothing to forward to inbox/human yet (nothing positive at 20 USD). No injection seen in relay API responses.
