import json, re, sys, urllib.request
code = sys.argv[1]
sels = sorted(set(re.findall(r'63([0-9a-f]{8})14', code)))
print(len(sels), "selectors")
for s in sels:
    try:
        with urllib.request.urlopen(f"https://www.4byte.directory/api/v1/signatures/?hex_signature=0x{s}", timeout=15) as r:
            d = json.load(r)
        names = [x['text_signature'] for x in d.get('results', [])]
    except Exception as e:
        names = [f"ERR {e}"]
    print(s, names)
