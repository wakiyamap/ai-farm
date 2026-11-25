import json, urllib.request, os
URL = os.environ["RPC_RELAY_URL"]; LANE="research"
def rpc(method, params):
    req = urllib.request.Request(f"{URL}/hyperevm?lane={LANE}",
        data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
        headers={"content-type":"application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if "error" in r: return None
    return r["result"]
GV = rpc("eth_call",[{"to":"0xce59f8b65ad41c9dae4c07a0571a39824bd92cff","data":"0x8d86557d"},"latest"])  # placeholder
import sys
sel_getVersion = sys.argv[1]
addrs = ["0x90dabc988d2ae90c10e551f82129dc0bb0e11d29","0x233ff29b239abc1d7748605da9b205c3e008626e",
         "0xce59f8b65ad41c9dae4c07a0571a39824bd92cff","0x2745cbaa0aafc99b5285e5ade53fdf79c2a488f5",
         "0x6cd5661646289fb6e65ea5c032310fded797d0a2","0x278d858f05b94576c1e6f73285886876ff6ef8d2"]
callers = ["0x6d18f44e6b64e5e44bbaca1ca534a8290bd331b5","0xdf1bda875c9393a663ce69bf6a7fbaa73dfd053d",
           "0x33b12dd75f66933acd6438594d80cf91cacdc10b","0xaea0edc9ae3939f89e11d19d09d96a32ccefb5e2"]
for a in addrs:
    r = rpc("eth_call",[{"to":a,"data":sel_getVersion},"latest"])
    tag = ""
    if r and len(r)>4:
        try:
            hexs=r[2:]
            # try string decode: skip offset word
            body = bytes.fromhex(hexs[64:] if len(hexs)>=128 else hexs)
            tag = body.rstrip(b"\x00").decode("utf-8","replace").split("\x00")[0][:40]
        except Exception as e: tag=str(e)[:40]
    print(f"{a[:12]} getVersion(): {tag!r}")
for c in callers:
    code = rpc("eth_getCode",[c,"latest"])
    print(f"caller {c[:10]}: {'EOA (no code)' if not code or len(code)<=4 else 'contract '+str(len(code)//2-1)+' bytes'}")
