import json
import subprocess

factory = "0x1f98431c8ad98523631ae4a59f267346ea31f984"
pairs = {
    "WETH/crvUSD": ("0x82af49447d8a07e3bd95bd0d56f35241523fbab1", "0x498bf2b1e120fed3ad3d42ea2165e9b73f99c1e5"),
    "WBTC/WETH": ("0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f", "0x82af49447d8a07e3bd95bd0d56f35241523fbab1"),
}
for label, (a, b) in pairs.items():
    for fee in (100, 500, 3000, 10000):
        calldata = subprocess.check_output(["/opt/foundry/bin/cast", "calldata", "getPool(address,address,uint24)", a, b, str(fee)], text=True).strip()
        out = subprocess.run(["python3", "tools/rpc.py", "arbitrum", "eth_call", json.dumps([{"to": factory, "data": calldata}, "0x1f409b29"])], capture_output=True, text=True)
        print(label, fee, out.stdout.strip(), out.stderr.strip())
