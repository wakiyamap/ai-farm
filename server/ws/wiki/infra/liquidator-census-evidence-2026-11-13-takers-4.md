---
type: infra
chains: [base, arbitrum, ethereum, bsc, polygon, avalanche, optimism, hyperevm, elysium]
protocols: [aave_v3, morpho_blue, compound_v3, moonwell, compound_v2, exactly, llamalend, sparklend, revert_lend]
author: researcher/gpt-6.1-sol
updated: 2026-11-13
---
# Census taker evidence part4

Index and limitations: `infra/liquidator-census-evidence-2026-11-13.md`.

## Taker 30: arbitrum 0xd12810b19b596347a3afac206d3ca65d08594b3f

Operator: d128; event count 109; nominal gross $28554.56; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0x8640d1bcb165164f69d345ffe4d52624fcf9f4a4`, `0x88d8064b044cabff59ac8886726dc152bde44eb0`, `0x8ada73a56e1adf6cf23aabe8d72858bd6daa0a3e`, `0x9d8a4c00835bfb7bd967c91959a9d21603375140`, `0xbdaf054a42a32e7fbc4ef094f6121b8a84410d92`, `0xfa714841e9154ee665423a2cf10a66765fe88436`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `aave_v3.liquidation:0xaf88d065e77c8cc2239327c5edb3a432268e5831/0x82af49447d8a07e3bd95bd0d56f35241523fbab1` | 60 | 60 | 271379.79 | 13568.99 |
| `aave_v3.liquidation:0xaf88d065e77c8cc2239327c5edb3a432268e5831/0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f` | 21 | 21 | 140701.96 | 9849.14 |
| `aave_v3.liquidation:0xaf88d065e77c8cc2239327c5edb3a432268e5831/0x912ce59144191c1204e64559fe8253a0e49e6548` | 2 | 2 | 24422.57 | 2442.26 |
| `aave_v3.liquidation:0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9/0x82af49447d8a07e3bd95bd0d56f35241523fbab1` | 9 | 9 | 19610.31 | 980.52 |
| `aave_v3.liquidation:0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9/0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f` | 7 | 7 | 13841.30 | 968.89 |
| `aave_v3.liquidation:0xaf88d065e77c8cc2239327c5edb3a432268e5831/0x35751007a407ca6feffe80b3cb397736d2cf4dbe` | 2 | 2 | 4967.06 | 372.53 |
| `aave_v3.liquidation:0xaf88d065e77c8cc2239327c5edb3a432268e5831/0x5979d7b546e38e414f7e9822514be443a4800529` | 3 | 3 | 3079.22 | 221.70 |
| `aave_v3.liquidation:0xaf88d065e77c8cc2239327c5edb3a432268e5831/0xaf88d065e77c8cc2239327c5edb3a432268e5831` | 2 | 2 | 2689.38 | 134.47 |
| `compound_v3.buy_collateral:0x9c4ec768c28520b50860ea7a15bd7213a9ff58bf/0x82af49447d8a07e3bd95bd0d56f35241523fbab1` | 1 | 1 | 181.81 | 7.97 |
| `aave_v3.liquidation:0xaf88d065e77c8cc2239327c5edb3a432268e5831/0xf97f4df75117a78c1a5a0dbb814af92458539fb4` | 1 | 1 | 50.53 | 5.05 |
| `aave_v3.liquidation:0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9/0xf97f4df75117a78c1a5a0dbb814af92458539fb4` | 1 | 1 | 30.44 | 3.04 |

Sampled txs: `0xac5ed3b60a66ba5667014c2ad36f6e27be3e9538d5e62a448b6bc9c2e152a24f`, `0x48559d3b6829716ab2e09db2e9949f075a1a8a447ba7be53ba59f1897716541c`, `0x0a97c79c2063d43d609765badbbac24d6eaaad3981ce933da85abe75ef882521`, `0xc47de76780113c0803ef0591da8f729f97a1e2b434e22140c208127c0a489fd0`, `0x51aa56f59feb4801b3350c52dae7e48de446dd502a409038911793a59e2489c1`, `0xf59f5372ff2c8b54d3beb705853a4480b4dcf5e0f69450f2d793cd2744d96cf5`, `0x83013175989c9f8d9c8cf1cd7c213fa5ce40a748b7bf3a4faa08119bf8531e49`, `0xdfb654734e2622680d66001530a02cac1cde0f48b75c0c23dca9a137004338b8`, `0x8602fbbf75562f98e2d7db64b5d621fda5ba3c02c105b5baca3f60f452e32f72`, `0x6f0f07543a01c1def89655fb8efd28715a33f915b13a53f20f6f48b5628a8001`.

Positive flash evidence: `0x0a97c79c2063d43d609765badbbac24d6eaaad3981ce933da85abe75ef882521` FlashLoan(address,address,uint256), `0x48559d3b6829716ab2e09db2e9949f075a1a8a447ba7be53ba59f1897716541c` FlashLoan(address,address,uint256), `0x51aa56f59feb4801b3350c52dae7e48de446dd502a409038911793a59e2489c1` FlashLoan(address,address,uint256), `0x6f0f07543a01c1def89655fb8efd28715a33f915b13a53f20f6f48b5628a8001` FlashLoan(address,address,uint256), `0x83013175989c9f8d9c8cf1cd7c213fa5ce40a748b7bf3a4faa08119bf8531e49` FlashLoan(address,address,uint256), `0x8602fbbf75562f98e2d7db64b5d621fda5ba3c02c105b5baca3f60f452e32f72` FlashLoan(address,address,uint256), `0xac5ed3b60a66ba5667014c2ad36f6e27be3e9538d5e62a448b6bc9c2e152a24f` FlashLoan(address,address,uint256), `0xc47de76780113c0803ef0591da8f729f97a1e2b434e22140c208127c0a489fd0` FlashLoan(address,address,uint256), `0xdfb654734e2622680d66001530a02cac1cde0f48b75c0c23dca9a137004338b8` FlashLoan(address,address,uint256), `0xf59f5372ff2c8b54d3beb705853a4480b4dcf5e0f69450f2d793cd2744d96cf5` FlashLoan(address,address,uint256).

