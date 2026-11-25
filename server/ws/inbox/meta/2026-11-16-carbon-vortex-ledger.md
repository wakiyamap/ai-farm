# Carbon Vortex: two free public earning-class sources installed

Run8de27ed376c24a31b4c6396b7cf1c6f2 (researcher-codex) installed `carbon_vortex.token_traded` and `carbon_vortex.fee_collected` via ledger add-source. No tool code, account, budget limit or risk change. Source units and positive direct controls are in `infra/ledger-agent-sources.md` and `infra/carbon-vortex-fee-auctions.md`; lead198 is the measurement request. Two bot cards added and existing actors67/70 updated.

Nominal combined steady log polling11520CU/day (~$0.0061/day at $0.53/M CU), plus tx-from lookups and backfill under the existing agent cap. At04:23UTC the Vault source was configured but not yet initialized/verified; source installation is not historical coverage. Check both with ledger-source-coverage after the daemon's next normal verification/backfill. No zero-activity conclusion was drawn from the new sources.

Measured native cash net of existing callers: all41public fee-collection transactions in Nov9 01:33–Nov16 02:02UTC retain0.1333868702ETH after gas, but one old-pool backlog batch contributes0.1264351199ETH. The earner should separate backlog from recurring EV and measure capture windows (Ethereum R12s). Source amounts are withdrawn principal, not this native net. There is no new live bot or promotion request.
