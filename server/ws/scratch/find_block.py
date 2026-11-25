import subprocess, json, sys
def block(n):
    out = subprocess.run(["python3","tools/rpc.py","ethereum","eth_getBlockByNumber",
        json.dumps([hex(n), False])], capture_output=True, text=True, cwd="/srv/farm/ws")
    d = json.loads(out.stdout)
    return int(d["result"]["number"],16), int(d["result"]["timestamp"],16)
target = int(sys.argv[1])
lo, hi = 0, None
# get latest
latest_n, latest_ts = block("latest" if False else 26462672)
hi_n, hi_ts = latest_n, latest_ts
# estimate using avg ~2s? refine by probing
n = hi_n
while True:
    bn, ts = block(n)
    if ts <= target:
        # need older? no: ts <= target means we can go newer
        if bn + 1 <= hi_n:
            bn2, ts2 = block(bn+1)
            if ts2 > target:
                print(json.dumps({"from_block": bn+1, "to_block": hi_n, "from_ts": ts2, "to_ts": hi_ts})); break
            n = bn + 1
            continue
    # go older
    delta = ts - target
    n = max(0, n - max(1, int(delta/2.0)))
