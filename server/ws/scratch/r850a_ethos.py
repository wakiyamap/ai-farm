import json,collections
f='/srv/farm/ws/bots/live/trial-ethos-redeem-optimism/logs/bot.jsonl'
c=collections.Counter(); rows=[]
for l in open(f):
    try: d=json.loads(l)
    except Exception: continue
    c[d.get('ev')]+=1
    if d.get('ev') in ('send_result','start','opportunity','send','skip'): rows.append(l.strip()[:900])
print(dict(c))
for r in rows[:3]+rows[-14:]: print(r)
