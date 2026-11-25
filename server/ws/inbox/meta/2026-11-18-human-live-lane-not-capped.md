# The live lane is not capped: live bots never fall to public nodes (human, 2026-11-18 09:45Z)

Correction to `inbox/human/2026-11-18-meta-alert85-live-lane.md` item 2 (and the same claim on 11-18 03:50Z).

- rpc-relay sends every live-lane read to Alchemy first whatever the day's spend: `alchemy_daily_cu.live` (1.5M) is shown in `/health` but nothing enforces it. Only paper / research / fork / scout / watch stop using Alchemy at their budget. Today's RPC table shows it: live/alchemy ok 68,343, live/public ok 1.
- So the live trial bots are NOT on public nodes after 08:40Z. Do not discount any hours of trial results for that reason on 11-24. No budget move from paper to live is needed.
- What the uncapped live lane does mean: it is the one lane that can run the month's Alchemy allowance out. Since 15e (03:49Z) it grows about 2.9M CU a day with 33 live bots. The human checked the Alchemy dashboard (33.9M of 95.2M at 09:35Z) and is fine with this until the 11-24 decision. Keep reporting `cycle` as before; `alert_85` stays high through 11-19 because the pre-15e morning still counts in the recent pace.
