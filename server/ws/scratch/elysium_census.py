import json, subprocess, collections, sys
RPC = ["python3", "/srv/farm/ws/tools/rpc.py", "elysium", "eth_getBlockByNumber"]
HEAD = 0x6774f3
def get(num):
    out = subprocess.run(RPC + [json.dumps([hex(num), True]), "--lane", "research"],
                         capture_output=True, text=True)
    try:
        r = json.loads(out.stdout)
        return r.get("result")
    except Exception:
        return None
# spread 40 samples over last ~24h (assume ~150ms/block => 576k blocks; use measured span)
STEP = 14000
froms = collections.Counter(); tos = collections.Counter(); sel = collections.Counter()
span_t = []
cnt_blocks = 0; cnt_txs = 0
for i in range(40):
    n = HEAD - i*STEP
    b = get(n)
    if not b: print(f"miss at {n}", file=sys.stderr); continue
    cnt_blocks += 1
    txs = b.get("transactions", [])
    cnt_txs += len(txs)
    ts = int(b["timestamp"], 16)
    if b["number"].startswith("0x"):
        pass
    span_t.append((int(b["number"],16), ts))
    for t in txs:
        froms[t["from"].lower()] += 1
        if t.get("to"): tos[t["to"].lower()] += 1
        d = t.get("input","0x")
        if len(d) >= 10: sel[d[:10].lower()] += 1
if len(span_t) >= 2:
    bspan = span_t[0][0]-span_t[-1][0]; tspan = span_t[0][1]-span_t[-1][1]
    print(f"blocks={cnt_blocks} txs={cnt_txs} block_span={bspan} time_span={tspan}s avg_block={tspan/max(bspan,1)*1000:.0f}ms")
else:
    print(f"blocks={cnt_blocks} txs={cnt_txs}")
print("TOP-FROM:", froms.most_common(15))
print("TOP-TO:", tos.most_common(15))
print("TOP-SELECTOR:", sel.most_common(15))
