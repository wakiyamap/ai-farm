import json, urllib.request, os
def rpc(chain, method, params, lane="research"):
    URL = os.environ["RPC_RELAY_URL"] + f"/{chain}?lane={lane}"
    r = urllib.request.Request(URL, json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(), {"content-type":"application/json"})
    j = json.loads(urllib.request.urlopen(r, timeout=30).read())
    if "error" in j: return {"__error": j["error"]}
    return j["result"]
PROXY = "0x37693f7b7090442844c07f8545234F075FE0C238"
addr_cases = ["0x37693f7b7090442844c07f8545234F075FE0C238","0x37693f7b7090442844c07f8545234f075fe0c238"]
out = {}
for chain in ["ethereum","base","arbitrum"]:
    head = int(rpc(chain, "eth_blockNumber", []),16)
    hdr = rpc(chain, "eth_getBlockByNumber", ["latest", False])
    c1 = rpc(chain, "eth_getCode", ["0xc02aaa39b223fe8d0a0e5c4f27bad9de9c4bf8d8", "latest"]) if chain=="ethereum" else rpc(chain, "eth_getCode", ["0x4200000000000000000000000000000000000006","latest"], "live")
    codes = {c: len(rpc(chain,"eth_getCode",[c,"latest"] if chain=="ethereum" else [c, "latest"])) for c in addr_cases[:1]}
    out[chain] = {"head": head, "weth_code_len": len(c1), "proxy_code_len_cases": [len(rpc(chain,"eth_getCode",[c,"latest"])) for c in addr_cases]}
print(json.dumps(out, indent=1))
