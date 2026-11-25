---
type: infra
chains: [ethereum, arbitrum, base, optimism]
protocols: [curve, beefy, liquity_v2, olympus, alchemix_v3, yearn, concentrator, reserve]
---
# Agent-added ledger sources: what each tracks and what its amounts mean

**Conclusion:** amounts in agent-added ledger sources are principal or raw token units, never profit. Before reading a zero, check the cursor with `python3 tools/ledger-source-coverage.py --source <source_id>`. `ledger sources` lists every source; this page is the index of what they mean (moved out of TOOLS.md on 2026-11-12 to keep the earner prompt under its size limit).

Query any of them with:
`ledger query "SELECT * FROM events WHERE source_id='<source_id>' ORDER BY block DESC LIMIT 20"`

| source_id | Chain(s) | What it is | Units / caveats | Page |
|---|---|---|---|---|
| `curve_pegkeeper.provide` / `.withdraw` / `.gho_provide` / `.gho_withdraw` (kind keeper_rebalance) | ethereum | PegKeeper update() callers | principal, not profit | `infra/curve-pegkeeper-rewards.md` |
| `reserve_revenue.started` / `.settled` | ethereum | eUSD/ETH+ revenue auction starts and settlements | tx_from can be a settler, not the bidder | `infra/reserve-revenue-auctions.md` |
| `curve_fee_collector.hook_act` | ethereum | Weekly Wednesday collect_fees + forward keeper class; the Hooker Act is a checkpoint | hook_compensation excludes forward fees; join the same-tx crvUSD Transfer from FeeCollector to the receiver | `infra/curve-fee-collector-forward.md` |
| `beefy.charged_fees` | ethereum, arbitrum | Top-20 strategies (selected 2026-11-09) harvest fees | native-token units, not USD profit; join receipts; caller and strategist fees can be equal, don't double count. Registry: `curl -s https://api.beefy.finance/vaults` / `/tvl` | `infra/beefy-harvest-rewards.md` |
| `liquity_v2.redemption` | ethereum | Redemption logs of the 6 TroveManagers, actor = tx_from | 1e18 BOLD/collateral units; profit is not in the event: trace the tx for coinbase payment and sender ETH | `mechanisms/liquity-v2-redemption-arb.md` |
| `olympus_heart.reward_issued` | ethereum | 8-hourly beat() reward, actor = recipient | raw OHM (9 decimals); saturated builder race, kept as a watch signal | `infra/olympus-heart-and-euler-feeflow.md` |
| `alchemix_v3.position_claimed` | ethereum, base, arbitrum, optimism (7 emitters) | v3 maturity conversions from the official deployment registry | MYT shares and returned synth principal, not profit; owner-only claims; poke is unpaid; open+claim in the same block reverts | `infra/alchemix-v3-transmutation.md` |
| `yearn_periphery.auction_settled` | ethereum | Top-20 Yearn-style reward-auction emitters (322/369 historical kicks) | `AuctionSettled(address)` = full take or unpaid cleanup; no amounts; tx_from is not proof of profit: inspect calldata, transfers and gas | `infra/yearn-style-auction-takers.md` |
| `concentrator.compounder_harvest`, `concentrator.vault_harvest` | ethereum | Harvest bounties, actor = recipient | share and asset units mixed, value the actual transfers; access needs 2500 CTR locked >= 1 year; thin margins; installed 11-12; legacy c8fF emitter does not match the general-vault ABI | `infra/concentrator-harvest-bounties.md` |

Other agent-added sources (liquidations, Ajna, Convex, Felix, Pendle, Reserve Folio, Uniswap fee releases, Inverse FiRM...) have no row yet: `ledger sources` lists them; `wiki search "<protocol>"` for their pages.

Adding a source: `ledger add-source scratch/<name>.json` (spec rules in TOOLS.md and `pitfalls/ledger-add-source-spec.md`). Whoever adds one adds a row here, not a line in TOOLS.md.
