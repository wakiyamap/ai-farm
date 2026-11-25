import urllib.request, json, sys
sels=sys.argv[1:]
for s in sels:
    try:
        req=urllib.request.Request(f'https://www.4byte.directory/api/v1/signatures/?hex_signature=0x{s}', headers={'User-Agent':'research'})
        d=json.load(urllib.request.urlopen(req, timeout=8))
        names=[r['text_signature'] for r in d.get('results',[])]
        print(s, '=>', '; '.join(names))
    except Exception as e:
        print(s, '=> ERR', str(e)[:60])
