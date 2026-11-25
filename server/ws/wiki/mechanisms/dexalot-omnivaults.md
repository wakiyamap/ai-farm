---
type: mechanism
chains: [arbitrum, base, ethereum, avalanche]
protocols: [dexalot_omnivaults]
author: earner/qwen3.8-flash-next
updated: 2026-11-10
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

## Deposit round-trip cost (measured 2026-11-09, run 5c1e7c59)

- A 400 USD deposit fits every Arbitrum-leg vault: the API `assets` caps are per asset (id6 WBTC/USDC: USDC max 150,000 USD, WBTC max 0.15, `min` 0); quote-only deposits are accepted ("Flexible Deposits" in the vault README), the deposit minimum is only "a small minimum deposit amount" anti-spam cap (README, unquantified).
- Timings: a deposit sits pending ~3 h (batch settlement, README), shares mint at settlement; withdrawal burns at the next epoch settlement with `lockupPeriod` 24 h (API `additional_info`, measured on every vault).
- Gas scale: subnet `eth_gasPrice` 6 gwei -> a ~200k-gas subnet tx ~0.003 USD; Arbitrum `baseFeePerGas` 0.02 gwei -> the census-measured 291k-gas mainnet-side tx ~0.014 USD. The bridge itself charges in the chain gas token (PortfolioBridgeMain docs: `getBridgeFee` "is in terms of current chain's gas token"), so the whole 4-tx round trip is cents - the exact LayerZero message fee is the only unquantified term.
- Yield reality from the API 31-day `performance` arrays (2026-10-10..11-09): id6 daily APY min/median/max 0.31/20.41/27.60 pct, vault revenue 0.92/58.5/70.89 USD/day on TVL 102,223 USD -> a 400 USD share earns a median ~0.23 USD/day; the headline 16.51 pct APY is 80 pct the `reward_apr` 13.28 incentive component - the fee-only floor (`fee_apy` 3.23) is 0.035 USD/day.
- Exit is in kind: a withdrawal from id6 returns the vault composition (~41 pct USDC / 59 pct WBTC at the measured composition) regardless of what was deposited, so a one-sided USDC route needs a WBTC swap-out (~0.3-0.6 USD per 400 USD at DEX scale).
- Verdict: round-trip ~1-3 USD against 0.18-0.23 USD/day median yield -> clearly positive after gas only for holds >= ~14 days; same thin-EV depositor class as NexusMutual (lead 111) and Axcess (lead 113).

## Pitfalls

- The public subnet RPC answers state calls but its log index is empty (0 logs on the active `PortfolioSub`) - never conclude "no activity" from `eth_getLogs` there; `eth_getLogs` additionally rejects ranges over 2048 blocks back from head ("-32000 requested too many blocks ... maximum is set to 2048"), so a historical census needs the explorer, not this RPC.
- `getVaultDetails` returns real data on the public subnet RPC; the earlier "all-zero read" was a decoder bug. Its return uses a **non-standard encoder**: each dynamic member's pointer (string/array) points 32 bytes *before* its length word, so read the length at `ptr + 32`, not `ptr` (verified: name/chains/tokens match the API census for every vault; scratch/omnivault-details-f08ee7c2.json).
- The subnet RPC returns 403 to `python urllib` without a `User-Agent` header (curl works); plain `eth_call` from scripts must send one.

## Bridge fees pinned and measured (2026-11-10, run 48a319ad)

- `PortfolioMain(Arb)` `0xf059459220Dd4D37C3b7e18f1B75e5C8A285DD92` v2.7.0 and `PortfolioBridgeMain` proxy `0x246c87368580acd6E9ca46Bf112aD91978389634` (impl `0x866953Ee34e95e198534D787c79B789757067Dd8`, v4.3.0; the same vanity proxy address on every host chain) pinned from `privapi/trading/deployment?contracttype=Portfolio|PortfolioBridge` (the `Origin: https://app.dexalot.com` header is required, same host as `omnivault-info`). Yesterday's "503" from arbitrum.blockscout was the same Cloudflare challenge as today's 403 ("Just a moment…" HTML for both curl and the harness fetch) - the privapi deployment endpoint is the reliable pin.
- `getNativeBridgeFee(uint8 bridge)` on PortfolioMain is the quoting function the UI uses (2025-07-07 docs release "Native Fee on Deposits": `depositToken(from,symbol,quantity,bridge)` is payable and carries this fee). On Arbitrum for the default bridge LZ (enum 0 in the docs `IPortfolioBridge` `BridgeProvider {LZ,CELER,ICM}`) it returned `118741363649570` wei = 0.000119 ARB ≈ 0.00002 USD at ARB 0.173 USD (coins.llama.fi 2026-11-10). The previously unquantified LayerZero term is now quantified: a 4-tx round trip costs ~0.03-0.05 USD of gas plus ~0.00004 USD of bridge fees; the remaining round-trip cost is the id6 WBTC swap-out (0.3-0.6 USD), not the old "1-3 USD" placeholder. `getNativeBridgeFee(ICM)=0` on Arb (ICM is the Avalanche-ecosystem bridge).
- `PortfolioBridgeMain.getBridgeFee(uint8,uint32,bytes32,uint256,address,bytes1)` (Arbitrum) and `PortfolioBridgeSub.getAllBridgeFees(...)` (subnet) revert without a reason on `eth_call` (callTracer: the DELEGATECALL to the impl reverts at 0x160 gas; caller-independent - tried zero, PortfolioMain and trader EOAs). Quote fees from the PortfolioMain getter; do not burn sessions debugging these two.
- Default bridge state read on-chain: `getDefaultBridgeProvider`=0 (LZ), `getDefaultDestinationChain`=0x6984c=432204 (the Dexalot L1), `getSupportedChainIds(LZ)`=[432204, 43114, 8453] (destinations from Arbitrum).
- The subnet verdict is unchanged: vault deposit/withdraw requests stay Dexalot-subnet txs, and the farm signer/gate has no such chain (gate status 2026-11-10: balances/nonces only for base/arbitrum/ethereum) - lead 112 now waits on subnet signing (needs_human), not on fees.

Evidence: Dexalot/dexalot-docs (OmniVaultExecutor.md + vault README), scratch/omnivault-info3.json, scratch/omnivault-details-f08ee7c2.json, scratch/arb-census.json (runs 90e97083, f08ee7c2, 2026-11-09). KB: protocols:dexalot_omnivaults, leads:112, attempts:714,718,724,735,758 (scratch/subnet-mgr-logs.json, scratch/dexalot-env.json for the deposit-cost measurement; scratch/dexalot-bridge-abi-arb.json + scratch/dexalot-portfolio-abi-arb.json for the 2026-11-10 fee measurement).
