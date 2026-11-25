import json, collections, glob, os, sys
sys.path.insert(0, "/srv/farm/ws/scratch")
STOPPED = open("/srv/farm/ws/scratch/meta-bad6-stopped.txt").read().split()
KEYS = ("send", "sent", "won", "lost", "tx", "receipt", "profit", "liquidat", "revert", "mined", "included")
for b in STOPPED:
    d = f"/srv/farm/ws/bots/archive/{b}"
    if not os.path.isdir(d):
        print(b, "NO ARCHIVE DIR"); continue
    c = collections.Counter()
    live_seen = False
    for f in glob.glob(d + "/logs/*.jsonl"):
        for l in open(f, errors="replace"):
            if not l.startswith("{"):
                continue
            try:
                j = json.loads(l)
            except Exception:
                continue
            if j.get("mode") == "live":
                live_seen = True
            ev = str(j.get("ev") or j.get("event") or j.get("type") or "")
            if any(k in ev.lower() for k in KEYS):
                c[ev] += 1
    print(b, "live_seen" if live_seen else "-", dict(c))
