import json, urllib.request, subprocess
IDS = {
 'whype77': '0xd7d38220652d19c87099c3b23de9a70a1893620a050c635d1a94bd947c9c59a8',
 'whype62': '0xd13b1bad542045a8dc729fa0ffcc4f538b9771592c2666e1f09667dcf85804fc',
 'whype86': '0xf1c3d487f417d00952e037e551fa01ec663092139d90e31fc901b3cd83f84ebb',
}
out = {}
for k, mid in IDS.items():
    users = []
    skip = 0
    while True:
        q = '{ marketPositions(first:1000, skip:%d, where:{chainId_in:[999], marketUniqueKey_in:["%s"], borrowShares_gte:"1"}){ items{ user{address} state{borrowShares collateral borrowAssetsUsd} } pageInfo{countTotal} } }' % (skip, mid)
        req = urllib.request.Request('https://blue-api.morpho.org/graphql', json.dumps({'query': q}).encode(), {'content-type': 'application/json', 'user-agent': 'curl/8'})
        try:
            d = json.load(urllib.request.urlopen(req, timeout=30))
        except urllib.error.HTTPError as e:
            d = json.loads(e.read())
        if 'data' not in d or not d['data']:
            print(k, str(d)[:400]); break
        items = d['data']['marketPositions']['items']
        users += [(i['user']['address'].lower(), i['state']['borrowShares'], i['state']['collateral'], i['state']['borrowAssetsUsd']) for i in items]
        print(k, skip, len(items), d['data']['marketPositions']['pageInfo'])
        if len(items) < 1000: break
        skip += 1000
    out[k] = users
json.dump(out, open('/srv/farm/ws/scratch/t228-positions.json', 'w'))
for k, v in out.items():
    print(k, len(v), 'top', sorted(v, key=lambda z: -(z[3] or 0))[:2])

# Multicall3 tryAggregate test on hyperevm: 2 calls (oracle price, morpho market)
def word(n): return format(n, '064x')
def aw(a): return a.lower().removeprefix('0x').zfill(64)
calls = [('0x194fff37872bac3531a41fa5c426090ff84f4f31', '0xa035b1fe'), ('0x68e37de8d93d3496ae143f2e900490f6280c57cd', '0x5c60e39a' + IDS['whype77'][2:])]
starts, acc = [], 32 * len(calls)
for _, data in calls:
    starts.append(acc); size = (len(data) - 2) // 2; acc += 96 + ((size + 31) // 32) * 32
enc = '0xbce38bd7' + word(0) + word(64) + word(len(calls)) + ''.join(word(x) for x in starts)
for t, data in calls:
    size = (len(data) - 2) // 2
    enc += aw(t) + word(64) + word(size) + data[2:].ljust(((size + 31) // 32) * 64, '0')
r = subprocess.run(['python3', '/srv/farm/ws/tools/rpc.py', 'hyperevm', 'eth_call', json.dumps([{'to': '0xca11bde05977b3631167028862be2a173976ca11', 'data': enc}, 'latest'])], capture_output=True, text=True)
print('multicall', r.stdout[:700], r.stderr[:300])
