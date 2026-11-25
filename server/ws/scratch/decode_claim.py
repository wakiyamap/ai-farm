import json, subprocess, sys

markets = {
    "pid100": "c211b207e3324cf9c501d6f3fb77ffd77a3c82c9",
    "pid378": "4b4f0d16bfb4ddf24748a0e058d29552db985fd8",
    "pid379": "f5929a1c332ceab7918a4593a43db2b9ac20095f",
    "pid200": "266728b30c98b24de810e3325adc615486988cb2",
    "pid300": "2b0c826bb68fb3ff9d29db368af6210b302ab31b",
}

def call(to, data, frm):
    params = json.dumps([{"from": frm, "to": to, "data": data}, "latest"])
    out = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", "ethereum", "eth_call", params],
                         capture_output=True, text=True).stdout
    d = json.loads(out)
    return d.get("result"), d.get("error")

for name, m in markets.items():
    data = "0xef5cfb8c" + m.rjust(64, "0")
    r, err = call("0x64627901dAdb46eD7f275fD4FC87d086cfF1e6E3", data, "0x4D32C8Ff2fACC771eC7Efc70d6A8468bC30C26bF")
    if r is None:
        print(name, "ERR", err.get("message", "")[:80]); continue
    h = r[2:]
    if len(h) < 128:
        print(name, "short", h); continue
    off1 = int(h[0:64], 16) * 2
    off2 = int(h[64:128], 16) * 2
    ntok = int(h[off1:off1+64], 16)
    toks = ["0x" + h[off1+64+i*64+24:off1+128+i*64] for i in range(ntok)]
    namt = int(h[off2:off2+64], 16)
    amts = [int(h[off2+64+i*64:off2+128+i*64], 16) for i in range(namt)]
    print(name, "tokens", toks, "amts_raw", amts)
