---
type: infra
chains: [hyperevm]
protocols: []
author: earner/qwen3.8-flash-next
updated: 2026-11-10
---
# HyperEVM (Hyperliquid L1) from this host

**Conclusion: treat HyperEVM as a chain with no free block explorer and with 2-second blocks.** The farm's `hyperevm` chain is Hyperliquid's HyperEVM; DefiLlama lists it as `Hyperliquid L1` (the chain is *not* called `HyperEVM` in `api.llama.fi/protocols`, so a `chains[] == "HyperEVM"` filter returns 0 and looks like an empty chain). Head 50916079 at 2026-11-10T19:23Z; blocks are ~2 s, so a day is ~43200 blocks and a 10000-block log range is only ~5.5 hours.

## What worked

- The relay serves HyperEVM reads (`RPC_RELAY_URL/hyperevm?lane=research`), including `debug_traceTransaction` with `callTracer` (the farm's `trace_*` methods are not served here), `eth_getBlockByNumber` with full transactions, `eth_call`, `eth_getTransactionReceipt`, and `alchemy_getAssetTransfers`.
- In `alchemy_getAssetTransfers` the chain's native token (HYPE) is labelled `asset: "ETH"` and `category: "external"` for a plain value transfer, so a keeper's reward withdrawals look like "0.2 ETH" transfers into an EOA.
- `relay-log-scan.py` is the way to scan HyperEVM logs: it builds a provider-acceptable request shape and it *rejects* a `topics[0]` that is not a full 32-byte hash, which caught a truncated receipt topic here (take topic0 from a real receipt or `cast keccak "<Event(...)>"`, never from a printed prefix).
- `eth_getLogs` with `toBlock = eth_blockNumber` answered `block range extends beyond current head block` on the public node: read `eth_blockNumber`, then use `head-10` as the upper bound.

## What failed (do not repeat)

- **No free block-explorer API for HyperEVM from this host.** `https://api.blockscout.com/hyperevm/api/v2/...` answers `{"error":"Proceed with API key or make a X402 payment to continue"}`; `https://api.hyperevmscan.io/api/v2?module=transaction&action=gettxhashstatus&...` and `?module=contract&action=gotocache` (keyless) returned HTTP 404; `https://verifier.hyperevmscan.io/api/contract/<addr>/source` did not resolve from the farm host at all (curl exit 000); `https://api.hyperblocks.com/api/v2/...` returned an empty body. So a contract's verified source and name have to come from the relay (getter probes) or from the DefiLlama adapters (`https://api.llama.fi/adapter/llamas/<slug>.js` lists the addresses — but since 2026-11-10 this endpoint answers `Route not found` for every Hyperliquid-L1 slug (4 URL variants tested, run 544ba9e9; the `chainContracts` field also lacks these contracts, and DefiLlama yields `poolAddress`/`protocol.address` are null for them), so addresses must come from the protocols’ own docs; the two busy HyperEVM contracts of the 2026-11-10 scout were in none of the top-45 Hyperliquid-L1 adapter files nor in `chainContracts`).
- `debug_traceTransaction` with `{"tracer":"prestateTracer","tracerConfig":{"diffMode":true}}` returned an empty `diff` (no `pre`/`post`) for two HyperEVM transactions: measure a caller's balance delta with two `eth_getBalance` reads at explicit block numbers, or on the fork.
- `eth_getLogs` on HyperEVM rejected the hand-built request with the public node's `Invalid variadic value or array type: data did not match any variant of untagged enum Variadic` for both `address` as a string and as a one-element array, as soon as `topics` was present (the same filter without `topics` was accepted).

## First keeper-class measurement (lead 127, closed `blocked_infra`)

The most frequent permissionless callers of 2026-11-10 poked their contracts about every 10 seconds (0.15 tx/block, 6480 tx/day), each tx costing 191168 gas at 0.2 gwei = 3.82e-5 native (3.82e-5 HYPE), i.e. 0.247 native/day of gas; the incumbent's entire measured income was 1.82 native withdrawn in five transfers over ~7 days = 0.26 native/day. Income ≈ gas, and a 10-second window is a same-block-race class per `decisions/human/2026-11-06-no-latency-race.md`. Detail: attempts 836 and 840, leads 127, protocols 192.

## Second keeper-class measurement (lead 129 leg 1, negative)

A second sweep (five 20-block full-transaction windows spread over ~8 h at head 50917031, run 544ba9e9) confirmed the two lead 127 pokers as the chain's two busiest callers and found four *slower* single-sender poke pairs, each poking its target about once per 40 blocks (~40–80 s — a poll-friendly cadence with no same-block race): `0x6d18f44e → 0x2745cbaa` (selector `0x500945d4`, 82780 gas), `0xdf1bda87 → 0x6cd56616` (`0x6d142da1`, 71105 gas), `0x33b12dd7 → 0xf9b0c8ee` (target emits no events), `0xaea0edc9 → 0xce59f8b6` (`0xb75436bb`, 93264 gas; this target is the same contract the lead 127 incumbent forwards value through, and an `eth_call` there reverts with the tag `WooracleV2_2` — a Woorasso oracle). None of the four pays its caller on-chain: every caller is an EOA with zero inbound native AND zero inbound ERC20 transfers in the 7-day window (blocks head-300000..head-100, `alchemy_getAssetTransfers` category `external` then `erc20`), while paying 0.00001–0.00003 native per tx themselves. Conclusion: on HyperEVM the visible maintenance pokers are *sponsored* (paid off-chain, oracle-operator style), not paid by protocol reward — only the 10-second `0x90dabc98` class measured in lead 127 had on-chain income. When scouting a poke class here, first ask for the inbound payment leg; a poker whose caller has no transfers in 7 d is a duty bot, and its reward will not be there for us. Detail: attempts 841, leads 129, actors 97–100.
