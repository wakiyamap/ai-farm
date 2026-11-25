# fork deploy mines status 0 for some artifacts (consolidated by meta e1762e9c, 2026-11-06)

RESOLVED 2026-11-07 (meta cabdecb4): root cause = constructor args not appended (decisions/human/2026-11-07-fork-deploy-meta-bash.md §1).
`fork deploy` now warns and takes `--args`. earner.md 3b.2, TOOLS.md and wiki pitfalls/shared-fork-concurrency.md updated.
No further occurrences need logging here unless status 0 happens WITH correct args.

One line per new occurrence: date, run, chain, reset block, artifact path, gasUsed, revert data.
Earlier reports (keep for evidence, not re-triaged): fork-deploy-old-block-revert.md (de13d8f2),
fork-oldblock-state-flaky.md (aed4765b), fork-deploy-deployer-prefix-revert.md (c8bcce4f),
and pitfalls/shared-fork-concurrency.md row "Creation deploy mines status 0".

Observed so far:
- Deterministic gasUsed, empty revert data, independent of the gas cap; reproduced at head and at old resets
  (c8bcce4f), so not only an old-state problem.
- scratch/aave2-probe Probe.sol has NO constructor and still reverted (de13d8f2's "constructor-bearing"
  explanation does not fit); Dummy.sol (one storage init) deployed fine. Both compiled evmVersion cancun.
- Same artifacts deploy fine under `forge test --fork-url` (de13d8f2).
- Root cause unknown; meta could not run commands this session (Bash denied). Escalated to the human in
  inbox/human/2026-11-06-meta-fork-deploy-bash.md (fork tool is outside the workspace).

Occurrences:
