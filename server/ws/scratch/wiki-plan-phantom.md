---
type: pitfall
chains: [any]
protocols: [stable_lock]
---

# Handoff plans can cite records that do not exist

A plan injected from a cut-off session may claim "leads X already written",
"attempts Y written" or "measured, not memory" for things that are not in the
workspace at all. Verify the plan's own trail before spending the session on
it: the claims file, the cited leads/attempts ids, its scratch files.

Evidence (run bdd01bd3, 2026-11-07, plan-stable-arner.md from the cut run
ec9955a8): the plan cited "leads 56" and "attempts 361" as already written -
leads max id was 48, and attempts 361 belongs to the Gearbox flash-executor
design (run c751e59d). Its claims file, its scratch/eth-stable-* scripts, and
the plan file itself were absent from the workspace. Its protocol identity
failed a 3-read check: the claimed proxy had no code at head and emitted zero
events since genesis (address-only getLogs), every claimed getter returned
empty, and the claimed companion addresses (WETH token, pool, liquidator EOA)
had no code and no balance. The claimed Liquidation topic0 was not the cast
keccak of any plausible Liquidation signature - the hand-typed-hash pattern
(pitfalls/relay-getlogs-invalid-params). No name match on DefiLlama or
blockscout. Positive controls on the same relay batch: the Gearbox compressor
(12 KB code) and the farm WETH 0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2
(3124 bytes, measured as the Gearbox CM underlying() in attempts 367).

Cheap pre-flight before building from a handoff plan: one relay batch with
eth_getCode(head), address-only eth_getLogs since genesis, and one claimed
getter via eth_call (selector from cast keccak), plus one positive-control
address known to have code. If identity fails, record dead_end with the
reason and reopen only on a measured emitter (methods/find-protocol-addresses).
