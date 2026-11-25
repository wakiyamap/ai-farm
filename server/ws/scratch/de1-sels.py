import json, re, subprocess, sys
def code(addr):
    out = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','bsc','eth_getCode',f'["{addr}","latest"]'],capture_output=True,text=True).stdout
    return json.loads(out)['result']
for name,addr in [('routerimpl','0x86f2058ba5e1466260055d1f3dab38b15f98be09'),('loimpl','0x347f9bfa1157b64a5b05cc2a1ffba834f8c0cc57')]:
    c = code(addr)
    sels = sorted(set(re.findall(r'60e0601c8081[^0-9a-f]{0,10}?ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff|804c6a2115', c)))
    # standard: PUSH1 0e... find pattern "84843d52" preceded by PUSH4 selector: "63"+8hex followed by "8"
    sels = re.findall(r'63([0-9a-f]{8})8[0-9a-f]', c[200:2000]) if False else set()
    # generic: any PUSH4 followed by EQ after shr 0xe0
    sels = re.findall(r'7ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff8001c8080', c)
    print(name, len(c))
