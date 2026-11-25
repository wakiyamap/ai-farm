import json
import subprocess

tokens = {
    "WETH": "0x82af49447d8a07e3bd95bd0d56f35241523fbab1",
    "crvUSD": "0x498bf2b1e120fed3ad3d42ea2165e9b73f99c1e5",
    "WBTC": "0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f",
}
pools = {
    "WETH/crvUSD/100": "0x152e3cc8a9ca64ab2abe514c50430e0403c6c317",
    "WETH/crvUSD/500": "0xddd624f589655282a379c5d18f3a164141eea3a1",
    "WETH/crvUSD/3000": "0x4b97925e14d000cffd0b290d880ef6c733fe7587",
    "WBTC/WETH/100": "0x03a3be7ab4aa263d42d63b6cc594f4fb3d3f3951",
    "WBTC/WETH/500": "0x2f5e87c9312fa29aed5c179e456625d79015299c",
    "WBTC/WETH/3000": "0x149e36e72726e0bcea5c59d40df2c43f60f5a22d",
    "WBTC/WETH/10000": "0x99dfc0126ed31e0169fc32db6b89adf9fee9a77e",
}
for label, pool in pools.items():
    a, b = label.split("/")[:2]
    for token in (a, b):
        calldata = subprocess.check_output(["/opt/foundry/bin/cast", "calldata", "balanceOf(address)", pool], text=True).strip()
        out = subprocess.check_output(["python3", "tools/rpc.py", "arbitrum", "eth_call", json.dumps([{"to": tokens[token], "data": calldata}, "0x1f409b29"])], text=True)
        balance = int(json.loads(out)["result"], 16)
        decimals = 8 if token == "WBTC" else 18
        print(label, token, balance / (10**decimals))
