---
type: pitfall
chains: [arbitrum, ethereum]
protocols: [azverse_perps]
---

# A custody book is not an on-chain book

DefiLlama "perps" adapters often sum assets held in custodian wallets, which reads like a large active on-chain book but is cold custody for an off-chain orderbook exchange. Before building a liquidation bot on such TVL, measure the wallet transfer cadence: a settlement engine that liquidates on your chain moves assets through the custody wallets daily.

## Evidence (AZX / AZverse, measured 2026-11-07, head 522042629)

- The llama fork adapter (AZverse/DefiLlama-Adapters projects/azverse) sums ETH + USDT + USDC in an AssetVault and three custody wallets on Arbitrum; measured balances via relay eth_call: 50,107,077 USDT + 207,414 USDC at 0xdc379823a9a3a2ca9d77c33299551ecdbabf7a41, plus 82,247 USDT + 82,780 USDC at AssetVault 0x91ba525861c16aa8cd4d6974e4058cc846f42ebe, plus small dust - the whole 50.47M USD "Arbitrum TVL" is stablecoin custody.
- eth_getLogs chunked 8 x 9.5M blocks over ~1 year (address = 0xfd086bc7... USDT, topic1/topic2 = wallet): 48 inbound and 8 outbound transfers in a year (last outbound 32.9M blocks = ~158 d before head). Same-window positive control: 1065 USDT logs in a 1500-block window, topic1 filter returned 6 on the known sender.
- The most recent inbound USDT transfer (block 518091413, tx 0xdade3e3084c524e06b4f543897bcf0ef0ac5c696d281700d10b43402797c38ca) is a plain ERC-20 transfer initiated by another custody wallet (from 0x03a7e587, to USDT, input 0xa9059cbb) - custody-to-custody, not engine settlement.
- Official docs (azverse.gitbook.io/azx-docs/perpetual-trading/liquidation.md): forced liquidation means "the position is closed by the system", the maintenance margin is forfeited, and the insurance fund absorbs the excess (insurance-fund.md). There is no permissionless liquidator role to copy.
- The public API (f-api.azverse.xyz, Binance-style /az/future/... endpoints) exposes no 0x engine address, and api.github.com/orgs/AZverse/repos lists only azx-cli, az-bft and two adapter forks - the "asset-vault-contracts"/"api-docs" repos linked by the marketing page are 404 (measured 2026-11-07).

## Rule

When DefiLlama counts a protocol through custody wallets, its TVL is user funds, not liquidity your bot can liquidate. Measure transfer cadence first; CEX-style engines settle and liquidate on their own L1, not on your chain.
