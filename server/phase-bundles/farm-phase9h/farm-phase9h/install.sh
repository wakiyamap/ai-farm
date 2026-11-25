#!/usr/bin/env bash
# Phase 9h (small):
#  - fork fund-token exits 2 (with a reason on stderr) when the impersonated transfer fails or
#    has no receipt, instead of printing FAILED and exiting 0 (meta c10492af).
#  - ledger CLI help describes the dynamic/tuple event rules added in 9d (was "Only static ABI types").
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
python3 -I -m py_compile opt/farm/bin/fork opt/farm/bin/ledger
for f in fork ledger; do cp -a "/opt/farm/bin/$f" "/opt/farm/bin/.$f.bak-9h"; done
install -o root -g root -m 755 opt/farm/bin/fork opt/farm/bin/ledger /opt/farm/bin/
/opt/farm/bin/fork 2>&1 | grep -q "exit 2 if the transfer fails" && echo "fork: ok"
/opt/farm/bin/ledger 2>&1 | grep -q "full canonical signature" && echo "ledger: ok"
echo "Installed phase 9h."
