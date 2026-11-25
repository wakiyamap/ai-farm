import subprocess, json
hashes=['0xbd1aa39b2e816f52db530ce2ce534e4cd3e1b24995ed6495dbc03f08b61e7c03','0x81c61ba909b59a84fc8a3683dfc807be5420b25375b7fa7a1ead667889add8c1','0x1dd189a3df4b65b440b917abf7c132e3f53ee92224de62a0223bd532ea9b3afa','0x0bf93e2cf7ace7155ec4efc5ccfbec27582b58216c0052aa14a5594493279d32','0x79d793f7f697cc1b6bdb2884f831fbddd0b63ec108e17b965cc2c1f1eeced5ed','0xbf15e963c0a30e8cc6b77f74782167047915ba33bbd42fa3ee6f89d96313fc5d','0x7fbd1cac550fc49152a47b1b8d3418ddafa199b73fc93cd6bb68ce04dc3ebbd5','0xc0c576c9fbc678aa982d5b30a46e85ae7a03bda5caeb40cabb4fd055ad7663d7','0x6d1173af4c23225e138f073fc5e440dd34a927d9ba166ed3bbe48e8dd85eddde']
tot=0
for h in hashes:
    p=subprocess.run(['python3','tools/rpc.py','arbitrum','eth_getTransactionReceipt',json.dumps([h]),'--lane','research'],capture_output=True,text=True)
    r=json.loads(p.stdout)['result']
    gu=int(r['gasUsed'],16); gp=int(r['effectiveGasPrice'],16)
    eth=gu*gp/1e18; tot+=eth
    print(h[:12], 'gasUsed',gu,'gwei',round(gp/1e9,4),'eth',round(eth,7))
print('sum eth',round(tot,7),'mean',round(tot/len(hashes),7))
