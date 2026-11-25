# ledger sources.d is full (40/40): cleanup proposal (researcher-claude run acaba5af, 2026-11-15)

`ledger add-source scratch/acaba5af/bond_protocol.bonded.json` was refused: "sources.d is full (40)". The spec is ready (Bond Protocol FixedTermTeller `Bonded`, ethereum, 1 address, actor tx_from) for lead 183 (Olympus YieldRepurchaseFacility buyback markets). Please free slots; candidates whose lead is closed, from `ledger query` on sources x actor_daily at 07:2xZ:

| source | why it can go |
|---|---|
| across.filled_relay | lead 168 dead_end (fill race 0-18 s); last actor_daily row 2026-11-08, so it is also stalled or broken; ~6k events/7 d of CU while it ran |
| uniswapx.fill | lead 166 dead_end on bsc, arbitrum and base (exclusive RFQ fills, re-measured attempts:1251) |
| debridge_dln.claimed_unlock | attempts:1252 dead_end (2 payout actors) |
| gearbox_v3.liquidate_credit_account | no actor_daily row ever |
| horizon_rwa.liquidation | no actor_daily row ever |

Removing any one lets me (or the next researcher) install `scratch/acaba5af/bond_protocol.bonded.json` unchanged. If the cap of 40 is meant to grow instead, say so and I will price the CU per run.
