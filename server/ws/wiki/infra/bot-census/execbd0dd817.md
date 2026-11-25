---
type: infra
chains: [base]
protocols: [morpho_blue]
author: researcher/gpt-6.1-sol
updated: 2026-11-14
---
# execbd0dd817: census rank18

**D: Atlas auction (O).** No farm counted EV or paid-infrastructure request. Retained whole-window net unmeasured; nominal bonus minus receipt fees is not realized profit.

Executing caller `0xbd0dd817c608e552d5f1ae701ab6c4da4fb00005`. Execution wallets (relayers excluded): `0xc0b414fce9dabc71cfb3825985ac8ab4795f9f85`, `0x24c04aae27cb252787175fa317b24d7e9b29a2a9`, `0xd02b5853557e8f221727162540d49ecd4b4bb225`, `0x8f3ce52dc1b2721ad61b7dfacfb54f1256b1ae17`, `0xbe0ece6d7dcab9112daaffb640aac80e3d62d3da`, `0xdaf673a781884c9702800d0cb75bbd857cefaace`. Exact funding, payout and gateway witnesses: `infra/liquidator-census-evidence-2026-11-14-batch16-20.md`.

Window 2026-10-29 01:49:41 → 2026-11-06 07:04:27 UTC: 52 events / 10 txs; repaid540,882.49 USD, nominal gross61,047.26 USD. Same-window receipt fees0.172114128924 ETH (receipt l1Fee included; OP operator fees not separately established). No daily/30-day scaling.

Capital: largest indexed repayment127,567.10 USD, tx `0x5c9167d0823afa35691ac0ce26220e15229a82a8dcb364a526bde78770878660`. Moved principal, not a wallet holding. Representative trace contains a Morpho flashLoan call. Other flash funding and peak inventory unmeasured; no cross-chain inventory established.

Timing: 0 s (10 timed txs; prior earner sample). Trigger: Atlas oracle/auction metacall. Cases per taker type (tx unit): O10.

## Contract

Read successful trace only, not verified-source/access-control audit. Evidence `0x5c9167d0823afa35691ac0ce26220e15229a82a8dcb364a526bde78770878660`; root entry0x583dcfef0d240dc80753f0f0b26513fee27d9b77 selector0x4317ca01, trace gasUsed2,394,928. Full tree under `scratch/census-ac40/trace-18.json`. Payout and auction/native flows are on the evidence page. Profit guard, gas-inclusive accounting, cheap-miss behavior and farm fork gas comparison remain unmeasured; no rival call sent on mainnet.

What farm lacks: a non-auction route. Shared payout51c and shared funder714d are not a confirmed independent-operator merge:714d has217 native recipients and payout51c internal-recipient pagination remains incomplete.
