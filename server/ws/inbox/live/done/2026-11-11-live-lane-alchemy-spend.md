# live lane Alchemy spend measured over budget (earner, 2026-11-11)

`GET $RPC_RELAY_URL/health` at 2026-11-11T18:20:40Z (run 6a90b7fd, attempts:932):

- live lane: alchemy_cu_today 2,118,644 against its 1,500,000/day lane budget - at 18:20Z the three live bots (morpho-watcher-ethereum, gearbox-v3-watcher-ethereum, franken-dutch-ethereum, all zero-send) already spent the live lane over budget; linear projection ~2.8M CU/day.
- paper lane 81,932 of 900,000 (the 20 s morpho-watcher2 paper bot is cheap in paper); research 260,436 of 1,000,000.

Per decisions/human/2026-11-11-moonwell-stopped.md item 3 a bot above ~1M CU/day needs the inbox/human rationale before promote: the live lane is already the farm's largest CU consumer with zero sends. If the live lane is capped by Alchemy, sends stop for every live bot (the moonwell stop reason). No action requested here - the reviewer and the human have the number.
