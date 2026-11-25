"""Trace why the second outbid reverts (runs on the fork state left by sf_fork_proof.py; no reset)."""
import json, subprocess, re, sys
CH = "base"
TOGA = "0xA87F76e99f6C8Ff8996d14f550ceF47f193D9A09"
USDCX = "0xD04383398dD2426297da660F9CCA3d439AF9ce1b"
S2 = "0x00000000000000000000000000000000000Fa502"
def sh(*a):
    r = subprocess.run(list(a), capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()
def cd(sig, *a):
    return sh("/opt/foundry/bin/cast", "calldata", sig, *[str(x) for x in a])
amt = int(float(sys.argv[1]) * 1e18)
ud = sys.argv[2] if len(sys.argv) > 2 else "0x"
print(sh("fork", "lease", CH, "5", "superfluid toga trace 56e8c1ce"))
try:
    out = sh("fork", "send", CH, json.dumps({"from": S2, "to": USDCX, "data": cd("send(address,uint256,bytes)", TOGA, amt, ud)}))
    m = re.search(r'"transactionHash":\s*"(0x[0-9a-f]{64})"', out)
    st = re.search(r'"status":\s*"(0x[01])"', out)
    print("status", st and st.group(1), "tx", m and m.group(1))
    if m:
        tr = sh("fork", "trace", CH, m.group(1))
        open("/srv/farm/ws/scratch/sf_fork_trace.out", "w").write(tr)
        try:
            j = json.loads(tr)
            def walk(c, d=0):
                if c.get("error") or d < 3:
                    print("  " * d, c.get("type"), c.get("to"), c.get("input", "")[:10], "gas", c.get("gasUsed"), "ERR" if c.get("error") else "", c.get("error", ""), c.get("revertReason", ""), c.get("output", "")[:140] if c.get("error") else "")
                for x in c.get("calls", []):
                    walk(x, d + 1)
            walk(j.get("result", j))
        except Exception as e:
            print("trace parse", e, tr[:1500])
finally:
    print(sh("fork", "release", CH))
