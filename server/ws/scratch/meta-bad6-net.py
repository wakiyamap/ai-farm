"""Per stopped bot: txs sent (nonce), funded in / swept out (native + USDC) from the intermediate wallet,
inflows from anyone else (wins), net = out + dust - in. Read-only, research lane."""
import json, subprocess, sys
INTER = "0x915bd260dcb166f86a499d5fdb3775b5bec70427"
RPC = "/srv/farm/ws/tools/rpc.py"

def rpc(chain, method, params):
    r = subprocess.run(["python3", RPC, chain, method, json.dumps(params)], capture_output=True, text=True)
    out = r.stdout.strip()
    try:
        j = json.loads(out)
    except Exception:
        return None, (out + r.stderr)[:160]
    if isinstance(j, dict) and "result" in j:
        j = j["result"]
    if isinstance(j, dict) and "error" in j:
        return None, str(j["error"])[:160]
    return j, None

def transfers(chain, addr, direction):
    res, cats = [], ["external", "erc20", "internal"]
    for attempt in range(2):
        p = {"fromBlock": "0x0", "toBlock": "latest", "category": cats, "withMetadata": False, "excludeZeroValue": True, "maxCount": "0x3e8"}
        p["fromAddress" if direction == "out" else "toAddress"] = addr
        j, err = rpc(chain, "alchemy_getAssetTransfers", [p])
        if j is not None:
            return j.get("transfers", []), None
        cats = ["external", "erc20"]
    return None, err

gate = json.load(open("/srv/farm/ws/scratch/meta-bad6-gate.json"))
# native USD price per chain from the intermediate wallet's balance now
price = {}
def native_price(chain):
    if chain not in price:
        j, _ = rpc(chain, "eth_getBalance", [INTER, "latest"])
        wei = int(j, 16) if j else 0
        usd = gate["intermediate_balances_usd"].get(chain, 0)
        price[chain] = usd / (wei / 1e18) if wei else None
    return price[chain]

rows = []
stopped = open("/srv/farm/ws/scratch/meta-bad6-stopped.txt").read().split()
addrs = json.load(open("/srv/farm/ws/scratch/meta-bad6-addrs.json"))
for b in stopped:
    addr, chain = addrs[b]
    a = addr.lower()
    nonce_j, _ = rpc(chain, "eth_getTransactionCount", [addr, "latest"])
    nonce = int(nonce_j, 16) if nonce_j else None
    bal_j, _ = rpc(chain, "eth_getBalance", [addr, "latest"])
    dust = int(bal_j, 16) / 1e18 if bal_j else 0
    tin, e1 = transfers(chain, addr, "in")
    tout, e2 = transfers(chain, addr, "out")
    if tin is None or tout is None:
        rows.append({"bot": b, "chain": chain, "nonce": nonce, "error": e1 or e2}); continue
    px = native_price(chain) or 0
    def usd(t):
        v = float(t.get("value") or 0)
        asset = (t.get("asset") or "").upper()
        if t.get("category") in ("external", "internal") or asset in ("ETH", "BNB", "POL", "MATIC", "AVAX", "HYPE"):
            return v * px, "native"
        if asset.startswith("USDC") or asset == "USD₮0":
            return v, "usdc"
        return 0.0, "other:" + asset
    fund = swept = win = paid_other = 0.0
    other_assets = set()
    for t in tin:
        u, k = usd(t)
        if k.startswith("other"): other_assets.add(k)
        if (t.get("from") or "").lower() == INTER: fund += u
        else: win += u
    for t in tout:
        u, k = usd(t)
        if k.startswith("other"): other_assets.add(k)
        if (t.get("to") or "").lower() == INTER: swept += u
        else: paid_other += u
    net = swept + dust * px - fund
    rows.append({"bot": b, "chain": chain, "nonce": nonce, "funded_usd": round(fund, 2), "swept_usd": round(swept, 2),
                 "dust_usd": round(dust * px, 3), "inflow_other_usd": round(win, 2), "n_inflow_other": sum(1 for t in tin if (t.get("from") or "").lower() != INTER),
                 "outflow_other_usd": round(paid_other, 2), "net_usd": round(net, 2), "other_assets": sorted(other_assets)})
json.dump(rows, open("/srv/farm/ws/scratch/meta-bad6-net.json", "w"), indent=1)
for r in rows:
    print(json.dumps(r))
