import sys
h=sys.stdin.read().strip()
if not h or h=='null': print('EMPTY'); sys.exit()
b=bytes.fromhex(h[2:] if h.startswith('0x') else h)
if len(b)>=64:
    off=int.from_bytes(b[0:32],'big'); ln=int.from_bytes(b[32:64],'big')
    if off==32 and ln<len(b): print('str:', b[64:64+ln].decode(errors='replace'))
    else: print('word:', hex(int.from_bytes(b[:32],'big')) if len(b)==32 else 'len%d'%len(b), b[:64].hex())
print('full:', h[:200])
