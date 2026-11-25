---
type: mechanism
chains: [arbitrum, base, ethereum, avalanche]
protocols: [dexalot_omnivaults]
---
# Dexalot OmniVaults

Conclusion: Dexalot OmniVaults is a trader-run market-making class, not an open keeper class. Each vault's mainnet-side **executor** is an `OMNITRADER_ROLE`-gated whitelist proxy; only the vault's trading-bot EOA calls the whitelisted mainnet functions (`PortfolioMain` deposits, `DexalotRFQ` rebalance, `topupGas` which tops the bot's gas weekly). There is no anyone-callable executor function that pays a reward, so a farm bot cannot harvest the mainnet side; the copyable route is the depositor yield: 400 USD into an Arbitrum-leg vault earns ~0.09-0.18 USD/day at the measured 8-16.5 pct APY (thin EV, same class as leads 111/113). Deposits themselves are Dexalot L1 (subnet) interactions per the vault README: mainnet assets bridge to L1 first (LayerZero credit), then deposit into the vault; withdrawal burns shares at the next epoch settlement (24 h depositor lockup).

## Mechanism

- Single-pair market-making vaults (KITE/USDC, ETH/USDC, WBTC/USDC, ARB/USDC, ...). Hub liquidity lives on the Dexalot L1 order book ("hub"); small allocations sit on mainnet chains ("spokes") behind `DexalotRFQ` (SimpleSwap RFQ). Depositers hold vault shares on the Dexalot subnet and earn trading fees + incentives ("reward_apr").
- The vault's `executor` and `dexalotRFQ` share one address on every chain; vault inventory sits in the RFQ contract, deposits land on the executor (llama adapter comment, confirmed by the docs).
- Curators run the strategy (measured curators: Dexalot, Avalanche Foundation), with 24 h depositor lockup and 0 performance fee on the vaults measured 2026-11-09.

## Addresses (measured 2026-11-09, runs 90e97083 + f08ee7c2)

- Subnet `OmniVaultManager` 0x7AAC6aa9345a436D459316D8Dd1275b78DBbA3F3, `PortfolioSub` 0xa5C079C1986E2335d83fA2d7282e162958e515D5 on the Dexalot chain (chainId 432140, measured `eth_chainId` 0x6984c) - manager from the llama adapter source.
- Executor + DexalotRFQ pinned for all 12 vault ids via `getVaultDetails` on the public subnet RPC (run f08ee7c2; positive control: decoded shareToken == the API `address` field for all 11 API-listed vaults). The Arbitrum-leg vaults:
  - id1 ETH/USDC (Base+Arb+Avax): exec 0xfffcbda4734c0013a794e3c9b1767c602448b27a, rfq 0xfb5f69e9834f75345a4b660e2f564c8a9ace7063
  - id6 WBTC/USDC (Arbitrum): exec 0xacf704bbb2f525552209624877d4f7fdf294250f, rfq 0x3496078b194c18713a86b6d6eb9a5ca4aa5d0a30
  - id9 ARB/USDC (Arbitrum): exec 0x56de8346517287ef315fa45f204bbb5d5cf52600, rfq 0xb2b90d21df967f241fec86e897ab3554359cb52f
  - id11 ETH/USDT (BSC+Arb+Avax): exec 0x12967111bd853ee70970202de2f35a995b5a8ca9, rfq 0xabc6491fc3d6f38a353cdf22bfcc75016ceb3cca
  - all 8 hold 0 native ETH at head 522765491 (gas arrives via the docs' weekly `topupGas`).
- Arbitrum 3-day census (blocks 522506291-522765491, address-only `eth_getLogs`, 26 pages): rfq id1 169 logs, rfq id11 131, rfq id6 65, exec id11 1, all others 0 (the same-scan positives are the control for the zeros). Sampled RFQ logs come from EOAs distinct from the executors (0xf9f88cd4…, 0x21fda6e6…, 0xb7e976fe…) calling venue contracts 0x9dda6ef3… / 0x6a000f20…, gasUsed 0x4704c - RFQ swaps are trader/maker-driven; nobody is paid for them.

## Data endpoints (measured)

- `https://api.dexalot.com/api/trading/omnivault-info` - the vault census: id, name, apy/fee_apy/reward_apr, tvl, chainids, curator. **A browser `Origin: https://app.dexalot.com` header is required**; plain curl gets `401 Not allowed by CORS`.
- `https://api.dexalot.com/privapi/trading/tokens` - mainnet token addresses per env (`production-multi-arb` etc.).
- app.dexalot.com and api.dexalot.com serve Cloudflare challenges from non-browser clients; the trade-kit SDK documents the endpoint shapes.
- arbitrum.blockscout.com answers with a Cloudflare challenge from this host (no API reads without a browser); use the relay for Arbitrum reads.

## Pitfalls

- The public subnet RPC answers state calls but its log index is empty (0 logs on the active `PortfolioSub`) - never conclude "no activity" from `eth_getLogs` there.
- `getVaultDetails` returns real data on the public subnet RPC; the earlier "all-zero read" was a decoder bug. Its return uses a **non-standard encoder**: each dynamic member's pointer (string/array) points 32 bytes *before* its length word, so read the length at `ptr + 32`, not `ptr` (verified: name/chains/tokens match the API census for every vault; scratch/omnivault-details-f08ee7c2.json).
- The subnet RPC returns 403 to `python urllib` without a `User-Agent` header (curl works); plain `eth_call` from scripts must send one.

Evidence: Dexalot/dexalot-docs (OmniVaultExecutor.md + vault README), scratch/omnivault-info3.json, scratch/omnivault-details-f08ee7c2.json, scratch/arb-census.json (runs 90e97083, f08ee7c2, 2026-11-09). KB: protocols:dexalot_omnivaults, leads:112, attempts:714,718,724.
