for f in ['swap1','swap2']:
    data=open('scratch/dtf92-%s.txt'%f).read().strip()[10:].lower()
    print('==',f, len(data)//2,'bytes')
    for name,a in [('winner','d98d34008d1bbb29013592c637f8e9fca4179fa0'),('folio','2cf4dafc17e163abd6770e1794e1ad10deb7d32e'),('CSCO','060505527c83e8bfeb9b4ff08248b82e688800f1'),('MRVEL','f404e5f887dbd5508e16a1198fcdd5de1a4296b8'),('USDC','a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'),('vault','8f10b468b06c6fd214b65f87778827f7d113f996'),('swapper','6131b5fae19ea4f9d9964eac0408e4408b66337b')]:
        idx=[]; s=0
        while True:
            i=data.find(a,s)
            if i<0: break
            idx.append(i//2); s=i+2
        print(name, idx[:6])
