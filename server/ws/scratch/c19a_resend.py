import json
r=json.load(open('scratch/c19a_batch_tx.json'))['result']
tx={'from':r['from'],'to':r['to'],'input':r['input'],'nonce':0,'value':'0x0','gas':'15000000'}
print(json.dumps(tx))
