import json, subprocess, sys
def rpc(method, params):
    out = subprocess.run(['python3','tools/rpc.py','ethereum',method,json.dumps(params)],capture_output=True,text=True).stdout
    r = json.loads(out)
    if 'error' in r: raise SystemExit(f'ERROR {method}: {r["error"]}')
    return r['result']
head = int(rpc('eth_getBlockByNumber',['latest',False])['number'],16)
hts = int(rpc('eth_getBlockByNumber',['latest',False])['timestamp'],16)
print('head', head, hex(hts), __import__('datetime').datetime.utcfromtimestamp(hts).isoformat()+'Z')
# find block at hts-7d by binary search
lo, hi = 0, head
target = hts - 7*86400
while lo < hi:
    mid = (lo+hi)//2
    ts = int(rpc('eth_getBlockByNumber',[hex(mid),False])['timestamp'],16)
    if ts < target: lo = mid+1
    else: hi = mid
b = rpc('eth_getBlockByNumber',[hex(lo),False])
print('7d-ago block', int(b['number'],16), int(b['timestamp'],16), __import__('datetime').datetime.utcfromtimestamp(int(b['timestamp'],16)).isoformat()+'Z')
for a in ['0xb1cFF81b9305166ff1EFc49A129ad2AfCd7BCf19','0x9cCbb2F03184720Eef5f8fA768425AF06604Daf4','0x3DB39B538Db1123389c77F888a213F1A6dd22EF3','0x1456688345527bE1f37E9e627DA0837D6f08C925','0x1a5Ff58BC3246Eb233fEA20D32b79B5F01eC650c']:
    c = rpc('eth_getCode',[a,'latest'])
    print(a, 'codelen', (len(c)-2)//2)
