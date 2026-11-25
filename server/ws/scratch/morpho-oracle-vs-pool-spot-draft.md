---
type: pitfall
chains: [ethereum]
protocols: [morpho_blue]
---

# Morpho liquidation sizing uses the market oracle; the realized UniV3 delta can diverge

Conclusion: when a Morpho liquidation executor sizes the repayment from the **market oracle
price** (1e36 USDC-per-collateral) but sells the seized collateral on a **UniV3 pool spot**,
the realized executor-token delta can differ from the oracle-sized profit by tens of percent —
favourably or unfavourably. Size and set floors on the conservative oracle value and treat the
pool-spot outcome as measured, not as the sizing basis.

Measured (run 95d60886, local fork reset to the real parent block, no state/time tweaks):
pinned WETH/USDC market, winner block 26300862 (tx
0x97a32346a6a6c39113ea005cfe1c7329d5a3e2fed2a778ff3bd97f929a4a7679). The market oracle at the
parent read 2264.92 USD/WETH; the UniV3 WETH/USDC 0.05% pool spot was ≈ 2560 USD/WETH
(+13 %). Final-size cap 398 USDC repayment (capital_limited, seized 0.183427573279480961 WETH):
oracle-sized proceeds 415.448849 → oracle profit 17.448849 USDC; the executor's realized USDC
delta was **+71.731107** (swap proceeds ≈ 469.7 at pool spot) — 4.1× the oracle estimate.
Success tx 0xede2f12f8793e4f41120d855de4051b025a6cf827fc6acf781903cc309ce689c (era parent base
fee) and 0xc3325eb49a9af13cac968d32af70c999edd904503c5ae831cc84db34bff6cdf8 (era winner-block
base fee), gas 306636.

Consequences for a bot:
- A NO_PROFIT guard floor set from the oracle estimate alone can be BELOW the realized delta
  (this run's first attempt used a 29 USDC guard floor and the guard itself liquidated, delta
  71.73) — set guard floors above the oracle estimate by the plausible spot divergence, and
  disclose the re-run when a floor was corrected.
- The converse risk (pool spot BELOW oracle) makes the realized delta smaller; the on-chain
  minProfit floor then reverts NO_PROFIT and only gas is lost — the loss mechanism is
  unchanged, which is exactly why the floor must be affordable on the ORACLE estimate.
- Market oracles on Morpho are push prices and can lag a fast pool move by minutes; the
  oracle-vs-pool gap measured here (13 %) is not exotic at high base-fee eras with volatile
  prices. Evidence: scratch/morpho-eth-natural2/natural-big.json (+ log), same fork hashes
  recorded in the morpho-watcher-ethereum manifest fork_evidence.
