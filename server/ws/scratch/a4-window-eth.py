import json, subprocess, sys, time

RELAY = "http://127.0.0.1:8545"
SPOKE = "0x973a023a77420ba610f06b3858ad991df6d85a08"
sels = json.load(open('scratch/a4-sel.json'))

def rpc(method, params, lane="research"):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
    r = subprocess.run(["curl","-s","-X","POST",f"{RELAY}/ethereum?lane={lane}","-H","content-type: application/json","-d",body],
                       capture_output=True, text=True)
    resp = json.loads(r.stdout)
    if "error" in resp: print("ERR", json.dumps(resp["error"])[:200], file=sys.stderr)
    return resp.get("result")

def call(data_hex, block, lane="research"):
    return rpc("eth_call", [{"to":SPOKE,"data":data_hex}, hex(block)], lane)

def words(ret): return [ret[2+64*i:2+64*(i+1)] for i in range(len(ret[2:])//64)]
def W(h): return int(h,16)

caps = [
 (26155698, "0xfcb4e71bc4b5fbbf7c558a94161db194c2e653de", 1, 10),
 (26193232, "0xf7b50786c52b6aeb8e98f011003afbbe2deb0432", 0, 5),
 (26246672, "0xac90a9f2cf5636202919455f263746e5f98f937d", 1, 5),
 (26271929, "0x7dd782cd81dc1f8b8c54cc9fdbd1f577f0add3cb", 0, 5),
 (26301940, "0x59a82f3a784850da9f7e6722f792b50a01450990", 0, 4),
 (26352006, "0x00fa944a4253f4c00add246827dbac5844104980", 0, 7),
]
offsets = [1,2,4,8,16,32,64]

# liquidation config at latest + near each capture
out = {"config": None, "captures": []}
cfg = call(sels["cfg"]+"", 26364000)  # getLiquidationConfig no args
print("cfg words:", [W(w) for w in words(cfg)[1:4]])

data_hf = sels["accdata"] + "0"*(64-40)  # selector + placeholder user; replace below
for (E, user, cR, dR) in caps:
    rec = {"block": E, "user": user}
    cfd = sels["accdata"] + user[2:].rjust(64,"0")
    ladder = {}
    for off in offsets:
        ret = call(cfd, E-off)
        if ret and len(ret) >= 2+64*8:
            ws = words(ret)
            ladder[off] = {"hf": W(ws[3]), "collval": W(ws[4]), "debtray": W(ws[5])}
    rec["ladder"] = ladder
    # bonus for the collateral reserve at a deep HF
    bonus_data = sels["bonus"] + hex(cR)[2:].rjust(64,"0") + user[2:].rjust(64,"0") + hex(int(0.5e18))[2:].rjust(64,"0")
    b = call(bonus_data, E-1)
    rec["bonus_at_0p5HF"] = int(b,16) if b else None
    out["captures"].append(rec)
    print(E, user[:10], {k: round(v["hf"]/1e18,4) for k,v in ladder.items()})
json.dump(out, open("scratch/a4-window-eth.json","w"), indent=1)
