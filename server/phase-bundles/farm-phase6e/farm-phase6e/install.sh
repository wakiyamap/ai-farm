#!/usr/bin/env bash
# Phase 6e: earner model GLM-5.3-Flash (:8000) -> Qwen3.8-Flash-Next (:8003).
#   - earner-headless.patch.yml: new default provider; model id read from the server
#   - farm.nft: earner may reach :8003 (8000 kept for rollback)
#   - earner drop-in: LOCAL_LLM_API_KEY=none
#   - roles.conf: model label for reports/dashboard
# Env overrides: MODEL_ID, CONTEXT (default 262144), MAX_TOKENS (default 32768).
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }

models=$(curl -sf -m 5 http://127.0.0.1:8003/v1/models) || { echo "no server on 127.0.0.1:8003 (/v1/models)" >&2; exit 1; }
: "${MODEL_ID:=$(printf '%s' "$models" | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"][0]["id"])')}"
: "${CONTEXT:=262144}" "${MAX_TOKENS:=32768}"
echo "model id: $MODEL_ID  context: $CONTEXT  maxTokens: $MAX_TOKENS"
# one smoke completion so a wrong id fails here, not in the earner's first session
curl -sf -m 120 http://127.0.0.1:8003/v1/chat/completions -H 'content-type: application/json' \
  -d "$(python3 -c 'import json,sys; print(json.dumps({"model": sys.argv[1], "messages": [{"role": "user", "content": "Reply with the single word OK."}], "max_tokens": 8}))' "$MODEL_ID")" \
  | python3 -c 'import json,sys; r=json.load(sys.stdin); print("smoke:", r["choices"][0]["message"]["content"].strip()[:40])'

sed -e "s|@MODEL_ID@|$MODEL_ID|g" -e "s|@CONTEXT@|$CONTEXT|g" -e "s|@MAX_TOKENS@|$MAX_TOKENS|g" \
  etc/farm/earner-headless.patch.yml.in > /tmp/earner-headless.patch.yml.$$
cp -a /etc/farm/earner-headless.patch.yml "/etc/farm/earner-headless.patch.yml.bak-$(date +%Y%m%d)" 2>/dev/null || true
install -o root -g root -m 644 /tmp/earner-headless.patch.yml.$$ /etc/farm/earner-headless.patch.yml
rm -f /tmp/earner-headless.patch.yml.$$
install -o root -g root -m 644 etc/farm/farm.nft /etc/farm/
install -o root -g root -m 644 etc/systemd/system/agent@earner-local.service.d/earner.conf /etc/systemd/system/agent@earner-local.service.d/
sed -i -E 's/^(earner-local[[:space:]]+earner[[:space:]]+dsh[[:space:]]+).*/\1qwen3.8-flash-next/' /etc/farm/roles.conf
grep -E '^earner-local' /etc/farm/roles.conf
systemctl daemon-reload
systemctl restart farm-nft.service
/opt/farm/bin/assemble-prompt earner-local
echo
echo "Installed phase 6e. The running earner session still uses GLM; switch now with:"
echo "  sudo systemctl restart agent@earner-local     (cuts the current session)"
echo "or wait for it to end (RuntimeMaxSec=75min) — the next session picks up the new model."
