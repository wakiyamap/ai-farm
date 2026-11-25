import json, subprocess, sys
pid = int(sys.argv[1]); depth = int(sys.argv[2])
tx = {"from": "0x000000000000000000000000000000000000dEaD", "to": "0xF403C135812408BFbE8713b5A23a04b3D48AAE31", "data": "0xcc956f3f" + pid.to_bytes(32, "big").hex(), "gas": "0x1c9c380"}
r = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", "ethereum", "debug_traceCall", json.dumps([tx, "latest", {"tracer": "callTracer", "tracerConfig": {"withLog": True}}]), "--lane", "research"], capture_output=True, text=True)
res = json.loads(r.stdout)["result"]
def show(c, d):
    if d > depth: return
    print("  " * d + c["type"], c["from"][:10], "->", c["to"], c["input"][:10], c.get("error", ""))
    for l in c.get("logs", []) or []:
        t = l["topics"]
        if t and t[0].startswith("0xddf252ad") and len(t) == 3:
            print("  " * d + "  LOG Transfer", l["address"][:10], "0x" + t[1][-40:][:8], "->", "0x" + t[2][-40:][:8], int(l["data"], 16) / 1e18)
    for s in c.get("calls", []) or []:
        show(s, d + 1)
show(res, 0)
