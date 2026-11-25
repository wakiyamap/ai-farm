#!/usr/bin/env bash
# Phase 9e — blockers found while the first promotions were attempted (2026-11-09):
#  - gate-ctl / farm-signer: manifest parsing tolerates every YAML list style for allowed_contracts
#    and chains (block / inline / list of mappings, trailing comments); the gate refused
#    franken-dutch, and the signer would have refused any address written with a trailing comment.
#  - gate-ctl: the executor is deployed WITH manifest `executor_args` (it ignored them, so every
#    constructor-with-arguments deployment reverted); `{bot}` in executor_args = the bot's address;
#    the gate waits for the deployment receipt and refuses to promote if it did not succeed.
#  - ledger-ingest: agent sources get a fair, rotating share of the per-run CU budget (sources late
#    in file order, e.g. uniswap_protocol_fees.released, never got a cursor).
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/gate-ctl opt/farm/bin/farm-signer opt/farm/bin/ledger-ingest
for f in gate-ctl farm-signer ledger-ingest; do cp -a "/opt/farm/bin/$f" "/opt/farm/bin/.$f.bak-9e"; done
install -o root -g root -m 755 opt/farm/bin/gate-ctl opt/farm/bin/farm-signer opt/farm/bin/ledger-ingest /opt/farm/bin/
systemctl restart farm-signer.service
sleep 3
systemctl is-active farm-signer.service
echo "== how the gate now reads each paper manifest"
python3 -I - <<'PY'
import glob, importlib.machinery, importlib.util, sys
sys.path.insert(0, "/opt/farm/lib")
l = importlib.machinery.SourceFileLoader("gc", "/opt/farm/bin/gate-ctl")
m = importlib.util.module_from_spec(importlib.util.spec_from_loader(l.name, l)); l.exec_module(m)
for p in sorted(glob.glob("/srv/farm/ws/bots/paper/*/manifest.yaml")):
    t = open(p).read()
    print(f"{p.split('/')[-2]:32} chains={m.manifest_list(t, 'chains')} allowed={len(m.manifest_addresses(t))} "
          f"executor_args={'yes' if 'executor_args:' in t else 'no'}")
PY
echo "Installed phase 9e."
