"""Flatten a callTracer result: depth, type, from, to, selector, value, error. usage: rc-trace-flat.py trace.json [maxlines]"""
import json, sys
j = json.load(open(sys.argv[1]))['result']
mx = int(sys.argv[2]) if len(sys.argv) > 2 else 200
out = []
def walk(c, d):
    out.append(f"{'  '*d}{c.get('type')} {c.get('from','')[:12]}->{c.get('to','')} {c.get('input','')[:74]} v={int(c.get('value','0x0'),16)} {c.get('error','')} out={c.get('output','')[:66]}")
    for s in c.get('calls', []) or []: walk(s, d + 1)
walk(j, 0)
print('\n'.join(out[:mx]))
