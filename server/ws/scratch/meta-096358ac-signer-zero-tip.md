---
type: pitfall
chains: [any]
protocols: []
---
# Signer: `max_priority_fee_per_gas=0` is sent as maxFee/10

**Conclusion.** `/opt/farm/lib/farmbot_signer.py` `send()` builds
`maxPriorityFeePerGas = max_priority_fee_per_gas or max_fee_per_gas // 10`. An explicit `0` is falsy, so a bot asking
for a zero tip bids **a tenth of its maxFee** instead. To bid (almost) nothing, pass `1` (wei). Until the library is
changed, a manifest or README that says "priority fee 0" is wrong if the code passes `0`.

- Loss stays bounded: the signed `maxFeePerGas x gasLimit` (L) is unchanged; only the tip and therefore the
  per-send cost and ordering differ from what the bot states.
- Matters most where a zero tip is the strategy (behind-the-oracle sends, OP Stack first-block jobs:
  `pitfalls/opstack-first-block-index.md`) and on ethereum, where maxFee/10 can be a large tip.
- Reviewers: grep the bot for `max_priority_fee_per_gas=0` / `priority ... 0`.

**Evidence.** Found by paper-reviewer-claude run 51c32068 in trial-bim-harvest-base (manifest "priority fee bid 0%"),
inbox note `inbox/meta/2026-11-18-signer-priority-zero.md`. Library fix (`is None` test) proposed to the human
2026-11-18 (meta run 096358ac); the library is outside the workspace.
