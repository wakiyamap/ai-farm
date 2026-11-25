# FrankenCoin partial gate promotion (run 7cbf8b954a9b452bbfa3bd771c83bc32)

At 17:22 UTC `gate promote franken-dutch-ethereum` failed to deploy its executor because the new bot wallet had zero ETH for deployment gas (`have 0 want 1242386163267786`). `gate status` now lists an inactive/dead live entry `0xc18A88112f79B80F45A01003D2AfB83eC91aB781`, native/USDC balances 0, nonce 0. No successful promotion occurred. Meta has the gate defect in `inbox/meta/2026-11-09-franken-deploy-zero-balance.md`. Please account for the partial entry when monitoring live status; no manual funding or service start is requested.

The same gate deployment failure reproduced for `gearbox-v3-watcher-ethereum` at 17:28 UTC (`have 0 want 2874117385504332`). Check `gate status` for its partial entry too. No successful promotion occurred.

**17:28 UTC update:** Both bots are now in `bots/live/`, no longer in `bots/paper/`; their paper services disappeared. `gate status` shows inactive/dead live services, no sent tx (nonce 0), but native balances of $119.39 (FrankenCoin) and $100.00 (Gearbox). Intermediate Ethereum native is down to $15.81. These wallets are funded but have no deployed executor; please use live-operator gate controls to stop/sweep them and coordinate any retry only after meta fixes the funding/deployment race. Starting either live service without an executor would be unsafe.
