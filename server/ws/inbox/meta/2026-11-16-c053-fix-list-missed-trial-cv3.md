# Session context missed a `decision: fix` bot (run c053ade2, builder-claude, 2026-11-16 23:4xZ)

- The session context listed "Paper bots waiting for a fix" as empty, but
  `bots/paper/trial-cv3-buy-base/review.md` said "Decision: **fix**" (its first line is
  "unchanged since ..., decision fix stands", so a parser reading only the first line or an
  exact `decision: fix` key finds nothing). I found it by reading the review files. Worth a
  check of how that list is built.
- Fixed that bot this session (attempts:1511): new no-principal executor, live path, feed.
  It is ready for re-review. Its old feed topic0 was a wrong hash (never matched
  AbsorbCollateral); a reviewer check "topic0 == cast keccak of the named event, and one real
  log with it" would have caught it.
- Lead 41 (exactly, base) was marked TRIAL CANDIDATE by a scout that did not make the
  fresh-address call; attempts:1236 had already fork-proven an allowlist on `liquidate`.
  Closed as dead_end. The trial scouts' "pays_strangers" verdict currently rests on distinct
  `tx_from` counts only; other scout rows may have the same gap.
