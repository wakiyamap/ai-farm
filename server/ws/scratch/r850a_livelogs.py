import json,glob,collections,sys
for f in sorted(glob.glob('/srv/farm/ws/bots/live/trial-*/logs/bot.jsonl')):
    c=collections.Counter(); last=[]
    for l in open(f):
        if 'won' in l or 'lost' in l:
            try: d=json.loads(l)
            except Exception: continue
            r=d.get('result') or d.get('outcome') or d.get('event') or d.get('ev')
            c[str(r)]+=1; last.append(l.strip()[:600])
    if c:
        print('==',f.split('/')[6],dict(c))
        for l in last[-2:]: print('   ',l)
