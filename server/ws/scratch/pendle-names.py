import json, os, urllib.request
RELAY = os.environ["RPC_RELAY_URL"]
def rpc(method, params, lane="research"):
    req = urllib.request.Request(f"{RELAY}/ethereum?lane={lane}",
        data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
        headers={"content-type":"application/json"})
    with urllib.request.urlopen(req, timeout=60) as r: d = json.loads(r.read())
    if "error" in d: raise RuntimeError(str(d["error"])[:120])
    return d["result"]
def call(to, data, blk):
    return rpc("eth_call",[{"from":"0x0000000000000000000000000000000000000000","to":to,"data":data}, blk])
def dec_str(hexret):
    h=hexret[2:]
    # offset 0x20 then length word
    length=int(h[64:128],16)
    raw=bytes.fromhex(h[128:128+length*2])
    return raw.decode("utf-8","replace")
SEL={"name()":"0x06fdde03","symbol()":"0x95d89b41","totalSupply()":"0x18160ddd"}
logs=json.load(open("scratch/pendle-create-logs.json"))
seen=set()
for lg in logs:
    a="0x"+lg["topics"][1][-40:]; b="0x"+lg["topics"][2][-40:]; blk=hex(int(lg["blockNumber"],16))
    for label,x in (("PT?",b),("MK?",a)):
        if x in seen: continue
        seen.add(x)
        try:
            nm=dec_str(call(x,SEL["name()"],blk))
            sym=dec_str(call(x,SEL["symbol()"],blk))
            ts=int(call(x,SEL["totalSupply()"],blk),16)
            print(f"{blk} {label} {x} name={nm!r} symbol={sym!r} totalSupply={ts}")
        except Exception as e:
            print(f"{blk} {label} {x} name REVERT {str(e)[:100]}")
