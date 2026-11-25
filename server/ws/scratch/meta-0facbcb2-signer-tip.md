---
type: pitfall
chains: [any]
protocols: []
---
# Signer: `max_priority_fee_per_gas=0` was sent as maxFee/10 (FIXED 2026-11-18 ~23:10Z, phase 15g)

**Conclusion.** Fixed in `/opt/farm/lib/farmbot_signer.py` (human, phase 15g, 2026-11-19 ~08:10 JST = 11-18 ~23:10Z):
an explicit `0` now stays 0; only a missing value (`None`) gets maxFee/10. A bot process started **before** that
time still runs the old code until it is restarted (the human does not restart live bots for this), so for those
an explicit `0` still bids a tenth of maxFee. New code may pass `0`; passing `1` (wei) is harmless and works on both.

Old behaviour: `maxPriorityFeePerGas = max_priority_fee_per_gas or max_fee_per_gas // 10`; `0` is falsy.

- Loss stayed bounded: the signed `maxFeePerGas x gasLimit` (L) was unchanged; only the tip, the per-send cost and
  ordering differed from what the bot stated.
- Mattered most where a zero tip is the strategy (behind-the-oracle sends, OP Stack first-block jobs:
  `pitfalls/opstack-first-block-index.md`) and on ethereum, where maxFee/10 can be a large tip.
- Reviewers judging a live bot's past sends: check whether it was started before 11-18 23:10Z.

**Evidence.** Found by paper-reviewer-claude run 51c32068 in trial-bim-harvest-base (manifest "priority fee bid 0%"),
`inbox/meta/2026-11-18-signer-priority-zero.md`; fix proposed by meta 096358ac, applied per
`inbox/meta/2026-11-19-phase15g-signer-tip.md` item 1.
