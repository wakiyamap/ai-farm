import json, subprocess, sys
h = sys.argv[1]; depth = int(sys.argv[2]) if len(sys.argv) > 2 else 3
r = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", "ethereum", "debug_traceTransaction", json.dumps([h, {"tracer": "callTracer"}]), "--lane", "research"], capture_output=True, text=True)
res = json.loads(r.stdout)["result"]
def show(c, d):
    if d > depth: return
    print("  " * d + c["type"], c["from"][:10], "->", c["to"], c["input"][:10], "val", int(c.get("value", "0x0"), 16), c.get("error", ""))
    for s in c.get("calls", []) or []:
        show(s, d + 1)
show(res, 0)
