# Decision: demote

Run: f43c93536e664f1f852be25886ffac07 (2026-11-11 UTC)
Next review: none; archived.

The named payout route has no demonstrated poll-catchable liquidation. Lead 147 was changed to `blocked_infra` after placement. Attempt 943 used Morpho's own health rule at the parent blocks: five sampled captures, including the two whale captures, were healthy at C-1 (3.87–6.8% cushion). The claimed >=8192-block windows in the README used repayment feasibility rather than the protocol's liquidation eligibility. On the fork at 26353673, the proposed executor action reverted `HEALTHY_POSITION`; only replay of the incumbent transaction in its capture block succeeded. The sampled route is a same-block eligibility race excluded by `decisions/human/2026-11-12-morpho-stop-researcher-runs.md`. Its counted poll-compatible EV is zero versus 120,000 CU/day (~$0.064/day at $0.53/M CU). Paper logs also show repeated `aggregate-revert` with `kept:0` through 22:11Z, so detection is not sound. Static manifest check passed, but these are decisive blockers. No fork rerun is needed to establish the later lead classification.
