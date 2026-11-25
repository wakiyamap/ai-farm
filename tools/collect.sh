#!/usr/bin/env bash
# Collect the Farm's configuration, code, workspace, wiki and databases into a
# redacted tree for publication, and pack it as ~/farm-public-server.tgz.
#
# Run on the farm host as the admin user (needs sudo), from the directory that
# holds this script, sanitize.py, gather_secrets.py and the private
# identities.tsv (host/operator names; never published):
#   bash collect.sh
#
# Never copied: /var/lib/farmgate/mnemonic, any *.key, .env files in the
# workspace, .git directories, symlinks, sockets/FIFOs/device nodes, agent
# harness credentials.
# ws/scratch: only the agents' own notes are kept (top-level *.md *.log *.py
# *.json *.txt up to 1 MB, minus anything that is third-party contract source).
# Subdirectories (cloned repos, verified-source dumps, site bundles) are left out.
# Everything copied is redacted by sanitize.py; the real secret values on this
# host are gathered first so they can be matched exactly and checked for.
# If sanitize.py fails (anything other than exit 0 or 2), nothing is packed and
# any old pack is deleted.
set -euo pipefail
trap 'echo "collect.sh: stopped at line $LINENO (exit $?)" >&2' ERR

HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${OUT:-/tmp/farm-public}
S="$OUT/server"
PACK=${PACK:-$HOME/farm-public-server.tgz}
for f in sanitize.py gather_secrets.py identities.tsv; do
  [ -f "$HERE/$f" ] || { echo "missing $HERE/$f" >&2; exit 1; }
done
command -v rsync >/dev/null || { echo "rsync is required (sudo apt install rsync)" >&2; exit 1; }

echo "== 0. check that the farm is down"
if systemctl list-units --state=active --no-legend 'farm-*' 'bot@*' 'agent@*' 'paper@*' 'fork@*' 'rpc-relay*' 2>/dev/null | grep -q .; then
  systemctl list-units --state=active --no-legend 'farm-*' 'bot@*' 'agent@*' 'paper@*' 'fork@*' 'rpc-relay*'
  echo "some farm units are still active; stop them first (farm/farm-wind-down.md step 5)" >&2
  exit 1
fi

# An old pack must never survive a failed run and be mistaken for a good one.
rm -f "$PACK"
sudo rm -rf "$OUT"
sudo mkdir -p "$S"

EXCL=(
  --no-links --no-specials --no-devices
  --exclude='.git' --exclude='.git/'
  --exclude='node_modules/' --exclude='__pycache__/' --exclude='.venv/'
  --exclude='cache/' --exclude='out/build-info/'
  --exclude='lib/forge-std/' --exclude='lib/openzeppelin*/' --exclude='lib/solmate/'
  --exclude='*.key' --exclude='mnemonic' --exclude='.env' --exclude='.env.*'
  --exclude='.codex/' --exclude='.claude/' --exclude='.dsh/'
)

echo "== 1. workspace (kb, wiki, ledger, bots, decisions, inbox, reports, logs, scratch, history)"
sudo rsync -a "${EXCL[@]}" --max-size=95m --exclude='/scratch/' /srv/farm/ws/ "$S/ws/"
echo "   scratch: agents' own notes only"
# (rsync uses the first rule that matches, so the named exclusions come before the includes.)
sudo rsync -a "${EXCL[@]}" --max-size=1m --exclude='/dol_llms_full.txt' \
  --include='/*.md' --include='/*.log' --include='/*.py' --include='/*.json' --include='/*.txt' \
  --exclude='*' /srv/farm/ws/scratch/ "$S/ws/scratch/"
# Verified-source dumps and copied contracts are other people's code.
# (grep exits 1 for a batch with no match, so find's status is ignored here.)
L3P=$(mktemp)
sudo find "$S/ws/scratch" -maxdepth 1 -type f -exec grep -lZE 'pragma solidity|SPDX-License-Identifier|"SourceCode"' {} + >"$L3P" 2>/dev/null || true
n3p=$(tr -cd '\0' <"$L3P" | wc -c)
xargs -0r sudo rm -f <"$L3P"
rm -f "$L3P"
echo "   scratch: removed $n3p third-party source files, kept $(sudo find "$S/ws/scratch" -type f | wc -l)"
# Databases may be larger than the cap above; copy them whole and report sizes later.
for db in kb/knowledge.db ledger/ledger.db; do
  if sudo test -f "/srv/farm/ws/$db"; then
    sudo mkdir -p "$S/ws/$(dirname "$db")"
    sudo cp "/srv/farm/ws/$db" "$S/ws/$db"
    for ext in -wal -shm; do
      sudo test -f "/srv/farm/ws/$db$ext" && sudo cp "/srv/farm/ws/$db$ext" "$S/ws/$db$ext" || true
    done
  fi
done

echo "== 2. prompts and assembled prompts"
sudo rsync -a "${EXCL[@]}" /srv/farm/prompts/ "$S/prompts/"
sudo mkdir -p "$S/runners"
for d in /srv/farm/runners/*/; do
  n=$(basename "$d")
  sudo test -f "$d/prompt.md" && { sudo mkdir -p "$S/runners/$n"; sudo cp "$d/prompt.md" "$S/runners/$n/"; } || true
done

echo "== 3. code (/opt/farm), without vendored binaries or vendored Python packages"
sudo rsync -a "${EXCL[@]}" --exclude='/dsh' --exclude='/dsh/' --exclude='/lib/rustxng' \
  --exclude='/pylib' --exclude='/pylib/' /opt/farm/ "$S/opt-farm/"
# Other people's packages are not republished; list them so the code can be set up again.
if [ -d /opt/farm/pylib ]; then
  { echo "# Python packages that were vendored in /opt/farm/pylib (not included; install from PyPI)"
    ls -1 /opt/farm/pylib | sed -n 's/\.dist-info$//p' | sed 's/-\([^-]*\)$/==\1/' | sort; } \
    | sudo tee "$S/opt-farm/pylib-packages.txt" >/dev/null
fi

echo "== 4. config (/etc/farm), systemd units, sudoers, nftables"
sudo rsync -a "${EXCL[@]}" /etc/farm/ "$S/etc-farm/"
sudo mkdir -p "$S/systemd"
for pat in 'farm-*' 'agent@*' 'bot@*' 'paper@*' 'fork@*' 'rpc-relay*' 'ledger-ingest*'; do
  for u in /etc/systemd/system/$pat; do
    [ -e "$u" ] && sudo cp -r "$u" "$S/systemd/" || true
  done
done
sudo mkdir -p "$S/sudoers.d"
for f in /etc/sudoers.d/*; do
  sudo grep -qiE 'farm|harness|earner|gate' "$f" 2>/dev/null && sudo cp "$f" "$S/sudoers.d/" || true
done

echo "== 5. run records and the gate's ledger (not the seed)"
sudo mkdir -p "$S/var-lib-farm" "$S/var-lib-farmgate"
sudo test -f /var/lib/farm/ops.db && sudo cp /var/lib/farm/ops.db "$S/var-lib-farm/" || true
for f in gate.log signer.log pnl.json accounts.json; do
  sudo test -f "/var/lib/farmgate/$f" && sudo cp "/var/lib/farmgate/$f" "$S/var-lib-farmgate/" || true
done

echo "== 6. phase bundles left in $HOME"
sudo mkdir -p "$S/phase-bundles"
shopt -s nullglob nocaseglob
for b in "$HOME"/*phase*.tgz "$HOME"/*phase*.tar.gz "$HOME"/*phase*.tar; do
  name=$(basename "$b"); name=${name%.tgz}; name=${name%.tar.gz}; name=${name%.tar}
  dest="$S/phase-bundles/$(echo "$name" | tr 'A-Z' 'a-z')"
  sudo mkdir -p "$dest"
  sudo tar -xf "$b" -C "$dest" --no-same-owner --no-same-permissions || echo "  could not unpack $b"
done
shopt -u nullglob nocaseglob
# Bundles may carry their own copy of the vendored packages.
sudo find "$S/phase-bundles" -type d -name pylib -prune -exec rm -rf {} +

echo "== 7. gather this host's real secret values (kept only in a 0600 temp file)"
SECRETS=$(sudo mktemp /root/farm-secrets.XXXXXX)
trap 'sudo shred -u "$SECRETS" 2>/dev/null || sudo rm -f "$SECRETS"' EXIT
sudo python3 -I "$HERE/gather_secrets.py" "$SECRETS"

echo "== 8. redact"
WL=/opt/farm/lib/bip39-english.txt
HINTS=${HINTS:-$(dirname "$OUT")/farm-public-hints.txt}
rc=0
sudo python3 -I "$HERE/sanitize.py" "$S" --secrets "$SECRETS" --identities "$HERE/identities.tsv" \
  --wordlist "$WL" --hints "$HINTS" || rc=$?
if [ "$rc" -ne 0 ] && [ "$rc" -ne 2 ]; then
  echo >&2
  echo "sanitize.py failed (exit $rc). The tree at $OUT is only partly redacted." >&2
  echo "Nothing was packed. Fix the error and run collect.sh again." >&2
  exit 1
fi

echo "== 9. pack"
sudo chown -R "$(id -u):$(id -g)" "$OUT"
echo "files over 95 MB (GitHub refuses files over 100 MB; use Git LFS or xz them):"
find "$OUT" -type f -size +95M -exec ls -lh {} \; || true
echo "largest directories under $S (for deciding what to leave out):"
{ du -sh "$S"/*; du -sh "$S"/ws/*; } 2>/dev/null | sort -rh | head -n 15 || true
tar -C "$(dirname "$OUT")" -czf "$PACK" "$(basename "$OUT")"
ls -lh "$PACK"
sha256sum "$PACK"

if [ "$rc" -eq 2 ]; then
  echo
  echo "The residual scan found something (RESIDUAL FINDINGS above). Open those files"
  echo "and check them by hand before publishing. The tree is at $OUT."
  echo "Heuristic hints (not findings) are in $HINTS."
  exit 2
fi
echo "done: $PACK (tree at $OUT; heuristic hints in $HINTS)"
