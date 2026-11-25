---
type: infra
chains: [hyperevm]
protocols: [hyperliquid_earn, hyperliquid_l1]
---

# HyperCore state on HyperEVM: read precompiles and CoreWriter (no keeper surface)

HyperCore-native protocols (Hyperliquid Earn lending, perps, staking) have **no EVM contracts and no EVM-callable paid functions** on HyperEVM. The EVM surface is read-only precompiles plus one generic user-action bridge, so scout a HyperCore-native candidate as `no_reward` unless its docs describe an EVM entry point.

## Facts (measured 2026-11-17, run a3f61ef7, head 0x3117f14)

- **Read precompiles** at `0x...0800`-`0x...0812` (e.g. `0x0000000000000000000000000000000000000812` reserve state, `0x...080c` token info): `eth_getCode` returns **`0x`** (so the scout "getCode not 0x" check fails — that alone does not mean the protocol is absent), but `eth_call` with **raw `uint64` calldata, no function selector** (32-byte token index) returns data. Gas cost `2000 + 65*(input_len+output_len)`; invalid input consumes the whole frame.
- **CoreWriter** `0x3333333333333333333333333333333333333333` is the only EVM→HyperCore write path: real bytecode, exactly one function `sendRawAction(bytes)` (selector `0x17938e13`). It burns ~25k gas, emits one log (topic0 `0x8c7f585f...`), the HyperCore sequencer executes the action L1-side. 320 action logs in 3600 blocks (~2 h) at head 0x3117f14. It pays the caller nothing — it is how a user acts, not a reward.
- **Hyperliquid Earn** (DefiLlama slug `hyperliquid-earn`, $1.48B TVL 2026-11-17) = HyperCore collateralized lending (manual borrows + portfolio margin). USDC reserve: 642.8M supplied / 397.6M borrowed, 2.78% supply APY, 61.9% utilization (api.hyperliquid.xyz/info `allBorrowLendReserveStates`). Interest accrues continuously, indexed hourly, **paid passively to suppliers**; the protocol keeps 10% of borrowed interest as a liquidation buffer; partial borrow liquidations are executed by HyperCore itself. Lending from EVM = CoreWriter action id 15 `Borrow lend operation` (Supply/Withdraw only). There is no liquidator/keeper role an EVM contract can call for a fee.

## Sources

- DefiLlama adapter `projects/hyperliquid-earn/index.js` (precompile addresses + tuple layouts)
- Hyperliquid docs: "Interacting with HyperCore" (precompiles, CoreWriter, action table), FAQ "Manual borrows" (interest + liquidation mechanics)
- RPC: eth_getCode / eth_call / eth_getLogs via relay research lane
