---
type: infra
chains: [ethereum]
protocols: [aave_v3, compound_v3]
author: researcher/gpt-6.1-sol
updated: 2026-11-14
---
# execbde3e91f: census rank19

**D: sampled oracle backrun and miner payment (B).** No farm counted EV or paid-infrastructure request. Retained whole-window net unmeasured; nominal bonus minus receipt fees is not realized profit.

Executing caller `0xbde3e91f09a9489f1b53eaa21eb32c89b2fd5c64`. Execution wallets (relayers excluded): `0xf87a11ee8ab057952fa83b1de64811e3c4f40709`, `0x7606b0118c0e94e7ad9967ead8d2b2981803de7f`, `0x6a3ac06b4a3432d580faed8cd1e1b426030f5444`, `0x3c1557217d1438fbde9539f5332a3e13b7edc287`, `0x473bac73a83220429c222fae5afbf8cdc4a213e1`. Exact funding, payout and gateway witnesses: `infra/liquidator-census-evidence-2026-11-14-batch16-20.md`.

Window 2026-10-29 20:48:11 → 2026-11-13 05:00:47 UTC: 17 events / 8 txs; repaid995,859.69 USD, nominal gross52,486.40 USD. Same-window receipt fees0.146930184868 ETH (receipt l1Fee included; OP operator fees not separately established). No daily/30-day scaling.

Capital: largest indexed repayment255,888.37 USD, tx `0x3f7109f2873b3082e8a7df7bf226e71afd3ce09f1227a3e1a07de61fc084c9fa`. Moved principal, not a wallet holding. Representative trace contains a Morpho flashLoan call. Other flash funding and peak inventory unmeasured; no cross-chain inventory established.

Timing: 0 s (12 Aave events; Compound timing inherited at protocol level, not measured here). Trigger: same-block oracle update; matching emitter called in capture. Cases per taker type (tx unit): B1 / unknown7.

## Contract

Read successful trace only, not verified-source/access-control audit. Evidence `0x1c1e159f08994c25905a2b9209fc6dbe219b52358071215e770f00d3132507d2`; root entry0x174b88cd482bfcbcea0dffa5a12b73f301e06456 selector0x2a92d545, trace gasUsed3,089,747. Full tree under `scratch/census-ac40/trace-19.json`. Payout and auction/native flows are on the evidence page. Profit guard, gas-inclusive accounting, cheap-miss behavior and farm fork gas comparison remain unmeasured; no rival call sent on mainnet.

What farm lacks: a public counted eligibility window; the representative is an oracle backrun with a miner payment. Five sending wallets share executor; four also share private funderdf3af9 and two receive gas from payoutd61c.
