import json, os, urllib.request
URL=os.environ['RPC_RELAY_URL']
def rpc(chain, method, params):
    data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    r=urllib.request.urlopen(urllib.request.Request(f"{URL}/{chain}?lane=research",data=data,headers={"content-type":"application/json"}),timeout=60)
    body=json.loads(r.read().decode())
    return body.get('result') or body
TRF="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
head=int(rpc("polygon","eth_blockNumber",[]),16)
logs=rpc("polygon","eth_getLogs",[{"fromBlock":hex(head-99),"toBlock":hex(head),"topics":[TRF]}])
print("polygon Transfer ctrl 100 blocks:", len(logs) if isinstance(logs,list) else logs, list(set(l['address'] for l in logs[:200]))[:4] if isinstance(logs,list) else "")
