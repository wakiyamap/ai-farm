import subprocess, json

RPC = ["python3", "/srv/farm/ws/tools/rpc.py", "arbitrum"]
def rpc(method, params):
    r = subprocess.run(RPC + [method, json.dumps(params)], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return ("ERR", (r.stdout + r.stderr).strip()[:200])
    try: return ("OK", json.loads(r.stdout).get("result"))
    except Exception: return ("ERR", r.stdout[:200])

addrs = ["0xDDD4f2A962BB9e8394C8E748d8Fd343cA870682C","0x2E6c54DCf1C14A2E36C3eD63bA690Bd3867c4961",
"0x01F90a7b1C749F4a0B7D115120dedA0e2343381d","0x4fE17dEFc597cC3bD6fBe16135d8Ac42D421907e",
"0x3ca8F12D7B376E9Ef338d1C432CA1b51DD319009","0x263b7B6499874E6E2758cD1aBe288Ea83b55da11",
"0x0792dcAa8e4ce37Cb5A32C5fbe2610872F9A29CA","0x54602E5cBa09e01EeE9B2050F1F4f0Dc902CeE34",
"0xF37Fe9396Bb95f7823A29090c939847f1817bC8a"]
for a in addrs:
    st, res = rpc("eth_getCode", [a, "latest"])
    print(a, "code_len:", (len(res)-2)//2 if st=="OK" and res else st, res[:20] if st!="OK" or not res else "")
# keeper() on active ones
for a in ["0x4fE17dEFc597cC3bD6fBe16135d8Ac42D421907e","0xF37Fe9396Bb95f7823A29090c939847f1817bC8a"]:
    st, res = rpc("eth_call", [{"to": a, "data": "0xaced1661"}, "latest"])
    print(a, "keeper():", st, res)
# vaultParams on active ones
for a in ["0x4fE17dEFc597cC3bD6fBe16135d8Ac42D421907e","0xF37Fe9396Bb95f7823A29090c939847f1817bC8a","0x3ca8F12D7B376E9Ef338d1C432CA1b51DD319009","0x54602E5cBa09e01EeE9B2050F1F4f0Dc902CeE34"]:
    st, res = rpc("eth_call", [{"to": a, "data": "0x9fcc2d75"}, "latest"])
    print(a, "vaultParams:", st, (res or "")[:400])
