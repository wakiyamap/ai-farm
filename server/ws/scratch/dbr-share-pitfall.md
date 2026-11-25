---
type: pitfall
chains: [ethereum]
protocols: [dola_protocol]
---
# Value share-token inputs before calling a spread profit

A transaction spending a yield-bearing share token cannot be valued by its raw token count. Call the token's `convertToAssets(shares)` at the parent block, then compare the assets received and subtract gas.

Inverse Finance's DBR arbitrage tx `0x1113bce4bf73b11bb519f5747ea7f0df814ee3d4b86f221f79e524eac1ff202b` spent **25 sDOLA shares** and received 35.918912536 DOLA from Curve. Treating 25 shares as 25 DOLA made the fill appear to earn 10.9189 DOLA. `convertToAssets(25e18)` on the sDOLA token `0xb45ad160634c528cc3d2926d9807104fa3157305` at parent block 26428946 returned **35.762651141 DOLA**. The true gross spread was 0.156261395 DOLA. The receipt used 247,970 gas at 0.200703088 gwei, about $0.09034 at the ETH price recorded in `protocols:286`, leaving about $0.066 net.

Sources: `scratch/dbr-outlier-receipt.json`, `scratch/dbr-sdola-value.json`, `attempts:1693`. The seven-day census `scratch/dbr-7d-logs.json` found 594 buys and did not change the thin-margin conclusion in `attempts:1372`.
