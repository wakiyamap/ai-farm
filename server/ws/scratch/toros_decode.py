import json, sys
d = json.load(open('scratch/toros_pools.json'))
h = d['result'][2:]
n = int(h[128:192], 16)
addrs = ['0x' + h[192 + i*64 + 24:192 + (i+1)*64] for i in range(n)]
print(n)
for a in addrs:
    print(a)
