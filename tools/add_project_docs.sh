#!/usr/bin/env bash
# Add the Project's human-side documents (from a claude.ai data export), the
# README and the redaction tools to the already-redacted tree, then repack.
#
#   bash add_project_docs.sh <path to projects.json from the export>
#
# Needs the tree left by collect.sh at $OUT (default /tmp/farm-public), and in
# this directory: extract_project_docs.py, sanitize.py, gather_secrets.py,
# collect.sh, README.md and the private identities.tsv (never copied).
set -euo pipefail
trap 'echo "add_project_docs.sh: stopped at line $LINENO (exit $?)" >&2' ERR

HERE=$(cd "$(dirname "$0")" && pwd)
SRC=${1:?usage: bash add_project_docs.sh <projects.json>}
PROJECT=${PROJECT:-マルチエージェントbot運用}
OUT=${OUT:-/tmp/farm-public}
PACK=${PACK:-$HOME/farm-public-server.tgz}
for f in extract_project_docs.py sanitize.py gather_secrets.py collect.sh README.md LICENSE LICENSE-docs identities.tsv; do
  [ -f "$HERE/$f" ] || { echo "missing $HERE/$f" >&2; exit 1; }
done
[ -d "$OUT/server" ] || { echo "no redacted tree at $OUT (run collect.sh first)" >&2; exit 1; }

echo "== 1. extract the Project's documents"
rm -rf "$OUT/project-docs"
python3 -I "$HERE/extract_project_docs.py" "$SRC" "$PROJECT" "$OUT/project-docs"

echo "== 2. gather this host's real secret values (0600 temp file)"
SECRETS=$(sudo mktemp /root/farm-secrets.XXXXXX)
trap 'sudo shred -u "$SECRETS" 2>/dev/null || sudo rm -f "$SECRETS"' EXIT
sudo python3 -I "$HERE/gather_secrets.py" "$SECRETS"

echo "== 3. redact project-docs"
rc=0
sudo python3 -I "$HERE/sanitize.py" "$OUT/project-docs" --secrets "$SECRETS" \
  --identities "$HERE/identities.tsv" --wordlist /opt/farm/lib/bip39-english.txt || rc=$?
if [ "$rc" -ne 0 ] && [ "$rc" -ne 2 ]; then
  echo "sanitize.py failed (exit $rc); nothing was packed" >&2; exit 1
fi

echo "== 4. README and tools (identities.tsv stays here)"
cp "$HERE/README.md" "$OUT/README.md"
mkdir -p "$OUT/tools"
cp "$HERE/collect.sh" "$HERE/sanitize.py" "$HERE/gather_secrets.py" \
   "$HERE/extract_project_docs.py" "$HERE/add_project_docs.sh" "$OUT/tools/"

echo "== 5. check the whole tree once more without changing it (with the current identities rules)"
rc2=0
sudo python3 -I "$HERE/sanitize.py" "$OUT" --secrets "$SECRETS" \
  --identities "$HERE/identities.tsv" --check-only || rc2=$?
if [ "$rc2" -ne 0 ] && [ "$rc2" -ne 2 ]; then
  echo "check failed (exit $rc2); nothing was packed" >&2; exit 1
fi

echo "== 6. licenses (added after the check: they carry the publisher's handle)"
cp "$HERE/LICENSE" "$HERE/LICENSE-docs" "$OUT/"

echo "== 7. pack"
sudo chown -R "$(id -u):$(id -g)" "$OUT"
rm -f "$PACK"
tar -C "$(dirname "$OUT")" -czf "$PACK" "$(basename "$OUT")"
ls -lh "$PACK"
sha256sum "$PACK"
if [ "$rc" -eq 2 ] || [ "$rc2" -eq 2 ]; then
  echo
  echo "Residual findings above: check them by hand before publishing."
  exit 2
fi
echo "done: $PACK"
