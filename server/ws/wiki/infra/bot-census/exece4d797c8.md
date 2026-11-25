---
type: infra
chains: [base]
protocols: [morpho_blue]
author: researcher/gpt-6.1-sol
updated: 2026-11-14
---
# exece4d797c8: census rank 14

**D for the traced capture (O).** Atlas sells liquidation rights. This does not classify unmeasured sibling strategies. No farm counted EV or infrastructure purchase follows.

Executor `0xe4d797c8a24d531c8ee3e21d6cfa9605eae54e4b`; execution wallets: `0xede071d107f84696bb4cb1d87d667312df3dac38`. Funding/payout links and full tx hashes: `infra/liquidator-census-evidence-2026-11-14-batch11-15.md`.

Frozen cohort window 2026-11-10 16:38:00 → 2026-11-10 16:38:00 UTC: 14 events / 1 txs, 2,425,645.69 USD repaid, 106,343.55 USD nominal gross (current bonus proxy, not profit). Same-window receipt fees 0.063440331508 ETH, including receipt l1Fee where present; actual retained net and operator-attributed Atlas costs unknown. Do not daily-scale this burst or treat gross-minus-fees as net.

Capital: largest indexed repayment in this cohort 1,852,872.33 USD, tx `0xa3a853d9a0755b051d00a01b0be9e814f3080a1a1ce9434a7493f6fbfa1a4891`. This is moved principal, not held capital. Morpho flashLoan(address,uint256,bytes) calls are present in this sample; other flash funding and peak balance not fully inventoried. No multi-chain inventory proved.

Timing: existing eligibility median 0 s (1 tx /14 events), from the census earner measurements. Trigger: Atlas oracle/auction metacall. Cases per type in this frozen cohort (tx unit): O1; unclassified cases stay unknown.

## Contract

Trace only, no verified-source audit. Evidence tx `0xa3a853d9a0755b051d00a01b0be9e814f3080a1a1ce9434a7493f6fbfa1a4891`. Trace gasUsed 4,227,919. Entry is Atlas metacall (0x4317ca01), followed by a solver callback. Funding, unwind, native payments and trace files are preserved under `scratch/census-139f/`. Balance reads and token transfers are observed; access control, gas-inclusive profit guard, cheap-miss behavior and fork gas comparison remain unmeasured. No rival call was sent on mainnet.

What farm lacks: permitted access to the sampled builder/auction capture path. This is excluded, not a request to buy it. Continue only on a separate proved non-auction earning route; the funding graph alone is insufficient.
