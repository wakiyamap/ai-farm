#!/usr/bin/env python3
import subprocess, json, sys
src = open('/srv/farm/ws/scratch/t170_probe.py').read().split('cases = [')[0]
ns = {}; exec(src, ns)
rpc, params, call, pos = ns['rpc'], ns['params'], ns['call'], ns['pos']

def oracle_price(o, tag):
    return int(call(o, "0xa035b1fe", tag), 16)

def market_struct(mk, tag):
    r = call("0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb", "0x5c60e39a" + mk[2:], tag)
    w = [int(r[2+i*64:2+(i+1)*64], 16) for i in range(6)]
    return w  # tSA,tSS,tBA,tBS,lastUpdate,fee

def receipt(h):
    return rpc("eth_getTransactionReceipt", [h])

cases = [
    (58300657, "0xdc64dd8916b05c56fd82d33497e182636886b889010f9ec5ac887cb9a829e292", "0x1a3e69d0109bb1be42b80e11034bb6ee98fc466721f26845dc83b2aa8d979137", "0xe7be437cf1a842a9bb8fa1e6f1bc980d91ce583e", 10.921242, "0x715a3219fe626e24cd7325ac1d06008ab0ebbd47", "0x715a3219"),
    (58292957, "0x6a585d7d856096a8260e9e5f9175a42ea86fe48a8b07597d6f73a55ff1c9dd34", "0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836", "0xab96157243d61ccd386c0e3108b3b22407aed83e", 0.740765, "0xe8711b02ee2d779c736fea98c042aeb3b390c398", "0xe8711b02"),
    (58192028, "0x329d49d2fe21f7bd6bc9c3fd6452ee14725ac46a397787426b2f8ec17eec4812", "0x1a3e69d0109bb1be42b80e11034bb6ee98fc466721f26845dc83b2aa8d979137", "0x3aada47cff218d478a4064fd848265ce4461b4e5", 0.196456, "0x844124693a429cb9ed04472a23d6aebfd1395dfe", "0x84412469"),
    (58015037, "0x0102c183c34f82b36e9db198c7f2090505279ce5f1a261ae7fc7d5c01121e6a8", "0xdaa04f6819210b11fe4e3b65300c725c32e55755e3598671559b9ae3bac453d7", "0xa2451e7404b3e1811dd06649dfd8f34d1c579be0", 10481.470436, "0xd4e96922b5122087cf414b400a1dc491f0f56a48", "0xd4e96922"),
    (57997287, "0x4c0799b647ec1effb919850abcaa313361e7f52f058abad27d4ddb20ac64b5fd", "0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda", "0x1c8d5cf2649eff5cf936df5ace7da9cc53faa609", 349.658673, "0xd4e96922b5122087cf414b400a1dc491f0f56a48", "0xd4e96922"),
    (57861487, "0xb3e775e15317b4ffc5c25f5928420642a98675773c00a4e0cf70eb86d1e137cd", "0x0ca10126f6c94cbd9cf0a48cc9516ae5e3dec5aa68303e6d988ee37c5149bf0d", "0xb0e08793964449a4c1a470cabc286f73baf21e7d", 41.869443, "0xdbc48be5816fd1132ceb4024332da51f59f63df0", "0xdbc48be5"),
]
mp = {}
for C, tx, mk, user, repaid, caller, tag_a in cases:
    if mk not in mp: mp[mk] = params(mk)
    p = mp[mk]
    row = {"C": C, "caller": tag_a, "repaid": repaid}
    try:
        for lag in (1, 16, 160):
            tag = hex(C - lag)
            px = oracle_price(p["oracle"], tag)
            ms = market_struct(mk, tag)
            po = pos(mk, user, tag)
            borrow_sh, coll = po[1], po[2]
            debt = borrow_sh * ms[2] / ms[3] if borrow_sh and ms[3] else 0
            maxdebt = coll * px / 1e36 * p["lltv"] / 1e18
            hf = (maxdebt / debt) if debt else None
            row[f"hf@C-{lag}"] = round(hf, 5) if hf else "no-debt"
            if hf is None or hf >= 1.0:  # healthy here -> window start is later; stop walking
                break
    except Exception as e:
        row["err"] = str(e)[-80:]
    r = receipt(tx)
    row["gasUsed"] = int(r["gasUsed"], 16)
    row["effGasGwei"] = int(r["effectiveGasPrice"], 16) / 1e9
    row["status"] = r["status"]
    print(json.dumps(row)); sys.stdout.flush()
