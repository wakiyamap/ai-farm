---
type: mechanism
chains: [base]
protocols: []
---

# Base: OP Stack fee anatomy and the enforceable loss bound

Conclusion: on Base every transaction pays THREE fee kinds, all deducted from the
sender's native balance and validated against it at inclusion time. An L-bound
"worst case is gas" for a base bot is therefore enforced only as
`min(balance_at_inclusion, signed L2 cap + operator fee + L1 data fee)`, and a
balance read just before signing is only a validity condition, not an upper
bound — unless the bot never receives inbound ETH and the wallet holds exactly a
low, immutable gas float (funding invariant).

## The three fees

1. **L2 execution fee** (base + priority). Capped by the SIGNED fields:
   at most `maxFeePerGas x gasLimit`. This is the only part a transaction field
   bounds.
2. **Operator fee** (Isthmus): `operatorFeeScalar/1e6 x gas + operatorFeeConstant`,
   charged pre-execution. Parameters come from the L1 Block Info predeploy
   `0x4200000000000000000000000000000000000015` getters (`operatorFeeScalar()`
   selector `0x4d5d9a2a`, `operatorFeeConstant()` `0x16d3bc7f`), read at inclusion.
   Measured 2026-11-04: scalar and constant both 0, so the fee is 0 today.
3. **L1 data fee**: the full encoded signed transaction is weighted by bytes
   ("zeroes x 4 + ones x 16") and charged at the L1 origin block's basefee (plus
   the blob-fee component). No transaction field caps it. The GasPriceOracle
   predeploy `0x420000000000000000000000000000000000000f` exposes
   `getL1Fee(bytes)` selector `0x49948e0e`; the pre-Isthmus `l1Fee(bytes)`
   `0x3fd1263d` no longer exists (eth_call reverts — measured 2026-11-04).

`getL1Fee` accepts ARBITRARY bytes and does not validate a canonical
transaction, so the estimate is only honest if the bytes are the real signed
payload: the canonical EIP-1559 type-2 order is
`[chainId, nonce, gasLimit, maxPriorityFeePerGas, maxFeePerGas, to, value, data,
accessList, yParity, r, s]` — gasLimit BEFORE the fee fields, data BEFORE the
access list; RLP-empty for zero integers (`nonce 0` is `0x80`, not `0x00`).
Measured 2026-11-04 (morpho-watcher-base, run 0182bdda): `getL1Fee` over a
~700-byte type-2 transaction (≈650-byte calldata) returns 1.79e9 wei; the signed
L2 cap 1,500,000 x 0.2 gwei = 3.0e14 wei ≈ 0.0003 ETH ≈ 0.7 USD at ETH/USD
2335 — the whole all-fee worst case is well under 20 USD on this chain today.

## Why the balance is the enforced bound

The Isthmus pre-execution validation requires the sender account to cover
worst-case gas + L1 data fee + worst-case operator fee from its balance; the L1
data fee is explicitly charged "from the L2 transaction-sender ETH balance".
Fees cannot debit the wallet more than the wallet holds, so with a fixed low gas
float the enforced per-transaction worst case is `min(balance_at_inclusion, the
formula side)`. Inclusion-time balance can exceed a value read earlier only by
incoming transfers or funding — hold the bot to sends and a declared funding
cap, and the read becomes an enforceable bound.

Primary sources: https://specs.optimism.io/protocol/exec-engine.html ("Fees")
and https://specs.optimism.io/protocol/isthmus/exec-engine.html
(pre-execution fee validation).
