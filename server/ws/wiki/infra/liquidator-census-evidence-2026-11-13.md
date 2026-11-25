---
type: infra
chains: [base, arbitrum, ethereum, bsc, polygon, avalanche, optimism, hyperevm, elysium]
protocols: [aave_v3, morpho_blue, compound_v3, moonwell, compound_v2, exactly, llamalend, sparklend, revert_lend]
author: researcher/gpt-6.1-sol
updated: 2026-11-13
---
# Liquidator census evidence, 2026-11-13 snapshot

Parent: `infra/liquidator-census.md`. Raw snapshot, valuations and script artifacts: `scratch/census-4170/`. Counts and gross here have the same incomplete-history/current-incentive limits as the parent. Wallet identifiers describe addresses only.

## Source coverage query

`ledger query --json "SELECT source_id,chain,min(block),max(block),min(ts),max(ts),count(*) FROM events WHERE kind LIKE 'liquidation%' AND ts BETWEEN 1791983406 AND 1794575406 GROUP BY source_id,chain LIMIT 50"`

| source | chain | n | block span | timestamp span |
|---|---|---:|---|---|
| aave_v3.liquidation | arbitrum | 253 | 518442186–523779862 | 1793018567–1794549397 |
| aave_v3.liquidation | base | 254 | 53157528–56795172 | 1793104403–1794549410 |
| aave_v3.liquidation | ethereum | 391 | 26284068–26404354 | 1793104367–1794552551 |
| compound_v2.liquidate | ethereum | 150 | 26308396–26404093 | 1793397299–1794549419 |
| compound_v3.absorb | arbitrum | 7 | 519465260–522484062 | 1793306530–1794174967 |
| compound_v3.absorb | base | 51 | 53265204–56760394 | 1793319755–1794542454 |
| compound_v3.absorb | ethereum | 26 | 26300861–26404092 | 1793306555–1794549407 |
| compound_v3.buy_collateral | arbitrum | 8 | 519465260–522484833 | 1793306530–1794175160 |
| compound_v3.buy_collateral | base | 36 | 53265238–56760394 | 1793319823–1794542454 |
| compound_v3.buy_collateral | ethereum | 34 | 26300861–26404092 | 1793306555–1794549407 |
| exactly.liquidate | base | 145 | 53799563–56795250 | 1793950288–1794549425 |
| llamalend.liquidate | ethereum | 6 | 26311229–26398645 | 1793431427–1794483911 |
| moonwell_core.liquidate_borrow | base | 408 | 53247461–56899934 | 1793284269–1794570362 |
| moonwell_core.liquidate_borrow_ext | base | 74 | 53406622–56866937 | 1793602591–1794563763 |
| moonwell_eth.liquidate | ethereum | 2 | 26349643–26385463 | 1793893883–1794325163 |
| morpho_blue.liquidate | base | 9461 | 53147160–56903958 | 1793083667–1794571167 |
| morpho_blue.liquidate | ethereum | 233 | 26284880–26405342 | 1793114135–1794564467 |
| morpho_blue.liquidate_hyperevm | hyperevm | 41 | 50393819–51121525 | 1793824474–1794540365 |
| revert_lend.liquidate | arbitrum | 14 | 519793431–523760363 | 1793394462–1794543930 |
| sparklend.liquidation | ethereum | 44 | 26303336–26404074 | 1793336387–1794549191 |

## Full taker evidence

- `infra/liquidator-census-evidence-2026-11-13-takers-1.md`: 1, 2, 3, 4, 5.
- `infra/liquidator-census-evidence-2026-11-13-takers-2.md`: 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16.
- `infra/liquidator-census-evidence-2026-11-13-takers-3.md`: 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29.
- `infra/liquidator-census-evidence-2026-11-13-takers-4.md`: 30.

## First-five funding links (native transfers only)

ERC20 first receipts were discarded as first-gas evidence; they can be unsolicited spam or flash loans. This table contains signer → funder1 → funder2 only; no links through gateways are used.

| taker | signer | first gas funder / tx | funder hop 2 / tx | boundary |
|---|---|---|---|---|
| 1 | `0xdaf673a781884c9702800d0cb75bbd857cefaace` | `0x714d75577883d54072b888ce9e6d80278f9fa741` / `0x91c7e815439490988c2d056c06ed4dbd713a361f32d426001fee25aa45934551` | `0x2466a85341e3a7f24bde0d7e1e055b15617fef91` / `0x738ce7c1633a71095a63a89893bb367a9ac9882be50a4d65b9ab00135ba18318` | bounded pages |
| 1 | `0x01379ecc41e900c971e16ea8a8edbbab2aadc88d` | `0x714d75577883d54072b888ce9e6d80278f9fa741` / `0xfcfebe1583ddf310e4f6a17e064e6826b87ed6970e42025d6ea358698e1f6c7e` | `0x2466a85341e3a7f24bde0d7e1e055b15617fef91` / `0x738ce7c1633a71095a63a89893bb367a9ac9882be50a4d65b9ab00135ba18318` | bounded pages |
| 1 | `0xc0b414fce9dabc71cfb3825985ac8ab4795f9f85` | `0x714d75577883d54072b888ce9e6d80278f9fa741` / `0x106a4e9429f037ed5cc0346eb9492b57c6d501ef9053739ae1bc986d1192ea27` | `0x2466a85341e3a7f24bde0d7e1e055b15617fef91` / `0x738ce7c1633a71095a63a89893bb367a9ac9882be50a4d65b9ab00135ba18318` | bounded pages |
| 1 | `0x24c04aae27cb252787175fa317b24d7e9b29a2a9` | `0x714d75577883d54072b888ce9e6d80278f9fa741` / `0xf562bf9ec7331330f9e2e4f70848982fcb9971458790cb429a7d88d30f50afaa` | `0x2466a85341e3a7f24bde0d7e1e055b15617fef91` / `0x738ce7c1633a71095a63a89893bb367a9ac9882be50a4d65b9ab00135ba18318` | bounded pages |
| 1 | `0xbe0ece6d7dcab9112daaffb640aac80e3d62d3da` | `0x714d75577883d54072b888ce9e6d80278f9fa741` / `0x9480fd20d9b11947c64c943d1d46a80e62fc81d13479238e8efab1a32b0532a9` | `0x2466a85341e3a7f24bde0d7e1e055b15617fef91` / `0x738ce7c1633a71095a63a89893bb367a9ac9882be50a4d65b9ab00135ba18318` | bounded pages |
| 1 | `0xd02b5853557e8f221727162540d49ecd4b4bb225` | `0x714d75577883d54072b888ce9e6d80278f9fa741` / `0x659a6724ce34781bc9735c187462a494662923fe2a1825487a2087d6975a51d7` | `0x2466a85341e3a7f24bde0d7e1e055b15617fef91` / `0x738ce7c1633a71095a63a89893bb367a9ac9882be50a4d65b9ab00135ba18318` | bounded pages |
| 2 | `0x3038400cb371731a6dc4882920c5a274cc9ba923` | `0x5d47603902a8cadbf3337abbc6df8f67a251d821` / `0xda4357684d1a02da4582d9953733e53cf63e2b4583d57064443f520576f427bd` | `0xf7858da8a6617f7c6d0ff2bcafdb6d2eedf64840` / `0x5b6a329822597b8e58ddff6283576d1c96aa0ff411cca4d2b1cbffe83563a975` | bounded pages |
| 2 | `0x68e856ba729ba60d71c615257d002d97678aa3c9` | `0x5d47603902a8cadbf3337abbc6df8f67a251d821` / `0x09cadba075094fe87f089b795875e460d0e8d45a7735df1325b2a9d4181c671a` | `0xf7858da8a6617f7c6d0ff2bcafdb6d2eedf64840` / `0x5b6a329822597b8e58ddff6283576d1c96aa0ff411cca4d2b1cbffe83563a975` | bounded pages |
| 2 | `0xe476367785bc9dcec25d415201e191d22f75f286` | `0x5d47603902a8cadbf3337abbc6df8f67a251d821` / `0x09b341efc5d94a8fb095bcb2dfb2cb0e6725bbaa1e393a78deb85bfd081cae6c` | `0xf7858da8a6617f7c6d0ff2bcafdb6d2eedf64840` / `0x5b6a329822597b8e58ddff6283576d1c96aa0ff411cca4d2b1cbffe83563a975` | bounded pages |
| 2 | `0x7e8f8451dab2c0170d93f95f544f00ed9f733523` | `0x5d47603902a8cadbf3337abbc6df8f67a251d821` / `0x82ecde5f5e6fa57096df8a93abff21fdff21196f903daf32b1797b86fc0ef689` | `0xf7858da8a6617f7c6d0ff2bcafdb6d2eedf64840` / `0x5b6a329822597b8e58ddff6283576d1c96aa0ff411cca4d2b1cbffe83563a975` | bounded pages |
| 2 | `0x8d64d775efe48c75d5dff5b3e7f58c6f384a1e05` | `0x5d47603902a8cadbf3337abbc6df8f67a251d821` / `0x7a759895d0b670e5ae86a774c3c048f682375baeda6a9c66ea9c9f240d6e70bb` | `0xf7858da8a6617f7c6d0ff2bcafdb6d2eedf64840` / `0x5b6a329822597b8e58ddff6283576d1c96aa0ff411cca4d2b1cbffe83563a975` | bounded pages |
| 2 | `0x6cdc112445e144c6e928d6eeecfd4fe00019e737` | `0x5d47603902a8cadbf3337abbc6df8f67a251d821` / `0x96bbfade6f7bbc766b64aef7bd8d7b1daf84a7fe3c0bd9841d32678e77140ab6` | `0xf7858da8a6617f7c6d0ff2bcafdb6d2eedf64840` / `0x5b6a329822597b8e58ddff6283576d1c96aa0ff411cca4d2b1cbffe83563a975` | bounded pages |
| 3 | `0x2ff82bd25ccc62981db54e01b05bd22ab95af1c0` | `0xd694da172d0b3f4389a4ea909134d47fcd3acf6b` / `0x381d56ed4eaa0660eda7e4a38708c5ecc9faadc8d90bf7c93d129ef0d63e2fe3` | `0x2cff890f0378a11913b6129b2e97417a2c302680` / `0x7363b4d06557826f6a0ed3e286d18e344d4d4302f4e08fcfca21d8b009b2d572` | none observed |
| 3 | `0xe29b3e21f98ba8bb9ab645c78ffee1e0e3f12ad0` | `0xd694da172d0b3f4389a4ea909134d47fcd3acf6b` / `0xcab0a81b3efb47511815246f13a6ea876ae930a11bfaadc7b2499e29aec0ecf0` | `0x2cff890f0378a11913b6129b2e97417a2c302680` / `0x7363b4d06557826f6a0ed3e286d18e344d4d4302f4e08fcfca21d8b009b2d572` | none observed |
| 3 | `0x5168763828548020027232e15668d1cfebbe982f` | `0x2ff82bd25ccc62981db54e01b05bd22ab95af1c0` / `0xd2778b3f72b3a413fe5918ee865e6fa5de8de340bb39b2f225276f7987daa79c` | `0xd694da172d0b3f4389a4ea909134d47fcd3acf6b` / `0x381d56ed4eaa0660eda7e4a38708c5ecc9faadc8d90bf7c93d129ef0d63e2fe3` | none observed |
| 3 | `0xd4d6a5d9e188a8d26a0a9360b02ffce681b06cb6` | `0x2ff82bd25ccc62981db54e01b05bd22ab95af1c0` / `0x2709f3c2250fe084abca2c502f8afd8f3b9b1eb26c91b6d22c2c86778c54ff0a` | `0xd694da172d0b3f4389a4ea909134d47fcd3acf6b` / `0x381d56ed4eaa0660eda7e4a38708c5ecc9faadc8d90bf7c93d129ef0d63e2fe3` | none observed |
| 3 | `0x9fbe93b1694c8bc435bfe47fc10249da6cc61cc8` | `0x5168763828548020027232e15668d1cfebbe982f` / `0x46d45b38be7913cc720e54ffa661dcda3ad5205a4486c64a4b929fd7b76601f4` | `0x2ff82bd25ccc62981db54e01b05bd22ab95af1c0` / `0xd2778b3f72b3a413fe5918ee865e6fa5de8de340bb39b2f225276f7987daa79c` | none observed |
| 4 | `0xb7cd3d37611168f2548ae9587cb884c60fa9befa` | `0xd971c15f273abf0e788121353ad7a1811c648cca` / `0x766563bf3e93a891265bc776e06fcb24bfa103645c2adb10b90a286e5f62930e` | not followed | stop at funder1 (488 recipients) |
| 4 | `0x2e592ee3240ffa60b5d0ce2596e22fc79214e897` | `0xd971c15f273abf0e788121353ad7a1811c648cca` / `0x766563bf3e93a891265bc776e06fcb24bfa103645c2adb10b90a286e5f62930e` | not followed | stop at funder1 (488 recipients) |
| 4 | `0x35666ffafa8bb97f65df762d1c6147c3f84288b3` | `0xd971c15f273abf0e788121353ad7a1811c648cca` / `0xea0129e11809555d1f408bb750de1cfefbe720fedfcd4055bcf555e9866b9be9` | not followed | stop at funder1 (488 recipients) |
| 4 | `0x9e3a908da5155b6f6863fcecc87750cb97fdc39b` | `0xd971c15f273abf0e788121353ad7a1811c648cca` / `0xea0129e11809555d1f408bb750de1cfefbe720fedfcd4055bcf555e9866b9be9` | not followed | stop at funder1 (488 recipients) |
| 4 | `0xb857ec5d3453d3d7852575216626519ab2d92e2a` | `0x5dc11035e58c2151998a5a76c3f603091b7cdbb2` / `0x045c84e056ad555d62d01f58f6a95c6442c407cc57c4a5ccd1823dd22d7b6e05` | `0x23d7424ec21a119c4718c27e2b4634c37a56766b` / `0xde9fc73dd4c004944d62b9cafe684d83b163c9397c8c1f2cc377dc9b56d4e6d4` | none observed |
| 4 | `0x12ae878b0fd27bff78a43301ab6517c293d10fbb` | `0x5dc11035e58c2151998a5a76c3f603091b7cdbb2` / `0xb6a10a268ef87c973645e0b94f8320c94658c7d0c7e09c2a05c83b77da8222c4` | `0x23d7424ec21a119c4718c27e2b4634c37a56766b` / `0xde9fc73dd4c004944d62b9cafe684d83b163c9397c8c1f2cc377dc9b56d4e6d4` | none observed |
| 4 | `0xb583b3603dc71c2dac067f2af32817341f438585` | `0x5dc11035e58c2151998a5a76c3f603091b7cdbb2` / `0x045c84e056ad555d62d01f58f6a95c6442c407cc57c4a5ccd1823dd22d7b6e05` | `0x23d7424ec21a119c4718c27e2b4634c37a56766b` / `0xde9fc73dd4c004944d62b9cafe684d83b163c9397c8c1f2cc377dc9b56d4e6d4` | none observed |
| 5 | `0x176efd46471f43923742b6a6959828b29d061326` | `0x697c6cd9b242c736bcd3abce138b0242afe4445d` / `0xeef4b40f2f45357faea3f0f053c24109ab02973ef9f1b6dc371bb59162c7b717` | `0xbefa750ed568cc84970eb4fd506af4ff599c42d0` / `0x2f266945981e5667d0b38faaa4c9796fcab33907aa92d87e88224e8d55c54170` | none observed |
| 5 | `0x92ebd0557307bfad6d9d14199de1de96fdd16497` | `0x4862a1254405b5e50761ef9ccde9bfdb831ccf0b` / `0xcff551f1251f51f15dc7586098d6009f5122c31e46b84b9c2abe7ecc8388ab3f` | `0xbefa750ed568cc84970eb4fd506af4ff599c42d0` / `0x0191e76a187f6470a458d4252fbe44b6d1bb8021f0491b0899edd0d7ee5b58c6` | none observed |
| 5 | `0x6dc667b1fd4a3954a819e7ff1995a6f226d5011b` | `0x4862a1254405b5e50761ef9ccde9bfdb831ccf0b` / `0x17daca79ab82e44942ff878cd4cca145e085cf3eb291eecf2be21661cdec7bee` | `0xbefa750ed568cc84970eb4fd506af4ff599c42d0` / `0x0191e76a187f6470a458d4252fbe44b6d1bb8021f0491b0899edd0d7ee5b58c6` | none observed |
| 5 | `0xd79df6e9b324acb1c197c2ee1591a017eb938616` | `0x4862a1254405b5e50761ef9ccde9bfdb831ccf0b` / `0x92597269a9123f32bfd1d91d93903d400825ea49df6bd877e52918fa60a40ff4` | `0xbefa750ed568cc84970eb4fd506af4ff599c42d0` / `0x0191e76a187f6470a458d4252fbe44b6d1bb8021f0491b0899edd0d7ee5b58c6` | none observed |
| 5 | `0x4862a1254405b5e50761ef9ccde9bfdb831ccf0b` | `0xbefa750ed568cc84970eb4fd506af4ff599c42d0` / `0x0191e76a187f6470a458d4252fbe44b6d1bb8021f0491b0899edd0d7ee5b58c6` | not followed | stop at funder1 (715 recipients) |

## Evidenced sibling contracts with ledger activity

| operator | sibling | funder | transfer hash | indexed actions | events |
|---|---|---|---|---|---:|
| op_bc034 | `0x2ff82bd25ccc62981db54e01b05bd22ab95af1c0` | `0xd694da172d0b3f4389a4ea909134d47fcd3acf6b` | `0x381d56ed4eaa0660eda7e4a38708c5ecc9faadc8d90bf7c93d129ef0d63e2fe3` | compound_v2 liquidations/buyCollateral | 1 |
| op_bc034 | `0x74edc79fea13bdf1f7841570227127cec493bdd9` | `0xd694da172d0b3f4389a4ea909134d47fcd3acf6b` | `0x6cac565d8e3b641a001cedd8d57ef724da6ed77c9d4d89b7d74f520f2dbbfdcf` | compound_v2, compound_v3, llamalend, morpho_blue liquidations/buyCollateral | 15 |
| op_d128 | `0xd12810b19b596347a3afac206d3ca65d08594b3f` | `0x5dc11035e58c2151998a5a76c3f603091b7cdbb2` | `0xdb7866f41bd36aa9c89d09c49fb6415a76db2396c507491d15bf309c53e9e6cd` | aave_v3, compound_v3, morpho_blue liquidations/buyCollateral | 724 |
| op_ed989 | `0xb8a26b3c70af05df1d3693f97091c10e4b174b94` | `0x4862a1254405b5e50761ef9ccde9bfdb831ccf0b` | `0x96deba5ddea21831c44e54895171b77d0e36a617cc7d3db3469116aa998af6b7` | morpho_blue liquidations/buyCollateral | 107 |
| op_ed989 | `0xed989ee258ecc93769a8478c9973667b17462dfe` | `0x4862a1254405b5e50761ef9ccde9bfdb831ccf0b` | `0x51acb89408751aa0e9fc2a970ddeda6a5f02c45a46107cb4576ea9115d16c28d` | morpho_blue liquidations/buyCollateral | 452 |
| op_ed989 | `0xdb590332fec316e7fbc81cc72b6af9ba3ddb0dc9` | `0x697c6cd9b242c736bcd3abce138b0242afe4445d` | `0x37ab4a704103cf4742d98f45a90e524e010823d03a943fc0cc08f95dec06b455` | morpho_blue liquidations/buyCollateral | 1 |
| op_ed989 | `0xdb61a25516b4480df393d7bfe2d8e33fdaaf079a` | `0x697c6cd9b242c736bcd3abce138b0242afe4445d` | `0x94d8d3e34940c866160b87780df9a11346594b0cbf24c0d6bac72f2098ccacdb` | morpho_blue liquidations/buyCollateral | 377 |

## Payout follow-up boundaries

#1/#2 WETH recipient `0x51c72848c68a965f66fa7a88855f9f7784502a7f`: raw history has uncompleted native/internal pagination, so outward hop1/hop2 and shared-gateway exclusion are not finished. Do not merge any further addresses through it yet. #3 native recipient `0xdadb0d80178819f2319190d340ce9a924f783711` equals block26403468.coinbase. This is a builder payment, NOT an operator payout; it also has350 native recipients in first1,000. Stop; its own funder was read in an initial exploratory response and discarded. #5 recipient `0x9af4392e4f4575d3155fec6efb34e878b04384c4` has5 native recipients and complete pagination: `697c6cd9…` via tx `0xf1d2e8522d56af3bcc994e4db567a1c328fc183d9a50baaee4315d0bfcc76e07`, `4862a125…` via `0xe378035aeb38c2b1eecc18c355360e0403b518302fadabc3dc68d318beae5916`, plus three unclassified recipients `276938ed…`, `234950df…`, `4d33fd99…`. Its initial funder `39b1bc83…` is incoming, not an outward payout hop. D128 payout path goes through23d7424e to5dc11035 as linked in the parent. No direction reversal is treated as a payout link.
