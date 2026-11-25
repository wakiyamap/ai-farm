#!/usr/bin/env python3
"""Phase 15i text patches.

  patch-15i.py check <rpc-relay> <context/earner> <context/builder>
  patch-15i.py apply <rpc-relay> <context/earner> <context/builder> <outdir>

rpc-relay
  1. Fork lane: every read goes to Alchemy only, with no daily cap (human decision 2026-11-20).
     15h sent a fork's read to Alchemy only when is_historical() said the block was old. For anvil's
     reads it said no, so within the budget a fork read went [Alchemy, public] (Alchemy skipped while
     cooling down -> public 403), and past the budget it went to public nodes only
     (`public: HTTP 403 Archive requests require a personal token`, all day on 11-19 after 09:43Z).
     Public nodes cannot serve a fork anyway (arbitrum answers 403 to any non-latest block, bsc keeps
     recent state only), so the fork lane no longer looks at the block or the budget.
     Alchemy is then the only provider, so the 15h cooldown exception and 429 rewrite still apply.

context/earner (the builder session context)
  2. "Paper bots waiting for a fix": the current decision is the first decision line or decision
     heading near the top of review.md (`**Decision: fix**`, `decision fix stands`, `## ... — fix`).
     A bot whose bot.py / *.sol / manifest.yaml is newer than its review.md is listed separately as
     resubmitted (reviewer's work, not the builder's).
  3. "Measured leads without a bot": leads whose next_steps say TRIAL BOT PLACED or NOT A BUILD
     TARGET, and leads named in a paper/live manifest (`lead: N`, `lead_id: N`, `leads:N`), are left out.

context/builder
  4. "Trial bots live: N / 45" (decision 2026-11-20-trial-slots-45; it said / 10).
"""
import os
import sys

RELAY = [
("fork lane: Alchemy only, before every other branch",
'''        if method.startswith(("debug_", "trace_", "alchemy_")) or method == "eth_simulateV1":
''',
'''        if lane == "fork" and alchemy:
            # 15i: the fork lane reads through Alchemy only, whatever the block and with no daily cap
            # (decision 2026-11-20). Public nodes cannot serve a fork (arbitrum: 403 on any non-latest
            # block; bsc: recent state only), and is_historical() missed anvil's reads, so 15h fell
            # through to public nodes. Alchemy is the only provider, so the 15h cooldown exception
            # and the 429 rewrite apply to every fork read.
            return alchemy
        if method.startswith(("debug_", "trace_", "alchemy_")) or method == "eth_simulateV1":
''',
"# 15i: the fork lane reads through Alchemy only"),
("drop the 15h / 15c fork branches (unreachable now)",
'''        if lane == "fork" and alchemy and params is not None and self.is_historical(chain, method, params):
            # 15h: a fork's old state needs an archive node; public nodes answer "missing trie node"
            return alchemy
        if lane == "fork" and alchemy and spent < self.budget.get(lane, 0):
            # 15c: fork state for proofs: Alchemy first while the fork lane's own budget lasts
            return alchemy + public
''',
'''''',
None),
]

EARNER = [
("fix list: current decision from the first decision line or heading; resubmitted bots apart",
'''echo "### Paper bots waiting for a fix"
for d in "$WS"/bots/paper/*/; do
  [[ -d "$d" ]] || continue
  r="$d/review.md"
  if [[ -f "$r" ]] && head -5 "$r" | grep -qi 'decision: *fix'; then
    echo "- $(basename "$d"): $(grep -i -m1 'decision' "$r")"
  fi
done
''',
'''echo "### Paper bots waiting for a fix"
# 15i: the current decision is the first decision line or decision heading near the top of review.md
# (`**Decision: fix**`, `decision fix stands`, `## <time> — fix`). A bot whose code or manifest is newer
# than its review.md was resubmitted: the reviewer's turn, listed apart.
resub=""
for d in "$WS"/bots/paper/*/; do
  [[ -d "$d" ]] || continue
  r="$d/review.md"
  [[ -f "$r" ]] || continue
  line=$(head -15 "$r" | grep -m1 -iE 'decision[*: ]+(fix|wait|promote|demote|reject|archive)|^#+ .*(—|–| - ) *(fix|wait|promote|demote)([^a-z]|$)')
  printf '%s' "$line" | grep -qiE 'decision[*: ]+fix|(—|–| - ) *fix([^a-z]|$)' || continue
  newer=$(find "$d" -maxdepth 3 \\( -name logs -o -name state -o -name out -o -name cache -o -name __pycache__ \\) -prune \\
          -o -type f \\( -name '*.py' -o -name '*.sol' -o -name 'manifest.yaml' \\) -newer "$r" -print -quit 2>/dev/null)
  if [[ -n "$newer" ]]; then
    resub+="- $(basename "$d"): ${newer#"$d"} is newer than review.md"$'\\n'
  else
    echo "- $(basename "$d"): ${line:0:200}"
  fi
done
echo
echo "### Paper bots resubmitted after a fix (waiting for the reviewer; not builder work)"
printf '%s' "${resub:-(none)}"
[[ -n "$resub" ]] || echo
''',
"# 15i: the current decision is the first decision line"),
("measured leads: leave out leads with a bot or marked done",
'''  echo "### Measured leads without a bot (newest 8)"
  $KB query "SELECT id, chain, target, substr(next_steps,1,160) AS next_steps FROM leads WHERE status='measured' ORDER BY updated_at DESC LIMIT 8" 2>/dev/null || echo "(kb unavailable)"
''',
'''  echo "### Measured leads without a bot (newest 8)"
  # 15i: leave out leads marked TRIAL BOT PLACED / NOT A BUILD TARGET and leads a paper or live
  # manifest names (lead: N, lead_id: N, leads:N)
  skip=$(cat "$WS"/bots/paper/*/manifest.yaml "$WS"/bots/live/*/manifest.yaml 2>/dev/null \\
         | grep -oiE '^[[:space:]]*lead(_id)?[[:space:]]*:[[:space:]]*[0-9]+|leads:[0-9]+' | grep -oE '[0-9]+$' | sort -un | paste -sd, -)
  $KB query "SELECT id, chain, target, substr(next_steps,1,160) AS next_steps FROM leads WHERE status='measured' AND COALESCE(next_steps,'') NOT LIKE '%TRIAL BOT PLACED%' AND COALESCE(next_steps,'') NOT LIKE '%NOT A BUILD TARGET%'${skip:+ AND id NOT IN ($skip)} ORDER BY updated_at DESC LIMIT 8" 2>/dev/null || echo "(kb unavailable)"
''',
"# 15i: leave out leads marked TRIAL BOT PLACED"),
]

BUILDER = [
("trial slots: / 45",
'''echo "### Trial bots live: $(ls -d /srv/farm/ws/bots/live/trial-* 2>/dev/null | wc -l) / 10"
''',
'''echo "### Trial bots live: $(ls -d /srv/farm/ws/bots/live/trial-* 2>/dev/null | wc -l) / 45"   # 15i: decision 2026-11-20-trial-slots-45
''',
"# 15i: decision 2026-11-20-trial-slots-45"),
]


def patch(text, hunks, name):
    done = [m for _t, _o, _n, m in hunks if m]
    if done and all(m in text for m in done):
        print(f"  {name}: already the 15i version")
        return text
    for title, old, new, _marker in hunks:
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{name}: cannot apply '{title}': old text found {n} times (expected 1); nothing was changed")
        text = text.replace(old, new)
        print(f"  {name}: {title}")
    return text


def main(argv):
    if len(argv) < 4 or argv[0] not in ("check", "apply") or (argv[0] == "apply" and len(argv) < 5):
        raise SystemExit(__doc__)
    out = []
    for path, hunks, base in ((argv[1], RELAY, "rpc-relay"), (argv[2], EARNER, "earner"), (argv[3], BUILDER, "builder")):
        out.append((base, patch(open(path, encoding="utf-8").read(), hunks, base)))
    if argv[0] == "apply":
        os.makedirs(argv[4], exist_ok=True)
        for base, text in out:
            with open(os.path.join(argv[4], base), "w", encoding="utf-8") as f:
                f.write(text)
    print(f"patch-15i: {argv[0]} ok")


if __name__ == "__main__":
    main(sys.argv[1:])
