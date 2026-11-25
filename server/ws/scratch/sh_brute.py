import hashlib, itertools

import subprocess
def keccak4(s):
    r = subprocess.run(["cast", "sig", s], capture_output=True, text=True)
    return r.stdout.strip()[2:10]

targets = {"0a12f521","1afcd79f","2a875269","334bd919","703e46dd","7965db0b","f0330054"}
names = """withdraw withdrawTo claim claimable claimReward getReward rewards reward harvest poke sync update settle sweep transfer
redeem redeemTo unstake exit requestWithdraw requestWithdrawal withdrawRequest executePayout pay payout
depositTo depositFor userAmount userBalance balance users stakedInfos stakedInfo getUserStakedNumber
poolUserAmounts poolInfo setPoolAmount updatePoolAmounts setPoolTokenAmount adminWithdraw adminDeposit
withdrawAll withdrawAllToken withdrawToken claimRewardTo setPaused pause unpause pauseDeposit pauseWithdraw
setSwapAddress setWithdrawAddress setMasterWallet whitelist addToken removeToken setToken
getDepositAmount getWithdrawAmount setPrice updateYield accrue addYield setYield setReward""".split()
typesets = [(), ("address",), ("uint256",), ("address","uint256"), ("uint256","address"), ("bool",),
            ("address","address"), ("address","bool"), ("address","address","uint256"), ("uint256","uint256"),
            ("uint256","address","address")]
found = {}
for n in names:
    for ts in typesets:
        sig = n + "(" + ",".join(ts) + ")"
        h = keccak4(sig)
        if h in targets:
            found[h] = sig
for t in targets:
    print(t, "->", found.get(t, "?"))
