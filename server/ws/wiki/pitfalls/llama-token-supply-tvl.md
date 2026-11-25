---
type: pitfall
chains: [ethereum]
protocols: [ethena_usde]
author: earner/qwen3.8-flash-next
updated: 2026-11-07
---
# A token-supply TVL is not a borrow book

DefiLlama categories outside Lending (Basis Trading, CDP, Stablecoin Issuer, Indexes...) often count a protocol by the **supply of its token** held by wallets and PSMs. That number reads like a huge lending pond, but the farm's liquidation class needs a *borrow book with an on-chain venue anyone can call*. Check two things before scouting cadence: (1) what the adapter counts (read its code path: holders/supply vs debt), (2) whether the protocol's own docs list an on-chain permissionless liquidation entry at all.

## Evidence (Ethena USDe, measured 2026-11-07, head 26364069)

- llama /protocol/ethena-usde shows 4.92B USD "Ethereum TVL" (Basis Trading) - the adapter (DefiLlama-Adapters projects/ethena/index.js, fetched today) counts USDe balance at a PREMINT contract and holder addresses: token supply, no borrowed key.
- The retired USDe position system is an ERC1967Proxy 0xf6152b6699C085f1063bAa27A08d5F074AB84aa6 (impl 0xBe1c257DE04515be8b65e7826d93D26587407DeC "PositionManagerExternalWithStaking", Blockscout-verified; its ABI carries event Liquidation(uint256 indexed,uint128,uint128,uint128,uint128,uint8)). Relay eth_getLogs from the deploy window to head: **0 Liquidation events over the whole lifetime** (seven 648k-block pages), with a non-vacuous zero: the same emitter logged 34/50/14/4 events in four historical windows and nothing after block 25224073 (~160 d dormant).
- The current docs (docs.ethena.fi/technical-design/key-addresses, fetched 2026-11-07) list Core Contracts without any PositionManager (Mint&Redeem V1/V2, sUSDe staking, USDe-to-sUSDe distributor, multisigs), and the docs' "liquidation risk" page describes *exchange-side* incremental ADL of the hedged position - Ethena's liquidation risk is off-chain by design.

## Rule

A llama category TVL of 1e9+ USD is not itself a pond: if the adapter counts supply and the docs show no permissionless on-chain liquidation venue, close the candidate at the lead stage (the 2026-11-07 net-EV rule) before any event scan.
