#!/usr/bin/env python3
import subprocess, json, sys

MORPHO = "0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb"

def rpc(method, params, tag="latest"):
    p = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", "base", method,
                        json.dumps(params), "--lane", "research"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-300:])
    return json.loads(p.stdout)["result"]

def call(to, data, tag):
    r = rpc("eth_call", [{"to": to, "data": data}, tag])
    return r

def params(mkid):
    d = "0x2c3c9157" + mkid[2:]
    r = call(MORPHO, d, "latest")
    # 5 words: loanToken, collateralToken, oracle, irm, lltv
    w = [r[2+i*64:2+(i+1)*64] for i in range(5)]
    a = lambda i: "0x" + w[i][-40:]
    return dict(loan=a(0), coll=a(1), oracle=a(2), irm=a(3), lltv=int(w[4], 16))

def enc_addr(x): return x[2:].rjust(64, "0")

def liq_data(p, borrower, max_repaid="f"*64):
    tuple_word = lambda h: h[2:].rjust(64, "0")
    data = "0xd8eabcb8"
    # head: offset to tuple(0x20), borrower, maxRepaidShares, minSeized, offset to data, data len, data
    data += "00000000000000000000000000000000000000000000000000000000000000a0"
    data += enc_addr(borrower)
    data += max_repaid
    data += "0" * 64  # minSeizedTokens = 0
    data += "00000000000000000000000000000000000000000000000000000000000000e0"
    data += "0" * 63 + "4"  # bytes length 4
    data += "00000000" + "0" * 56  # 4-byte payload padded to 32
    data += tuple_word(p["loan"]) + tuple_word(p["coll"]) + tuple_word(p["oracle"]) + tuple_word(p["irm"])
    data += hex(p["lltv"])[2:].rjust(64, "0")
    return data

def pos(mkid, user, tag):
    d = "0x93c52062" + mkid[2:] + enc_addr(user)
    r = call(MORPHO, d, tag)
    w = [int(r[2+i*64:2+(i+1)*64], 16) for i in range(3)]
    return w  # supplyShares, borrowShares, collateral

cases = [
    ("C58300657", 58300657, "0x1a3e69d0109bb1be42b80e11034bb6ee98fc466721f26845dc83b2aa8d979137", "0xe7be437cf1a842a9bb8fa1e6f1bc980d91ce583e", 10.921242, "0x715a3219fe626e24cd7325ac1d06008ab0ebbd47"),
    ("C58292957", 58292957, "0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836", "0xab96157243d61ccd386c0e3108b3b22407aed83e", 0.740765, "0xe8711b02ee2d779c736fea98c042aeb3b390c398"),
    ("C58192028", 58192028, "0x1a3e69d0109bb1be42b80e11034bb6ee98fc466721f26845dc83b2aa8d979137", "0x3aada47cff218d478a4064fd848265ce4461b4e5", 0.196456, "0x844124693a429cb9ed04472a23d6aebfd1395dfe"),
    ("C58015037", 58015037, "0xdaa04f6819210b11fe4e3b65300c725c32e55755e3598671559b9ae3bac453d7", "0xa2451e7404b3e1811dd06649dfd8f34d1c579be0", 10481.470436, "0xd4e96922b5122087cf414b400a1dc491f0f56a48"),
    ("C57997287", 57997287, "0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda", "0x1c8d5cf2649eff5cf936df5ace7da9cc53faa609", 349.658673, "0xd4e96922b5122087cf414b400a1dc491f0f56a48"),
    ("C57861487", 57861487, "0x0ca10126f6c94cbd9cf0a48cc9516ae5e3dec5aa68303e6d988ee37c5149bf0d", "0xb0e08793964449a4c1a470cabc286f73baf21e7d", 41.869443, "0xdbc48be5816fd1132ceb4024332da51f59f63df0"),
]

mp = {}
out = []
for name, C, mkid, user, repaid, caller in cases:
    if mkid not in mp:
        mp[mkid] = params(mkid)
    p = mp[mkid]
    ld = liq_data(p, user)
    res = {"case": name, "C": C, "market": mkid[:10], "lltv": p["lltv"]/1e18, "repaid_usdc": repaid, "caller": caller[:10]}
    for lag, tag in [(1, hex(C-1)), (16, hex(C-16)), (160, hex(C-160))]:
        try:
            r = call(MORPHO, ld, tag)
            res[f"liq@C-{lag}"] = "OK" if r and r != "0x" else "OK-empty"
        except Exception as e:
            s = str(e)
            if "position is healthy" in s:
                res[f"liq@C-{lag}"] = "healthy"
            else:
                res[f"liq@C-{lag}"] = "revert:" + s[s.find("revert"):][:40] if "revert" in s else s[-60:]
    out.append(res)
    print(json.dumps(res))
    sys.stdout.flush()
