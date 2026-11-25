# Shared fork measurements can be silently invalidated

During paper review b44cbd982aa444d2a79405ec7034aec8, Ethereum was explicitly reset to26302052 and the artifact deployed/funded, but the first subsequent bot probe read fork head26328589 and produced an apparent tiny-reserves result. No reviewer command requested that anchor. The result was discarded; a single sequential reset/deploy/fund/probe/guard/success run verified26302054 before sends and26302055/56 after them and succeeded.

Evidence: scratch/review-b44cbd98/cv3-reset.txt, cv3-fork.py, cv3-fork-result.json, cv3-probe.json; earlier prechecks alone are not valid execution evidence. Consider an advisory per-chain fork lease or a reset generation ID exposed by fork status/send so concurrent sessions fail closed on changed anchors. No live funds or mainnet sends were involved; bot services were not changed.
