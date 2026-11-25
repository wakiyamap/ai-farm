import collections, json, subprocess

lines=[json.loads(x) for x in open('scratch/ironbank_scan.out') if x.strip()]
markets=next(x['markets'] for x in lines if 'markets' in x)
pages=[x['page'] for x in lines if 'page' in x and x['all']>0]
topics=collections.Counter()
addresses=collections.Counter()
for a,b in pages:
    args=['python3','tools/rpc.py','ethereum','eth_getLogs',json.dumps([{'address':markets,'fromBlock':hex(a),'toBlock':hex(b)}])]
    p=subprocess.run(args,capture_output=True,text=True,check=True)
    for log in json.loads(p.stdout)['result']:
        topics[log['topics'][0]]+=1
        addresses[log['address'].lower()]+=1
print(json.dumps({'pages':pages,'topic_counts':topics,'address_counts':addresses}))
