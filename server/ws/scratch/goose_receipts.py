import subprocess, json
MC="0xe70e9185f5ea7ba3c5d63705784d8563017f2e57".lower()
EGG="0xf952fc3ca7325cc27d15885d37117676d25bfda6".lower()
TR="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
txs=[("4c65db72","0xe5bcba00efb4db52735c16a0c33fd41df6f6ac83550a79fc2fa067b7075d412a"),
("ef669b7c","0x82d26b5e64ba67a8adca0317da6d5d35c836b733e10c10ade28ecc150b4af18b"),
("1b368e3d","0xb7e1c3176089c0e2f3150ad531cf346bbba8ff4dd44ab1720182c42620797e09"),
("09806632","0xd6eeb0c3b0882d28b0a5aedf39a773d67f093af4a1197d3643bb6386ada5f2a7"),
("a2fc19ec","0xf247c7a3f103b38fc1ca269c1af878e9221f82fae1a1dc8cbd8e5cc744fe1ff0")]
for u,tx in txs:
    r=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","bsc","eth_getTransactionReceipt",json.dumps([tx])],capture_output=True,text=True)
    rc=json.loads(r.stdout)["result"]
    gasUsed=int(rc["gasUsed"],16); gp=int(rc.get("gasPrice", rc.get("effectiveGasPrice","0x1")),16)
    eggpaid=0
    for lg in rc["logs"]:
        if lg["address"].lower()==EGG and lg["topics"][0].lower()==TR:
            frm="0x"+lg["topics"][1][-40:]
            if frm.lower()==MC:
                eggpaid+=int(lg["data"],16)
    print(f"{u} tx={tx[:14]}.. eggPaid={eggpaid/1e18:.2f} gasUsed={gasUsed} gasPriceGwei={gp/1e9:.2f}")
