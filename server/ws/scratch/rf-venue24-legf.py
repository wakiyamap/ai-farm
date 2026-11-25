import json, subprocess, os
WS="/srv/farm/ws"
ENV=dict(os.environ, PATH="/opt/farm/bin:/opt/foundry/bin:"+os.environ.get("PATH",""))
def sh(*c):
    r=subprocess.run(c, capture_output=True, text=True, env=ENV)
    if r.returncode!=0 or "FAILED" in r.stdout: raise SystemExit("FAILED %s: %s"%(c[:3],r.stdout[-200:],r.stderr[-200:]))
    return r.stdout.strip()
import urllib.request
def rpc(method, params, soft=False):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request("http://127.0.0.1:9003",data=body,headers={"content-type":"application/json"})
    out=json.loads(urllib.request.urlopen(req,timeout=180).read())
    if "error" in out:
        if soft: return out["error"]
        raise SystemExit("RPC %s: %s"%(method,out["error"]))
    return out["result"]
def addr_word(a): return a[2:].lower().rjust(64,"0")
SWAPPER="0x6131b5fae19ea4f9d964eac0408e4408b66337b5"; WINNER="0xd98d34008d1bbb29013592c637f8e9fca4179fa0"
SELL="0x060505527c83e8bfeb9b4ff08248b82e688800f1"; BUY="0xf404e5f887dbd5508e16a1198fcdd5de1a4296b8"
USDC="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"; FOLIO="0x2cf4dafc17e163abd6770e1794e1ad10deb7d32e"
VAULT="0x8f10b468b06c6fd214b65f87778827f7d113f996"; FUNROUTER="0xA043FDc5A6E2E381e3532d5A97404b82fb7A0af8"
def bal(token, who): return int(rpc("eth_call",[{"to":token,"data":"0x70a08231"+addr_word(who)},"latest"]),16)
legf=open(WS+"/scratch/dtf92-swap2.txt").read().strip()
print("selector", legf[:10], "len chars", len(legf))
watch=[(t,n) for t,n in ((SELL,"SELL"),(BUY,"BUY"),(USDC,"USDC"))]
accts=[(WINNER,"WINNER"),(FOLIO,"FOLIO"),(VAULT,"VAULT"),(FUNROUTER,"FUNROUTER")]
def snap(tag):
    out={}
    for t,tn in watch:
        for a,an in accts:
            out[tn+"/"+an]=bal(t,a)
    print(tag, json.dumps({k:v for k,v in out.items()}))
    return out
b=snap("pre")
r=json.loads(sh("fork","send","ethereum",json.dumps({"from":WINNER,"to":SWAPPER,"data":legf,"gas":"0x989680","value":"0x0"})))
print("send status", r.get("status"), "gas", r.get("gasUsed"), "hash", r.get("transactionHash"))
a=snap("post")
for k in b: print(k, "Δ", a[k]-b[k])
