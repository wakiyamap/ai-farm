# Arbitrum fork replay receipt timeout

Builder run `ccf8f231cf424518bad902474752d606`: `fork replay arbitrum
0xfe6fedf39f345a61f6fd781241d2a604d8fc53a73d929efc344329aa68d13721`
reset the fork to block 524327777 but returned `no receipt ... after 30s`
for its re-sent transaction. Historical `debug_traceTransaction` through the
relay succeeded (`scratch/revert-trial-fe6-trace.json`), and direct fork
reset/deploy/send proofs succeeded twice on the same parent state
(`scratch/trial-revert-lend-arbitrum/proof-result.json`). The direct proofs
provide reviewable evidence; the replay wrapper's receipt wait may need
diagnosis if this recurs on Arbitrum.
