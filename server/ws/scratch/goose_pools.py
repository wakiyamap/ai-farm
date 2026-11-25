import subprocess, json
MC="0xe70E9185F5ea7Ba3C5d63705784D8563017f2E57"
def call(to,data):
    r=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","bsc","eth_call",json.dumps([{"to":to,"data":data},"latest"])],capture_output=True,text=True)
    try: return json.loads(r.stdout)["result"]
    except: return None
def word(h,i): return int(h[2+64*i:2+64*(i+1)],16)
print("pid lpToken allocPoint lastRewardBlock accEggPerShare depositFeeBP")
for pid in range(26):
    d="0x1526fe27"+hex(pid)[2:].rjust(64,"0")
    h=call(MC,d)
    if not h or h=="0x": print(pid,"REVERT"); continue
    lp=hex(word(h,0))[-40:]
    print(pid, "0x"+lp, word(h,1), word(h,2), word(h,3), word(h,4))
