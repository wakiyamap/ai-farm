**Decision: promote** — 2026-11-20T22:33:30Z, run `2bbc606422a846a4bf7c6120107f9ea9`. Cheap-chain trial.

The missing manifest has been added; `manifest-check` PASS. Base, `capital_usd: 18`, `max_loss_per_tx_usd: 1`, `allowed_contracts: []`, 59/60 live trial ids before this promotion (`gate status` at 22:33Z). The intermediate Base wallet held $33.35, enough for $18 plus deployment gas. The route uses public Morpho flash loans, ICHI deposit/withdraw and a pool swap in one owner-only Solidity transaction. The human allowed this ICHI price-arbitrage class in `decisions/human/2026-11-21-ichi-yes-peapods-fee-no.md` §1. No pending transaction watching or price manipulation in the code.

I reproduced the current artifact on the Base fork at block 57,504,773: deploy `0x6b5a9f3a1d0aef3028e2391c5d35a8f7e5aa9e8c87b032d049ad7ec1a198476d`; success `0x2067c213c152d333af8df213568c2711467f722581738d5c8df9fe6998a42fdb`, owner +0.000474922571 ETH before fork gas, 809,776 gas. Excessive minProfit `0x531704f82d0d2f75c62d7a8ecc0a06e3659548c813c1d7b601f1d3e99d53fc79` and non-owner `0x958facd5ec69989bd12684bf894e555f47c236bba45c74b7fec3402e7bb030c7` reverted; same route after take reverted. Executor native/WETH/USDC/cbBTC/shares and vault/Morpho approvals were zero after success. The fresh bot-code selftest matched cast calldata for all 37 candidates, scan calldata, selectors and artifact runtime, and the paper scan answered in 0.4 s. Historical paid incumbent tx `0x69da87f3e3a75ebee521dc271f585cda4ef5e1aaf31ab8f84061e4b78306c535` took this entry in the last 7 days: about $0.760 gross against 735,044 gas at 0.0153 gwei plus L1 fee, about $0.018 total at $1,600/ETH.

Loss guard: flash principal is repaid within `run()` or the transaction reverts; `profit > 0 && profit >= minProfit` is checked after repayment, and gains reach the wallet as native or USDC. The bot sends only after `eth_estimateGas`, signed fee cap plus `getL1FeeUpperBound(500)` is held below $0.95 at pool ETH/USD ×1.15, priority bid ≤35% of gross, and simulated gross ≥1.2× that cap. Base's native wallet is capped at $18 by the gate. The paid receipt above has L1 fee 44,000,669,355 wei and no operator-fee field. CU guard wraps every RPC call, including startup; 27-second scan polls cost 3,200 × 26 ≈83,200 CU/day, plus price and opportunity reads, code cap 98,000 CU/day. Paper service is running with regular scan heartbeat and no loop errors; natural capture and reaction-time EV are waived for this trial class.

next_review_at: null

**Decision: fix** — 2026-11-20T20:57:00Z, run `36da3a59002d4657b5076338df39938d`.

`manifest.yaml` is missing. `python3 tools/manifest-check.py bots/paper/trial-ichi-vault-base/manifest.yaml` fails with “No such file or directory.” Add the manifest and pass the static check before review can continue. The paper service is inactive.

next_review_at: 2026-11-20T22:00:00Z
