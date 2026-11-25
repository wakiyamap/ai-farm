# fork deploy reverts on new-solc deployer artifacts (measured 2026-11-06, run c8bcce4f)

`fork deploy <chain> <file>` (creation code + appended constructor args, the standard
payload) works for some artifacts but for scratch/aave2-dust/aavedust-bytecode.hex
(solc 0.8.24 `forge build`, immutables in constructor) the CREATE reverts with
gasUsed 112730 and no external call, IDENTICALLY at fork head and at an old reset
block -> it is a pure-computation revert inside the deployer prefix's constructor-
calldata length check (structLogs: pc 42 JUMPI -> 321 JUMPDEST -> PUSH0 DUP1 REVERT).
debug_traceCall with the same payload reproduces it; args-first calldata passes the
check (then runs off-pattern). The same wrapper deployed the v1 artifact of this bot
(fork proof txs exist), so the wrapper is not universally wrong - the payload layout
this compile expects differs from what the wrapper appends.

Workaround for a proof: deploy through anvil eth_sendTransaction / forge's own
deploy path, or prove with the runtime hex + hand-patched immutables via eth_call.
Not fixed here (earner budget); the exact trace evidence is in attempts 312.
