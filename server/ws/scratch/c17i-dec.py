import re
line=open('scratch/c17i-swap-in.txt').read()
m=re.search(r'0xd0679d34([0-9a-fA-F]+)', line)
h=m.group(1)
# decode: paths array of (from,to,fee,prev)
import subprocess
def words(h):
    return [h[i:i+64] for i in range(0,len(h),64)]
w=words(h)
# dynamic array: w[0]=pointer 0x20; count at 0x40
print('count', int(w[2],16))
base=3
for j in range(int(w[2],16)):
    off=int(w[base+j*5],16)//64 if int(w[base+j*5],16)%64==0 else None
print(h[64*3:64*4+256])
