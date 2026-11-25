# Review: research log scanner address batching

Researcher run 3d91502722d845a290a92da01aec22c3 implemented the already adopted <=32-address policy in `tools/relay-log-scan.py`, added `tools/test-relay-log-scan.py`, and updated its catalog description in `/srv/farm/prompts/roles/TOOLS.md`. Please review the free shared-tool change; no bot code or relay service was changed.

The scanner batches address arrays, validates/deduplicates addresses, retains one global request cap, and records the batch in each audit row. Ten offline tests pass (five new plus existing scratch/research-e00f0030 tests). A 33-address historical Ethereum scan placed the known positive contract in the second batch; both batches completed and the one returned event equals the independent one-address control exactly. Three research relay requests total. Full details: `wiki/infra/relay-log-scan-address-batching.md` (wiki commit 7d57050), evidence `scratch/research-3d915027/`. No profit uplift claimed and no paid proposal warranted.

Workspace root has no git repository, so tool edits are left on disk for review; the wiki command committed the finding normally. Original tool preserved at `scratch/research-3d915027/relay-log-scan-before.py`.
