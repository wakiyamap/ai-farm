# Lead 191 item 2(a) answered early (earner run db4e828b, 2026-11-15 22:3xZ)

In reply to inbox/meta/2026-11-16-phase12f-relayapi.md section 2 (the two bridge questions for
lead 191's analysis). Item (a) is now answered and recorded (attempts:1348, lead 191 next_steps
head, wiki `infra/elysium-official-bridge.md`, commit 961c540), so tomorrow's post-17:45Z analysis
session only owes item (b) (gap vs 7-day lock, 7-day-span gap moves — needs the completed logger
series and a rebuild of pool-A gap history from logs; the 11-15 15:06-17:27Z hole is permanent).

Summary of (a): the official bridge costs gas ONLY (~0.007-0.03 USD for the whole exit: 175,487 gas
on Elysium at 0.5 gwei + a 158,908-175,994-gas claim on the HyperEVM Outbox at 0.1-1.26 gwei,
HYPE ~67.2-67.8 USD), pays exactly 1:1, waits the challenge period 483,840 HyperEVM blocks
(~5.6 d; the UI's ~7 d), and the claim is **open to anyone** (the recipient needs no HyperEVM gas).
Correct docs: https://elysium.kinetiq.xyz/docs — not docs.elysiumchain.tech (old Vulcan Forged).

The crontab logger was left running as agreed (self-stop 2026-11-16 17:20Z; tick 29 at 22:10Z,
series growing). The analyzing session removes the crontab entry. No other crontab entries added.

For the human's design question (in case the numbers say it pays): capital in transit 5.6-7 days
is outside the holding frame (168 h cap, gate cannot exit it) — same conclusion decision
2026-11-16-bridge-vs-bridge-quotes §3 already states for bridges generally.
