import subprocess, json, sys
ADDR="0x0918242d33718b7cb3a1c6dd36fdfa9e9db37786"
USDC="0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
SEL="0x70a08231000000000000000000000000"+ADDR[2:]
def call(to,data,blk):
    p=subprocess.run(["python3","tools/rpc.py","base","eth_call",json.dumps([{"to":to,"data":data},blk])],capture_output=True,text=True)
    try: return int(json.loads(p.stdout)["result"],16)
    except Exception as e: return None
def sym(addr):
    r=call(addr,"0x95d89b41","latest")
    if r is None: return None
    h="%x"%r
    # decode ABI string
    s=bytes.fromhex(h).decode(errors="replace")
    return s
blocks=[60089062,60058155,60050396,60001574,59649321,60092656,59988193,59664326]
for b in blocks:
    pre=call(USDC,SEL,hex(b-1)); post=call(USDC,SEL,hex(b))
    print(b, pre, post, None if pre is None or post is None else (post-pre))
print("current USDC bal of contract:", call(USDC,SEL,"latest"))
for a in ["0xcbd06e5a2b0c65597161de254aa074e489deb510","0xa9d366007bcf1edcc6ccu82jjtvmmbn47b31wasb"]:
    pass
print("symbol cBd06e5a:", sym("0xcbd06e5a2b0c65597161de254aa074e489deb510"))
