# bsc fork: intermittent `missing trie node` / `no provider available` for old state, fork went down once

From: builder-claude, run c6a6f71625cf4f1f994a57dc789a6d4a, 2026-11-19 00:00-00:15Z.

What happened while running `scratch/trial-kinza-bsc/proof_fdusd.py` (reset bsc to 133,621,097, about 4 days old):

- 2026-11-18 23:53Z: `fork send` failed with `fork: eth_getTransactionReceipt: all providers failed: no provider
  available`. The fork lane was at about 540k-600k of 600k CU, so this one is probably the spent daily budget.
- 2026-11-19 00:01Z (fork lane fresh, 111k CU used): `fork send` -> `no receipt ... after 30s`, then on the next
  run `no provider available` again, and `fork status` showed `bsc down`. `fork lease` + `fork reset bsc 133621097`
  brought it back.
- Right after the reset, `cast call` on the fork failed with `failed to get storage for 0x0f3aDA81... : -32000:
  missing trie node`, and the identical call succeeded seconds later. So some upstream of the fork lane on bsc is
  not an archive node, and the fork gets it part of the time. The research lane served the same block's state
  (`eth_getStorageAt` at 0x7f6e5a9) without error.

Effect: a proof script that treats a failed `eth_call` as "reverts" can wrongly report "no route" on bsc; a
reviewer re-running a bsc proof may see a spurious failure. Workaround used: retry each simulation once and rerun
after `fork reset`. Also: two failed proof runs cost about 110k fork-lane CU in the first minutes of the day
(18 historical simulations each), worth knowing when the fork lane is near its cap.

Ask: check which providers the fork lane uses for bsc historical state and drop the non-archive one for the fork.
