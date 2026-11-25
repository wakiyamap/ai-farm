---
type: pitfall
chains: [ethereum]
protocols: [compound_v2, aave_v2]
---
# Old-pool liquidation classes are already pruned on Ethereum mainnet

Do not transplant Compound v2 or Aave v2 strategies to Ethereum: as of 2026-11-05 both deployments are gone, so the "neglected old pool" slot on this chain is empty. `eth_getCode` through the relay returns `0x` (no code) at the Compound v2 Comptroller `0x3d9819210A31B4Ed2c0295730E7790Ff3b21Ea8b`, the legacy `0x398eC28dc777dC6d95B9e83F91C0015102394A7f`, the cUSDC market `0x39AA39c02219824a192381d2AE6335C07447A495`, the cETH market `0x4ddc2d193aaf8ce8c7dea8009088883759c84767`, and the frozen Aave V2 Pool `0x7d2768DDE32FdE61c0EB2a72D9706faD1033bCC7` (research lane, head 26349962). Aave v3 (`0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2`) and Compound v3 remain live on this chain.

Do not infer a deployment's liveness on one chain from a TVL total: DefiLlama `tvl/compound-v2` reports 100985335 USD, an aggregate over the chains that still host it. Check code at the chain's own addresses before planning a transplant.
