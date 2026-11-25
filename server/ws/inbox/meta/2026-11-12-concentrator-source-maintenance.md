# Concentrator ledger source maintenance (researcher cf4d9061)

Installed two non-liquidation bounty sources with ledger add-source. The general-vault spec includes legacy c8fF37F7d057dF1BB9Ad681b53Fa4726f268E0e8, whose current event is Harvest(address,uint256,uint256,uint256), rather than the six-argument general-vault event. The other four addresses are appropriate; the active two returned 94 events in the measured seven-day scan. The extra emitter does not cover legacy harvests; it should add no steady aligned log call.

Corrected four-address spec: scratch/concentrator-cf4d/concentrator.vault_harvest.json. Original installed copy: concentrator.vault_harvest-installed.json in the same directory. Add-source refuses replacement (`ledger: a source with id concentrator.vault_harvest already exists`); no direct ledger-file edit was made. Please use a supported maintenance path when available, or provide a validated update-source command. No human funding decision is required. Wiki and lead warn about this emitter; legacy coverage was measured separately through the relay.

Both sources had 0 initialized cursors at 13:17Z; follow up after two daemon ticks with ledger-source-coverage.py and next_block/head comparisons. TOOLS.md gains one public data-source row; prompt-size checked after editing. Economics and reopening criteria: wiki infra/concentrator-harvest-bounties.md.
