#!/usr/bin/env bash
# Phase 9d (inbox/human/2026-11-09-meta-ledger-dynamic-events.md; 2026-11-08 small tool ask §1):
#  - ledger sources may track events with dynamic / tuple / array parameters. topic0 is still checked
#    against keccak256 of the full canonical signature; indexed dynamic values are stored as their
#    topic hash; `data` names only a leading run of static one-word parameters, later ones stay unnamed
#    and undecoded (no extra CU).
#  - a topic0 mismatch now prints the signature the tool hashed and the hash it computed.
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/ledger-ingest
cp -a /opt/farm/bin/ledger-ingest "/opt/farm/bin/.ledger-ingest.bak-9d"
install -o root -g root -m 755 opt/farm/bin/ledger-ingest /opt/farm/bin/
echo "== current sources against the new validator (seed + sources.d)"
sudo -u farmdata python3 -I - <<'PY'
import json, importlib.machinery, importlib.util
l = importlib.machinery.SourceFileLoader("li", "/opt/farm/bin/ledger-ingest")
m = importlib.util.module_from_spec(importlib.util.spec_from_loader(l.name, l)); l.exec_module(m)
cfg = json.load(open("/etc/farm/ledger.json"))
seed, agent, problems = m.load_sources(cfg)
print(f"seed {len(seed)} ok, agent {len(agent)} ok, rejected {len(problems)}")
for f, why in problems:
    print("  rejected", f, ":", why)
PY
echo "Installed phase 9d. Rejected agent sources can now be fixed and re-added with 'ledger add-source'."
