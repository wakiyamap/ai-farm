import json, subprocess, sys
ADDR="0x302649ccdfc232ee49a28755c8a6c06e707b7d15".lower()
TRANSFER="0xddf252ad1be2c89b65b6917621c93819028d7abf521d99e020e4e0e2a17e4bbb"[:10]
def rpc(method, params):
    out = subprocess.run(["python3","tools/rpc.py","base",method,json.dumps(params),"--lane","research"],
                         capture_output=True, text=True).stdout
    d=json.loads(out)
    if "error" in d: print("ERR", d["error"]["message"][:120]); return None
    return d["result"]
for h in sys.argv[1:]:
    r = rpc("eth_getTransactionReceipt",[h])
    if not r: continue
    print("== tx", h[:16], "gasUsed", int(r["gasUsed"],16), "block", int(r["blockNumber"],16))
    for l in r["logs"]:
        t=l["topics"]
        if len(t)==3 and t[0].startswith("0xddf252ad"):
            frm="0x"+t[1][-40:]; to="0x"+t[2][-40:]; amt=int(l["data"],16)
            tag = " *** " if ADDR in (frm.lower(),to.lower()) else "     "
            print(f"{tag}{l['address'][:12]} {frm[:10]} -> {to[:10]} {amt}")
