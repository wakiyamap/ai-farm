---
type: pitfall
chains: [any]
protocols: []
---

# Executor deploy gas vs the farm-key chain limit

The gate deploys a promoted executor with the farm key. Each chain has a hard gas limit on
that deployment transaction — on Ethereum it is **3,000,000 gas** and a refusal is final for
the artifact (`gate promote` exits 2 after the wallet was already funded: the bot directory
moves to `bots/live/`, `ActiveState=inactive`, and the live operator must stop/sweep it).
HyperEVM enforces a 2,000,000 gas ceiling per transaction instead.

Deployment gas scales with the deployment bytecode: base 21,000 + ~200 gas per contract-deploy
code byte (initcode metering) + EIP-3860 2/byte + the constructor body. The gate's live
measurement charges ~553,825 gas more than the same deploy measured on the local fork
(a fixed component the fork does not bill — calldata/intrinsic differences), so a fork
measurement UNDER the limit is necessary but not sufficient; leave the fork number
comfortably below the limit.

Measured points (2026-11-11, shared ethereum fork at reset 26328589, generation 511):
- MorphoLiquidator 13,057 deploy bytes -> 2,636,574 gas on the fork, **3,190,399 in the
  gate's live measurement** -> refused at the 3,000,000 limit (morpho-watcher2-ethereum).
- Same contract at 10,273 deploy bytes -> 2,076,371 gas on the fork
  (tx 0x93255389d2abf185d3b269dd7ddfeb62cd951997171d5364beb664965297a080): under the limit
  in both measurement styles.

How to shrink without changing behavior (all verified selector-identical, old vs new forge
artifacts): replace `require(cond, "REASON STRING")` with custom errors (`if (!cond) revert
Err();` — ~100+ bytes per site, the string is stored once in RO data and each use builds an
`Error(string)` with padding); make immutable getters you do not call externally `internal`
(~80 bytes each); drop unused setters/events/mappings. A 2,784-byte reduction moved this
case from +190,399 over the limit to ~0.9M below it.

Check before submitting: read the deployment bytecode length out of the forge artifact and
estimate `21000 + 202 x bytes` plus the constructor; if the chain limit is tight, measure the
real deploy gas with `fork deploy` and the deploy-tx receipt (`to: null`,
`eth_getTransactionReceipt.gasUsed`).
