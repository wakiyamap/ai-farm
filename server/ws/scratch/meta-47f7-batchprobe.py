import json, os, sys, urllib.request, urllib.error
base = os.environ.get("RPC_RELAY_URL", "http://127.0.0.1:8545").rstrip("/")
url = f"{base}/ethereum?lane=research"
for n in (int(a) for a in sys.argv[1:]):
    body = json.dumps([{"jsonrpc": "2.0", "id": i, "method": "eth_blockNumber", "params": []} for i in range(n)]).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "X-Lane": "research"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            out = json.loads(r.read())
            print(n, "HTTP", r.status, "items", len(out) if isinstance(out, list) else type(out).__name__)
    except urllib.error.HTTPError as e:
        print(n, "HTTP", e.code, e.read()[:200])
    except Exception as e:  # noqa: BLE001
        print(n, "ERR", e)
