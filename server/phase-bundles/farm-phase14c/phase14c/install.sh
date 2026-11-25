#!/usr/bin/env bash
# Phase 14c: scouts were cut off before writing anything (7 of the first 8 sessions).
#  - roles/scout.md: write the result 25 minutes after the start, partial or not; samples of at most
#    20 occurrences, totals from one query
#  - /opt/farm/context/scout: the trial and protocol steps ask for samples, not every occurrence
#  - agent@scout-1..4: cut-off 20 -> 35 minutes
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
R=/srv/farm/prompts/roles; C=/opt/farm/context; S=/etc/systemd/system
sha() { sha256sum "$1" | cut -d' ' -f1; }
check() {  # file, old, new
  local h; h=$(sha "$1")
  if [[ $h == "$3" ]]; then echo "  $1: already the 14c version"
  elif [[ $h == "$2" ]]; then echo "  $1: as expected"
  else echo "  $1 changed since 14b (sha256 $h). Nothing was changed." >&2; exit 1; fi
}
echo "== checks (nothing is changed yet)"
check $R/scout.md 7eabc6637bde4504eb65ba4c22d8ab06979553a0367f4b2b2f555f5341bf89dc b7accc523f0cd6296b065ba7f45f325c5aa344baae260ed88b038046ec307d0b
check $C/scout ba94a6815819e62273f821bc2439b924e9c4eef9b4a4505c9160aa075fd9185c debc1442b561f21150ec76a1e582128ede446826fdcc6742f892337980509994
python3 -I -B -c 'import sys; compile(open(sys.argv[1]).read(), sys.argv[1], "exec")' context-scout
bash test-14b.sh /opt/farm/bin/scout-enum context-scout /opt/farm/bin/scout-done
echo "== install"
install -o harness -g harness -m 644 new/scout.md $R/scout.md
install -o root -g root -m 755 context-scout $C/scout
for n in 1 2 3 4; do
  f="$S/agent@scout-$n.service.d/scout.conf"
  sed -i -e 's/^RuntimeMaxSec=20min$/RuntimeMaxSec=35min/' -e 's/^Environment=SESSION_MAX_MIN=20$/Environment=SESSION_MAX_MIN=35/' "$f"
  grep -qx 'RuntimeMaxSec=35min' "$f" && grep -qx 'Environment=SESSION_MAX_MIN=35' "$f" || { echo "  $f: cut-off not changed" >&2; exit 1; }
done
systemctl daemon-reload
for n in 1 2 3 4; do /opt/farm/bin/assemble-prompt "scout-$n"; done
echo "  scout prompt: $(stat -c %s /srv/farm/runners/scout-1/prompt.md) bytes, cut-off $(systemctl show agent@scout-1.service -p RuntimeMaxUSec --value)"
echo "  sha256 (expected / installed)"
echo "    scout.md b7accc523f0cd6296b065ba7f45f325c5aa344baae260ed88b038046ec307d0b"
echo "             $(sha $R/scout.md)"
echo "Installed phase 14c. Sessions running now keep the old prompt and cut-off; the next ones use the new."
