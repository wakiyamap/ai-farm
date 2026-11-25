# phase 15c: fork / scout lanes, cycle in /health, farm-hermes, reviewer-claude daily (human, 2026-11-18)

Applied by the human. Decision: `decisions/human/2026-11-18-lanes-hermes-toga.md` (your report of 2026-11-17 21:45Z, items 4, 5 and 6).

- **rpc-relay**: two lanes with their own daily Alchemy budget, chosen by the unix user of the connecting process (relay.json `lane_by_user`), whatever `lane=` the URL says. `fork` = user farmfork (the anvil forks), 400k CU/day, Alchemy first while it lasts. `scout` = user earner (the Qwen scouts), 300k CU/day, public first. `research` 1.0M -> 700k (builders, reviewers, meta, ledger-ingest). Nobody else can ask for fork or scout (they get research). `GET /lane?lane=research` shows which user and lane a connection gets.
- **/health** now has `cycle`: `cu`, `projected_cu`, `projected_share`, `alert_85` (relay count from ops.db, without farm-feed; the same numbers as the dashboard). Please watch `alert_85` (decision 2026-11-18-trial-slots-20 item 5).
- **farm-hermes** (127.0.0.1:29486): Pyth Hermes with the human's key added as `Authorization: Bearer`. GET only, price endpoints only, the stream is refused, 30,000 calls/day. The key is a 2-week trial (ends around 12-02). Please add a TOOLS.md row after `relayapi` (trim earner.md first: 5 bytes of headroom). The install output says which users (earner, harness, farmbot) can reach the port; if farmbot cannot, a live bot cannot fetch update data yet - tell the human before a bot that needs it is promoted.
- **paper-reviewer-claude** runs 24 h after its last run (timer drop-in `daily.conf`). If a Codex-built bot needs a quick review, forward that to `inbox/human` (the human starts the run by hand).
- Superfluid TOGA: no exception. Please mark lead 248 `dead_end` with that reason.
- The dashboard's per-chain Alchemy table still shows only live / paper / research; fork and scout appear in "alchemy CU today" and the cycle's `lanes`.
