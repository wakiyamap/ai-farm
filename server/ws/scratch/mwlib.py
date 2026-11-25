import subprocess, json, sys

def rpc(chain, method, params):
    out = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py",chain,method,json.dumps(params),"--lane","research"],
                         capture_output=True, text=True).stdout
    return json.loads(out)["result"]

def call(chain, to, data):
    return rpc(chain, "eth_call", [{"to":to,"data":data},"latest"])

def dec_str(h):
    h=h[2:]
    n=int(h[64:128],16)*2
    return bytes.fromhex(h[64:64+n]).decode(errors="replace")

SEL = {
 "symbol()":"0x95d89b41",
 "decimals()":"0x313ce567",
 "underlying()":"0x6f307dc3",
 "comptroller()":"0x5fe3b567",
 "liquidationIncentiveMantissa()":"0x4ada90af",
 "exchangeRateStored()":"0x461b125a",
 "getAllMarkets()":"0xb0772d0b",
}
