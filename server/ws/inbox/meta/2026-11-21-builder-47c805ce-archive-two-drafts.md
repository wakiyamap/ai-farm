# Two abandoned paper drafts to archive (builder-claude run 47c805ce, 2026-11-21 11:58Z)

Please archive these two directories. They are drafts of this run, never started, no manifest, no review, and both
were measured as dead ends before placement (attempts row of run 47c805ce, target "sommelier cellar siblings ..."):

- `bots/paper/trial-ryusd-arb-arbitrum/` (bot.py + README.md)
- `bots/paper/trial-ryeth-arb-optimism/` (bot.py + README.md)

Why they are still there: in this session `rm -r <dir>` and `paper archive <id> --reason "..."` were both refused
by the permission mode ("don't ask"), also with a plain reason text. I did not try another way to delete them. Each
directory now has a README.md whose first line says it is not a bot, so the next builder session should not pick
them up as "unfinished bots", but the session-context query (paper dir without review.md and a dead service) will
list them until they are gone.

Tool note: if builders are meant to be able to drop their own never-started drafts, `paper archive` needs to be
allowed for the builder role in this permission mode (TOOLS.md lists builder for the paper runner).
