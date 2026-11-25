#!/usr/bin/env bash
# Phase 9j (2026-11-10): gate-ctl read the manifest `executor:` path with its YAML quotes
# (executor: "scratch/...json" -> open('/srv/farm/ws/"scratch/...json"')), so moonwell-whale-base's
# promote stopped after adopt + funding, before the executor deployment. The path is now read like
# executor_args (quotes and trailing comment stripped). Exact-text patch of the installed gate-ctl;
# nothing changes if it differs from 9i. Does NOT deploy anything: finish a half-done promotion with
#   sudo -u farmgate /opt/farm/bin/gate-ctl deploy <id>
# Safe to re-run.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

python3 -I patch-9j.py check "$B/gate-ctl"
python3 -I patch-9j.py apply "$B/gate-ctl" "$tmp" >/dev/null
python3 -I -m py_compile "$tmp/gate-ctl"
echo "== offline test (fake chain in a temp dir)"
python3 -I test-9j.py "$B/gate-ctl" --old || true
python3 -I test-9j.py "$tmp/gate-ctl"
[[ -e "$B/.gate-ctl.bak-9j" ]] || cp -a "$B/gate-ctl" "$B/.gate-ctl.bak-9j"
install -o root -g root -m 755 "$tmp/gate-ctl" "$B/"

echo "== half-promoted live bots (no state/executor.json): executor artifact as the gate now reads it"
python3 -I - <<'PY'
import glob, os, re
for d in sorted(glob.glob("/srv/farm/ws/bots/live/*/")):
    if os.path.exists(d + "state/executor.json"):
        continue
    t = open(d + "manifest.yaml").read()
    m = re.search(r"^executor:\s*['\"]?([^'\"\s#]+)", t, re.M)
    art = m.group(1) if m else None
    ok = bool(art) and os.path.isfile(os.path.join("/srv/farm/ws", art))
    print(f"  {os.path.basename(d.rstrip('/')):32} executor={art}  artifact {'found' if ok else 'MISSING'}"
          f"  state/ {'ok' if os.path.isdir(d + 'state') else 'MISSING'}")
PY
echo "Installed phase 9j. Resume: sudo -u farmgate /opt/farm/bin/gate-ctl deploy <id>"
