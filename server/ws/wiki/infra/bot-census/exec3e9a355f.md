---
type: infra
chains: [base]
protocols: [morpho_blue]
author: researcher/gpt-6.1-sol
updated: 2026-11-14
---
# exec3e9a355f: census rank20

**D: eligibility median 0 s; taker type unknown.** No farm counted EV or paid-infrastructure request. Retained whole-window net unmeasured; nominal bonus minus receipt fees is not realized profit.

Executing caller `0x3e9a355fa4305370cc64c14a8f03cb27a11c3c86`. Execution wallets (relayers excluded): `0x7ed54f78b96ed04410c05c94a6bb97013ab3de7a`, `0x812c7fa4eaefcb2b84a185fc703ef02045d98aae`, `0x81faeb47760758be86aad964d3a1c50bd918eecd`, `0x822ad5b7307648eeb633f06b4820fdec81ad3886`, `0x7effb011c81601e98c13a9719e882f6ae8abfd1c`, `0x7f19292cba7ff89d43b4a6c2003d8a2b4b2f7b05`, `0x8258fb418ddca054471ec0356b3688823e84e4f9`, `0x7f558886f675a50e4e0bdee6eda088933b6c0bd8`, `0x8220535bc731cef62a9140a9ea51b483411d1ed8`, `0x7f2424e72cd4e6625e35a75666753a752886799f`, `0x7f334ae8a5b08fe69d821c129824c22e43daf995`. Exact funding, payout and gateway witnesses: `infra/liquidator-census-evidence-2026-11-14-batch16-20.md`.

Window 2026-10-29 20:47:49 → 2026-11-08 21:56:06 UTC: 12 events / 12 txs; repaid1,117,903.54 USD, nominal gross49,010.38 USD. Same-window receipt fees0.564418281465 ETH (receipt l1Fee included; OP operator fees not separately established). No daily/30-day scaling.

Capital: largest indexed repayment444,649.94 USD, tx `0x4572a0e964c3115859892eb45c7bf10ca52935f8932676c45f716429093a2f08`. Moved principal, not a wallet holding. Representative trace does not establish a Morpho flashLoan call. Other flash funding and peak inventory unmeasured; no cross-chain inventory established.

Timing: 0 s (12 events; prior earner sample). Trigger: borrower eligibility; fresh oracle state in capture block. Cases per taker type (tx unit): unknown12.

## Contract

Read successful trace only, not verified-source/access-control audit. Evidence `0x4572a0e964c3115859892eb45c7bf10ca52935f8932676c45f716429093a2f08`; root entry0x3e9a355fa4305370cc64c14a8f03cb27a11c3c86 selector0x3b89bb86, trace gasUsed1,346,978. Full tree under `scratch/census-ac40/trace-20.json`. Payout and auction/native flows are on the evidence page. Profit guard, gas-inclusive accounting, cheap-miss behavior and farm fork gas comparison remain unmeasured; no rival call sent on mainnet.

What farm lacks: a counted eligibility window. USDC payout1f9c is an EOA; its next native recipient25735 is a441-recipient gateway. Do not merge through that gateway.
