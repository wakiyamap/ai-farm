import json
d = json.load(open('/srv/farm/ws/scratch/facets.json'))
res = d['result'][2:]
n = int(res[64:128], 16)
print('facets:', n, flush=True)
off = 0xC0  # after offset + length? no: head at 0x40 relative
# head starts at word index 2 (offset word then array length at word1)
# For Facet[] the head begins after length word: data starts at char 0xC0
for i in range(n):
    w0 = int(res[0xC0 + i*128 : 0xC0 + i*128 + 64], 16)
    w1 = int(res[0xC0 + i*128 + 64 : 0xC0 + i*128 + 128], 16)
    print('0x%040x' % w0, 'seloff_word', w1)
