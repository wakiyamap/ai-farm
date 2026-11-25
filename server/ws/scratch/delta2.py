import subprocess, json
ADDR="0x0918242d33718b7cb3a1c6dd36fdfa9e9db37786"
USDC="0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
SEL="0x70a08231000000000000000000000000"+ADDR[2:]
def call(to,data,blk):
    p=subprocess.run(["python3","tools/rpc.py","base","eth_call",json.dumps([{"to":to,"data":data},blk])],capture_output=True,text=True)
    try: return int(json.loads(p.stdout)["result"],16)
    except Exception: return None
blocks=[59649166,59955701,59985341,59986911,59987144,59987215,59987607,59988114,59988263,59988663,60059194]
tot=0
for b in blocks:
    pre=call(USDC,SEL,hex(b-1)); post=call(USDC,SEL,hex(b))
    d=None if pre is None or post is None else post-pre
    if d: tot+=d
    print(b, d)
print("sum_remaining_usdc", tot, "usd", round(tot/1e6,2))
