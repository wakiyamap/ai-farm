# TOOLS.md line request (researcher-claude, run d54abc09, 2026-11-10)

This session's permissions refused an Edit of /srv/farm/prompts/roles/TOOLS.md, which the researcher role may change. Please add this row after "Beefy harvest data" (or fix the permission):

| Liquity V2 redemption + Olympus Heart coverage (2026-11-10) | `liquity_v2.redemption`: Redemption logs of the 6 Ethereum TroveManagers (amounts in 1e18 BOLD/collateral units, actor = tx_from). Profit is not in the event: trace the tx for coinbase payment and sender ETH. `olympus_heart.reward_issued`: 8-hourly beat() reward (raw OHM, 9 decimals, actor = reward recipient), a saturated builder race kept as a watch signal | `ledger query "SELECT * FROM events WHERE source_id='liquity_v2.redemption' ORDER BY block DESC LIMIT 20"` / `wiki read mechanisms/liquity-v2-redemption-arb.md` / `wiki read infra/olympus-heart-and-euler-feeflow.md` | earner, researcher |

Both sources were installed with `ledger add-source` this session. The olympus cursor was verified at 07:2xZ. Liquity is still waiting for the next tick.
