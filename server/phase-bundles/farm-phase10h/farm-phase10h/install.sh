#!/usr/bin/env bash
# Phase 10h: ledger-ingest, after meta's report of 2026-11-10 (inbox/human/2026-11-10-meta-ledger-
# emitter-init-stall.md): beefy.charged_fees had cursors for 9 of its 40 emitters and
# reserve_folio.auction_opened for 11 of 20, for more than a day.
#  - cause: every emitter of a source was read with its own eth_getLogs (60 CU), so a source paid
#    60 CU per emitter and run only to stay at the head. With the 600 CU fair share of an agent
#    source (9e) that is 10 emitters; the 12th emitter, and every later chain of the source, was
#    never initialized. Nothing failed at a particular address.
#  - fix: one eth_getLogs with an address list for all emitters of a (source, chain) that stand at
#    the same block. A lagging emitter (still backfilling) is advanced first until it joins them.
#    At the head a source costs 60 CU per chain and run, whatever the number of emitters. No budget
#    was raised.
#  - also: a source whose actor is tx_from (one receipt per event) moved its cursor past the whole
#    block range when the budget ran out in the middle, losing the remaining events of that range.
#    The cursor now stops at the first block that was not stored.
# Checks run before anything changes; nothing is restarted (the timer starts the program every
# 15 min). Backup: .ledger-ingest.bak-10h. Cursors and events are not touched.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
export PYTHONDONTWRITEBYTECODE=1

for f in patch-10h.py test-10h.py; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$f"
done
echo "== patch texts"
python3 -I -B patch-10h.py check "$B/ledger-ingest"
python3 -I -B patch-10h.py apply "$B/ledger-ingest" "$tmp" >/dev/null
python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$tmp/ledger-ingest"
echo "== offline tests (installed file: report only)"
python3 -I -B test-10h.py "$B/ledger-ingest" --old || true
echo "== offline tests (patched file)"
python3 -I -B test-10h.py "$tmp/ledger-ingest"

echo "== cursors now (agent sources with emitters still missing)"
python3 -I -B - <<'PY' || echo "  (could not read the ledger; not needed for the install)"
import glob, json, os, sqlite3
cfg = json.load(open("/etc/farm/ledger.json"))
con = sqlite3.connect(f"file:{cfg['db']}?mode=ro", uri=True, timeout=30)
for path in sorted(glob.glob(os.path.join(cfg["agent_sources_dir"], "*.json"))):
    try:
        s = json.load(open(path))
        for chain, addrs in s["chains"].items():
            n = con.execute("SELECT count(*) FROM cursors WHERE source_id=? AND chain=?", (s["id"], chain)).fetchone()[0]
            if n < len(set(a.lower() for a in addrs)):
                print(f"  {s['id']}@{chain}: {n} of {len(addrs)} emitters have a cursor")
    except Exception as exc:
        print(f"  {os.path.basename(path)}: {exc}")
PY

echo "== backup"
[[ -e "$B/.ledger-ingest.bak-10h" ]] || cp -a "$B/ledger-ingest" "$B/.ledger-ingest.bak-10h"
echo "== install"
install -o "$(stat -c %u "$B/ledger-ingest")" -g "$(stat -c %g "$B/ledger-ingest")" -m "$(stat -c %a "$B/ledger-ingest")" "$tmp/ledger-ingest" "$B/ledger-ingest"
python3 -I -B patch-10h.py check "$B/ledger-ingest"
systemctl list-timers ledger-ingest.timer --no-pager 2>/dev/null | sed -n '1,2p' || true
note=/srv/farm/ws/inbox/meta/2026-11-11-phase10h-ledger-emitters.md
[[ -e $note ]] || install -m 664 inbox-meta-2026-11-11-phase10h-ledger-emitters.md "$note"
echo "Installed phase 10h. Paste everything from '== patch texts' down."
echo "After two or three timer runs: journalctl -u ledger-ingest -n 6 --no-pager"
