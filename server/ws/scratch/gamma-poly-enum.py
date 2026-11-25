import json, subprocess

REGS = {
 "uniswap":  ("0x0Ac4C7b794f3D7e7bF1093A4f179bA792CF15055", 61),
 "sushi":    ("0x97686103B3E7238Ca6c2C439146B30adBd84a593", 17),
 "quick":    ("0xAeC731F69Fa39aD84c7749E913e3bC227427Adfd", 143),
 "retro":    ("0xcAC19d43C9558753d7535978A370055614Ce832E", 81),
 "ascent":   ("0x7b9c2f68f16c3618bb45616fb98d83f94fd7062e", 1),
}
MC = "0xcA11bde05977b3631167028862bE2a173976CA11"
REG_SEL = "5893253c"

def abi_encode_calls(calls):
    # aggregate3((address,bool,bytes)[]) : dynamic array of tuples
    n = len(calls)
    # head: offset(32) + array len + per-item: 3 heads (offsets to tuple contents)
    # simpler: encode as function call with one dynamic array param
    # layout: sel + off(=0x20) + n + n*3 words(heads pointing to tuple data) ... 
    # tuple (address,bool,bytes) is dynamic (bytes) -> each item has head offset to its data
    # compute sizes
    body = b""
    heads = []
    bod = []
    for (addr, ok, calldata) in calls:
        data = bytes.fromhex(addr[2:].rjust(64,'0')) + (b'\xff'*31 if ok else b'\x00'*31)
        if ok is None: data = (b'\xff'*31 if False else b'\x00'*31)
        cl = bytes.fromhex(calldata[2:])
        d = b'\x00'*12 + bytes.fromhex(addr[2:])
        d += b'\x01' if ok else b'\x00'
        d += d[0:0]  # noop
        itembody = d  # 64 bytes for addr+bool... wait bool is full word
        itembody = (b'\x00'*12 + bytes.fromhex(addr[2:]) ) + (b'\x00'*31 + b'\x01' if ok else b'\x00'*32)
        itembody += b'\x00'*32*0
        # bytes field offset (32), then length + data padded
        blen = len(cl)
        pad = (32 - blen % 32) % 32
        itembody2 = itembody + b'\x00'*32*0
        # item head is offset into item tuple data; tuple data = word(addr) word(bool) word(bytesOffset=0x60) then bytes...
        tup = (b'\x00'*12+bytes.fromhex(addr[2:])) + ((b'\x00'*31+b'\x01') if ok else b'\x00'*32) + b'\x00'*32 + b'\x20' + b'\x00'*32 + b'\x60'
        # hmm this is getting wrong; use manual known layout:
        # tuple (dynamic) data: addr(32) bool(32) bytesOffset(=0x60)(32) len(32) data...
        tup = (b'\x00'*12+bytes.fromhex(addr[2:])) + ((b'\x00'*31+b'\x01') if ok else b'\x00'*32) + (32*3).to_bytes(32,'big') + blen.to_bytes(32,'big') + cl + b'\x00'*pad
        bod.append(tup)
    # heads region size = n * 32 (offsets to tuple data)
    headsize = 32*n
    offs = 0
    headsb = b""
    for t in bod:
        headsb += (headsize + offs).to_bytes(32,'big')
        offs += len(t)
    arr = n.to_bytes(32,'big') + headsb + b"".join(bod)
    data = "0x0f2819d" + "0"  # aggregate3 selector computed below
    return data, arr

# aggregate3 selector:
import hashlib
def sel(sig):
    # keccak
    import sha3 if False else None
