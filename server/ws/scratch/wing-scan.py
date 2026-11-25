import json, subprocess, sys

RPC = ["python3", "/srv/farm/ws/tools/rpc.py", "bsc", "eth_getLogs"]
addrs = json.load(open("/srv/farm/ws/scratch/wing-addrs.json"))

def call(params):
    r = subprocess.run(RPC + [json.dumps(params)], capture_output=True, text=True, timeout=90)
    try:
        d = json.loads(r.stdout)
    except Exception:
        return None, r.stdout[:200] + r.stderr[:200]
    if "error" in d:
        return None, str(d["error"])[:300]
    return d["result"], None

# head
r = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", "bsc", "eth_getBlockByNumber", '["latest",false]'], capture_output=True, text=True)
blk = json.loads(r.stdout)["result"]
head = int(blk["number"], 16)
head_ts = int(blk["timestamp"], 16)
start = head - 1209600 + 1  # 7d at 0.5s blocks
print(f"head={head} ts={head_ts} start={start} (ts_7d_ago~{head_ts-604800})", flush=True)

total = 0
per_addr = {}
by_type = {}
errors = 0
done = 0
ranges = 0
for f in range(start, head + 1, 5000):
    t = min(f + 4999, head)
    res, err = call([{"address": addrs, "fromBlock": hex(f), "toBlock": hex(t)}])
    ranges += 1
    if res is None:
        errors += 1
        print("ERR", hex(f), err, flush=True)
        continue
    done += 1
    total += len(res)
    for lg in res:
        a = lg["address"].lower()
        per_addr[a] = per_addr.get(a, 0) + 1
        topic = lg["topics"][0].lower() if lg["topics"] else "none"
        by_type[(a, topic)] = by_type.get((a, topic), 0) + 1
    if len(res) >= 10000:
        print("TRUNCATION RISK at", hex(f), flush=True)

print(f"ranges={ranges} ok={done} errors={errors} wing_logs_7d={total}", flush=True)
print("per_addr:", json.dumps(per_addr, indent=1)[:1200], flush=True)
print("event_types:", json.dumps({f"{k[0][:10]}..{k[1][:10]}": v for k, v in sorted(by_type.items(), key=lambda x: -x[1])[:25]}, indent=1), flush=True)

# control: WBNB Transfer, same shape, newest range
ctrl = call([{"address": ["0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"],
              "topics": [["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"]],
              "fromBlock": hex(head - 4999), "toBlock": hex(head)}])
n = len(ctrl[0]) if ctrl[0] is not None else f"ERR {ctrl[1]}"
print(f"control WBNB Transfer newest 5000 blocks: {n}", flush=True)
# control 2: mid-range
mid = (start + head) // 2
ctrl2 = call([{"address": ["0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"],
               "topics": [["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"]],
               "fromBlock": hex(mid), "toBlock": hex(mid + 4999)}])
n2 = len(ctrl2[0]) if ctrl2[0] is not None else f"ERR {ctrl2[1]}"
print(f"control WBNB Transfer mid 5000 blocks: {n2}", flush=True)
