import re, sys
s = open(sys.argv[1], encoding='utf-8', errors='replace').read().replace('\\"', '"')
for m in re.finditer(r'"value":"' + re.escape(sys.argv[2]) + r'"', s):
    seg = s[m.end():m.end() + 3000]
    rows = re.findall(r'"children":"([A-Za-z0-9 ]{3,40})"\}\][^0]{0,200}?(0x[0-9a-fA-F]{40})', seg)
    print(rows[:6])
