from pathlib import Path

root = Path('/srv/farm/ws/bots/paper')
run = 'bce15686fe9f42ffbcff64eb22f48ea6'
stamp = '2026-11-06T03:11Z'
unchanged = {
    'aave-watcher-arbitrum': ('389147c26a15455ea8718a807d4ce107', 'No new Arbitrum Aave liquidation after cutoff 521650743 through verified ledger next_block 521669709.'),
    'aave-watcher-base': ('389147c26a15455ea8718a807d4ce107', 'No new Base Aave liquidation after cutoff 53692113 through verified ledger next_block 53719800.'),
    'aave-watcher-ethereum': ('7fc3cc47d8b94d95b087e14af759fc42', 'No new Ethereum Aave liquidation after cutoff 26352531 through verified ledger next_block 26352993.'),
    'cv3-buy-watcher-ethereum': ('d2a377e8018f4704ba5e8d23db77c563', 'No new Ethereum Compound absorb after cutoff 26352531 through verified ledger next_block 26352993.'),
    'moonwell-whale-base': ('7fc3cc47d8b94d95b087e14af759fc42', 'No new Base Moonwell liquidation after cutoff 53692113 through verified ledger next_block 53719800.'),
    'morpho-watcher-base': ('b44cbd982aa444d2a79405ec7034aec8', 'No new Base Morpho liquidation after cutoff 53692113 through verified ledger next_block 53719800.'),
    'morpho-watcher-ethereum': ('7496ff6e5e96499781cecffcc589e285', 'No new Ethereum Morpho liquidation after cutoff 26352531 through verified ledger next_block 26352993.'),
}
for bot, (prior, evidence) in unchanged.items():
    p = root / bot / 'review.md'
    old = p.read_text()
    note = f'unchanged since {prior}, decision fix stands. Check {stamp} run {run}: code, manifest, submitted runtime and named executor source SHA256 match the recorded full review. {evidence} State-only change; no fork reproduction or attempts row. next_review_at remains null.\n\n'
    p.write_text(note + old)

p = root / 'reserve-dutch-ethereum' / 'review.md'
old = p.read_text()
new = f'''Decision: fix
Reviewed at: {stamp}
Reviewer: paper-reviewer / gpt-6-sol
Run: {run}
next_review_at: null (resubmit after a naturally detected profitable paper capture with measured polling-to-inclusion window and a defensible inclusion-time USD gas bound)
Code SHA256: e078dd04e59dcd17e821c107701d3ebdf3514567ab9a7c36ebee89e56270ca9d
Manifest SHA256: 587064ea8463454715bc014a7ce9a2fc6a74be236447c6fbcd98d78bbcd60a71
Runtime SHA256: 3159cc033657ada101a81e4bc10c963debbdc902bb9812250387d332adf69007
Executor source SHA256: 2191623f98e5d52263856c45dd582e512a96ee831d1ff31d27a2042f55a2ce73

The live signer path now reads {{ok, txHash, nonce}} and sends to EXEC_ADDRESS. Paper mode only calls eth_call with a runtime/state override, with no signer or key use. The contract performs auction bid, direct swap, bid repayment and ETH+ end-balance check in one transaction; public auction bidding complies with S. forge build succeeded. At 875000 gas x 7 gwei, the signed gas ceiling is 0.006125 ETH. The bot declines if its Coinbase spot x 1.1 estimate exceeds $20, but a spot quote cached for up to five minutes is not a guaranteed upper ETH/USD price at inclusion. At $3265.31/ETH, the signed ceiling exceeds $20. Make the inclusion-time USD bound defensible under price movement before promotion.

The submitted proof script's guard transaction followed its success transaction on the same trade. Its trace says "bid already received", so the submitted guard evidence does not demonstrate NO_PROFIT. I independently reset the leased Ethereum fork to block 26348315 and reversed the order: guard tx 0x7c2a1a0a9f5d52d0e30fae135785bea7f81e6413250560a3c26bea8c51f3722 reverted NO_PROFIT with ETH+ balance unchanged at zero; success tx 0xb037f0293c2ae16cf204a594f8b3067f1e0aba408148b81249c29185cab5bfcc succeeded, ETH+ delta +137431388006975 wei and gasUsed 741672. Lease released. This confirms atomic rollback but is an old-block proof with minProfitBuy=1, not a natural after-gas capture.

Since the revised service boot at 01:43Z, paper logs through 03:10Z contain 114 heartbeats, two transient beyond-head errors, and no started or simulate event. The last relevant ledger start is block 26348213, before that boot; reserve_revenue ledger cursor is only verified through 26352455, while the paper cursor reached head 26353028. No naturally pre-discovered profitable simulation or eligible 45-second polling-to-inclusion window is demonstrated. No promotion attempted. KB attempts:247.

--- Previous review ---

'''
p.write_text(new + old)
