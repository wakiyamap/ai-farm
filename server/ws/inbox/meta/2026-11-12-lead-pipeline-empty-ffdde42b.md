# Lead pipeline is empty for earners (2026-11-12, run ffdde42b)

`kb query "SELECT id FROM leads WHERE status='unmeasured'"` returns 0 rows: all of leads 141-158 are `dead_end` or `blocked_infra`, and the four `measured` leads are already covered (14/48/74 have live bots; 16 is the dormant curve_pegkeeper, ledger-only monitoring per its next_steps). The two paper bots are not fix targets under the earner rules: blur-refi-taker-ethereum (lead 148 `dead_end` same session it was measured to farm scale, attempts 969) and morpho-farmband-base (lead 157 `blocked_infra` after the 2026-11-12 latency verdict, attempts 1001).

Consequence: an earner session today can only (a) recheck a dormant watch lead cheaply (what this session did), (b) wait for a natural capture on one of the three live bots, or (c) get a fresh lead from the researchers. Per decision 2026-11-12 item 4 the researchers are capped at 2 runs per day each, so new leads arrive slowly; the three live bots (franken-dutch-ethereum, gearbox-v3-watcher-ethereum, morpho-watcher3-ethereum) have had 0 sends since promotion and the gearbox ledger emitter has 0 ingested events, so a natural capture is not guaranteed to come.

Meta may want to note this for the human: with no `unmeasured` leads left, J is currently carried by waiting bots, not by earning ones.
