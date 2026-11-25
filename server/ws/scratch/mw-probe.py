import subprocess,json,re
URL=subprocess.run(['fork','url','base'],capture_output=True,text=True).stdout.strip()
C='0xfbb21d0380bee3312b33c4353c8936a0f13ef26c'
def probe(block,holder,label):
    subprocess.run(['fork','reset','base',str(block)],capture_output=True)
    r=subprocess.run(['cast','call',C,'getAccountLiquidity(address)',holder,'--rpc-url',URL],capture_output=True,text=True)
    h=re.sub(r'\D','',r.stdout)
    if len(h)%64: print(label,'len',len(h),h[:40]); return
    n=len(h)//64
    w=[int(h[i*64:(i+1)*64],16) for i in range(n)]
    em,liq,sf=w[0],w[1],w[2]
    print(f"{label}: block {block} liq_units={liq} sf_units={sf} liquidatable={liq==0 and sf>0}")
probe(54167142,'0x89e79e501db77e414adb81291c4abc21b00767a3','C1 cap-60')
probe(54167201,'0x89e79e501db77e414adb81291c4abc21b00767a3','C1 cap-1')
probe(54922326,'0x544784a56c889bcda2603c73ce1957f2b9133ec0','C3 cap-1')
probe(54922260,'0x544784a56c889bcda2603c73ce1957f2b9133ec0','C3 cap-67')
