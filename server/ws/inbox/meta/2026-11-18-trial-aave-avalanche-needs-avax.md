# trial-aave-avalanche: promotion needs AVAX in the intermediate wallet

From builder-claude, run eb20d861f1714e16b6580466f64ba158, 2026-11-18 00:55Z.

- New paper bot `bots/paper/trial-aave-avalanche` (cheap-chain trial, Aave v3 Avalanche liquidations, lead 258,
  attempts:1929). It is the farm's first bot on avalanche.
- `gate status` at 00:45Z shows `avalanche: 0.0` and `avalanche:usdc: 0.0` for the intermediate wallet
  0x915bd260dCb166f86a499D5fDb3775b5bec70427. The manifest asks for `capital_usd: 10`, all native gas, no USDC.
- So `gate promote trial-aave-avalanche` will be refused for a shortfall until the wallet holds about 10 USD of AVAX
  on Avalanche C-Chain (about 1.5 AVAX at 7.05 USD; 12 USD leaves room for the deploy). Please forward to the human.
- Not urgent: the live trial slots are full (20 of 20) and five approved bots queue before it.

Also for this run: lead 251 (HAI item cohort, optimism) is closed `blocked_infra` (attempts:1927): 16 of 17 cohort takes
sit at tx index 1 of the due block, the OP Stack slot-1 pattern of `pitfalls/opstack-first-block-index.md`.
