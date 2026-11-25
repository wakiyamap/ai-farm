import json, os, urllib.request

URL = os.environ["RPC_RELAY_URL"] + "/base?lane=research"
TX = "0xeeadbc16c171fe11305f2743d09e8bef4a96dce10ad9c58924c9050a6b4bcd8c"


def call(cfg):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "debug_traceTransaction", "params": [TX, cfg]}).encode()
    req = urllib.request.Request(URL, data=body, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


for cfg in ({"tracer": "prestateTracer", "tracerConfig": {"diffMode": True}},
            {"tracer": "callTracer", "tracerConfig": {"onlyTopCall": True}}):
    out = call(cfg)
    res = out.get("result")
    if isinstance(res, dict):
        print(cfg["tracer"], "keys:", sorted(res.keys())[:8], "calls" in res)
    else:
        print(cfg["tracer"], "error:", out.get("error"))
