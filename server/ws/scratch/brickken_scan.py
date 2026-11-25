import json, subprocess, sys
esc = ["0x4e0b35c1f5216d0af258b540d36fe203760664e1","0xaf05ec70deac9cfd008a9746b3a3b3c81eeb082e","0xbc76a5b1d77e3176b8f43e8833af89764c55e5ac","0xd834f282bcbce9c51f2316c792433990adf5dfec","0x7499c9d4e6570ad72e966b4c169757b85aaa7c40","0x2111299173ea3cba797bfac071c0889beaa1ce0e","0x8995c7a3e1efae06794a9e4bf2443dec1eba7aaf","0x97d0ef13638808338c738976121fea386717ef1b","0xb05b88c3b909fd98e4012c1002a0636ccdc06fa0","0x9cb82ea0cf4c7db178f6adac6731931bdd0068e7","0x1e6c49f03172e48cabce41c0a5225ebf85347ede","0x6e882a824808754f733634a040d8f5f6bd1d8336","0x74a2b75afd84851550012680a3e9ffec5d838e33","0xe438ba23376c2f0e8226b5a367204a6181e830d3","0xf511017b674e2819bea96f0b9614efb698f4eb78","0x1c8e1b6b20f7dbca2e1502eca9ba912d9c8eb816","0x4833c8bd788ddd898244847266521bc828275069","0xfee2f82bbaf02d915257e338e9fb4a41ebaed139","0x1de6b774c0e018e5e9bca8e9ea268c80036c00aa","0xbea63fe91e090123e799f9225e0fe8b61bb8391e","0xc5bb3da113d4285d6d9f01cd7ffcabb9a3b79e6b","0xc8369adc2e8e6e10dec9215d0116cc4de347b8ce","0x558b3f6c73a811752de4813c2088a29a982befb2","0x8b45a6417837318ce0370501f130ea72937ca4e9","0x1ac9d700868ab7ac807ff1d16fed1f21d418406d","0x7497919346c0c4b89a7021e6c2c0ab3fc3815057","0xda790deeb5727d3063ed796a5683835b756eb854","0xd6e03d4bdd1ea53d49024da5e1a2c9591820c043","0x94f0b9e831231d29a82f13514a9c767401162015","0x06da71166c6de3497bfc86bbe41b749897a748fd","0x3685963d1b9af78c3d633d06919eef80576ad3cc","0xaa50d2f5b0825cb2c84a93a9e0db90cd7cdf2234","0x036f6b156a32dd318c5a4e4b81aee28fdca62f57","0x12ada8b0bd7cf0d786081ca0e043e319f534f4dc","0x09c41e6ce43ece9d80d97abd024b1282a8baeefc","0xa81f5b99bc1f1b1d89a4cadfbe41020e9a0f0eb5","0x3a4bef6549051c84a3466b0fc0776b3c935e49ae","0x67de58ffab05a3a0d9316d00c15ee3cd3687c834","0x6d450a3093920f72a170c91a3c99da4d0120ed3d","0xf4bf55cd32c7fd4a4ebd54bca9165b30bd83d461","0x605de99fb426c6c3385e39c61a187d73adbf75f3","0xee28be593a5ce2f5207b1db25c20567c43abb11a","0x97bf062938802e859c3639adf5da75bbe27a1e14","0xe9916af1d8b18c991832def532cf577950c5e2e7","0xd3a2b857632cd40fdb5aaa5e7ed0a80b961686eb","0xfa381bc84e8666b1cb2dc5e213b0a75f085e84ec","0xf883b55ba5bda00f8069610ef6a0f82767a700d5","0x84317e16f1578062af3a9422caf8bdfb7ccd9eca","0x4a1aedce1d472aa8806fb64b33f6eb3d1c328205","0x2a86b99f04e34017138b1becf6dccc9a3b264f4c","0x93e90573971db1fb2e76bf4a5a50e4e862bebf41","0x6b4a427597f91246b137efb6f7a3a7f2a2e65f6d","0xab79b0dbdf7b9bf39f1018daf9d3a280d987aa7d","0x6c0a8d28ace093af52a9d3f899f1c5ce37f4b1ef","0x6b54c5a6aa832f53a67ed363fde5d56af1827c1c","0xd887639b3a5ea0a5b88f1b2e748c45b1bcc475a0","0xaf0e330fe3019743e302f3a188a9a82bc9a6bb20","0x4560a01bdc16b66119da10229b5ff4e7f48d26f5"]
all_logs=[]
for chunk in (esc[:32], esc[32:]):
    params=[{"fromBlock":"0x1930692","toBlock":"0x193cae7","address":chunk}]
    out=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","ethereum","eth_getLogs",json.dumps(params)],capture_output=True,text=True)
    d=json.loads(out.stdout)
    if 'error' in d: print("ERR", d['error']); sys.exit(1)
    all_logs+=d['result']
print("total logs on 58 escrows:", len(all_logs))
txs={}
for L in all_logs:
    txs.setdefault(L['transactionHash'],[0,set()])
    txs[L['transactionHash']][0]+=1
    txs[L['transactionHash']][1].add(L['address'])
print("distinct txs:", len(txs))
for L in all_logs[:20]:
    print(int(L['blockNumber'],16), L['address'], L['transactionHash'], L['topics'][0][:10])
