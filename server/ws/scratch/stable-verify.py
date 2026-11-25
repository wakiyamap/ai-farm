import json, urllib.request, os
URL = os.environ["RPC_RELAY_URL"] + "/ethereum?lane=research"
def rpc(method, params):
    r = urllib.request.Request(URL, json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(), {"content-type":"application/json"})
    j = json.loads(urllib.request.urlopen(r, timeout=30).read())
    if "error" in j: return {"__error": j["error"]}
    return j["result"]
def call(to, data):
    return rpc("eth_call", [{"to": to, "data": data}, "latest"])
PROXY = "0x37693f7b7090442844c07f8545234F075FE0C238"
WETH = "0x82aF379146118cd817459B4dA77a8fF61376709b"
out = {}
head = int(rpc("eth_blockNumber", []), 16)
out["head"] = head
code = rpc("eth_getCode", [PROXY, "latest"])
out["proxy_code_len"] = (len(code)-2)//2
impl = rpc("eth_getCode", ["0x26908a97213e40e85147566488f29704c6351e96", "latest"])
out["impl_code_len"] = (len(impl)-2)//2
# look for the claimed Liquidation topic0 in recent proxy logs
T0 = "0x19309d6902b0cbb6ad077ddca5986f53c7216d2ff0a8ae11cc00f8a64231570d"
lo, hi = head-11000, head
logs = rpc("eth_getLogs", [{"address": PROXY, "topics": [T0], "fromBlock": hex(lo), "toBlock": hex(hi)}])
out["liquidation_logs_11000b"] = len(logs) if isinstance(logs, list) else logs
out["last_liq_logs"] = [ {"block": int(l["blockNumber"],16), "tx": l["transactionHash"]} for l in logs[-3:] ] if isinstance(logs, list) else None
# getters
for name, sel in [("DEBT_TOKEN","0x854db43c5d8184ec481029e2497713e7e81e361b9d98c2746789d356ead0cb36"),
                  ("RESERVE_TOKEN","0x9ed7a6c48ea9b7479e891229736560f210344113abadb622275e1f3fe62eb1cc"),
                  ("PRICE_ORACLE","0x0a19399a2b5472094f23caf890167f9401343e3ff44dba17c885f1a85fecafea"),
                  ("POOL","0x7535d2464a63b7bf37797750fe9eb25b3c63e7e477ce5cc56ed399dce78e0d04"),
                  ("POOL_ADDRESS","0xfe94df88339cc68e6283c1e0c2433691f6a5165678f680ce1b8fd91d80e46d31")]:
    out[name] = call(PROXY, sel)
# getPool(WETH)
out["getPool_WETH"] = call(PROXY, "0xbbe4f6dbf8c8209d6c25e0e729a52c31115b338051ea0d406c4713a0af83ba23" + WETH[2:].lower().rjust(64,"0"))
# WETH liquidityData -> availableBalance (field 0)
ld = call(WETH, "0x2e029228af6f02b568983f46809f5678fd4768991935550168effcacad467dae")
out["weth_liquidityData"] = ld
json.dump(out, open("scratch/stable-verify.json","w"), indent=1)
print(json.dumps(out, indent=1)[:2000])
