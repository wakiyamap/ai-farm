import json, collections, glob, os
days = ["2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13", "2026-11-14"]
for d in days:
    p = f"/srv/farm/ws/logs/sessions/{d}.jsonl"
    if not os.path.exists(p):
        continue
    c = collections.Counter()
    models = collections.Counter()
    for line in open(p):
        try:
            r = json.loads(line)
        except Exception:
            c["bad_json"] += 1
            continue
        if r.get("role") != "earner":
            continue
        c["sessions"] += 1
        c["out:" + str(r.get("outcome"))] += 1
        models[r.get("model")] += 1
    print(d, dict(sorted(c.items())), dict(models))
