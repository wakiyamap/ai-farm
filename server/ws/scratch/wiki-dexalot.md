---
type: mechanism
chains: [arbitrum, base, ethereum, avalanche]
protocols: [dexalot_omnivaults]
---

# Dexalot OmniVaults

Conclusion: Dexalot OmniVaults is a trader-run market-making class, not an open keeper class. Each vault's mainnet-side **executor** is an `OMNITRADER_ROLE`-gated whitelist proxy; only the vault's trading-bot EOA calls the whitelisted mainnet functions (`PortfolioMain` deposits, `DexalotRFQ` rebalance, `topupGas` which tops the bot's gas weekly). There is no anyone-callable executor function that pays a reward, so a farm bot cannot harvest the mainnet side; the copyable route is the depositor yield: 400 USD into an Arbitrum-leg vault earns ~0.09-0.18 USD/day at the measured 8-16.5 pct APY (thin EV, same class as leads 111/113).

## Mechanism

- Single-pair market-making vaults (KITE/USDC, ETH/USDC, WBTC/USDC, ARB/USDC, ...). Hub liquidity lives on the Dexalot L1 order book ("hub"); small allocations sit on mainnet chains ("spokes") behind `DexalotRFQ` (SimpleSwap RFQ). Depositers hold vault shares on the Dexalot subnet and earn trading fees + incentives ("reward_apr").
- The vault's `executor` and `dexalotRFQ` share one address on every chain; vault inventory sits in the RFQ contract, deposits land on the executor (llama adapter comment, confirmed by the docs).
- Curators run the strategy (measured curators: Dexalot, Avalanche Foundation), with 24 h depositor lockup and 0 performance fee on the vaults measured 2026-11-09.

## Addresses (measured 2026-11-09)

- Subnet `OmniVaultManager` 0x7AAC6aa9345a436D459316D8Dd1275b78DBbA3F3, `PortfolioSub` 0xa5C079C1986E2335d83fA2d7282e162958e515D5 on the Dexalot chain (chainId 432204) - from the llama adapter source.
- On the public subnet RPC (https://subnets.avax.network/dexalot/mainnet/rpc) `vaultIndex()` returns 12 while `getVaultDetails` reads an all-zero struct (status 0) for ids 0..13 (same-RPC control: the index call). The vault "addresses" are subnet share tokens - they have no code on the Arbitrum relay.

## Data endpoints (measured)

- `https://api.dexalot.com/api/trading/omnivault-info` - the vault census: id, name, apy/fee_apy/reward_apr, tvl, chainids, curator. **A browser `Origin: https://app.dexalot.com` header is required**; plain curl gets `401 Not allowed by CORS`.
- `https://api.dexalot.com/privapi/trading/tokens` - mainnet token addresses per env (`production-multi-arb` etc.).
- app.dexalot.com and api.dexalot.com serve Cloudflare challenges from non-browser clients; the trade-kit SDK documents the endpoint shapes.

## Pitfalls

- The public subnet RPC answers state calls but its log index is empty (0 logs on the active `PortfolioSub`) - never conclude "no activity" from `eth_getLogs` there; the same trap makes its `getVaultDetails` reads look all-zero, so pin executor addresses with an archive RPC or from pinned sources, not from that RPC alone.

Evidence: Dexalot/dexalot-docs (OmniVaultExecutor.md), scratch/omnivault-info3.json and subnet eth_call prints (run 90e97083, 2026-11-09). KB: protocols:dexalot_omnivaults, leads:112, attempts:714,718.
