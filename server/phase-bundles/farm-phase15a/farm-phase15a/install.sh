#!/usr/bin/env bash
# Phase 15a: Blockscout PRO API as a second backend of farm-explorer.
#  - /opt/farm/bin/farm-explorer: asks Etherscan first; asks Blockscout (api.blockscout.com/v2/api,
#    same Etherscan-style modules, chain_id=) when Etherscan says the chain is not on its plan /
#    unsupported / the key is invalid, and for source / abi when Etherscan has no verified source.
#    Answers say "via". Both keys are scrubbed from every answer and log line.
#  - /opt/farm/bin/explorer (CLI): prints "via", reads Blockscout's multi-file sources
#    (AdditionalSources) and proxy fields, `explorer chains` shows both backends
#  - /etc/farm/explorer.json: + "blockscout" {upstream, min_interval_s 0.25, daily_limit 20000}
#  - farm-explorer.service.d/blockscout.conf: LoadCredential=bkey:/etc/farm/blockscout.key
#  - inbox/meta note for TOOLS.md and the wiki
# The key file is placed by the human before this runs (root 0600). Order: checks, offline tests,
# one live call with the key, then backup + install + restart. If the service does not come back,
# the files are restored and it is restarted. Backups: .<name>.bak-15a.
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }

B=/opt/farm/bin
KEY=/etc/farm/blockscout.key
CONF=/etc/farm/explorer.json
DROPDIR=/etc/systemd/system/farm-explorer.service.d
DROP=$DROPDIR/blockscout.conf
NOTE=/srv/farm/ws/inbox/meta/2026-11-18-phase15a-blockscout.md
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT

echo "== checks"
for f in new/farm-explorer new/explorer test-15a.py inbox-meta-2026-11-18-phase15a-blockscout.md; do
  [[ -s $f ]] || { echo "missing $f in the bundle" >&2; exit 1; }
done
if [[ ! -s $KEY ]]; then
  echo "!! $KEY is missing or empty. Put the key there first (nothing was changed):" >&2
  echo "   sudo sh -c 'umask 077; cat > $KEY'   (paste the key, Enter, then Ctrl-D)" >&2
  exit 1
fi
perm=$(stat -c '%U:%G %a' "$KEY")
if [[ $perm != "root:root 600" ]]; then
  echo "   $KEY was $perm -> root:root 600"
  chown root:root "$KEY"; chmod 600 "$KEY"
fi
[[ $(wc -l < "$KEY") -le 1 ]] || { echo "!! $KEY has more than one line; keep only the key (nothing was changed)" >&2; exit 1; }
head -c 7 "$KEY" | grep -q '^proapi_' || echo "   note: the key does not start with proapi_ (Blockscout PRO keys do); the live check below decides"

check_file() {   # path, 12e marker
  local path=$1 marker=$2 new=$3
  if cmp -s "$path" "$new"; then echo "  $path: already phase 15a"; return 0; fi
  if ! grep -qF "$marker" "$path" || grep -qF "phase 15a" "$path"; then
    echo "!! $path is not the phase 12e version this bundle expects. Nothing was changed." >&2
    echo "   Send it to the chat: sudo cat $path" >&2
    exit 1
  fi
  echo "  $path: phase 12e, will be replaced"
}
check_file $B/farm-explorer "a local read-only door to the Etherscan V2 API that keeps the API key" new/farm-explorer
check_file $B/explorer "Etherscan API key; you never need one" new/explorer
python3 -I -c 'import json,sys; c=json.load(open(sys.argv[1])); assert isinstance(c.get("chains"), dict) and c.get("upstream")' "$CONF" \
  || { echo "!! $CONF does not look like the 12e config. Nothing was changed." >&2; exit 1; }
systemctl is-active --quiet farm-explorer || echo "   note: farm-explorer is not active right now"

echo "== offline tests"
python3 -I test-15a.py new

echo "== live check of the key (one block-number call on base, one source call; the key is not printed)"
python3 -I - "$KEY" <<'PY'
import json, sys, urllib.parse, urllib.request
key = open(sys.argv[1]).read().strip()
def call(params):
    url = "https://api.blockscout.com/v2/api?" + urllib.parse.urlencode(dict(params, chain_id="8453", apikey=key))
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "farm-explorer/2"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(300).decode("utf-8", "replace").replace(key, "***")
    except Exception as exc:
        return None, str(exc).replace(key, "***")
s1, d1 = call({"module": "block", "action": "eth_block_number"})
print(f"  block number: HTTP {s1} {str(d1)[:160]}")
s2, d2 = call({"module": "contract", "action": "getsourcecode", "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"})
ok2 = isinstance(d2, dict) and str(d2.get("status")) == "1" and d2.get("result") and d2["result"][0].get("ContractName")
print(f"  base USDC source: HTTP {s2} " + (f"ok, {d2['result'][0]['ContractName']}" if ok2 else str(d2)[:200].replace(key, "***")))
ok1 = isinstance(d1, dict) and d1.get("result")
sys.exit(0 if ok1 and ok2 else "!! the Blockscout key did not work; nothing was changed. Paste the two lines above.")
PY

echo "== backup and install"
for n in farm-explorer explorer; do
  [[ -e $B/.$n.bak-15a ]] || cp -a $B/$n $B/.$n.bak-15a
  cp -a $B/$n "$tmp/$n.before"
  install -o "$(stat -c %u $B/$n)" -g "$(stat -c %g $B/$n)" -m "$(stat -c %a $B/$n)" new/$n $B/$n
done
[[ -e /etc/farm/.explorer.json.bak-15a ]] || cp -a "$CONF" /etc/farm/.explorer.json.bak-15a
cp -a "$CONF" "$tmp/explorer.json.before"
python3 -I - "$CONF" <<'PY'
import json, os, sys
p = sys.argv[1]
c = json.load(open(p))
if "blockscout" not in c:
    c["blockscout"] = {"upstream": "https://api.blockscout.com/v2/api", "min_interval_s": 0.25, "daily_limit": 20000}
    st = os.stat(p)
    with open(p + ".new", "w") as f:
        json.dump(c, f, indent=2)
        f.write("\n")
    os.chown(p + ".new", st.st_uid, st.st_gid)
    os.chmod(p + ".new", st.st_mode & 0o7777)
    os.replace(p + ".new", p)
    print("  explorer.json: + blockscout")
else:
    print("  explorer.json: blockscout already there")
PY
had_drop=0; [[ -e $DROP ]] && had_drop=1
mkdir -p "$DROPDIR"
printf '%s\n' '# phase 15a: Blockscout PRO API key for farm-explorer (root 0600, placed by the human)' \
  '[Service]' "LoadCredential=bkey:$KEY" > "$DROP"
systemctl daemon-reload

restore() {
  echo "!! $1 - restoring the phase 12e files and restarting" >&2
  for n in farm-explorer explorer; do cp -a "$tmp/$n.before" $B/$n; done
  cp -a "$tmp/explorer.json.before" "$CONF"
  (( had_drop )) || rm -f "$DROP"
  systemctl daemon-reload
  systemctl restart farm-explorer || true
  sleep 2; systemctl is-active farm-explorer || true
  exit 1
}

echo "== restart farm-explorer"
systemctl restart farm-explorer || restore "restart failed"
ok=0
for _ in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:29484/health >"$tmp/health" 2>/dev/null; then ok=1; break; fi
  sleep 0.5
done
(( ok )) || { journalctl -u farm-explorer -n 20 --no-pager >&2 || true; restore "no /health answer"; }
python3 -I -c 'import json,sys; h=json.load(open(sys.argv[1])); assert "blockscout" in h["backends"], h' "$tmp/health" \
  || restore "the service started without the Blockscout backend"

echo "== check the installed service"
sha256sum $B/farm-explorer $B/explorer
$B/explorer chains || restore "explorer chains failed"
$B/explorer source base 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913 | head -5 || true
curl -fsS http://127.0.0.1:29484/health | python3 -I -c 'import json,sys; h=json.load(sys.stdin); print("  backends:", {k: {"calls_today": v["calls_today"], "ok": v["upstream_ok"], "failed": v["upstream_failed"]} for k, v in h["backends"].items()})'
journalctl -u farm-explorer -n 3 --no-pager -o cat | grep -c proapi_ >/dev/null && echo "!! a key-like string is in the log - tell the chat" >&2 || true

[[ -e $NOTE ]] || install -o harness -g "$(stat -c %G /srv/farm/ws/inbox/meta)" -m 664 inbox-meta-2026-11-18-phase15a-blockscout.md "$NOTE"
echo "Installed phase 15a. Paste everything from '== restart farm-explorer' down."
