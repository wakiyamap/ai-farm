---
type: infra
chains: [base, arbitrum, ethereum, bsc, polygon, avalanche, optimism, hyperevm, elysium]
protocols: [aave_v3, morpho_blue, compound_v3, moonwell, compound_v2, exactly, llamalend, sparklend, revert_lend]
author: researcher/gpt-6.1-sol
updated: 2026-11-13
---
# Census taker evidence part3

Index and limitations: `infra/liquidator-census-evidence-2026-11-13.md`.

## Taker 17: base 0x7372825fd055d2ed613283419af846a53cdcbfb6

Operator: unclustered; event count 25; nominal gross $69914.63; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0x0e9729b4b792ae6a6032565e9782668ef9b8f05e`, `0x1a9cf9713b79c2e3663e91d574ecdc8fc7d1c2d8`, `0x36633e2bb3af873b356933a8972cf791cd717572`, `0x71ddd2967c319d5c1cccb853f1289be3b4bcc816`, `0x78c57d30fa6efe0cb150e38a979b55c3a66a61f1`, `0x8e6d903802b6579800379340f4a885199278b5b8`, `0xa77eafd1307aadf56936e5c61a9d9bf47b23e69b`, `0xb10dc8bc2846afa3b0e79486dfc41f4b757e399e`, `0xb67b043de186137bf11c3ed1a3b6c9236acea6fd`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `morpho_blue.liquidate:0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836` | 11 | 11 | 1473925.31 | 64618.86 |
| `morpho_blue.liquidate:0xd4a903dc6d949519060c7707f9604fdc9772c046e05c2e3a8fce0bd7196e4109` | 11 | 11 | 32501.30 | 4119.88 |
| `morpho_blue.liquidate:0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda` | 1 | 1 | 26050.19 | 1142.08 |
| `morpho_blue.liquidate:0xd7520ad198b497b6eb75bc690268f4597630dbc12e305e9d4105843bab36e41d` | 1 | 1 | 153.94 | 19.51 |
| `morpho_blue.liquidate:0x13c42741a359ac4a8aa8287d2be109dcf28344484f91185f9a79bd5a805a55ae` | 1 | 1 | 326.25 | 14.30 |

Sampled txs: `0x741b863927f2d738744d00fe7d40c6a58b3b34de9f0afa1f45e2f900076aed7c`, `0xbabcaa041202e4815b6c8124d02f1be2e8e03b2e7223a4e0127e221fb1436be4`, `0x3babcd51559b11c51fe9f25f487a7948d8988b1611ebc099ff31a4be4203ab68`, `0xd75c925addf1c6533177643a7ebf6ea70b85f727cdb61ca8e1ccde7895ac7a3b`, `0x785d58c3a0b4155a75e5d7dab690fb009aa0c5a7c99ee7ebaaff2166842882ab`, `0x792a75d15979c7cd3b523f03b84591ce586dbe4e481a9e7f31514800e4d8a023`, `0x3d3fc60938bb0070cdfa07639381d748c4d90903ec8468fe7c6c828ce4f8cdc4`, `0xf457241d7d7ab5c5fb3646d7a80520235be0408e684b990ea6217d9d9572c231`, `0x01b8e21079a5452fb223b46d28a8412bd9fa9fc922b22cd79943228500afef12`, `0xbfcfebdd79fef64d42cbde989c8bb57204ba7e2fa2df99e77cfc35bf3bc9b9ef`.

## Taker 18: base 0xbd0dd817c608e552d5f1ae701ab6c4da4fb00005

Operator: unclustered; event count 52; nominal gross $61047.26; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0x01f973383af228622836a466227adc931ca463f6`, `0x3c29a270dc6c52673e9f59d47636a7069575cba9`, `0x6159e0ab35170e5df0b02d81af2d6f985f2b4746`, `0x92e83da3bda8bf72aa855fb587f626d1b2770190`, `0xdcd7d20b14c9d6214418a93dead5f55c270bd6f1`, `0xe34fa7c2c84c31e847bc4256c73c4105305150c1`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `morpho_blue.liquidate:0xd4a903dc6d949519060c7707f9604fdc9772c046e05c2e3a8fce0bd7196e4109` | 36 | 36 | 433310.41 | 54926.67 |
| `morpho_blue.liquidate:0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836` | 7 | 7 | 90634.10 | 3973.52 |
| `morpho_blue.liquidate:0xd7520ad198b497b6eb75bc690268f4597630dbc12e305e9d4105843bab36e41d` | 6 | 6 | 9752.28 | 1236.20 |
| `morpho_blue.liquidate:0x73527ddd796e6d4f48387adaae36f6f3d49d606d7f2a15eb0c931416a58875d8` | 3 | 3 | 7185.70 | 910.86 |

Sampled txs: `0xc555c55c9f9f2b60f0327c6e90cb1d5c5ddd1d59d490f48f7d84e1257800324b`, `0xfb3d690719a83f4381c73635385815b68409f6dc328ef898ea5b4d14f0da3cb5`, `0xade57b28fd1f16ea7d302476ef5bb72089759afefe41e488b692490ed4a46a20`, `0x7cca25c5e21f2c72ff96a03f442cf8a0fc6652c4c622b68c42a7188cd8f93a71`, `0x1c2340d408419741c1568ff519ef3f2c325c927185929e5a0843ed8ccd69c716`, `0xfe19e8fd015b833430f97cfc79ae19b988c4c769f07c3ce64f5dc57784632020`, `0x27bfaa6713754ccac40e71e09120290c30bcecf6d660439992d4a8ca8a0f0cd1`, `0x5c9167d0823afa35691ac0ce26220e15229a82a8dcb364a526bde78770878660`, `0x388ef9fe47cd485ed28157468d573647912792eee53da79b28f93511fec9dc13`, `0xcd1b41524a4f846ef5998bb384b724ed092c00336bab9704be47dac117152d30`.

Positive flash evidence: `0x1c2340d408419741c1568ff519ef3f2c325c927185929e5a0843ed8ccd69c716` FlashLoan(address,address,uint256), `0x27bfaa6713754ccac40e71e09120290c30bcecf6d660439992d4a8ca8a0f0cd1` FlashLoan(address,address,uint256), `0x388ef9fe47cd485ed28157468d573647912792eee53da79b28f93511fec9dc13` FlashLoan(address,address,uint256), `0x5c9167d0823afa35691ac0ce26220e15229a82a8dcb364a526bde78770878660` FlashLoan(address,address,uint256), `0x7cca25c5e21f2c72ff96a03f442cf8a0fc6652c4c622b68c42a7188cd8f93a71` FlashLoan(address,address,uint256), `0xade57b28fd1f16ea7d302476ef5bb72089759afefe41e488b692490ed4a46a20` FlashLoan(address,address,uint256), `0xc555c55c9f9f2b60f0327c6e90cb1d5c5ddd1d59d490f48f7d84e1257800324b` FlashLoan(address,address,uint256), `0xcd1b41524a4f846ef5998bb384b724ed092c00336bab9704be47dac117152d30` FlashLoan(address,address,uint256), `0xfb3d690719a83f4381c73635385815b68409f6dc328ef898ea5b4d14f0da3cb5` FlashLoan(address,address,uint256), `0xfe19e8fd015b833430f97cfc79ae19b988c4c769f07c3ce64f5dc57784632020` FlashLoan(address,address,uint256).

## Taker 19: ethereum 0xbde3e91f09a9489f1b53eaa21eb32c89b2fd5c64

Operator: unclustered; event count 17; nominal gross $52486.40; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0x3c1557217d1438fbde9539f5332a3e13b7edc287`, `0x473bac73a83220429c222fae5afbf8cdc4a213e1`, `0x6a3ac06b4a3432d580faed8cd1e1b426030f5444`, `0x7606b0118c0e94e7ad9967ead8d2b2981803de7f`, `0xf87a11ee8ab057952fa83b1de64811e3c4f40709`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `compound_v3.buy_collateral:0xc3d688b66703497daa19211eedff47f25384cdc3/0x2260fac5e5542a773aa44fbcfedf7c193bc2c599` | 2 | 2 | 312052.32 | 19918.23 |
| `compound_v3.buy_collateral:0xa17581a9e3356d9a858b789d68b4d866e593ae94/0xdac17f958d2ee523a2206206994597c13d831ec7` | 1 | 1 | 255888.37 | 9280.93 |
| `aave_v3.liquidation:0xdac17f958d2ee523a2206206994597c13d831ec7/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | 4 | 4 | 179466.89 | 8973.34 |
| `compound_v3.buy_collateral:0x3afdc9bca9213a35503b077a6072f3d0d5ab0840/0x2260fac5e5542a773aa44fbcfedf7c193bc2c599` | 1 | 1 | 139844.15 | 8926.22 |
| `aave_v3.liquidation:0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48/0x2260fac5e5542a773aa44fbcfedf7c193bc2c599` | 1 | 1 | 52234.22 | 2611.71 |
| `aave_v3.liquidation:0xdac17f958d2ee523a2206206994597c13d831ec7/0x2260fac5e5542a773aa44fbcfedf7c193bc2c599` | 2 | 2 | 19916.89 | 995.84 |
| `compound_v3.buy_collateral:0xc3d688b66703497daa19211eedff47f25384cdc3/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | 1 | 1 | 21815.70 | 956.43 |
| `aave_v3.liquidation:0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | 2 | 2 | 8695.32 | 434.77 |
| `aave_v3.liquidation:0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48/0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0` | 2 | 2 | 3800.79 | 228.05 |
| `aave_v3.liquidation:0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48/0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9` | 1 | 1 | 2145.05 | 160.88 |

Sampled txs: `0xeb272f44de37a854fc8cfedaf19fb592084ff681666b4e3001d8b24ee2662829`, `0x2a19798eeed2f8a9d86e24583109303f865c8e0872f5eae35004579107a18633`, `0xefbad3143bf07a3cf1116f9cc2b4ff3c5147d89c1bc3867a2c373765aa26c16c`, `0xd9994fea36a57fcb52d4c31c2325e394a79cef8af42e10514277d3961fc5593b`, `0x3f7109f2873b3082e8a7df7bf226e71afd3ce09f1227a3e1a07de61fc084c9fa`, `0xa0eb265b244db1b14dd813161f819a184f3bfa0e88558257615c8df068b4e79a`, `0x3ee0d46e64a8112b9b618691e009f14c824718a777e130069539c74c40f88a43`, `0x1c1e159f08994c25905a2b9209fc6dbe219b52358071215e770f00d3132507d2`.

Positive flash evidence: `0x1c1e159f08994c25905a2b9209fc6dbe219b52358071215e770f00d3132507d2` FlashLoan(address,address,uint256), `0x2a19798eeed2f8a9d86e24583109303f865c8e0872f5eae35004579107a18633` FlashLoan(address,address,uint256,uint256), `0x3ee0d46e64a8112b9b618691e009f14c824718a777e130069539c74c40f88a43` FlashLoan(address,address,uint256), `0x3f7109f2873b3082e8a7df7bf226e71afd3ce09f1227a3e1a07de61fc084c9fa` FlashLoan(address,address,uint256), `0xa0eb265b244db1b14dd813161f819a184f3bfa0e88558257615c8df068b4e79a` FlashLoan(address,address,uint256,uint256), `0xd9994fea36a57fcb52d4c31c2325e394a79cef8af42e10514277d3961fc5593b` FlashLoan(address,address,uint256), `0xeb272f44de37a854fc8cfedaf19fb592084ff681666b4e3001d8b24ee2662829` FlashLoan(address,address,uint256), `0xefbad3143bf07a3cf1116f9cc2b4ff3c5147d89c1bc3867a2c373765aa26c16c` FlashLoan(address,address,uint256).

## Taker 20: base 0x3e9a355fa4305370cc64c14a8f03cb27a11c3c86

Operator: unclustered; event count 12; nominal gross $49010.38; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0x7ed54f78b96ed04410c05c94a6bb97013ab3de7a`, `0x7effb011c81601e98c13a9719e882f6ae8abfd1c`, `0x7f19292cba7ff89d43b4a6c2003d8a2b4b2f7b05`, `0x7f2424e72cd4e6625e35a75666753a752886799f`, `0x7f334ae8a5b08fe69d821c129824c22e43daf995`, `0x81faeb47760758be86aad964d3a1c50bd918eecd`, `0x8220535bc731cef62a9140a9ea51b483411d1ed8`, `0x822ad5b7307648eeb633f06b4820fdec81ad3886`, `0x8258fb418ddca054471ec0356b3688823e84e4f9`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `morpho_blue.liquidate:0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836` | 12 | 12 | 1117903.54 | 49010.38 |

Sampled txs: `0x4572a0e964c3115859892eb45c7bf10ca52935f8932676c45f716429093a2f08`, `0x6acc97869952456f5a1b2919d454dc7c3e492a567bf5a12099b9c54fb34f9d5c`, `0x83789bf5f02707fb79118194eb557cac01fb40ffafd1302028abb4ecd44137b9`, `0xea825134a647b9e04b0421dd7360c66d058bc6e557a7047ae18c7133560f2fc7`, `0xaf67af00217bf60b2b7564ab56ce8b15a6565ec8b737dc5c3d640221b0055c51`, `0xd656260bf3499260a63b82978022d4ff58c41c0454249eea818c2a5abc3c9406`, `0xf2a6faa63d8c818958cd27acf1be3368ce1f21dc06c2bcb417b56f7df83115ec`, `0x55b08533f4c53b63b79c7b0dc997eb76c824cf50bc5bf354014759529e6c643d`, `0x5c73884e6fc3533f5c0f531d4109c602d3846e7570c46467588a4210a9362482`, `0x9ee9ee71c54a3f2930550294cb466f5896aa90b5eb86cfb3cb4ad0bf90b08280`.

## Taker 21: ethereum 0x557d0f989621387892342c390bec9cc7c74d5d89

Operator: unclustered; event count 4; nominal gross $48540.01; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0xb18ee2312d3b91d58c1bc3b8febccffc87a3f23d`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `aave_v3.liquidation:0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48/0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9` | 1 | 1 | 565766.23 | 42432.47 |
| `aave_v3.liquidation:0xdac17f958d2ee523a2206206994597c13d831ec7/0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9` | 1 | 1 | 77685.80 | 5826.43 |
| `aave_v3.liquidation:0xdac17f958d2ee523a2206206994597c13d831ec7/0x2260fac5e5542a773aa44fbcfedf7c193bc2c599` | 1 | 1 | 3314.91 | 165.75 |
| `aave_v3.liquidation:0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48/0x8236a87084f8b84306f72007f36f2618a5634494` | 1 | 1 | 1357.24 | 115.37 |

Sampled txs: `0x4edf732d272412134fd7fb15891f32e4fc11cb009752799faebad422565afbf1`, `0x4a48624165ead398fd38ee2b920a1dfb181855a724cc2dc329f334cc4d853abc`, `0x3757fae6e9bcef5b1fcc506e0ffa616e7ae66ac135a1d3aaf9a082f2cd021836`, `0x2a288df37ea9502d6f1fbf8c871ebe781fdc977e2fba5cf7f533555ea6612fb9`.

Positive flash evidence: `0x3757fae6e9bcef5b1fcc506e0ffa616e7ae66ac135a1d3aaf9a082f2cd021836` FlashLoan(address,address,uint256).

## Taker 22: base 0xd8413bf7e7782b536abdeebbcb9e7c4fc481e2e7

Operator: unclustered; event count 255; nominal gross $42820.10; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0x18f815a663f0b26cb6a86f2687b2525b7868faf6`, `0x255435d3f49b9c7094a60646a7f8f1b8bd483bd9`, `0x6159e0ab35170e5df0b02d81af2d6f985f2b4746`, `0xe34fa7c2c84c31e847bc4256c73c4105305150c1`, `0xeeacf719dbbbe9a2a06c076ab6bd5beb08e8c41d`, `0xf966cf17edb87c6991f554547e3aeb6ab18e667b`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `morpho_blue.liquidate:0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836` | 136 | 136 | 662951.96 | 29064.70 |
| `morpho_blue.liquidate:0x09276541cfecb6920a80679a1deced4dde3ae64bf5fc2c9c1f9c21e0c152e1a5` | 46 | 46 | 49319.59 | 6251.78 |
| `morpho_blue.liquidate:0x7dc02ff6c536b1d49d7fba770438d79f5bd1f1c78884629b7d1aaee19675782b` | 21 | 21 | 28425.12 | 3603.18 |
| `aave_v3.liquidation:0x833589fcd6edb6e08f4c7c32d4f71b54bda02913/0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf` | 8 | 8 | 39190.86 | 2351.45 |
| `aave_v3.liquidation:0x833589fcd6edb6e08f4c7c32d4f71b54bda02913/0x4200000000000000000000000000000000000006` | 11 | 11 | 23639.06 | 1181.95 |
| `morpho_blue.liquidate:0xd4a903dc6d949519060c7707f9604fdc9772c046e05c2e3a8fce0bd7196e4109` | 20 | 20 | 970.26 | 122.99 |
| `aave_v3.liquidation:0x833589fcd6edb6e08f4c7c32d4f71b54bda02913/0x04c0599ae5a44757c0af6f9ec3b93da8976c150a` | 1 | 1 | 1573.47 | 118.01 |
| `morpho_blue.liquidate:0x6a331b22b56c9c0ee32a1a7d6f852d2c682ea8b27a1b0f99a9c484a37a951eb7` | 1 | 1 | 905.45 | 67.11 |
| `morpho_blue.liquidate:0x4440abd9eff38ebf76b8f64c074682acef8c89e77555075478a7582883206604` | 1 | 1 | 634.21 | 47.00 |
| `morpho_blue.liquidate:0x0ca10126f6c94cbd9cf0a48cc9516ae5e3dec5aa68303e6d988ee37c5149bf0d` | 10 | 10 | 160.90 | 11.92 |

Sampled txs: `0xaaaad48bd61806f79418d076032dd47954216372e5482d603cd51a92bb1e04da`, `0xbefbd8366ba8236dddd7169b7ee1b5ae42151b797716fe09fa40cf3264a5437c`, `0x0136c71967c877aeeea5257b157121d8ee423ec0c2c36dad660a7030a4d42cc5`, `0x2bcab5d2eb3e7f42d1e69e7f53e928d5844873a9734b1e40af0291045a33faa6`, `0x96b4483306c417384808c9d1193f46d1b6540652133ece7f9ec7afc022f1153a`, `0xf75275ed9640cb25d4e2be7337a59c399c3e9dabc34d4e6ff8a034991fa135c1`, `0x7b9dd01d8c2f887e5315db01bdb773a5caa82cddc511726dd12d5c4a407400f7`, `0xb139b454e92157863f52df8e9ef975d9d2e20ce680565790bdd491a1a665567a`, `0x3994a7ddbdc066d8da640497520a19cde70549c7136fd28314a63152c6e1a151`, `0x8c13bfd8a5533f475f46421df5bca56f1697b8a8eb15fd5f9de2cd961c330f67`.

## Taker 23: base 0x2ea89fc4b65ed6fa0494b6c9b15403bf1137907f

Operator: unclustered; event count 23; nominal gross $41185.15; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0xdcd7d20b14c9d6214418a93dead5f55c270bd6f1`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `morpho_blue.liquidate:0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836` | 2 | 2 | 630521.83 | 27642.92 |
| `morpho_blue.liquidate:0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda` | 20 | 20 | 280396.51 | 12292.96 |
| `morpho_blue.liquidate:0x73527ddd796e6d4f48387adaae36f6f3d49d606d7f2a15eb0c931416a58875d8` | 1 | 1 | 9855.39 | 1249.27 |

Sampled txs: `0xa9e5eed93e6270ad660b3401f2cda63dc066befc22d48cc91244ea981dc456fd`, `0xaffdefca691f0ed9419c8577aa8922ed1f62aec66d46ba7b5053dec0715bed4b`, `0xa96ae10bcdc1f4cc5e6a23e0508b3f1234b50c0cefe9df8513f5869333d36c17`.

## Taker 24: hyperevm 0x281354062fa932086890a6bbf7dff7d0a67d220f

Operator: unclustered; event count 1; nominal gross $32109.46; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0x6c246928f16528b0defd0891573da0c02cfc14f7`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `morpho_blue.liquidate_hyperevm:0xd7d38220652d19c87099c3b23de9a70a1893620a050c635d1a94bd947c9c59a8` | 1 | 1 | 433244.99 | 32109.46 |

Sampled txs: `0x42e86f9809439c83791333becab02b647a45caefeb01fc20aecaa4cdcb75b5b7`.

## Taker 25: base 0x65f14ba7984512c9aa552f133c248075b488b9ee

Operator: unclustered; event count 1; nominal gross $31516.13; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0x6159e0ab35170e5df0b02d81af2d6f985f2b4746`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `compound_v3.buy_collateral:0xb125e6687d4313864e53df431d5425969c15eb2f/0x4200000000000000000000000000000000000006` | 1 | 1 | 1019021.64 | 31516.13 |

Sampled txs: `0xb092daab30d68e69f49677b453650b3b5641a7756b8de1552630cc3f46605110`.

## Taker 26: base 0x83557c6d286553ad103bb08f0c04ec25724c0e06

Operator: unclustered; event count 34; nominal gross $30817.88; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0x09bc8c6b13a63139f6f87b7fc8aa416e46b0aae9`, `0x0f646659914da93edd34954d2da278e0e81e62b4`, `0x25bda62f1cc0323e93b311815afbd414868b8c85`, `0x7cbfc51582312c2872d2934b9ff31eb0928e8dc5`, `0x999b4e5acb84ea1fc58250c4ba45f23279db9e2a`, `0x9b1a9c9810facc59e27b3a221a166feee326cab8`, `0xacc91eaf149a47d796a5b64356f70238a2c06aa5`, `0xc5f988a60071ea0409a420a6721d5670c742a6d2`, `0xf13ef9d0f371d0de64027d5f54cff9e51ec0518e`, `0xf42b27ce8959f7b96188aaa50c89aad2ce971298`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `morpho_blue.liquidate:0x0ca10126f6c94cbd9cf0a48cc9516ae5e3dec5aa68303e6d988ee37c5149bf0d` | 34 | 34 | 415818.08 | 30817.88 |

Sampled txs: `0x1356ab9f86da730eeead1bcede76f6bf0b0298c6f56143687d9e763290d89676`, `0x472659e77b17a586bae12f3d31154972ac67a798bfb5ea706b0b2467ce3324dc`, `0xdc938cf5acd03d8544822d5771f3fd6199e6e622174edb13186ce8d8f2c5a388`, `0xe2e860d71a8fbad209a5c10cdb9e6b23c7658fb82384895312fb99e88edcf3f9`, `0xb9c631255a1c10d4bb8f792a506bbd2b176b4d0f36702dd78450243c59fe9296`, `0x1881fb1781ca2bd14ce2c8fc5182d70c21078d74aa053e99ba070cdf8c38e080`, `0x6d58871e60288c01bd575eee80f98f1f57500950dcf5a6649c14979fbce45fee`, `0x263687773402dedf6d4aed646950f70ef00aa4f8122fd0daf82170f4ce0972cf`, `0x672e6a4d586e006997f522757d8afa812b75508d36725ca91cb823f4826dcf72`, `0xbf7a53dce53960ac2e893da85c6af2e9fcb703ff36487f485d299877f1f07084`.

## Taker 27: base 0xecd48b7dc7862f5d529121f6e5d6ed4b0774f2ca

Operator: unclustered; event count 18; nominal gross $30537.74; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0x0e87512f1947794c4046a15610ea0cef94b7c642`, `0x398484012093a0b66c58fc7ae07c13c9d13d5c70`, `0x3c466815a0842df894e69366d14ac314bb85d613`, `0x7bc88c62637eb21d360bfc7891d334caad789781`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `morpho_blue.liquidate:0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836` | 6 | 6 | 641479.22 | 28123.31 |
| `morpho_blue.liquidate:0x0ca10126f6c94cbd9cf0a48cc9516ae5e3dec5aa68303e6d988ee37c5149bf0d` | 10 | 10 | 32577.07 | 2414.41 |
| `morpho_blue.liquidate:0xd4a903dc6d949519060c7707f9604fdc9772c046e05c2e3a8fce0bd7196e4109` | 1 | 1 | 0.10 | 0.01 |
| `morpho_blue.liquidate:0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda` | 1 | 1 | 0.10 | 0.00 |

Sampled txs: `0xff694ead70c57a33cb8f14a41f0218846e1a41fc72772d490b76aebf34926047`, `0x42615412f2e19a7e56570a2845c510aafa807e23926bb707d2bddf6945e638a1`, `0x45a9d8dfaa6b3594ba8b7350706e9291ea0b968140553f4a68c71b3e07264925`, `0x3d89a71ff7054f1a0358d4dac240f6b4485b933999c56b2dff01adadc3ab36a5`, `0xb928d3c094fa01b2b3bd989cac0e3eab170bd2df651ff250bc1d86d1f5d55ab7`, `0x71d3106b3ebecbdd45003c82a534d1920fab5ad2c7e6c5f4b480a6be828814be`, `0x8d629fdcfdad4e047cf398e67b61b69f6e69cf5b68e229088e37b2ab115730e7`, `0x06d33842cdd0367376a4ee6c439205e64aebb8de4e0307be7a348a1ad78bd41c`, `0x1916bdb39a59e45a152ab5c3a912ed6a9b8ff9afd2b4d6300f4df0190b38381b`, `0x8de091a81dbef4dd7970914b7ad33f52463362e8b6aff183bf612e81a37ee209`.

## Taker 28: ethereum 0x9d5b90baf46e622b348e49b9e2ac872c5bbf5f7d

Operator: unclustered; event count 14; nominal gross $30349.07; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0x11911dc62260eb702b39dbafd0c14e388ba64f17`, `0x3b569d2678f5f46360f6c29a20fd8b641d7f6195`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `aave_v3.liquidation:0xdac17f958d2ee523a2206206994597c13d831ec7/0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0` | 1 | 1 | 224242.57 | 13454.55 |
| `aave_v3.liquidation:0xdac17f958d2ee523a2206206994597c13d831ec7/0x2260fac5e5542a773aa44fbcfedf7c193bc2c599` | 4 | 4 | 170563.84 | 8528.19 |
| `aave_v3.liquidation:0xdac17f958d2ee523a2206206994597c13d831ec7/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | 3 | 3 | 82341.05 | 4117.05 |
| `aave_v3.liquidation:0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48/0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | 2 | 2 | 47907.78 | 2395.39 |
| `aave_v3.liquidation:0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48/0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0` | 1 | 1 | 24165.56 | 1449.93 |
| `aave_v3.liquidation:0x40d16fc0246ad3160ccc09b8d0d3a2cd28ae6c2f/0x2260fac5e5542a773aa44fbcfedf7c193bc2c599` | 1 | 1 | 7028.25 | 351.41 |
| `morpho_blue.liquidate:0x64d65c9a2d91c36d56fbc42d69e979335320169b3df63bf92789e2c8883fcc64` | 1 | 1 | 773.86 | 33.93 |
| `aave_v3.liquidation:0xdac17f958d2ee523a2206206994597c13d831ec7/0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf` | 1 | 1 | 248.13 | 18.61 |

Sampled txs: `0xf8f169623037dc655f25c0cfb64fee4ecf65ca3d9c1643c564302a4cfb4ae2e8`, `0x1005e3078176fc81cad8dc6950440fb0ff7956bb5934c133bb0521af2c158346`.

Positive flash evidence: `0x1005e3078176fc81cad8dc6950440fb0ff7956bb5934c133bb0521af2c158346` FlashLoan(address,address,uint256), `0xf8f169623037dc655f25c0cfb64fee4ecf65ca3d9c1643c564302a4cfb4ae2e8` FlashLoan(address,address,uint256).

## Taker 29: base 0x0268e896b6b1b06f58b4828551e895856914f828

Operator: unclustered; event count 151; nominal gross $28664.87; slowness unmeasured.

Sample tx senders (Atlas senders are relayers, not solver owners): `0x00befef6df0aa38e024f964097b2bf1e7163f597`, `0x6ff2d3bc60a5548ac1030592a7ea4e666b911e0e`, `0x8a98c9542dbb99ab1c584fede70fe1d2479ad775`, `0x905f171b861b0ec8d914641aeb45c291de315d9d`, `0x99f171a1042119c520bd09a1aff24fba3ca0af9b`.

| protocol / full market key | events | priced | repaid USD | nominal gross USD |
|---|---:|---:|---:|---:|
| `morpho_blue.liquidate:0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836` | 88 | 88 | 483166.93 | 21182.68 |
| `morpho_blue.liquidate:0xd4a903dc6d949519060c7707f9604fdc9772c046e05c2e3a8fce0bd7196e4109` | 30 | 30 | 53550.08 | 6788.04 |
| `morpho_blue.liquidate:0x0ca10126f6c94cbd9cf0a48cc9516ae5e3dec5aa68303e6d988ee37c5149bf0d` | 29 | 29 | 5255.63 | 389.51 |
| `morpho_blue.liquidate:0x7dc02ff6c536b1d49d7fba770438d79f5bd1f1c78884629b7d1aaee19675782b` | 3 | 3 | 2323.30 | 294.50 |
| `morpho_blue.liquidate:0xd7520ad198b497b6eb75bc690268f4597630dbc12e305e9d4105843bab36e41d` | 1 | 1 | 79.94 | 10.13 |

Sampled txs: `0x146cbb3a01691a7c81f2faac778adafeefdcdf8e27b2c614983106fa679c8c67`, `0x81966881e107a65d838f47f8e14064c58d6d94d7e659c8ace0c28cc6c95cd65c`, `0xce05f10a422180a7aa8befebe02cdce7dbd80a6fe58574213b3d18a30fee7e37`, `0x4d1ce749dfb56117c9738cee5104111ec2058342f70d9a86dc285af0e7eaf565`, `0x63126b76e119d30abae4db374ffddfcbb502e5d2dacbb57ca37ac9b476aaa95e`, `0x6834c5587d035b7cf014e2a948cbdc75af62d1924b0cf875dfe0b4e1f8e3bd87`, `0x2ab5b54b4e5e20048108b1fe932a7e4be0df9ab6962a171cc851b8a42e12c424`, `0x440cfab149f1b6724e5417da3da7d9d1b224946b217307f41f0cb785e63146c2`, `0x7e8784f8965e1d11a15ae66b64b2385e1b8316ff53e17af42c52a3c8c9b24054`, `0xc726dbec6a95948e4985148333287970c737ab18c4ed9cc10673c41e2218b69d`.

Positive flash evidence: `0x63126b76e119d30abae4db374ffddfcbb502e5d2dacbb57ca37ac9b476aaa95e` FlashLoan(address,address,uint256), `0x6834c5587d035b7cf014e2a948cbdc75af62d1924b0cf875dfe0b4e1f8e3bd87` FlashLoan(address,address,uint256), `0xce05f10a422180a7aa8befebe02cdce7dbd80a6fe58574213b3d18a30fee7e37` FlashLoan(address,address,uint256).

