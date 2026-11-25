# Reaction-time table is written — for the human via meta (lead 192, run 44446bcc, 2026-11-15)

The R-per-chain table (human request 2026-11-15, lead 192) is in wiki `infra/reaction-time.md` (attempt 1318). Summary: feed detection p90 is 0–3.5 s on every chain we could sample; the farm's only send-to-inclusion sample (ethereum, n=1) was **8.06 s**, so R(ethereum) ≈ **11.6 s, worse than the 3 s placeholder**; on the sub-second-block chains (polygon, avalanche, optimism, elysium) the estimate R = feed p90 + one block lands at **0.9–2.2 s, below 3 s**.

**Verdict-change list (per the lead's rule: chains where measured R differs from 3 s by more than 1 s):**
- **ethereum (11.6 s > 3 s):** no blocked_infra lead's verdict flips — ethereum speed closures (73 inverse forceReplenish, 147, 174, 5, 33, 35, 67, 91/94/103 needs_human) were all closed for reasons that an 11.6 s R strengthens or leaves untouched (races lost in the same/next block). Nothing to reopen.
- **polygon, avalanche, optimism, elysium (est R 0.9–2.2 s < 3 s):** zero blocked_infra leads exist on these chains — no verdicts to change.
- **base (est ~0.8–1.9 s):** below 3 s but only as an estimate; its speed closures (13, 21, 170, 18, …) are liquidation-class closures the human already made (`2026-11-15-widen-beyond-liquidations.md`), and per the lead only *measured* R may deviate — so no change requested, flagging for awareness only.
- **hyperevm: no sample** — estimate ~2.0 s, marked as estimate in the table; its 2 blocked_infra leads (129, 145) are needs_human / class leads, not speed closures.

Until the human accepts the table (decision 2026-11-14-race-rule-seconds item 19 asks for ≥20 samples per chain — met only by ethereum/elysium/polygon/avalanche/optimism on the *detection* leg, by none on send-to-inclusion), **3 s stays everywhere**, which is also what this measurement recommends for ethereum (11.6 s is worse for us, so 3 s is not blocking anything; the binding limit there is block cadence + our send path).

One process note for meta: live bots should log the send wall-time **and** the receipt's block timestamp (`send` → `included` pair) — without that, the send-to-inclusion leg of R can never grow past its single ethereum sample.
