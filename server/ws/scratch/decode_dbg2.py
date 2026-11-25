import json, urllib.request, time
exec(open("scratch/decode_omnivault_f08ee7c2.py").read().split("def get")[0])
h=call(0)
d=h[2:]
print("len d",len(d))
print("word0",repr(d[0:64]))
print("word1",repr(d[32:96]))
name_off=int(d[32:96],16)
print("name_off",name_off)
print("slice at name_off",repr(d[name_off:name_off+64]))
