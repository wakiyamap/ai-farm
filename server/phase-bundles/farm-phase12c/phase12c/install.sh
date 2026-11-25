#!/usr/bin/env bash
# Phase 12c: (1) the private send route of 12b explained to the agents, (2) `wiki search` by BM25.
#  - prompts: common.md (send route paragraph), roles/earner.md, roles/paper-reviewer.md,
#    roles/researcher.md. Edited copies of the files as they were on 2026-11-15 13:31 JST; if any
#    of them changed since, the script stops before changing anything.
#  - decisions/human/2026-11-15-private-send.md and a note for meta
#  - /opt/farm/bin/wiki: 1 text patch (ranking only; output, limit and the floor are unchanged)
# No service is restarted. Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
P=/srv/farm/prompts
R=$P/roles
WS=/srv/farm/ws
export PYTHONDONTWRITEBYTECODE=1
sha() { sha256sum "$1" | cut -d' ' -f1; }
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

declare -A OLD=(
  [common]=2d91d488a8ba8bb8428c78e5cbf5241474dd0a8bac22c800c36b85239613e875
  [earner]=6dff265ac052313567ae6317d311c82873e70886067991f097a215c60a207f90
  [researcher]=894f815aeab5e40c25b3165a1c572542638c0d8d423223a997771459de993cf8
  [paper-reviewer]=a926fa20c46288d44d7e728e07e821e675355556bed7ee575f4c88ba620070a5
)
OLD_WIKI=dfe47b8626ecb6cb492cc3af7a3846b3f95f31b0c3b8e06328053d59dec098cb
NEW_WIKI=64f558d37fa0dd9ec18e4c7599b20cf1b5bd9cd552612b1c6048166cc7fe32ae
path_of() { [[ $1 == common ]] && echo "$P/common.md" || echo "$R/$1.md"; }

echo "== checks (nothing is changed yet)"
for f in patch-12c.py test-12c.py; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$f"
done
for k in common earner researcher paper-reviewer; do
  f=$(path_of "$k"); h=$(sha "$f")
  if [[ $h == $(sha "new/$k.md") ]]; then echo "  $f: already the new version"
  elif [[ $h == "${OLD[$k]}" ]]; then echo "  $f: as expected"
  else echo "  $f changed since the bundle was built (sha256 $h). Nothing was changed." >&2; exit 1
  fi
done
hw=$(sha /opt/farm/bin/wiki)
if [[ $hw == "$NEW_WIKI" ]]; then
  echo "  /opt/farm/bin/wiki: already the new version"; cp /opt/farm/bin/wiki "$tmp/wiki"
elif [[ $hw == "$OLD_WIKI" ]]; then
  echo "  /opt/farm/bin/wiki: as expected"
  python3 -I -B patch-12c.py check /opt/farm/bin/wiki
  python3 -I -B patch-12c.py apply /opt/farm/bin/wiki "$tmp/wiki"
  [[ $(sha "$tmp/wiki") == "$NEW_WIKI" ]] || { echo "  patched wiki has an unexpected sha256; nothing was changed" >&2; exit 1; }
else
  echo "  /opt/farm/bin/wiki changed since the bundle was built (sha256 $hw). Nothing was changed." >&2; exit 1
fi
VAR=$WS/tools/wiki-eval/rank-variants.py
vopt=(); [[ -f $VAR ]] && vopt=(--variants "$VAR")
echo "== offline tests (patched wiki)"
python3 -I -B test-12c.py "$tmp/wiki" "${vopt[@]}"

evalrun() { runuser -u harness -- python3 "$WS/tools/wiki-eval/run.py" 2>&1 | tail -3 | sed 's/^/  /' || echo "  (wiki-eval did not run)"; }
if [[ $hw != "$NEW_WIKI" ]]; then
  echo "== wiki-eval before"
  evalrun
  cp -a /opt/farm/bin/wiki /opt/farm/bin/.wiki.bak-12c
  install -o root -g root -m 755 "$tmp/wiki" /opt/farm/bin/wiki
fi
echo "== wiki-eval now"
evalrun

echo "== prompts"
changed=0
for k in common earner researcher paper-reviewer; do
  f=$(path_of "$k")
  if [[ $(sha "$f") != $(sha "new/$k.md") ]]; then
    cp -a "$f" "$(dirname "$f")/.$k.md.bak-12c"
    if [[ $k == common ]]; then install -o root -g root -m 644 "new/$k.md" "$f"
    else install -o harness -g harness -m 644 "new/$k.md" "$f"; fi
    changed=1
  fi
done
undo_prompts() {
  echo "!! restoring the previous prompt files" >&2
  for k in common earner researcher paper-reviewer; do
    f=$(path_of "$k"); b="$(dirname "$f")/.$k.md.bak-12c"
    [[ -f $b ]] && cp -a "$b" "$f"
  done
}
echo "== assembled prompts (limit 60000, keep at or under 56000)"
for i in $(awk '!/^#/ && NF {print $1}' /etc/farm/roles.conf); do
  if ! /opt/farm/bin/assemble-prompt "$i"; then undo_prompts; exit 1; fi
  n=$(stat -c %s "/srv/farm/runners/$i/prompt.md")
  echo "  $i: $n bytes"
  if (( n > 56000 )); then echo "  $i is over 56000 bytes" >&2; undo_prompts; exit 1; fi
done

echo "== decision and note for meta"
install -o root -g root -m 644 decision-2026-11-15-private-send.md $WS/decisions/human/2026-11-15-private-send.md
install -o root -g root -m 644 inbox-meta-2026-11-15-phase12c-private-send-wiki-bm25.md \
  $WS/inbox/meta/2026-11-15-phase12c-private-send-wiki-bm25.md
echo "Installed phase 12c. Running sessions keep their old prompt until their next start."
echo "To undo: restore the .bak-12c files (prompts, /opt/farm/bin/.wiki.bak-12c) and remove the two notes"
