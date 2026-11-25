import json, sys
def load(p):
    d = json.load(open(p))
    rows = d if isinstance(d, list) else (d.get("results") or d.get("rows") or d.get("per_query"))
    out = {}
    if isinstance(rows, list):
        for r in rows:
            out[r.get("q")] = r.get("rank")
    return out, list(d.keys()) if isinstance(d, dict) else None
a, ka = load(sys.argv[1])
b, kb = load(sys.argv[2])
print("keys", ka, kb, len(a), len(b))
for q in b:
    if q in a and a[q] != b[q]:
        print(a[q], "->", b[q], q)
