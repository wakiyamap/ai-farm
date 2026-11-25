# Phase 16e: scouts move to codex; builder-codex and paper-reviewer-claude retired (human, 2026-11-24)

## What changed

- `scout-1` .. `scout-4` now run on codex (`gpt-6-sol`) as user harness, not on the local Qwen (dsh, user earner).
  The human is taking the local LLM server for other work. Same role file (`roles/scout.md`), same queue, same
  35-minute sessions; the unit no longer waits for qwen-server or checks :8003.
- `builder-codex` is retired: its timer is disabled (unit and roles.conf line kept). builder-claude is the only builder.
- `paper-reviewer-claude` is retired: its timer is disabled (unit and roles.conf line kept). The review-queue wrapper
  (`/opt/farm/context/paper-reviewer`) no longer routes Codex-built bots away: `paper-reviewer` (codex) reviews every
  bot. Codex-built bots already in paper (grad-flatmoney-arbitrum among them) are reviewed by the same model family;
  the reviewer is told to write `same-model review (codex)` in review.md.

## What the human asks of you

1. Remove the two-reviewer routing and the builder-codex lane from the role files where they appear
   (paper-reviewer.md, builder.md, common.md, TOOLS.md), so the files match one builder and one reviewer.
2. The note in `inbox/meta/2026-11-23-human-flatmoney-without-hermes.md` said "builder-claude or builder-codex": hand it
   to builder-claude.
3. Report per day for the codex scouts: sessions, candidates closed by verdict, and whether the codex usage limit was
   hit (sessions that ended with a rate-limit or usage error). Four scouts can run back to back while the queue is not
   empty, sharing the ChatGPT plan with paper-reviewer. If paper-reviewer starts failing on limits, say so in
   inbox/human with the counts; the human may cut the scouts to two.
4. scout.md was kept short for a local model. It may stay as it is; do not grow it.
