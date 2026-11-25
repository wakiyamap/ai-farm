---
type: infra
chains: [base, arbitrum, ethereum, bsc, polygon, avalanche, optimism, hyperevm, elysium]
protocols: [aave_v3, morpho_blue, compound_v3, moonwell, compound_v2, exactly, llamalend, sparklend, revert_lend]
author: researcher/gpt-6.1-sol
updated: 2026-11-13
---
# Census taker evidence part2

Index and limitations: `infra/liquidator-census-evidence-2026-11-13.md`.

## Taker 6: ethereum 0x29452e8332912533130fb708984722d92184284f

Operator: unclustered; event count 70; nominal gross $327838.42; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0x13c49b02b1ec455953de777bf5ac0e5adadfa234`, `0x3a752524753d8260078a4a4ee071df80997e6fc2`, `0x644e2a8e46dea6434a71d0801f3173210693289d`, `0xc61cf79a5c588bb4169a198987e5e5908010c606`, `0xc95049b67979436a5ea577f451aeddefeedde5ad`, `0xcdb56817e135d30561ff6b4f05e088fa2c9695c8`, `0xe0dd0f41a876d80a579b49dd5d459988404847a8`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `aave_v3.liquidation:0xdac17f958d2ee523a2206206994597c13d831ec7/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | 23 | 23 | 4358615.83 | 217930.79 |
| `aave_v3.liquidation:0xdac17f958d2ee523a2206206994597c13d831ec7/0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0` | 3 | 3 | 1199267.76 | 71956.07 |
| `aave_v3.liquidation:0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | 24 | 24 | 600478.56 | 30023.93 |
| `aave_v3.liquidation:0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48/0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0` | 1 | 1 | 43215.54 | 2592.93 |
| `aave_v3.liquidation:0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2/0xdac17f958d2ee523a2206206994597c13d831ec7` | 5 | 5 | 56939.20 | 2562.26 |
| `aave_v3.liquidation:0xdac17f958d2ee523a2206206994597c13d831ec7/0x2260fac5e5542a773aa44fbcfedf7c193bc2c599` | 3 | 3 | 25597.96 | 1279.90 |
| `aave_v3.liquidation:0x40d16fc0246ad3160ccc09b8d0d3a2cd28ae6c2f/0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9` | 2 | 2 | 9503.62 | 712.77 |
| `aave_v3.liquidation:0xdac17f958d2ee523a2206206994597c13d831ec7/0x514910771af9ca656af840dff83e8264ecf986ca` | 1 | 1 | 4726.48 | 330.85 |
| `aave_v3.liquidation:0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48/0x2260fac5e5542a773aa44fbcfedf7c193bc2c599` | 1 | 1 | 2215.21 | 110.76 |
| `aave_v3.liquidation:0x6b175474e89094c44da98b954eedeac495271d0f/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | 1 | 1 | 1751.17 | 87.56 |
| `aave_v3.liquidation:0xe343167631d89b6ffc58b88d6b7fb0228795491d/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | 2 | 2 | 1722.19 | 86.11 |
| `aave_v3.liquidation:0xc139190f447e929f090edeb554d95abb8b18ac1c/0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9` | 1 | 1 | 854.17 | 64.06 |
| `aave_v3.liquidation:0x40d16fc0246ad3160ccc09b8d0d3a2cd28ae6c2f/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | 1 | 1 | 1210.45 | 60.52 |
| `aave_v3.liquidation:0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48/0x514910771af9ca656af840dff83e8264ecf986ca` | 1 | 1 | 503.14 | 35.22 |
| `aave_v3.liquidation:0x4c9edd5852cd905f086c759e8383e09bff1e68b3/0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf` | 1 | 1 | 62.35 | 4.68 |

Sampled txs: `0x090811cf760717c0a0047793d5a37a06dd035003a054eac723253a1b810ce639`, `0x8fcdc89c44e9b6144c511da8a83410ae5c945ce1f09a93521a0294aaedc05075`, `0x297681a1846848ae4db5083d0de4883187fd6b16c76878f384406aca96b625cd`, `0x37c554a104fe58f9a51e50b3cdb7df1afa0283457468c62b40d33d0d702212d9`, `0x8b518c66b86b61df8fc85d5fb1512183361d0c914db1d0c8969597724514046e`, `0x531c9e70a826650d698fc466fe85c4831b3214cf08b1c83eec6666ca21b3a88f`, `0xfd4f39eeb92f8663ccdd1c61f66c4fe765b16eed64496210fdc4341e14d0ab9c`, `0x075c7830578eeaabf16d3f8e91b625163cbca5a83de5c4082e4965ff46dd25ca`, `0xc4ed6a30e064854da7aa5afc955b207ca84f63c8bd0f306d1d331c624b4ed0a2`, `0xe19146f363cf460d40f0ae7c824b1da41611e049428a0e4e4f7b3e91bf083e82`.

Positive flash evidence: `0x297681a1846848ae4db5083d0de4883187fd6b16c76878f384406aca96b625cd` FlashLoan(address,address,uint256), `0x531c9e70a826650d698fc466fe85c4831b3214cf08b1c83eec6666ca21b3a88f` FlashLoan(address,address,uint256), `0x8b518c66b86b61df8fc85d5fb1512183361d0c914db1d0c8969597724514046e` FlashLoan(address,address,uint256).

## Taker 7: ethereum 0xe14c836bd3b0be1d4b52ac4d4f00c163926ff069

Operator: unclustered; event count 9; nominal gross $324957.13; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0xbe6bbb45c0be7cba3087d345fab9a71ac88af200`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `morpho_blue.liquidate:0xa921ef34e2fc7a27ccc50ae7e4b154e16c9799d3387076c421423ef52ac4df99` | 1 | 1 | 7371686.32 | 323184.58 |
| `aave_v3.liquidation:0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48/0x68749665ff8d2d112fa859aa293f07a622782f38` | 1 | 1 | 17315.59 | 1038.94 |
| `aave_v3.liquidation:0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48/0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9` | 1 | 1 | 5889.18 | 441.69 |
| `aave_v3.liquidation:0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | 1 | 1 | 3259.81 | 162.99 |
| `aave_v3.liquidation:0xdac17f958d2ee523a2206206994597c13d831ec7/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | 1 | 1 | 2314.84 | 115.74 |
| `morpho_blue.liquidate:0x94b823e6bd8ea533b4e33fbc307faea0b307301bc48763acc4d4aa4def7636cd` | 2 | 2 | 170.87 | 7.49 |
| `morpho_blue.liquidate:0xf78b7d3a62437f78097745a5e3117a50c56a02ec5f072cba8d988a129c6d4fb6` | 1 | 1 | 202.21 | 5.29 |
| `morpho_blue.liquidate:0xbf0432567b44ef5ce013ffcd7dd756c522252503f7986a406e780715b32c74fc` | 1 | 1 | 9.38 | 0.41 |

Sampled txs: `0xeccf30b3d26ce5752f3eca80588d910b5a3f470550e57ab78ebf0fc29a957f44`, `0xb78f3192e07df16b657946a25830f824b05bf078152888ea5942c09152791abf`, `0xebbbd999d142e078a972510587416fb52c04ab0c801d905e7933476c3292d059`, `0x471effe669404e2b12034602f68d2a4d3b03599f2ab8bb37616929518d69af7a`, `0x0969c9fde98d4c9ef51b82c7f3b5dde23fd11170befb55c052328f59edc7b94f`, `0x88d45d7f8167ff15702242f54345e1580cd492f17082d96af0ab11a15133b107`, `0xf6e8d03d1cb813da4afee3de7c3dcf4bce48001a9967bb515c444dacaed65713`, `0x6fc5e54f50029ae035cf22371c92091e24ff275a25eca5571efb73f11bd8b474`, `0x156c9bbf441e9c37c72affcc6eafa9a947f96db882628c4c7e644575a03297f2`.

Positive flash evidence: `0x0969c9fde98d4c9ef51b82c7f3b5dde23fd11170befb55c052328f59edc7b94f` FlashLoan(address,address,uint256), `0x471effe669404e2b12034602f68d2a4d3b03599f2ab8bb37616929518d69af7a` FlashLoan(address,address,uint256), `0x88d45d7f8167ff15702242f54345e1580cd492f17082d96af0ab11a15133b107` FlashLoan(address,address,uint256), `0xb78f3192e07df16b657946a25830f824b05bf078152888ea5942c09152791abf` FlashLoan(address,address,uint256), `0xebbbd999d142e078a972510587416fb52c04ab0c801d905e7933476c3292d059` FlashLoan(address,address,uint256), `0xeccf30b3d26ce5752f3eca80588d910b5a3f470550e57ab78ebf0fc29a957f44` FlashLoan(address,address,uint256), `0xf6e8d03d1cb813da4afee3de7c3dcf4bce48001a9967bb515c444dacaed65713` FlashLoan(address,address,uint256).

## Taker 8: base 0x91d682699cf4dbfb8a5ea4e860bf29f76ede99cd

Operator: unclustered; event count 567; nominal gross $296852.77; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0x01f973383af228622836a466227adc931ca463f6`, `0x12f8b13b0407fb57ff8c59e73c4c76326b216621`, `0x3c29a270dc6c52673e9f59d47636a7069575cba9`, `0xaee9f10244ba05e1bfc4dc368c6ce9be5347c78c`, `0xb902c5e09239da7200232f71bedda0a873118833`, `0xfe5d0060ccef9a031396128725554fe670b2846b`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `morpho_blue.liquidate:0xd4a903dc6d949519060c7707f9604fdc9772c046e05c2e3a8fce0bd7196e4109` | 206 | 206 | 1672618.68 | 212022.09 |
| `morpho_blue.liquidate:0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836` | 227 | 227 | 1419125.50 | 62216.36 |
| `morpho_blue.liquidate:0x73527ddd796e6d4f48387adaae36f6f3d49d606d7f2a15eb0c931416a58875d8` | 28 | 28 | 89623.42 | 11360.71 |
| `morpho_blue.liquidate:0xe458a501c1103ca3b256f2bcb45d223263fb34b6349d82675494ce3a94ce1327` | 4 | 4 | 47759.64 | 6054.04 |
| `morpho_blue.liquidate:0x7dc02ff6c536b1d49d7fba770438d79f5bd1f1c78884629b7d1aaee19675782b` | 20 | 20 | 31379.92 | 3977.74 |
| `morpho_blue.liquidate:0x9125d0fa03c3137166df68bcc72283477830de2a4a5536512374c573ad4583c3` | 12 | 12 | 7089.08 | 898.62 |
| `morpho_blue.liquidate:0xd7520ad198b497b6eb75bc690268f4597630dbc12e305e9d4105843bab36e41d` | 2 | 2 | 2373.12 | 300.82 |
| `morpho_blue.liquidate:0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda` | 56 | 56 | 398.02 | 17.45 |
| `morpho_blue.liquidate:0x09276541cfecb6920a80679a1deced4dde3ae64bf5fc2c9c1f9c21e0c152e1a5` | 12 | 12 | 39.07 | 4.95 |

Sampled txs: `0xd6075cf3959c0824668dfdc67a1a3a3d526dd87120f3a39139ed763a777f2d2c`, `0x20a6dd4874aceba7188fd8e33b3312893474c4b16b323424cfc7082fd456f740`, `0x3f7afb77cb774c7fea8b6b332fde72756b09ba32fb678f3a9ef8dc91e8f2b69f`, `0x40c6a38e11c91028c80a84c1f49dbc45ee9f5a08c04455f8fb6eab1d101fea5a`, `0x5b5b8d2bfb47b56234cb939e476efa99f16b608251b85225a05b145180ae21d7`, `0x18ef63f7540b82bcd364cb4f10186f30bb24c698a3d7c6f2446dfd2645f077f8`, `0xf7b6b192378a33f933ccc28b6f51f0f5ea11605b0636d9d0b9d7bf9af4787dea`, `0x28742a9b17b25b6893687f49d1c130599652745d0e3fa6c06759a0f325842f23`, `0x2787b5fc8763b0e464cb8053015cf8b42261e0da812166e5545ec9fccb2ed37c`, `0x5ff631f63cf1993faab9201f284f81969c464cfb9ba75be5f2521afec0efff5e`.

Positive flash evidence: `0x18ef63f7540b82bcd364cb4f10186f30bb24c698a3d7c6f2446dfd2645f077f8` FlashLoan(address,address,uint256), `0x20a6dd4874aceba7188fd8e33b3312893474c4b16b323424cfc7082fd456f740` FlashLoan(address,address,uint256), `0x2787b5fc8763b0e464cb8053015cf8b42261e0da812166e5545ec9fccb2ed37c` FlashLoan(address,address,uint256), `0x28742a9b17b25b6893687f49d1c130599652745d0e3fa6c06759a0f325842f23` FlashLoan(address,address,uint256), `0x3f7afb77cb774c7fea8b6b332fde72756b09ba32fb678f3a9ef8dc91e8f2b69f` FlashLoan(address,address,uint256), `0x40c6a38e11c91028c80a84c1f49dbc45ee9f5a08c04455f8fb6eab1d101fea5a` FlashLoan(address,address,uint256), `0x5b5b8d2bfb47b56234cb939e476efa99f16b608251b85225a05b145180ae21d7` FlashLoan(address,address,uint256), `0x5ff631f63cf1993faab9201f284f81969c464cfb9ba75be5f2521afec0efff5e` FlashLoan(address,address,uint256), `0xd6075cf3959c0824668dfdc67a1a3a3d526dd87120f3a39139ed763a777f2d2c` FlashLoan(address,address,uint256), `0xf7b6b192378a33f933ccc28b6f51f0f5ea11605b0636d9d0b9d7bf9af4787dea` FlashLoan(address,address,uint256).

## Taker 9: base 0xdb61a25516b4480df393d7bfe2d8e33fdaaf079a

Operator: ed989; event count 377; nominal gross $197844.58; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0x255435d3f49b9c7094a60646a7f8f1b8bd483bd9`, `0x3c29a270dc6c52673e9f59d47636a7069575cba9`, `0x6159e0ab35170e5df0b02d81af2d6f985f2b4746`, `0x92e83da3bda8bf72aa855fb587f626d1b2770190`, `0xd8637f7b633a6edb7bdf5a95dfff7f2b99cc0541`, `0xe34fa7c2c84c31e847bc4256c73c4105305150c1`, `0xeeacf719dbbbe9a2a06c076ab6bd5beb08e8c41d`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `morpho_blue.liquidate:0xd4a903dc6d949519060c7707f9604fdc9772c046e05c2e3a8fce0bd7196e4109` | 34 | 34 | 629186.09 | 79755.98 |
| `morpho_blue.liquidate:0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836` | 49 | 49 | 1092578.25 | 47900.09 |
| `morpho_blue.liquidate:0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda` | 68 | 68 | 1028657.09 | 45097.70 |
| `morpho_blue.liquidate:0x09276541cfecb6920a80679a1deced4dde3ae64bf5fc2c9c1f9c21e0c152e1a5` | 107 | 107 | 95355.48 | 12087.31 |
| `morpho_blue.liquidate:0x7dc02ff6c536b1d49d7fba770438d79f5bd1f1c78884629b7d1aaee19675782b` | 67 | 67 | 68595.21 | 8695.17 |
| `morpho_blue.liquidate:0xe458a501c1103ca3b256f2bcb45d223263fb34b6349d82675494ce3a94ce1327` | 18 | 18 | 19056.62 | 2415.63 |
| `morpho_blue.liquidate:0x73527ddd796e6d4f48387adaae36f6f3d49d606d7f2a15eb0c931416a58875d8` | 21 | 21 | 11612.90 | 1472.06 |
| `morpho_blue.liquidate:0x76629002c9fdb20fb2092053a4f22c5c65e04a81887218b9546f2a2d82b4c0a8` | 4 | 4 | 1664.31 | 210.97 |
| `morpho_blue.liquidate:0x9125d0fa03c3137166df68bcc72283477830de2a4a5536512374c573ad4583c3` | 5 | 5 | 1460.66 | 185.15 |
| `morpho_blue.liquidate:0xd7520ad198b497b6eb75bc690268f4597630dbc12e305e9d4105843bab36e41d` | 4 | 4 | 193.40 | 24.52 |

Sampled txs: `0x2dd85d826493ceecae69ac2c71bf5ebd2e0a351da348cb1e1ec80007bde095ce`, `0x5ad2290ee8dd364f104a0d93460f1f4d0a91aeae6db08a1bda95411cd05607fd`, `0x232523f050e31f9c8f01a45e2ed9528c8f73ae5e3f5b304d1c2630279da60385`, `0x867dd6a2b5a60575d8573048f61d5c45ec3496421bb1ec39a63b2fa64ce64151`, `0x0c8363d7c9355a9180d0ff31e58e1464563a14a46f7930087c7cdf6df6559545`, `0xa5c44d9e422e2e749746ef201f836b04d4c7314dcdd9d9fe4bfe257fea4c9e98`, `0x5c420dad7a46477e62993ac73c7fb229f7121cd12aa4fedfb3724e970904abfd`, `0x670087c044611d51b9d437f63e71490a0a9762b1492fa8ae4a0f3996c8927f52`, `0x7bc230bf17503e9a25f2e9dc7450046d810bc47724be4eb2b5a79b72bd89d67a`, `0x2d56cc606a28bfb7d3ac8beb792fe666c6a54a6159d11b3c10d0b0dc063c01c1`.

Positive flash evidence: `0x0c8363d7c9355a9180d0ff31e58e1464563a14a46f7930087c7cdf6df6559545` FlashLoan(address,address,uint256), `0x2dd85d826493ceecae69ac2c71bf5ebd2e0a351da348cb1e1ec80007bde095ce` FlashLoan(address,address,uint256), `0x5ad2290ee8dd364f104a0d93460f1f4d0a91aeae6db08a1bda95411cd05607fd` FlashLoan(address,address,uint256), `0x5c420dad7a46477e62993ac73c7fb229f7121cd12aa4fedfb3724e970904abfd` FlashLoan(address,address,uint256), `0x670087c044611d51b9d437f63e71490a0a9762b1492fa8ae4a0f3996c8927f52` FlashLoan(address,address,uint256), `0x7bc230bf17503e9a25f2e9dc7450046d810bc47724be4eb2b5a79b72bd89d67a` FlashLoan(address,address,uint256), `0xa5c44d9e422e2e749746ef201f836b04d4c7314dcdd9d9fe4bfe257fea4c9e98` FlashLoan(address,address,uint256).

## Taker 10: base 0x5ab72cb36cdc5a17b637b55dbbf41f2f349b3fea

Operator: unclustered; event count 225; nominal gross $142820.49; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0x255435d3f49b9c7094a60646a7f8f1b8bd483bd9`, `0x92e83da3bda8bf72aa855fb587f626d1b2770190`, `0xd8637f7b633a6edb7bdf5a95dfff7f2b99cc0541`, `0xe34fa7c2c84c31e847bc4256c73c4105305150c1`, `0xeeacf719dbbbe9a2a06c076ab6bd5beb08e8c41d`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `morpho_blue.liquidate:0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda` | 59 | 59 | 1770328.97 | 77613.59 |
| `morpho_blue.liquidate:0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836` | 57 | 57 | 926483.49 | 40618.27 |
| `morpho_blue.liquidate:0x7dc02ff6c536b1d49d7fba770438d79f5bd1f1c78884629b7d1aaee19675782b` | 78 | 78 | 153924.86 | 19511.60 |
| `morpho_blue.liquidate:0xe458a501c1103ca3b256f2bcb45d223263fb34b6349d82675494ce3a94ce1327` | 31 | 31 | 40052.10 | 5077.03 |

Sampled txs: `0x744bbc60044cde7818bad22125f3ee37f3586a1a955c92c9fa4e0ac8bae29a4a`, `0x2e4f0553ce90579e728402ef048187859e9e0a0ac7fb5663ae421828cc706d5f`, `0x689a853da7e35424c230a900677d8b1d3b221a4e769cea9398bff4e04b3dbe83`, `0xec65c18a541da8402aa0a8570ffafbc66d2f46c2a30fbc79a8dca19650a462ff`, `0x1480a833d142a6c38c561a1533bb3ce843a91642da740a0fb7d952f8537e4373`, `0x3123d163c83b64ce22a863a3cd32987f1cda888c2c299af3177389dc2e6bb5b8`, `0x96a9df1eb68c6a477ab25ed2b3b0584c5b4631c11244c338e0fbcbb90ee7a2fc`, `0x4af4e370c84e112c0c45b0365bd2e2deee0325ea34503a3468fef274bb0f243f`, `0x105d7a3016cbff25c0644ea7b75df323347bbc91363974680d14a23e0caef0dd`, `0x47c306943f86cf2a74aeb44eadd4b8f080afe3f254094fa5883c2433cd6f8d9c`.

## Taker 11: ethereum 0xf000042d2b48921c234f15d167e7874f594f303e

Operator: unclustered; event count 3; nominal gross $140706.33; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0x2059c8bc2d4e71d6e7ab7af11b34ca4e63f58a22`, `0x5bb887b5e9348924af3b954f0753ae20d8799c36`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `morpho_blue.liquidate:0xe7e9694b754c4d4f7e21faf7223f6fa71abaeb10296a4c43a54a7977149687d2` | 1 | 1 | 2386112.79 | 104610.37 |
| `morpho_blue.liquidate:0xc2c53d2b868e163da71de14a5113cc2743fc9b5ad7488334720ed2846566a8f6` | 1 | 1 | 428655.37 | 18792.82 |
| `morpho_blue.liquidate:0xea4bfb18df0ee6bffb7b3f0270899a8adb92ab6b684709634c8276128813cfd4` | 1 | 1 | 394676.24 | 17303.13 |

Sampled txs: `0x844c540c47cf50504872e06cc00c2da7194d896590df0b578ab93e2ff5ede2cf`, `0xe25d65b568e61c2413809ab4591c0db6d42c03c57c202d351b675743fb932075`, `0x7dea97bdbd6de3858859432357d93f79d6cc49a76762c4beeae867de96f07e63`.

Positive flash evidence: `0x7dea97bdbd6de3858859432357d93f79d6cc49a76762c4beeae867de96f07e63` FlashLoan(address,address,uint256), `0x844c540c47cf50504872e06cc00c2da7194d896590df0b578ab93e2ff5ede2cf` FlashLoan(address,address,uint256), `0xe25d65b568e61c2413809ab4591c0db6d42c03c57c202d351b675743fb932075` FlashLoan(address,address,uint256).

## Taker 12: ethereum 0x789e3f3cad898948759402b347d1d1e007f93f79

Operator: unclustered; event count 4; nominal gross $136136.86; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0x59f369c0cf069cb67c28c593a6ab44f3aa43c479`, `0x6d4e355b97606bf2ed385cfa6c10304a7b07e86d`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `aave_v3.liquidation:0xdac17f958d2ee523a2206206994597c13d831ec7/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | 1 | 1 | 2721653.40 | 136082.67 |
| `aave_v3.liquidation:0x2260fac5e5542a773aa44fbcfedf7c193bc2c599/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | 1 | 1 | 950.61 | 47.53 |
| `aave_v3.liquidation:0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | 2 | 2 | 133.12 | 6.66 |

Sampled txs: `0x01cba12fc78efe18caa0f4d2496d62d330141b8fda433b4cff31a168063a2b47`, `0x285157d0da154393a1265ab62ac61b4c981387e8f0f8fb3cdbf60943b09cedb9`, `0x303c2338b5ce97654ba0c6c46b9368eeca31c5ffb8d96a71ac5e1670bc90c913`, `0xeb94c5e74a1e153b850f5149f313c9b9f995f25506fb20eb096d268ea78af422`.

## Taker 13: base 0x6109bc698ffd20de8114ec4c9291052a6ceff9f7

Operator: unclustered; event count 92; nominal gross $108638.79; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0x3c29a270dc6c52673e9f59d47636a7069575cba9`, `0xe34fa7c2c84c31e847bc4256c73c4105305150c1`, `0xeeacf719dbbbe9a2a06c076ab6bd5beb08e8c41d`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `morpho_blue.liquidate:0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836` | 72 | 72 | 2337107.26 | 102461.91 |
| `morpho_blue.liquidate:0x7dc02ff6c536b1d49d7fba770438d79f5bd1f1c78884629b7d1aaee19675782b` | 20 | 20 | 48728.79 | 6176.89 |

Sampled txs: `0x6b0dd1a22f3806c276a143ab7c0953d206cc2b61775a9262743f115c75869e4b`, `0x557b7dd47a38fdfb31fbd6e7a5a5a3dc10da0610604fdd1ab18d6e3517b8cc3f`, `0xb288463574a97b5d904f6cda45b6628b061ab04713705e112424e6370654e0e7`, `0xa37bf52efe5cda7fac3447484032ddcf0ad65fe2dc7bb54a346bd7c3966f668a`.

## Taker 14: base 0xe4d797c8a24d531c8ee3e21d6cfa9605eae54e4b

Operator: unclustered; event count 14; nominal gross $106343.55; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0x92e83da3bda8bf72aa855fb587f626d1b2770190`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `morpho_blue.liquidate:0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836` | 14 | 14 | 2425645.69 | 106343.55 |

Sampled txs: `0xa3a853d9a0755b051d00a01b0be9e814f3080a1a1ce9434a7493f6fbfa1a4891`.

Positive flash evidence: `0xa3a853d9a0755b051d00a01b0be9e814f3080a1a1ce9434a7493f6fbfa1a4891` FlashLoan(address,address,uint256).

## Taker 15: ethereum 0xf28307728ad7b7449e9b020a5c24292ce5f871ca

Operator: unclustered; event count 61; nominal gross $104349.33; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0xbe6bbb45c0be7cba3087d345fab9a71ac88af200`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `aave_v3.liquidation:0xdac17f958d2ee523a2206206994597c13d831ec7/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | 24 | 24 | 1224980.36 | 61249.02 |
| `aave_v3.liquidation:0xdac17f958d2ee523a2206206994597c13d831ec7/0xdac17f958d2ee523a2206206994597c13d831ec7` | 1 | 1 | 389276.26 | 17517.43 |
| `aave_v3.liquidation:0xdac17f958d2ee523a2206206994597c13d831ec7/0x2260fac5e5542a773aa44fbcfedf7c193bc2c599` | 8 | 8 | 197882.01 | 9894.10 |
| `aave_v3.liquidation:0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | 18 | 18 | 166021.26 | 8301.06 |
| `aave_v3.liquidation:0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48/0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0` | 1 | 1 | 71182.67 | 4270.96 |
| `aave_v3.liquidation:0x40d16fc0246ad3160ccc09b8d0d3a2cd28ae6c2f/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | 2 | 2 | 21173.75 | 1058.69 |
| `aave_v3.liquidation:0xdc035d45d973e3ec169d2276ddab16f1e407384f/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | 1 | 1 | 14922.45 | 746.12 |
| `aave_v3.liquidation:0x4c9edd5852cd905f086c759e8383e09bff1e68b3/0x2260fac5e5542a773aa44fbcfedf7c193bc2c599` | 2 | 2 | 10505.65 | 525.28 |
| `aave_v3.liquidation:0x4c9edd5852cd905f086c759e8383e09bff1e68b3/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | 2 | 2 | 8633.28 | 431.66 |
| `aave_v3.liquidation:0xdac17f958d2ee523a2206206994597c13d831ec7/0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0` | 1 | 1 | 4999.45 | 299.97 |
| `aave_v3.liquidation:0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48/0x68749665ff8d2d112fa859aa293f07a622782f38` | 1 | 1 | 917.22 | 55.03 |

Sampled txs: `0x36b8103e2d5d0147f3b781ead7c8501434f7da07fb188424d6117c56259c2858`, `0xbafbcea28d45824dc082da34c37eabb61265a0cfe5616ef3146588e7ffaaa7e4`, `0x56b092a7fce6f2a3023b9908093dba98159613c0c734ef02747a9f582d3f46b1`, `0x77893ad89da1ed2a0f594057dd4629cad3ea8f7d2dd7e1818015c4ed90c86b74`, `0x6192c13abb896b1b3e3c8a83e8fa8e525290f7430da55d3031ddb50fdfbe2a15`, `0x6784a9c3e57574b8cf78ae5fa92a4f8cf8b5f29c6c9deb4a14b3fdd87c768190`, `0x43efad7da9ac682ecd3af09af708fdc1f77f8d585416ae048963a973014f19be`, `0xa12f25c56f1824c0b26f25394bcae9fe64e28b848e12f87fa2b4a7003629915b`, `0x75157b48098dcf8ff0b9a5ae84d4bd8e9e9ff5926d932cfca2c88855ad47e817`, `0xdd23a2490ab4737104ece8e7008bdc3918c8dd72a05018d4b3b4044661c14cd9`.

Positive flash evidence: `0x36b8103e2d5d0147f3b781ead7c8501434f7da07fb188424d6117c56259c2858` FlashLoan(address,address,uint256), `0x43efad7da9ac682ecd3af09af708fdc1f77f8d585416ae048963a973014f19be` FlashLoan(address,address,uint256), `0x43efad7da9ac682ecd3af09af708fdc1f77f8d585416ae048963a973014f19be` FlashLoan(address,address,uint256,uint256), `0x56b092a7fce6f2a3023b9908093dba98159613c0c734ef02747a9f582d3f46b1` FlashLoan(address,address,uint256), `0x56b092a7fce6f2a3023b9908093dba98159613c0c734ef02747a9f582d3f46b1` FlashLoan(address,address,uint256,uint256), `0x6192c13abb896b1b3e3c8a83e8fa8e525290f7430da55d3031ddb50fdfbe2a15` FlashLoan(address,address,uint256), `0x6784a9c3e57574b8cf78ae5fa92a4f8cf8b5f29c6c9deb4a14b3fdd87c768190` FlashLoan(address,address,uint256), `0x75157b48098dcf8ff0b9a5ae84d4bd8e9e9ff5926d932cfca2c88855ad47e817` FlashLoan(address,address,uint256), `0x75157b48098dcf8ff0b9a5ae84d4bd8e9e9ff5926d932cfca2c88855ad47e817` FlashLoan(address,address,uint256,uint256), `0x77893ad89da1ed2a0f594057dd4629cad3ea8f7d2dd7e1818015c4ed90c86b74` FlashLoan(address,address,uint256), `0xa12f25c56f1824c0b26f25394bcae9fe64e28b848e12f87fa2b4a7003629915b` FlashLoan(address,address,uint256), `0xbafbcea28d45824dc082da34c37eabb61265a0cfe5616ef3146588e7ffaaa7e4` FlashLoan(address,address,uint256), `0xdd23a2490ab4737104ece8e7008bdc3918c8dd72a05018d4b3b4044661c14cd9` FlashLoan(address,address,uint256).

## Taker 16: hyperevm 0x9466140c8781e253fe426c87ac17ccba500140ff

Operator: unclustered; event count 2; nominal gross $70008.22; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0x6c246928f16528b0defd0891573da0c02cfc14f7`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `morpho_blue.liquidate_hyperevm:0x78f6b57d825ef01a5dc496ad1f426a6375c685047d07a30cd07ac5107ffc7976` | 2 | 2 | 552287.10 | 70008.22 |

Sampled txs: `0x6497ef6d73859aa20423a2145dc914a033993cf132accfbeec5e9b1c220b699b`, `0xd47d3df91eb3ca24014d9a7331badf00c51dad7cb733751b1e83697b532023c8`.

Positive flash evidence: `0x6497ef6d73859aa20423a2145dc914a033993cf132accfbeec5e9b1c220b699b` FlashLoan(address,address,uint256), `0xd47d3df91eb3ca24014d9a7331badf00c51dad7cb733751b1e83697b532023c8` FlashLoan(address,address,uint256).

