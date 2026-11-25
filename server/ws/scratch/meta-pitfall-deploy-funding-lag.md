---
type: pitfall
chains: [base, arbitrum, ethereum, bsc, polygon, avalanche, optimism, hyperevm, elysium]
protocols: []
---
# Executor deploy right after funding: a node can still read the old balance

**Conclusion:** at `gate promote`, the gate funds the bot wallet and then sends the executor deployment from it. The node that takes the deployment can lag the one that confirmed the funding and reject it with `insufficient funds ... have 0`. Since phase 15b (human, 2026-11-18) the gate waits until the bot wallet reads at least the deployment's worst-case gas and resends the same signed bytes while the node says "insufficient funds" (nonce unused, nothing accepted). After one minute it gives up: gate.log `deploy_executor_not_sent`, exit 2, nothing sent from the bot key, and the bot is a **partial promotion** (funded, no executor).

## What to do

- Reviewer after a promote with exit 2 / `deploy_executor_not_sent`: report it in `inbox/human/` as a partial promotion (phase 10f); `gate-ctl deploy <id>` (human / live-operator) finishes it. Do not re-run `gate promote`.
- Any other send error is raised as before and is not this case.
- Bot code: never assume `EXECUTOR_ADDR` is set after a partial promotion; exit with a clear message if it is unset (builder rule).

## Evidence

- 2026-11-17 20:21Z, trial-aave-optimism: funding receipt seen, deployment rejected `insufficient funds ... have 0` (paper-reviewer run 35ea4b72, reported to human). Fix: `inbox/meta/2026-11-18-phase15b-deploy-wait-park.md`.
