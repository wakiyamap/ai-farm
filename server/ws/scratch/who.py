import subprocess, json
hashes = {
 '0x992510b8f7685253ccb4ac18969e28cb4962be453612715107c7a4c9a0b067e4':'aave usdc5692',
 '0xf80fba22806b9ec89aa1096cf44be26bdc1306712e86989f641741710a63f510':'aave wbtc',
 '0x6d1248b8b2d040e7e26c75c6c897cbf5626e6e61fc9b333970910edfe5b66183':'aave usdt0',
 '0x421f81799df218cadee2106bf04268176aca2a053e42904e593b98b5586fcd0c':'aave dai',
 '0x741eb6413a9aebd562d93c8d944d04567c0914f785f20f55908227c3f8303c27':'aave link',
 '0xaec83bc96ed3f4cf41b27dc2ec0f265cb3f0cc3d056a17313d88a16a5158f5c3':'aave arb',
 '0x362d5578571aa698f17897391a3996a841350a5720d04c0a465096a985dcda03':'aave arb 21k',
 '0x8dd4d06d552c9fb85d850b909e0584665f6aedeeef923cacf46ecdddc82806ec':'compound buy',
}
for h,lbl in hashes.items():
    out = subprocess.run(['python3','tools/rpc.py','arbitrum','eth_getTransactionByHash','["%s"]'%h,'--lane','research'],capture_output=True,text=True)
    try:
        t=json.loads(out.stdout)['result']
        r=subprocess.run(['python3','tools/rpc.py','arbitrum','eth_getTransactionReceipt','["%s"]'%h,'--lane','research'],capture_output=True,text=True)
        rec=json.loads(r.stdout)['result']
        print(lbl, t['from'][:12], t['to'][:12], 'sel',t['input'][:10],'gasUsed',int(rec['gasUsed'],16),'gasprice_gwei',round(int(t['gasPrice'],16)/1e9,4),'status',rec['status'])
    except Exception as e:
        print(lbl,'ERR',e,out.stdout[:120],out.stderr[:120])
