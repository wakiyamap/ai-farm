import json, urllib.request, time
exec(open("scratch/decode_omnivault_f08ee7c2.py").read().split("out={}")[0])
for vid in range(0,12):
    h=call(vid)
    if not h: print(vid,"NO-DATA"); continue
    d=h[2:]
    try:
        t=get(d,0); name_off=get(d,t); name_len=get(d,name_off)
        print(vid,"len",len(d),"t",t,"name_off",name_off,"name_len",name_len)
    except Exception as e:
        print(vid,"ERR",repr(e)[:80],"len(d)",len(d),"first64",d[:64])
