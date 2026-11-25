# Phase 12f: Relay API key behind a local service; the official Elysium bridge; the earner crontab (human, 2026-11-16)

## 1. farm-relayapi (new)

- The human got a Relay API key. It lives in a local service (`farm-relayapi`, 127.0.0.1:29485); no agent sees it.
- Use: call `http://127.0.0.1:29485/<path>` in place of `https://api.relay.link/<path>`. The service adds `x-api-key`.
  Example: `curl -s 'http://127.0.0.1:29485/requests/v3?limit=5'`.
- Passed on: GET `/chains`, `/requests`, `/intents/status`, `/currencies`, `/config`, `/price`; POST `/quote`, `/price`,
  `/currencies` (each with its sub-paths such as `/quote/v2`). Everything else answers 403 from the service. It cannot
  send a transaction, and measurements still send none.
- Limits: 5 calls per second, 50,000 per day (the service's own count; `GET /health` shows it). If Relay answers 429,
  slow down and tell the human; do not go around the service.
- The earner (local model) may reach the port; the bots may not.
- One `relayapi` row was added to TOOLS.md after the `explorer` row (or not, if the installer said so). Shorten it as
  you see fit and keep the prompt at or under 56,000 bytes.
- This opens item 7 of decision 2026-11-15-cross-chain-gap-relay (quoted cost against the cost actually paid), which
  lead 191 found key-walled. Please queue it. The human's own bridge (ethereum USDC to elysium, 2026-11-15, to the
  intermediate wallet) is one known request to look up.

## 2. A fact for lead 191: the official bridge returns 1:1, in about 7 days

- The human checked the official Elysium bridge page: USDC elysium -> hyperevm is 1 USDC = 1 USDC, and the page says
  withdrawals take about 7 days and are claimed on HyperEVM.
- So the ~2.5% Relay asks for leaving elysium is the price of skipping a 7-day wait, not a cost that cannot be avoided.
  Please have lead 191's analysis record this and answer two more questions, by reading and quotes only:
  (a) what the official withdrawal costs in gas on each side, and whether anyone can claim for the recipient;
  (b) how the pool gap (0.6-1.0%) compares with having the capital locked for 7 days, and how the gap moved over 7-day spans (the price can move against the position while it waits).
- No bot is to use the bridge: funds in transit for 7 days are outside the holding frame (168 h limit, and the gate
  cannot exit them). If the numbers say it would pay, write it to the human as a design question.

## 3. The earner's crontab entry for lead 191

- The human accepts it for this one series: let it run to its own stop (2026-11-16 17:20Z) and use the data.
- After the analysis, remove the entry (as the earner asked) and confirm in inbox/human that `crontab -l` is empty.
- After that the human will close the earner's crontab. Before that happens, tell the human in inbox/human what a
  long measurement (hours to days, no keys, no sends) needs in order to run without it: the human does not want the
  closing to get in the agents' way. Until then, add no further crontab entries.

## 4. Reaction time

- Decision 2026-11-16-reaction-time: ethereum R = 12 s (one block); the other chains stay at 3 s until a real farm
  send is included on that chain. Please update wiki `infra/reaction-time.md` and the prompts where they say 3 s.
