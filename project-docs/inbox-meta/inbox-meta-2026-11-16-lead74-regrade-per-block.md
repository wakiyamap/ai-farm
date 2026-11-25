# Lead 74 (franken Dutch challenge): re-grade with a per-block check, not the 60 s poll (human, 2026-11-16)

The stop recommendation for franken-dutch-ethereum (attempts:1358) closed the route with R = 60 s poll + 12 s
inclusion = 72 s. The human asks why 60 s. The 60 s is the bot's own design choice, not a limit of the farm:

- The window opens by the clock (the Dutch price falls on a known schedule after `ChallengeStarted`), so no event
  marks it and the feed's `/logs` cannot wake the bot at that moment. That part is understood.
- But a challenge is live for a short, known period. During it a bot can read the price every block (one eth_call
  per 12 s, only while a challenge is open). Then the reaction time is the decision's R for ethereum, 12 s, not 72 s.
- With R = 12 s the three windows read differently under the race rule: 26 s (num 9) is at or past T + 2R and may
  count; 15.3 s (num 8) is "may try, not counted"; 0.28 s (num 10) stays out.

Please queue one measurement for the measure lane (reads and fork only, no sends):

1. For challenges 8, 9 and 10: the gross and the net (after gas at that block's base fee) a bid would have made at
   the first block at or after T + 12 s, and at T + 24 s. The price has only just crossed at T, so the gross that
   early may be tiny: that is the number that decides this.
2. What the incumbent 0xd694da17 waits for (it took them 15 to 26 s after the window opened): a profit threshold, a
   poll interval, or something else. If we bid one block earlier, what stops it from doing the same next time.
3. The read cost of the per-block check, counted only over the hours challenges were open in the last 30 days.

Close rule: if the net at T + 12 s is under 5 USD for all three, or the counted 30-day EV is under the read cost,
keep lead 74 blocked_infra and say so in one line. Otherwise write the per-occurrence table and tell the human
through inbox/human before anyone builds.

The live bot franken-dutch-ethereum (expiry + 3 s shape) is a separate matter; the human decides its stop.
