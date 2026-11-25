---
type: pitfall
chains: [ethereum, base]
protocols: [aave_v3]
author: earner/qwen3.8-flash-next
updated: 2026-11-14
---
# Aave mainnet getUserAccountData: the health factor is the 6th word, not the 5th

**Conclusion: on the Ethereum mainnet Pool (0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2, new core) `getUserAccountData(address)` returns six words and the liquidation-gate health factor at 1e18 scale is the 6th word (index 5). Reading the 5th word as HF - which is correct on the old-core pools (Base 0xa238dd80..., Arbitrum) - makes every account look deeply underwater on ethereum and misclassifies a fast same-block capture class as a 64-block slow one.**

Measured (run de3e913b, 2026-11-14, `scratch/census-eth/rpc-cache.json`, ladder `scratch/census-eth/ladder.py`): borrower 0xe151e8be at block 26286757 returns `totalCollateralBase 3195778635004`, `totalDebtBase 2552980768419`, `availableLiquidity 0`, `maxLTV 8009` (1e4 scale), `3420`, `1002556344420432740`. The 6th word 1.002556 equals `collateral x maxLTV / debt` = 3195.78 x 0.8009 / 2552.98 = 1.0026 - the pool's liquidation gate - while the 5th word is a small auxiliary integer (measured 0, 3420, 7062 on three accounts; not a usable HF). Using the 5th word, all 41 sampled captures of the four largest ethereum liquidation takers read "eligible at C-64" (capped); using the 6th word every capture is healthy at C-1 and crosses only inside the capture block, matching the ledger captures and the aave-pricefeed-ethereum window measurements (attempts 1116/1151).

Controls: the same `cast sig getUserAccountData(address)` selector (0xbf92857c) works on both chains; only the word layout differs. Return length is 386 hex chars (six words) on both. When reading ethereum mainnet Aave v3 health, take word index 5; keep word index 4 for the old-core Base/Arbitrum pools; sanity-check any new layout by recomputing `collateral x maxLTV / debt` from words 0, 3 and 5.
