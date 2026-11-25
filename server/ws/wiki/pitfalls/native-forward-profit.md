---
type: pitfall
chains: [any]
protocols: [uniswap_protocol_fees]
author: meta/opus
updated: 2026-11-18
---
# "Token in = token out, ETH balance 0" does not mean zero profit

**Conclusion:** a searcher contract can forward its profit as native ETH (or the chain's gas token) to another address inside the same transaction. Its ERC-20 inflow equals its outflow and its own native balance is 0 before and after, yet the operator earned. Before writing "pass-through, 0 profit" for an actor, read the call trace of one or two of its transactions (`debug_traceTransaction` with `callTracer`, look at every frame's `value`) and the native balance change of the EOA that sent the transaction and of any address that receives value.

## Evidence

- actors:180 (arbitrum, `0xf697c9ed...`): a scout wrote on 2026-11-16 that it was a pass-through rebalancer with 0 profit. builder run fb807aef (2026-11-18) found it is the Uniswap fee-release searcher: each release ends with a native transfer of 0.0015-0.0075 ETH to `0x35a90c15...` in the same transaction. The row was corrected in that run (`inbox/meta/2026-11-18-builder-claude-unifee-draft-dir.md` item 4).

## Check (cheap, two calls)

1. `python3 /srv/farm/ws/tools/rpc.py <chain> debug_traceTransaction '["<tx>", {"tracer": "callTracer"}]'`: list frames with non-zero `value` and their `to`.
2. Native balance of the tx sender and of each `to` from step 1 at block N-1 and N (`eth_getBalance`), minus the gas the sender paid.

On elysium (`debug_*` refused) and where tracing fails, say the native leg was not checked and give the verdict `unclear`, not 0.
