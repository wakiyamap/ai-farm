import glob, json, os, subprocess
STOPPED = """trial-aave-arbitrum trial-aave-avalanche trial-aave-bsc trial-aave-optimism trial-aave-polygon trial-aave2-avalanche
trial-aave2-polygon trial-aave4-avalanche trial-aave4-base trial-benqi-avalanche trial-dolomite-arbitrum trial-euler-base trial-euler-bsc
trial-exactly-optimism trial-felix-liq-hyperevm trial-fluid-arbitrum trial-fluid-polygon trial-flux-bsc trial-hyperlend-hyperevm
trial-hypurrfi-hyperevm trial-kinza-bsc trial-llamalend-arbitrum trial-moonwell-base trial-morpho-arbitrum trial-morpho-cbbtc-base
trial-morpho-khype-hyperevm trial-morpho-whype-hyperevm trial-revert-lend-arbitrum trial-silo1-liq-arbitrum trial-venus-bsc
trial-peapods-base gearbox-v3-watcher-ethereum morpho-nextblock-ethereum""".split()
found = {}
files = sorted(glob.glob("/srv/farm/ws/scratch/*.json"), key=os.path.getmtime, reverse=True)
for f in files:
    try:
        d = json.load(open(f))
    except Exception:
        continue
    if not isinstance(d, dict) or not isinstance(d.get("live"), dict):
        continue
    for k, v in d["live"].items():
        if k in STOPPED and k not in found and isinstance(v, dict) and "address" in v:
            found[k] = (v["address"], [c for c in v.get("balances_usd", {}) if ":" not in c], v.get("balances_usd"), os.path.basename(f))
    if len(found) == len(STOPPED):
        break
print("missing addresses:", [s for s in STOPPED if s not in found])
for k in STOPPED:
    if k not in found:
        continue
    addr, chains, last, src = found[k]
    for c in chains:
        r = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", c, "eth_getBalance", json.dumps([addr, "latest"])], capture_output=True, text=True)
        out = r.stdout.strip()
        try:
            wei = int(json.loads(out)["result"] if out.startswith("{") else json.loads(out), 16)
        except Exception:
            wei = out[:80] + " ERR " + r.stderr.strip()[:80]
        print(k, c, addr, "native_wei_now", wei, "last_seen", last, src)
