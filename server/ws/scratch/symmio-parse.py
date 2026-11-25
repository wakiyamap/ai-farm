import json
d = bytes.fromhex(json.load(open('/srv/farm/ws/scratch/symmio-facetsfull.json'))['result'][2:])
def w(pos): return int.from_bytes(d[pos:pos+32],'big')
arr = w(0)            # offset to Facet[]
n = w(arr)            # array length
facets=[]
for i in range(n):
    off = w(arr+32+i*32)          # offset relative to position of this element's word
    p = arr+32+i*32 + off         # struct start
    addr = '0x'+d[p+12:p+32].hex()
    selrel = w(p+32)              # offset to selectors array, relative to struct start
    sp = p + selrel
    seln = w(sp)
    sels = ['0x'+d[sp+32+j*32:sp+64+j*32].hex() for j in range(seln)]
    facets.append({'facet':addr,'selectors':sels})
json.dump(facets, open('/srv/farm/ws/scratch/symmio-facets-parsed.json','w'))
for f in facets: print(f['facet'], len(f['selectors']))
print('total selectors:', sum(len(f['selectors']) for f in facets))
