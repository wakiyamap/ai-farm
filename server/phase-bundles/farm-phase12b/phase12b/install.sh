#!/usr/bin/env bash
# Phase 12b: a private send route (Flashbots Protect, ethereum only).
#  - rpc-relay (7 text patches): relay.json "private_send" {chain: url}; a send on the farmgate
#    socket with ?route=private goes to that url only. It never falls back to Alchemy or a
#    public node: a transaction meant to stay private is dropped, not published.
#  - farm-signer (6 text patches): a bot whose live manifest says `send_route: private` is sent
#    through that route on ethereum (gate.json "private_send_chains", default ["ethereum"]).
#    Every other bot and chain goes out through Alchemy as before. Policy checks unchanged;
#    signer.log records the route.
#  - relay.json: "private_send": {"ethereum": "https://rpc.flashbots.net/fast"}
# No live bot uses the route until a manifest says so, so nothing changes for the 3 live bots.
# gate-ctl, farm-watchdog, units, prompts and keys are not touched.
# Checks and offline tests run before anything changes. rpc-relay and farm-signer are restarted
# (live bots lose reads for a few seconds); if either does not come back, both files are restored.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
B=/opt/farm/bin
CONF=/etc/farm/relay.json
URL=https://rpc.flashbots.net/fast
export PYTHONDONTWRITEBYTECODE=1
sha() { sha256sum "$1" | cut -d' ' -f1; }
OLD_RELAY=284ead565b2d1cd6ae7c67bed3c3142d7a04b00ea3d06999a541cfc565f8e03e
OLD_SIGNER=3a9a53b01ddb6faab680791a6e48830e56dfce2100cd2d5fd543f6b1e09b56a4
NEW_RELAY=0fb9481a019f10870ad56aa6c620c88515228c17b988b7157da6f9165c17fe4c
NEW_SIGNER=3a55bfbc379c570a85c3896416864f4ca94c57fe67e0810ccbed32157469ec32
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "== checks (nothing is changed yet)"
for f in patch-12b.py test-12b.py; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$f"
done
hr=$(sha $B/rpc-relay); hs=$(sha $B/farm-signer)
if [[ $hr == "$NEW_RELAY" && $hs == "$NEW_SIGNER" ]]; then
  echo "  rpc-relay and farm-signer are already the 12b versions"
  cp $B/rpc-relay $B/farm-signer "$tmp/"
elif [[ $hr == "$OLD_RELAY" && $hs == "$OLD_SIGNER" ]]; then
  echo "  rpc-relay and farm-signer: as expected"
  python3 -I -B patch-12b.py check $B/rpc-relay $B/farm-signer
  python3 -I -B patch-12b.py apply $B/rpc-relay $B/farm-signer "$tmp"
  [[ $(sha "$tmp/rpc-relay") == "$NEW_RELAY" && $(sha "$tmp/farm-signer") == "$NEW_SIGNER" ]] \
    || { echo "  patched files do not have the expected sha256; nothing was changed" >&2; exit 1; }
  echo "== offline tests (installed files: report only)"
  python3 -I -B test-12b.py $B/rpc-relay $B/farm-signer --old | tail -1
else
  echo "  rpc-relay ($hr) or farm-signer ($hs) changed since the bundle was built. Nothing was changed." >&2
  exit 1
fi
for f in rpc-relay farm-signer; do
  python3 -I -B -c 'import sys; compile(open(sys.argv[1], encoding="utf-8").read(), sys.argv[1], "exec")' "$tmp/$f"
done
echo "== offline tests (patched files)"
python3 -I -B test-12b.py "$tmp/rpc-relay" "$tmp/farm-signer"
python3 -I -B -c 'import json,sys; c=json.load(open(sys.argv[1])); assert "ethereum" in c["chains"]' "$CONF"

restore() {
  echo "!! restoring the previous rpc-relay and farm-signer" >&2
  [[ -f $B/.rpc-relay.bak-12b ]] && cp -a $B/.rpc-relay.bak-12b $B/rpc-relay
  [[ -f $B/.farm-signer.bak-12b ]] && cp -a $B/.farm-signer.bak-12b $B/farm-signer
  [[ -f $CONF.bak-12b ]] && cat "$CONF.bak-12b" > "$CONF"
  systemctl restart rpc-relay.service || true
  sleep 3
  systemctl restart farm-signer.service || true
}
relay_up() {   # a live-lane read through the relay answers chain id 1
  for _ in $(seq 1 30); do
    if curl -s -m 5 -X POST -H 'content-type: application/json' \
         --data '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' \
         'http://127.0.0.1:8545/ethereum?lane=live' | grep -q '"result": *"0x1"'; then return 0; fi
    sleep 1
  done
  return 1
}

if [[ $hr != "$NEW_RELAY" ]]; then
  echo "== relay.json"
  if ! python3 -I -B -c 'import json,sys; sys.exit(0 if "private_send" in json.load(open(sys.argv[1])) else 1)' "$CONF"; then
    cp -a "$CONF" "$CONF.bak-12b"
    python3 -I -B - "$CONF" "$URL" > "$tmp/relay.json" <<'PY'
import json, sys
c = json.load(open(sys.argv[1], encoding="utf-8"))
c["private_send"] = {"ethereum": sys.argv[2]}
json.dump(c, sys.stdout, indent=2)
sys.stdout.write("\n")
PY
    cat "$tmp/relay.json" > "$CONF"       # keeps owner and mode
  fi
  python3 -I -B -c 'import json,sys; print("  private_send:", json.load(open(sys.argv[1]))["private_send"])' "$CONF"

  echo "== install"
  cp -a $B/rpc-relay $B/.rpc-relay.bak-12b
  cp -a $B/farm-signer $B/.farm-signer.bak-12b
  install -o root -g root -m 755 "$tmp/rpc-relay" "$tmp/farm-signer" $B/

  echo "== restart rpc-relay, then farm-signer"
  systemctl restart rpc-relay.service
  relay_up || { echo "rpc-relay does not answer" >&2; restore; exit 1; }
  systemctl restart farm-signer.service
  ok=0
  for _ in $(seq 1 30); do
    if systemctl is-active --quiet farm-signer.service && [[ -S /run/farm/signer.sock ]]; then ok=1; break; fi
    sleep 1
  done
  (( ok )) || { echo "farm-signer did not come back" >&2; journalctl -u farm-signer -n 15 --no-pager >&2; restore; exit 1; }
fi
systemctl is-active rpc-relay.service farm-signer.service

echo "== the route on the send socket (no transaction is sent: both requests carry a malformed one)"
runuser -u farmgate -- python3 -I -B - <<'PY' || echo "  (probe failed; the route is still installed)"
import http.client, json, socket
def post(path):
    class C(http.client.HTTPConnection):
        def connect(self):
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.settimeout(20)
            self.sock.connect("/run/farm-relay/send.sock")
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_sendRawTransaction", "params": ["0x00"]}).encode()
    c = C("unix")
    c.request("POST", path, body=body, headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
    return json.loads(c.getresponse().read())
r = post("/base?lane=live&route=private")
print("  base, private (expect: no private send route):", (r.get("error") or {}).get("message", r))
r = post("/ethereum?lane=live&route=private")
print("  ethereum, private, malformed tx (expect: an error from the private endpoint):", (r.get("error") or {}).get("message", r))
PY

echo "== live bots"
systemctl list-units --plain --no-legend 'bot@*.service' | awk '{print "  " $1, $3 "/" $4}'
echo "Installed phase 12b. No bot uses the private route until its manifest says send_route: private."
echo "To undo: restore $B/.rpc-relay.bak-12b, $B/.farm-signer.bak-12b and $CONF.bak-12b, then restart rpc-relay and farm-signer"
