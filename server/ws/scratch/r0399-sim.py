import json, subprocess, sys
# eth_call earmarkRewards(pid) from an arbitrary EOA; then trace CRV transfer to caller via debug_traceCall callTracer with logs
FROM = "0x000000000000000000000000000000000000dEaD"
for pid in [int(x) for x in sys.argv[1:]]:
    data = "0xcc956f3f" + pid.to_bytes(32, "big").hex()
    tx = {"from": FROM, "to": "0xF403C135812408BFbE8713b5A23a04b3D48AAE31", "data": data, "gas": "0x1c9c380"}
    r = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", "ethereum", "debug_traceCall", json.dumps([tx, "latest", {"tracer": "callTracer", "tracerConfig": {"withLog": True}}]), "--lane", "research"], capture_output=True, text=True)
    try:
        res = json.loads(r.stdout)["result"]
    except Exception:
        print(pid, "ERR", r.stdout[:300], r.stderr[:300]); continue
    got = 0
    def walk(c):
        global got
        for l in c.get("logs", []) or []:
            t = l.get("topics", [])
            if len(t) == 3 and t[0].startswith("0xddf252ad") and l["address"].lower() == "0xd533a949740bb3306d119cc777fa900ba034cd52" and t[2][-40:].lower() == FROM[2:].lower():
                got += int(l["data"], 16) / 1e18
        for s in c.get("calls", []) or []:
            walk(s)
    walk(res)
    print(pid, "error=", res.get("error"), res.get("revertReason"), "gasUsed", int(res.get("gasUsed", "0x0"), 16), "CRV to caller %.2f" % got)
