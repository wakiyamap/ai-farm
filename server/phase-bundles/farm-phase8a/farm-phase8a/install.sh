#!/usr/bin/env bash
# Phase 8a: make the earner's web_search actually use RustXNG. Phase 8 put the provider package in
# the dsh install's node_modules, but dsh only loads packages reachable from the installation or the
# profile manifest, so web_search failed with 'configured web provider "rustxng" is not registered'.
# Now the provider is a proper dsh bundle (package.json "dsh.bundle" + its own cordis.patch.yml)
# installed into the headless profile with `dsh plugin add` (pnpm), and phase 8's rows are removed
# from /etc/farm/earner-headless.patch.yml.
# Run from the unpacked directory: sudo ./install.sh   (safe to re-run)
set -euo pipefail
trap 'echo "install.sh failed at line $LINENO: $BASH_COMMAND" >&2' ERR
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
DSH=/opt/farm/dsh/node_modules/.bin/dsh
NODE_DIR=$(dirname "$(readlink -f "$(command -v node || echo /opt/node/bin/node)")")
PROFILE=/home/earner/.dsh/profiles/headless
export PATH="$NODE_DIR:$PATH"   # npm/pnpm are `#!/usr/bin/env node` scripts
as_earner() { (cd /tmp && sudo -u earner env HOME=/home/earner PATH="$NODE_DIR:/usr/bin:/bin" "$@"); }
"$NODE_DIR/node" --check opt/farm/dsh-plugins/dsh-web-search-rustxng/lib/index.js

# 1. pnpm (dsh plugin add drives it)
if ! PATH="$NODE_DIR:$PATH" command -v pnpm >/dev/null; then
  "$NODE_DIR/npm" install -g pnpm@10.12.1
fi
echo "pnpm $(PATH="$NODE_DIR:$PATH" pnpm --version)"

# 2. undo phase 8's non-working placement and patch rows
rm -rf /opt/farm/dsh/node_modules/@farm
P=/etc/farm/earner-headless.patch.yml
python3 -I - "$P" <<'PY'
import re, sys
p = sys.argv[1]; s = open(p).read()
block = re.compile(r"\n?# web_search through the local RustXNG service.*?name: '@farm/dsh-web-search-rustxng'\n", re.S)
t = block.sub("\n", s).rstrip("\n") + "\n"
if t != s:
    open(p, "w").write(t); print("removed phase 8 rows from", p)
PY
install -o root -g root -m 644 etc/farm/earner-headless.patch.yml.in /etc/farm/earner-headless.patch.yml.in
install -o earner -g earner -m 600 "$P" "$PROFILE/cordis.patch.yml" 2>/dev/null || true

# 3. the bundle, installed into the headless profile
install -d -o root -g root -m 755 /opt/farm/dsh-plugins
rm -rf /opt/farm/dsh-plugins/dsh-web-search-rustxng
cp -r opt/farm/dsh-plugins/dsh-web-search-rustxng /opt/farm/dsh-plugins/
chown -R root:root /opt/farm/dsh-plugins; chmod -R a+rX,go-w /opt/farm/dsh-plugins
as_earner "$DSH" plugin --profile headless add /opt/farm/dsh-plugins/dsh-web-search-rustxng
echo "== profile manifest"; sudo -u earner cat "$PROFILE/package.json"
echo "== installed"; sudo -u earner ls -la "$PROFILE/node_modules/@farm/" || true
echo "Installed phase 8a. The earner's next session should search through rustxng."
