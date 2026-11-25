import sys, json, os, urllib.request
def call(chain, to, data, lane='research', method='eth_call', params_extra=None):
    url=os.environ.get('RPC_RELAY_URL')
    p=[{'to':to,'data':data}, 'latest'] if method=='eth_call' else []
    if method!='eth_call': p=params_extra
    body=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':[chain]+p if False else p})
    req=urllib.request.Request(f"{url}/{chain}?lane={lane}", data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':p}).encode(), headers={'content-type':'application/json'})
    try:
        r=json.loads(urllib.request.urlopen(req, timeout=30).read())
        return r.get('result') or r.get('error')
    except Exception as e:
        return {'EXC':str(e)}
if __name__=='__main__':
    # usage: c.py <chain> <to> <data>
    chain,to,data=sys.argv[1],sys.argv[2],sys.argv[3]
    lane=os.environ.get('LANE','research')
    print(call(chain,to,data,lane))
