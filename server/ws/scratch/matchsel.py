import subprocess
code = open('scratch/wbeth-impl.hex').read()[2:]
b = bytes.fromhex(code)
sels = set()
i = 0
while i < len(b)-5:
    if b[i] == 0x63 and 0x14 in b[i+5:i+12]:
        sels.add(b[i+1:i+5].hex())
    i += 1
cands = """name() symbol() decimals() totalSupply() balanceOf(address) transfer(address,uint256)
transferFrom(address,address,uint256) approve(address,uint256) allowance(address,address)
increaseAllowance(address,uint256) decreaseAllowance(address,uint256) nonces(address) DOMAIN_SEPARATOR()
eip712Domain() permit(address,address,uint256,uint256,bool,bytes32,bytes32) permit(address,address,uint256,uint256,uint256)
owner() renounceOwnership() transferOwnership(address) paused() pause() unpause()
upgradeTo(address) upgradeToAndCall(address,bytes) implementation() admin() changeAdmin(address) pendingAdmin() proxiableUUID()
exchangeRate() exchangeRateStored() convertBETHToETH(uint256) convertETHToBETH(uint256)
wrap() wrap(uint256) wrapTo(address,uint256) wrapTo(address) unwrap(uint256) unwrapTo(address,uint256)
mint(address,uint256) burn(uint256) burn(address,uint256) burnFrom(address,uint256)
setExchangeRate(uint256) updateExchangeRate(uint256) addMinter(address) removeMinter(address) isMinter(address)
deposit() deposit(address) withdraw(uint256) withdraw(address,uint256)
reward() rewards() claimReward() claimRewards() distribute() checkpoint() settle() harvest() poke() compound() rebalance() epoch()
version() subscribe(address,uint256)
setPendingAdmin(address) claimAdmin() setPendingOwner(address) claimOwnership()
transferOn(address,address,uint256) setContractConfig(address,bytes32)
addBlackList(address) removeBlackList(address) isBlackListed(address) setBlackList(address,bool)
setWhiteList(address,bool) isWhiteListed(address)""".splitlines()
found = {}
for sig in cands:
    sig = sig.strip()
    if not sig:
        continue
    h = subprocess.run(['cast','sig',sig], capture_output=True, text=True).stdout.strip()
    if not h:
        continue
    s = h[2:]
    if s in sels:
        found[s] = sig
        sels.discard(s)
print("MATCHED:")
for s in sorted(found):
    print(" ", s, found[s])
print("UNMATCHED:")
for s in sorted(sels):
    print(" ", s)
