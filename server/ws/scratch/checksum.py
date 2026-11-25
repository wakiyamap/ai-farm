import hashlib
def to_checksum(a):
    a=a.lower(); d=hashlib.sha3_256(a.encode()).hexdigest()
    return "0x"+"".join(ch.upper() if int(d[i],16)>=8 else ch for i,ch in enumerate(a[2:]))
