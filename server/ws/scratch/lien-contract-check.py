import json
import subprocess

contracts = [
    ("aggregator1", "0xE446158503d0F5c70579FCCE774C00E8Db544559", "0x9960d742"),
    ("aggregator2", "0x5F3b6405dfcF8b21f8dEB4eb6DA44a89a652aCb0", "0x9960d742"),
    ("aggregator3", "0xCc96397Cb86f98759BdbbF31802b366E7251F350", "0x9960d742"),
    ("bondmaker", "0xDA6FC5625E617bB92F5359921D43321cEbC6BEf0", "0xac3fd886"),
    ("gdotc", "0x2f84206b5ED3Eb855C886414f3905115DD166614", "0x0b1a3554"),
    ("lien_token", "0xaB37e1358b639Fd877f015027Bb62d3ddAa7557E", "0xc48c7342"),
    ("reserve1", "0x54ea75daf8f0c71ef5ac918bd2eda4448e814925", "0x8da5cb5b"),
    ("reserve2", "0xca18201c57370df5684b7cbad9b1b886e03f198f", "0x8da5cb5b"),
    ("reserve3", "0x9f6ff467fd6ca8832d9e0eff95c34f4939e7becb", "0x8da5cb5b"),
]


def rpc(method, params):
    p = subprocess.run(
        ["python3", "/srv/farm/ws/tools/rpc.py", "ethereum", method, json.dumps(params)],
        capture_output=True,
        text=True,
    )
    o = json.loads(p.stdout)
    return o.get("result", o.get("error"))


for name, address, selector in contracts:
    code = rpc("eth_getCode", [address, "latest"])
    response = rpc("eth_call", [{"to": address, "data": selector}, "latest"])
    print(json.dumps({"name": name, "address": address, "code_bytes": (len(code) - 2) // 2 if isinstance(code, str) else None, "getter": response}))
