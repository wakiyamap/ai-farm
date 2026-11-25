import subprocess, json, sys, time
RPC = ["python3", "/srv/farm/ws/tools/rpc.py", "bsc", "eth_getLogs"]
TOPIC = "0x820b7fd51bf79c54350bab98400651b3314ff6e79b33528821871d94a6669883"  # NativeFeeWithdrawn(address,address,uint256)
ADDRS = ["0x9f8c645f2d0b2159767bd6e0839de4be49e823de",  # sendUln302
         "0xb217266c3a98c8b2709ee26836c98cf12f6ccec1",  # receiveUln302
         "0x3ebd570ed38b1b3b4bc886999fcf507e9d584859"]  # executor
FROM, TO = 133284000, 134627683
logs = []
errs = 0
b = FROM
pages = 0
while b <= TO:
    e = min(b + 4999, TO)
    params = [{"fromBlock": hex(b), "toBlock": hex(e), "address": ADDRS, "topics": [TOPIC]}]
    r = subprocess.run(RPC + [json.dumps(params)], capture_output=True, text=True, timeout=120)
    pages += 1
    if r.returncode != 0:
        errs += 1
        if errs > 8:
            print("TOO MANY ERRORS", r.stderr[:200]); sys.exit(1)
        time.sleep(2)
        continue
    d = json.loads(r.stdout)
    if "error" in d:
        errs += 1; time.sleep(2); continue
    logs.extend(d["result"])
    b = e + 1
print(f"pages={pages} errs={errs} logs={len(logs)}")
byaddr = {}
for lg in logs:
    a = lg["address"].lower()
    byaddr.setdefault(a, []).append(lg)
for a, ls in byaddr.items():
    print(a, len(ls))
json.dump(logs, open("/tmp/lz_bsc_logs.json", "w"))
