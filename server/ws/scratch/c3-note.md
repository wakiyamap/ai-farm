# Camelot V3 (arbitrum) - Algebra AMM v1.9 sweep (scout 2026-11-19)

## Contracts (docs.camelot.exchange ammv3 section, Arbitrum mainnet)
- AlgebraFactory 0x1a3c9B1d2F0529D97f2afC5136Cc23e58f1FD35B (code 28064B; owner()=0xba6a06f8517e271db44540e68ba46beb4bc6155d; farmingAddress()=0x0; vaultAddress()=0x58095979b412a366687ca05cbe85ff56241be21f)
- NonfungiblePositionManager 0x00c7f3082833e796A5b3e4Bd59f6642FF44DCD15 (code 48272B; totalSupply()=48838)
- SwapRouter 0x1F721E2E82F6676FCE4eA07A5958cF098D339e18 (code 25396B)
- Quoter 0x0Fc73040b26E9bC8514fA028D998E73A254Fa76E; AlgebraInterfaceMulticall 0x1F98415757620B543A52E61c46B32eB19261F984
- Pools = AlgebraPool (v0.7.6), e.g. 0xb1026b8e7276e7ac75410f1fcbbe21796e8f7526, 0x4b0495c5f5147051ba5fa025424d393d343d10bf (pool.factory() = 0x1a3c9b1d...)

## Function sweep (verified sources via explorer)
- Factory: createPool permissionless, pays creator nothing; setOwner / setFarmingAddress / setDefaultCommunityFee / setVaultAddress / setBaseFeeConfiguration all onlyOwner.
- AlgebraPool v1.9: mint, collect, burn, swap, swapSupportingFeeOnInputTokens, flash = user actions (LP/recipient paid; flash borrower pays paid0/paid1); setCommunityFee, setTickSpacing, setLiquidityCooldown = onlyFactoryOwner; setIncentive = requires factory.farmingAddress() = 0x0 (no incentive layer configured, uncallable). No skim, no reward/bounty/keeper functions.
- NFPM: standard Uni-V3-periphery actions (mint / increaseLiquidity / decreaseLiquidity / collect / burn / multicall / refundNativeToken / unwrapWNativeToken); no reward function.

## Activity (control-backed)
- SwapRouter has txs within minutes of check (explorer txs; e.g. 0x11d83e9bfda8cb107e64b750ac5f0807dde817ff33efa2d68282b22190f559e9 exactInput, gasUsed 532039).
- Sample of 2 pools: 152 Swap events (topic0 0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67) in one 10k-block window (~42 min) ending block 525,479,204 (150 from 0xb1026b8..., 2 from 0x4b0495...).
- 0 new Pool creations in last 7 days (factory topic0 0x91ccaa7a278130b65168c3a0c8d3bcae84cf5e43704342bd3ec0b59e59c036db, 0x1f336a24..latest); same-shape control on V4 factory also 0.

## Verdict
no_reward - DEX pays LPs/swap users, not callers (same pattern as camelot-v4, attempts:1578). farmingAddress 0x0 means no active incentive layer.
