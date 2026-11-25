import json, sys
def enc(calls):
    # calls: list of (to, data_hex_without_0x)
    n=len(calls); tail=""
    for to,d in calls:
        tail+=f"{int(to,16):064x}"+f"{0:064x}"+f"{len(d)//2+4:064x}"+f"{4*32+ len(d)//2:064x}"[0:0]+f"{4*32:064x}"+f"{len(d)//2:064x}"+d+"0"*((63-len(d)//2)%64) if False else ""
        tail+=f"{int(to,16):064x}"+f"{0:064x}"+f"{len(d)//2+4:064x}"+f"{4*32:064x}"+f"{len(d)//2:064x}"+d+"0"*((63-(len(d)//2))%64)
    offs=[32*n+432*i for i in range(n)]
    hdr="0x82ad56cb"+f"{32:064x}"+f"{n:064x}"+"".join(f"{o:064x}" for o in offs)
    return hdr+tail
