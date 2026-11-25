import json, subprocess

H=['0xcf2b1528b9b2d9620f94a55b338fe2d1ce1852c105125677c441e68928cdffad','0xbe9ed0dc5bbd1bc0d4716305e8b15863d6b5e5a7480f9fe6c8edf6a88897937d','0x14f45e1b32051f3a98381fff6629c75860cb907c37d071fc50614333a53904a9','0x6d3cca0b9731ef9b400e2915b07046156a890554f0f9e9d964ba6695c294f83a','0x7117924188cb69a4fca2cc6f368cfc075efdc2f6363cd4bd5f2d20a98fc4b672','0xaa78e91754b14b2feea9043391dac8371bbf4879cdb6b187251d4ab080d057a3','0x3431759a0e325c63ad13ffc26ed1e21d29ad3d4f2af057717dd791e212a628ea','0x015d2039b265c228b0212fe7dc949315b9008a55615c8c2692321aa385697125','0xfc96ca18c747bcaef3e3fbedc98f78c1b533ff63783e8f5048c55a07a06c9542','0xfa4a4b980bb59d0e92237720d909033aaf026f8617e7372ace89e8aed2eb0670','0xfecf80041a28a6fc4b19dcfe69274cd1524fd83167fadf3a320421153b44dbef','0x30c84d93b24f77403f59efce62dda862d1e0c7cb642782324ce7328debb36469','0x8dad3b1d58497f643b41dedd7c1b28255a89e2cf32f11f055b656a4ba3090625','0x40c392aabc46c7b36d63f786cf2c8d7c039203c3580f62b861a9fb8a295cfdf7','0x55eeffe06d8fa721dbc020cba7b713ccba5a2342ac315249f12bfac8d0c98e60']
actor='f848670508a8f83767b0a1bf53a5fac737d30e31'
usdt='b8ce59fc3717ada4c02eadf9682a9e934f625ebb'
for h in H:
    p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','hyperevm','eth_getTransactionReceipt',json.dumps([h])],capture_output=True,text=True)
    if p.returncode: print(h[:10],p.stderr); continue
    r=json.loads(p.stdout)['result']
    flows={}
    for l in r['logs']:
        t=l['topics']
        if len(t)!=3 or t[0].lower()!='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef':continue
        src=t[1][-40:].lower(); dst=t[2][-40:].lower(); token=l['address'].lower()
        for who in (actor,'01ce5aa238f1ca4cc194b8256651b60642fe4b1a'):
            if src==who:flows[token+' '+who]=flows.get(token+' '+who,0)-int(l['data'],16)
            if dst==who:flows[token+' '+who]=flows.get(token+' '+who,0)+int(l['data'],16)
    gas=int(r['gasUsed'],16)*int(r['effectiveGasPrice'],16)/1e18
    print(json.dumps({'hash':h,'block':int(r['blockNumber'],16),'success':int(r['status'],16),'gas_hype':round(gas,7),'gas_usd':round(gas*63.3897540985,4),'flows':flows,'actor_usdt0':flows.get('0x'+usdt+' '+actor,0)/1e6}))
