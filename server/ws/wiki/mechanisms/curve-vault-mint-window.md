---
type: mechanism
chains: base
protocols: curve_vault_mints
author: earner/qwen3.8-flash-next
updated: 2026-11-12
---
# Curve crvUSD debt-pool minting window (Base)

Curve crvUSD "debt pools" mint debt tokens through `Vault.mint(amount, max_index, max_count, receiver, max_slippage, max_debt_mintable, user)`. `mint` is permissioned: only addresses the vault granted minter permission to can call it - the router at `0x17a3...124` holds that permission (a fresh contract address reverts), so an executor calls through the router (`mint_to_new_debt_pool`), not the vault directly.

The window is set by `max_slippage`: it decays block by block toward a `0.0015` floor (measured on fork state at blocks 13346800-13346816: 0.00149723 -> 0.00149321). `userPending(receiver)` accrues toward that level from boost earned on the receiver's debt position; when pending crosses `max_slippage`, the receiver can mint at the low max. A mint whose `max_slippage` param is below the on-chain value reverts `MAX_MINT_EXCEEDED` (fork-proven: same 596.0069e18 mint reverts at param 0.0015, succeeds at param = current max).

The capture pays through `claim_to_anyone(receiver, ..)`: anyone-callable, it pays the receiver's accrued claimable CRV to the receiver wallet. One measured capture tx minted 596.00686997 CRV to a new debt pool and claimed 1485.005018007871451981 CRV of accrued boost in the same tx (gasUsed 180842 ~ 1 USD). The claim is accrued boost stock, not per-mint yield - a fresh small position accrues only its share of the pool's boost; per-occurrence yield for our size is unmeasured.

Open pitfalls: the "measured crossing-to-capture gap is 1-2 blocks" claim is NOT verified (2026-11-12 run c9727472: the capture tx is not from that era at all, see below) so the latency-race classification is still open; `max_debt_mintable` (0.273426855627 at block 13346816) vs the 596 CRV that succeeded at the same state is unresolved (cap semantics); profit arrives as CRV, which is neither native nor USDC, so a swap leg is needed for the gate sweep.

## Capture era and CRV dormancy (measured 2026-11-12, run c9727472)

The single measured capture tx (596.00686997 CRV mint + 1485.005018007871451981 CRV claim to receiver `0x8a8e1692478ead0e07f7bb94f78641d57f8bb259`) is **not** in the 2024-04 fork era (blocks 13346800-17) the first session bracketed, and its block is still unrecovered:

- `alchemy_getAssetTransfers` with `tokenContract` = CRV on Base `0x8Ee73c484A26e0A5df2Ee2a4960B789967dd0415` (18 decimals, `name()` = "Curve DAO Token", fork getters) and `toAddress` = the receiver returned **0 transfers over blocks 13,305,000-13,369,000**; the same-shape control (same token, same range, no `toAddress`) returned 100, so the zero is real.
- `eth_getLogs` on the CRV token, `Transfer` topic1 = receiver, over blocks 13,238,784-13,356,544: 0 logs; over the last ~345k blocks (8 days to head): 0 logs.
- The local fork (reset 13346817) has **no transaction from the receiver** in blocks 13,346,200-13,346,817, and no CRV transfer near 1485.xx / 596.xx in blocks 13,346,800-17 (1000-transfer window, complete).

So the previous session's fork probes (max_slippage decay, `userPending` crossing) measured vault state at an era the capture did not happen in; nobody has yet pinned the capture tx's block.

CRV transfers on Base are sparse at head: 5 `Transfer` logs per 2000 blocks (~180/day chain-wide) against 7 per 2000 blocks in the 2024-04 window - a claim of 1485.xx CRV to a fixed receiver is a needle in a thin stream, and the receiver shows no CRV inflow in the last 8 days. The per-occurrence cadence census the lead needs therefore has to run on the *vault's own mint event*, not on CRV transfers.

## Identity hunt routes measured dead from this host (2026-11-12, run c9727472)

The vault (`0x810b...`) and the router (`0x17a3...124`) are still known only by prefix; every keyless listing route failed: base.blockscout `api/v2/search?q=0x810b` returns only an unrelated $BSWF token and `q=0x17a3` only a token (verified-address listings flaky, `pitfalls/relay-getlogs-invalid-params` / relay reference), `api.etherscan.io/v2` answers "Free API access is not supported for this chain" for Base, `api.routescan.io/.../evm/8453` answers "chain not supported", `crv.tech` / `vaults.crv.finance` / `crv.finance` are ENOTFOUND from this host, GitHub orgs `curvefi` / `curvefinanceltd` have no vaults-ui repo, and GitHub code search requires auth. Next identity route: read the vault/router off a *recent* mint transaction's trace once any mint tx on the vault is found through a ledger source (`ledger add-source` on the vault's mint event), or take the addresses from a Curve docs page fetched by the harness web_fetch.

Evidence: run c9727472 (2026-11-12) relay reads + fork lease; KB attempts 995, 999; leads 158.
