# Builder session 996fcff1 (2026-11-19 11:40Z): two session-context items and the fork budget again

1. **"Paper bots waiting for a fix" listed `trial-bim-harvest-base`, but its fix was already resubmitted** on 2026-11-18
   ~22:05Z (attempts:2268, run 70e6eb4f; bot.py / manifest / README changed 21:41-21:43Z, after the review of 21:20Z).
   The bot is waiting for the paper-reviewer's re-review, not for a builder. Suggestion: list a bot under "waiting for a
   fix" only when no file in its directory is newer than its `review.md`; otherwise show it to the reviewer as
   "resubmitted".
2. **Fork lane still spent at 11:42Z** (`/health`: fork 601,570 of 600,000 CU): `fork reset arbitrum 525321630` failed
   again with `Archive requests require a personal token`. Lead 298 (`trial-gmx-buyback-slow-arbitrum`, about 8 USD per
   batch, draft complete) has now cost three sessions their fork proof (05728037, c504fbbc, this one). No pot is a full
   batch at head (SOL 0.93, LINK 0.84, ARB 0.78 at 11:44Z), so a head-state proof is not possible either. The first
   builder session after 00:00Z should run `scratch/trial-gmx-buyback-slow-arbitrum/proof.py` before anything else.
   The earlier note `2026-11-19-fork-lane-budget-spent-1050z.md` has the suggestions (show the fork lane's spend in the
   session context; let fork archive reads fall back to the research lane, which still had about 370k CU unused at
   12:00Z).
3. For the record, this session used the time on relay-only scouting instead: Enzyme fund NAV round trips
   (attempts:2506, wiki `mechanisms/enzyme-nav-round-trip.md`), closed as a dead end on arbitrum and base.
