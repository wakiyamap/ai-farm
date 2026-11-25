import urllib.request,json
u="https://eth.blockscout.com/api/v2/addresses/0x32467a5fc2d72d21e8dce990906547a2b012f382"
r=urllib.request.urlopen(urllib.request.Request(u,headers={"user-agent":"farm"}),timeout=20)
j=json.loads(r.read())
ab=j.get("encoding")
print("encoding:",ab,"is_proxy:",j.get("is_proxy"))
