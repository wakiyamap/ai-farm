# phase 12c: private send rules in the prompts; `wiki search` ranks by BM25 (human, 2026-11-15)

## 1. Private send (phase 12b code, phase 12c prompts)

- Code (12b, 2026-11-15 04:28Z): rpc-relay has a private route for ethereum (Flashbots Protect); farm-signer sends a bot's ethereum transactions through it when the live manifest says `send_route: private`. It never falls back to the public mempool. signer.log lines carry `route`.
- Prompts (12c): common.md (one "Send route" paragraph under L), earner.md (a "Private send" bullet in section 5, the `private-send` rule in section 1 now says to re-evaluate on ethereum, `send_route` in the manifest template), paper-reviewer.md (a "Private send" paragraph before "Partial promotion"), researcher.md (the path is live on ethereum). The decision file is `decisions/human/2026-11-15-private-send.md`: it is already reflected, do not add it again.

What I ask of you:

1. `tools/manifest-check.py`: accept the key `send_route`; ERROR when its value is neither `public` nor `private` (the signer rejects every send of such a bot); WARN when it is `private` and `chains` does not include ethereum (the key has no effect there).
2. A wiki page `infra/private-send.md` from the decision file and section 5 of earner.md: what the route does, what it does not do (it does not win contested liquidations: lead 14, attempts 1244/1245), the deadline argument, `private_not_included`, the nonce replacement, the daily spend. Then the role files may point to it.
3. When the first bot uses the route, forward its first-send result (included or not, after how many blocks) to inbox/human.
4. Leads with `private-send` in `next_steps`: list them (id, chain) in your next report. Only the ethereum ones can be re-opened.

## 2. `wiki search` (your proposal 2026-11-15-meta-wiki-search-bm25.md): applied

`/opt/farm/bin/wiki` now ranks by the `bm25` variant of `tools/wiki-eval/rank-variants.py` (BM25, +2 for a term in the path or frontmatter, +1 in the title line, the matched-terms floor kept, output unchanged). An offline test checks that the tool and your `make_ranker` give the same order.

- Run `tools/wiki-eval/run.py` and record the numbers; the installer printed them before and after. If hit@1 is lower than before, say so in inbox/human and I put the old file back (`/opt/farm/bin/.wiki.bak-12c`).
- `rank-variants.py`'s `cur` variant is now stale (it copies the old order). Keep it as "old", or drop it.

## 3. Sizes

Assembled after 12c: earner 53,292, paper-reviewer 44,974, researcher 38,660, meta 35,126, live-operator 35,267 bytes. The earner has about 2,700 bytes left under 56,000: move detail to wiki pages before adding anything to earner.md.
