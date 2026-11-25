import json, subprocess, sys
from collections import Counter

def rpc(method, params):
    out = subprocess.run(['python3','tools/rpc.py','base',method,json.dumps(params)],
                         capture_output=True,text=True).stdout
    d = json.loads(out)
    if 'error' in d:
        return {'__error__': d['error']}
    return d['result']

HEAD = 60930588
W7 = 57906587
W90 = HEAD - 90*432000  # placeholder, refined below

HUB = "0x783251f103555068c1e9d755f69458f39ed937c0"
VAULTS = ["0x10a1bca416313725daeaf4eb0478c0c00d34eb52","0x114f63d0cc180e2e886a1eaa84eb4458632504cb",
"0x1baeb82f78f55c793296e7153f2b45396ceaeb4b","0x28b5f996e5aaf9e44d9a80743486573661317b1a",
"0x38b2abdfb2fe79ad5e240fbd934a87b63038df5b","0x4850755be53384727b2e135926b66991557cf72d",
"0x62e22eab1dde57d71211222d192ed914f5f40f9f","0x68e8bdfd2b1044cd705c0b6d6d1b9c4c00fb7da6",
"0x6eaf2a89e4930a8124d9424625c8dfb74dd23dcb","0x8cd82a50f1168e61b88f6f92ace198c0059fec73",
"0x9db6dbdcf6b3f158f8b02d762f99f8ce7663e1aa","0xa2ff9c7faa11e5febb587be2293bef3375e1e723",
"0xb511c70f6c37b200117e5ab950035ebc64b8062b","0xb98840b22618e77bbd0403c81365eefc7d449559",
"0xc96fb24fa4a9ab9d38aa06cb406e5e2bc0a2e43b","0xcf8c4665525dd2292bbe9aa51f8309609f5ad51e",
"0xded00ff949d611b9ee91ab1a086e81ecfc23bd76"]
USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"

def scan(addr_or_list, f, t, label):
    p = {"address": addr_or_list, "fromBlock": hex(f), "toBlock": hex(t)}
    r = rpc("eth_getLogs",[p])
    if isinstance(r, dict) and '__error__' in r:
        print(f"{label}: ERR {r['__error__']}")
        return None
    return r

# refine 90d window from timestamps
def bts(n):
    b = rpc("eth_getBlockByNumber",[hex(n), False])
    return int(b['timestamp'],16)

now = bts(HEAD)
f90 = None
lo, hi = 0, HEAD
target = now - 90*86400
while lo < hi:
    mid=(lo+hi)//2
    if bts(mid) < target: lo = mid+1
    else: hi = mid
f90 = lo
print("head",HEAD,"now",now,"f90",f90,"ts90",bts(f90))

# hub 7d (exact)
for lbl, f in [("hub_7d", W7), ("hub_90d", f90)]:
    logs = scan(HUB, f, HEAD, lbl)
    if logs is None: continue
    print(f"{lbl}: {len(logs)} logs  range {hex(f)}-{hex(HEAD)}")
    print("   topic0 counts:", Counter(l['topics'][0] for l in logs).most_common(12))

# control: USDC, same shape, small range
logs = scan(USDC, HEAD-20000, HEAD, "usdc_ctl")
print("usdc_ctl (20k blocks):", "ERR" if logs is None else len(logs))

# vaults 7d and 90d (17 addresses in one call)
for lbl, f in [("vaults_7d", W7), ("vaults_90d", f90)]:
    logs = scan(VAULTS, f, HEAD, lbl)
    if logs is None: continue
    print(f"{lbl}: {len(logs)} logs")
    print("   topic0 counts:", Counter(l['topics'][0] for l in logs).most_common(12))
    print("   by address:", Counter(l['address'] for l in logs).most_common(8))
