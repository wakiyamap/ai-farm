import json, subprocess, sys

RPC = ["python3", "/srv/farm/ws/tools/rpc.py"]
EXEC = "0x5451c4b4ea335bfb71f75316594bb68d26d30917".lower()
TRANSFER = subprocess.run(["/opt/foundry/bin/cast","keccak","Transfer(address,address,uint256)"],capture_output=True,text=True).stdout.strip()

def rpc(method, params):
    r = subprocess.run(RPC + ["base", method, json.dumps(params), "--lane","research"], capture_output=True, text=True)
    return json.loads(r.stdout)["result"]

sym_cache = {}
def sym(tok):
    tok = tok.lower()
    if tok in sym_cache: return sym_cache[tok]
    if tok == "0x0000000000000000000000000000000000000000":
        sym_cache[tok] = "ETH"; return "ETH"
    try:
        d = rpc("eth_call", [{"to": tok, "data": "0x95d89b41"}, "latest"])
        h = d[2:]
        ln = int(h[64:128], 16)
        s = bytes.fromhex(h[128:128+ln*2]).decode(errors="replace")
    except Exception:
        s = "?"
    dec = rpc("eth_call", [{"to": tok, "data": "0x313ce567"}, "latest"])
    d = int(dec[2:], 16) if dec and dec != "0x" else None
    sym_cache[tok] = (s, d)
    return sym_cache[tok]

txs = sys.argv[1:]
for tx in txs:
    rec = rpc("eth_getTransactionReceipt", [tx])
    gu = int(rec["gasUsed"], 16); gp = int(rec["effectiveGasPrice"], 16)
    inflow = {}; outflow = {}
    liq = 0; morpho_events = 0
    for lg in rec["logs"]:
        t = lg["topics"][0].lower()
        if t == TRANSFER.lower():
            frm = "0x"+lg["topics"][1][-40:]; to = "0x"+lg["topics"][2][-40:]
            val = int(lg["data"], 16)
            tok = lg["address"].lower()
            if to == EXEC: inflow[tok] = inflow.get(tok,0)+val
            if frm == EXEC: outflow[tok] = outflow.get(tok,0)+val
    print(f"TX {tx[:16]} status={rec['status']} gas={gu} gasusd_wei={gu*gp}")
    for tok in set(list(inflow)+list(outflow)):
        s = sym(tok)
        dec = s[1] if isinstance(s, tuple) else 18
        name = s[0] if isinstance(s, tuple) else s
        i = inflow.get(tok,0); o = outflow.get(tok,0)
        print(f"   {name}({dec}) {tok[:10]} in={i/10**dec:.6f} out={o/10**dec:.6f} net={(i-o)/10**dec:+.6f}")
