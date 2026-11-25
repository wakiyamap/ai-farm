#!/usr/bin/env bash
# Phase 8: keyless web search for the agents.
#   - farm-search.service: RustXNG (Rust SearXNG, AGPL-3.0, unmodified, "standard" keyless profile)
#     on 127.0.0.1:29483, DynamicUser, no disk state
#   - /opt/farm/bin/websearch: CLI for every role (claude roles get Bash(websearch *))
#   - earner (dsh): web_search tool switched from the key-less-broken DeepSeek provider to a local
#     provider plugin (@farm/dsh-web-search-rustxng) that queries farm-search
#   - farm.nft: the earner may reach 29483 (bots still may not)
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
DSH_ROOT=/opt/farm/dsh
DSH=$DSH_ROOT/node_modules/.bin/dsh
as_earner() { (cd /tmp && sudo -u earner env HOME=/home/earner PATH=/opt/node/bin:/usr/bin:/bin "$@"); }

glibc=$(getconf GNU_LIBC_VERSION | awk '{print $2}')   # not `ldd | head`: SIGPIPE + pipefail exits silently
if [[ $(printf '%s\n2.39\n' "$glibc" | sort -V | head -1) != 2.39 ]]; then
  echo "glibc $glibc is older than 2.39; this binary needs Ubuntu 24.04+" >&2; exit 1
fi
python3 -I -m py_compile opt/farm/bin/websearch
bash -n opt/farm/bin/run-role
(cd opt/farm/lib && sha256sum -c <(awk '/^sha256/{print $2"  rustxng"}' rustxng.d/SOURCE))

# 1. search service
install -o root -g root -m 755 opt/farm/lib/rustxng /opt/farm/lib/rustxng
install -d -o root -g root -m 755 /opt/farm/lib/rustxng.d
install -o root -g root -m 644 opt/farm/lib/rustxng.d/* /opt/farm/lib/rustxng.d/
install -o root -g root -m 644 etc/systemd/system/farm-search.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable farm-search.service
systemctl restart farm-search.service
for i in $(seq 1 30); do curl -fs -m 2 http://127.0.0.1:29483/healthz >/dev/null && break; sleep 1; done
curl -fs -m 2 http://127.0.0.1:29483/healthz >/dev/null || { journalctl -u farm-search -n 20 --no-pager; exit 1; }

# 2. CLI + claude allowlist
install -o root -g root -m 755 opt/farm/bin/websearch opt/farm/bin/run-role /opt/farm/bin/

# 3. firewall: earner may reach 29483
install -o root -g root -m 644 etc/farm/farm.nft /etc/farm/
systemctl restart farm-nft.service

# 4. dsh provider plugin, resolvable from the dsh install like the built-in @deepseek-ai packages
install -d -o root -g root -m 755 "$DSH_ROOT/node_modules/@farm"
rm -rf "$DSH_ROOT/node_modules/@farm/dsh-web-search-rustxng"
cp -r opt/farm/dsh-plugins/dsh-web-search-rustxng "$DSH_ROOT/node_modules/@farm/"
chown -R root:root "$DSH_ROOT/node_modules/@farm"; chmod -R a+rX,go-w "$DSH_ROOT/node_modules/@farm"
(cd "$DSH_ROOT" && sudo -u earner /opt/node/bin/node --input-type=module -e \
  'const m = await import("@farm/dsh-web-search-rustxng"); let p; m.apply({web:{registerSearchProvider:x=>p=x}});
   const r = await p.search({query:"wikipedia"}); console.log(`plugin ok as earner: ${r.sources.length} sources`)') \
  || echo "WARNING: plugin import/search test as earner failed (see above)"

# 5. earner profile patch: select the provider and load the plugin
P=/etc/farm/earner-headless.patch.yml
if ! grep -q 'searchProvider: rustxng' "$P"; then
  cp -a "$P" "$P.bak-$(date +%Y%m%d%H%M)"
  { echo; cat etc/farm/web-rustxng.patch.part; } >> "$P"
fi
install -o root -g root -m 644 etc/farm/earner-headless.patch.yml.in /etc/farm/earner-headless.patch.yml.in
install -o earner -g earner -m 600 "$P" /home/earner/.dsh/profiles/headless/cordis.patch.yml 2>/dev/null || true
cfg=$(as_earner "$DSH" --profile headless headless --dump-config 2>&1 || true)
echo "$cfg" | grep -n -B1 -A4 -E 'searchProvider|farm-web-search-rustxng' | head -20 \
  || echo "(dump-config did not show the rows; check the earner's next session)"

echo "== smoke test"
sudo -u harness /opt/farm/bin/websearch -n 5 '!gh' aave v3 liquidation bot || true
sudo -u earner /opt/farm/bin/websearch -n 3 morpho blue || true
echo "Installed phase 8. The earner's next session uses it; running sessions keep the old config."
