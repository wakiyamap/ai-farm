---
type: mechanism
chains: base
protocols: curve_vault_mints
---

# Curve crvUSD debt-pool minting window (Base)

Curve crvUSD "debt pools" mint debt tokens through `Vault.mint(amount, max_index, max_count, receiver, max_slippage, max_debt_mintable, user)`. `mint` is permissioned: only addresses the vault granted minter permission to can call it - the router at `0x17a3...124` holds that permission (a fresh contract address reverts), so an executor calls through the router (`mint_to_new_debt_pool`), not the vault directly.

The window is set by `max_slippage`: it decays block by block toward a `0.0015` floor (measured on fork state at blocks 13346800-13346816: 0.00149723 -> 0.00149321). `userPending(receiver)` accrues toward that level from boost earned on the receiver's debt position; when pending crosses `max_slippage`, the receiver can mint at the low max. A mint whose `max_slippage` param is below the on-chain value reverts `MAX_MINT_EXCEEDED` (fork-proven: same 596.0069e18 mint reverts at param 0.0015, succeeds at param = current max).

The capture pays through `claim_to_anyone(receiver, ..)`: anyone-callable, it pays the receiver's accrued claimable CRV to the receiver wallet. One measured capture tx minted 596.00686997 CRV to a new debt pool and claimed 1485.005018007871451981 CRV of accrued boost in the same tx (gasUsed 180842 ~ 1 USD). The claim is accrued boost stock, not per-mint yield - a fresh small position accrues only its share of the pool's boost; per-occurrence yield for our size is unmeasured.

Open pitfalls: the measured crossing-to-capture gap on the sampled occurrence is 1-2 blocks (latency race risk, decision 2026-11-12 - confirm with more pairs); `max_debt_mintable` (0.273426855627 at block 13346816) vs the 596 CRV that succeeded at the same state is unresolved (cap semantics); profit arrives as CRV, which is neither native nor USDC, so a swap leg is needed for the gate sweep.

Evidence: run 1847120f (2026-11-12), fork probes at reset 13346816 and KB attempts 995, leads 158.
