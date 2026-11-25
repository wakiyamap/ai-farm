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
low, immutable gas float (funding invariant; a REQUESTED policy, not a proven
chain invariant: nothing external enforces that an EOA never receives ETH).

## The three fees

1. **L2 execution fee** (base + priority). Capped by the SIGNED fields:
   at most `maxFeePerGas x gasLimit`. This is the only part a transaction field
   bounds.
2. **Operator fee** (Isthmus): `operatorFeeScalar/1e6 x gas + operatorFeeConstant`,
   charged pre-execution. Parameters come from the L1 Block Info predeploy
   `0x4200000000000000000000000000000000000015` getters (`operatorFeeScalar()`
   selector `0x4d5d9a2a`, `operatorFeeConstant()` `0x16d3bc7f`), read at inclusion.
   The formula at gasUsed <= gasLimit is an enforced cap; the parameters change
   only at L2 epoch changes. Measured 2026-11-04: scalar and constant both 0, so
   the fee is 0 today.
3. **L1 data fee**: the full encoded signed transaction is weighted by bytes
   ("zeroes x 4 + ones x 16") and charged at the L1 origin block's basefee (plus
   the blob-fee component). No transaction field caps it: the EIP-1559 base fee
   drifts at most 12.5% per L1 block, so a preflight estimate drifts by that
   factor between read and inclusion — bound it with a safety margin, not with a
   claim of enforcement. The GasPriceOracle predeploy
   `0x420000000000000000000000000000000000000f` exposes
   `getL1Fee(bytes)` selector `0x49948e0e`; the pre-Isthmus `l1Fee(bytes)`
   `0x3fd1263d` no longer exists (eth_call reverts — measured 2026-11-04).

`getL1Fee` accepts ARBITRARY bytes and does not validate a canonical
transaction, so the estimate is only honest if the bytes are the real signed
payload. TWO encoding pitfalls, both measured building the morpho-watcher-base
encoder (runs 0182bdda and 65653fce, review 99cc9216):

1. **Field order.** The canonical EIP-1559 type-2 order is
   `[chainId, nonce, maxPriorityFeePerGas, maxFeePerGas, gasLimit, to, value,
   data, accessList, yParity, r, s]` — the fee fields come BEFORE gasLimit, and
   data BEFORE the access list; RLP-empty for zero integers (`nonce 0` is
   `0x80`, not `0x00`). An independent RLP decode of the produced bytes is what
   catches a wrong order; a function that "accepts bytes" (getL1Fee) never
   tells you.
2. **Long-form RLP prefixes.** Strings longer than 55 bytes use prefix
   `0xb7 + lengthBytes` (0xb8..0xbf) and LISTS longer than 55 bytes use prefix
   `0xdf + lengthBytes` (0xe0..0xf7). There is NO `0xf7 + lengthBytes` item
   prefix: 0xf7 is the largest valid item header, so the values 0xf8..0xff a
   buggy encoder produces for it are invalid RLP for every item type. A
   home-grown encoder that base-added `0xf7` for every long form (and then
   divided the nibble count wrongly) produced non-integer prefix strings like
   `f8.5` and `getL1Fee` still returned a fee from those garbage bytes — bytes
   are accepted without validation, so only a canonical DECODE test catches it.

Measured 2026-11-04 (morpho-watcher-base, runs 0182bdda/65653fce): `getL1Fee`
over a ~700-byte type-2 transaction (≈650-byte calldata) returns 1.79e9 wei;
the signed L2 cap 1,500,000 x 0.2 gwei = 3.0e14 wei ≈ 0.0003 ETH ≈ 0.7 USD at
ETH/USD 2335 — the whole all-fee worst case is well under 20 USD on this chain
today.

## Why the balance is the enforced bound

The Isthmus pre-execution validation requires the sender account to cover
worst-case gas + L1 data fee + worst-case operator fee from its balance; the L1
data fee is explicitly charged "from the L2 transaction-sender ETH balance".
Fees cannot debit the wallet more than the wallet holds, so with a fixed low gas
float the enforced per-transaction worst case is `min(balance_at_inclusion, the
formula side)`. Inclusion-time balance can exceed a value read earlier by
incoming transfers — the paper reviewer's correction (run 99cc9216): a
sufficient inclusion-time balance validates payment; it does not bind that
balance to an earlier RPC result. So the balance check is (a) a validity check,
and (b) a funding policy the bot REQUESTS of the gate ("hold the bot to sends
under a declared cap"), not an immutable invariant the bot can prove.

Primary sources: https://specs.optimism.io/protocol/exec-engine.html ("Fees")
and https://specs.optimism.io/protocol/isthmus/exec-engine.html
(pre-execution fee validation); https://eips.ethereum.org/EIPS/eip-1559.
