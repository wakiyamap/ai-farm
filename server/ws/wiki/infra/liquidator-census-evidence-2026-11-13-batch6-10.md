---
type: infra
chains: [base, ethereum]
protocols: [morpho_blue, aave_v3]
author: researcher/gpt-6.1-sol
updated: 2026-11-13
---
# Census ranks 6–10: funding, payouts, and eligibility correction

**Conclusion:** rank8 belongs to ed989; ranks6,7,10 remain separate executor groups. Do not merge through funding gateways, builders, or Atlas. The four previously called slow Base Morpho takers are fast in the repeated historical-state sample. This is a continuation of the preserved 13:10 UTC snapshot, not a fresh 30-day export.

Run `a33d4ea2f557458aa48b619bade24e21`, researcher-codex, 2026-11-13. Raw relay responses and scripts: `scratch/census-a33d/`. Original rankings and event valuations: `scratch/census-4170/`. No mainnet transactions.

## Funding and shared-executor evidence

Atlas solver signers are decoded from SolverOperation.from using the existing validated layout. Relayer tx.from is excluded. Every listed signer called the same executor directly or as an Atlas solver; full signer→sample-tx mapping is `signers.json`.

| rank | executor | sampled signer | execution tx | first native funder | funding tx |
|---|---|---|---|---|---|
|6|`0x29452e8332912533130fb708984722d92184284f`|`0xcdb56817e135d30561ff6b4f05e088fa2c9695c8`|`0x090811cf760717c0a0047793d5a37a06dd035003a054eac723253a1b810ce639`|`0xd152f549545093347a162dce210e7293f1452150`|`0x690e60d383f01ed17680a0626756d0134fd1c767d133f4d3f06417d1e6eabd69`|
|6|`0x29452e8332912533130fb708984722d92184284f`|`0xc95049b67979436a5ea577f451aeddefeedde5ad`|`0xc4ed6a30e064854da7aa5afc955b207ca84f63c8bd0f306d1d331c624b4ed0a2`|`0xd152f549545093347a162dce210e7293f1452150`|`0x690e60d383f01ed17680a0626756d0134fd1c767d133f4d3f06417d1e6eabd69`|
|6|`0x29452e8332912533130fb708984722d92184284f`|`0x644e2a8e46dea6434a71d0801f3173210693289d`|`0xe19146f363cf460d40f0ae7c824b1da41611e049428a0e4e4f7b3e91bf083e82`|`0xd152f549545093347a162dce210e7293f1452150`|`0x690e60d383f01ed17680a0626756d0134fd1c767d133f4d3f06417d1e6eabd69`|
|6|`0x29452e8332912533130fb708984722d92184284f`|`0x3a752524753d8260078a4a4ee071df80997e6fc2`|`0x37c554a104fe58f9a51e50b3cdb7df1afa0283457468c62b40d33d0d702212d9`|`0xd152f549545093347a162dce210e7293f1452150`|`0x690e60d383f01ed17680a0626756d0134fd1c767d133f4d3f06417d1e6eabd69`|
|6|`0x29452e8332912533130fb708984722d92184284f`|`0xc61cf79a5c588bb4169a198987e5e5908010c606`|`0x8b518c66b86b61df8fc85d5fb1512183361d0c914db1d0c8969597724514046e`|`0xd152f549545093347a162dce210e7293f1452150`|`0x690e60d383f01ed17680a0626756d0134fd1c767d133f4d3f06417d1e6eabd69`|
|6|`0x29452e8332912533130fb708984722d92184284f`|`0xe0dd0f41a876d80a579b49dd5d459988404847a8`|`0xfd4f39eeb92f8663ccdd1c61f66c4fe765b16eed64496210fdc4341e14d0ab9c`|`0xd152f549545093347a162dce210e7293f1452150`|`0x690e60d383f01ed17680a0626756d0134fd1c767d133f4d3f06417d1e6eabd69`|
|6|`0x29452e8332912533130fb708984722d92184284f`|`0x13c49b02b1ec455953de777bf5ac0e5adadfa234`|`0x075c7830578eeaabf16d3f8e91b625163cbca5a83de5c4082e4965ff46dd25ca`|`0xd152f549545093347a162dce210e7293f1452150`|`0x690e60d383f01ed17680a0626756d0134fd1c767d133f4d3f06417d1e6eabd69`|
|7|`0xe14c836bd3b0be1d4b52ac4d4f00c163926ff069`|`0xbe6bbb45c0be7cba3087d345fab9a71ac88af200`|`0x156c9bbf441e9c37c72affcc6eafa9a947f96db882628c4c7e644575a03297f2`|`0xc618990a58638b9adbacc2dcd342b9afdc5e8864`|`0x6c037a424dc18686762e05177b029384d6b0c14ee683286f6e4d1e8b7dfa0e78`|
|8|`0x91d682699cf4dbfb8a5ea4e860bf29f76ede99cd`|`0x1ecc10ebeb6851a5644931f69b454a3aba8b7cf9`|`0xd6075cf3959c0824668dfdc67a1a3a3d526dd87120f3a39139ed763a777f2d2c`|`0x4862a1254405b5e50761ef9ccde9bfdb831ccf0b`|`0xd67a81b895cd97a12b574ab981d341694c3348bc8d1c1a33ad9d1f1983d8ce90`|
|8|`0x91d682699cf4dbfb8a5ea4e860bf29f76ede99cd`|`0xfe5d0060ccef9a031396128725554fe670b2846b`|`0x28742a9b17b25b6893687f49d1c130599652745d0e3fa6c06759a0f325842f23`|`0x49cb8c4cc78b7523e5d68ffd81ce3037a3ee2be3`|`0x57d9bd2f0d42c34ec3d3f48023a11c28aacba0d77f8432199d6797d1241cbb4f`|
|8|`0x91d682699cf4dbfb8a5ea4e860bf29f76ede99cd`|`0x55264f509c389d5592510daa2429a20b640491e9`|`0x3f7afb77cb774c7fea8b6b332fde72756b09ba32fb678f3a9ef8dc91e8f2b69f`|`0x697c6cd9b242c736bcd3abce138b0242afe4445d`|`0xf4235d31e815415f74f6e3662a473a65fa7ea80cbb8f6496e04a857c88beabc5`|
|8|`0x91d682699cf4dbfb8a5ea4e860bf29f76ede99cd`|`0x12f8b13b0407fb57ff8c59e73c4c76326b216621`|`0x2787b5fc8763b0e464cb8053015cf8b42261e0da812166e5545ec9fccb2ed37c`|`0x49cb8c4cc78b7523e5d68ffd81ce3037a3ee2be3`|`0x57d9bd2f0d42c34ec3d3f48023a11c28aacba0d77f8432199d6797d1241cbb4f`|
|8|`0x91d682699cf4dbfb8a5ea4e860bf29f76ede99cd`|`0xb902c5e09239da7200232f71bedda0a873118833`|`0x5b5b8d2bfb47b56234cb939e476efa99f16b608251b85225a05b145180ae21d7`|`0x49cb8c4cc78b7523e5d68ffd81ce3037a3ee2be3`|`0x57d9bd2f0d42c34ec3d3f48023a11c28aacba0d77f8432199d6797d1241cbb4f`|
|8|`0x91d682699cf4dbfb8a5ea4e860bf29f76ede99cd`|`0xaee9f10244ba05e1bfc4dc368c6ce9be5347c78c`|`0x5ff631f63cf1993faab9201f284f81969c464cfb9ba75be5f2521afec0efff5e`|`0x49cb8c4cc78b7523e5d68ffd81ce3037a3ee2be3`|`0x57d9bd2f0d42c34ec3d3f48023a11c28aacba0d77f8432199d6797d1241cbb4f`|
|9|`0xdb61a25516b4480df393d7bfe2d8e33fdaaf079a`|already linked to ed989|see prior census evidence|`697c6cd9…`|`0x94d8d3e34940c866160b87780df9a11346594b0cbf24c0d6bac72f2098ccacdb`|
|10|`0x5ab72cb36cdc5a17b637b55dbbf41f2f349b3fea`|`0xe7f416f98f752e3e3ba7c557481461d2a6fd7867`|`0x105d7a3016cbff25c0644ea7b75df323347bbc91363974680d14a23e0caef0dd`|`0x3ad7bca01c48d70925d1c8a52500457e67f674a3`|`0x55ee032acf920fbaa62596f87e4754edbcf207c4e5851a126619c595ef6faeb6`|
|10|`0x5ab72cb36cdc5a17b637b55dbbf41f2f349b3fea`|`0xb266193cfbdb27482eea2dc38ae4bf745dfecd5e`|`0x96a9df1eb68c6a477ab25ed2b3b0584c5b4631c11244c338e0fbcbb90ee7a2fc`|`0x3ad7bca01c48d70925d1c8a52500457e67f674a3`|`0xd295b643b2decf723012f4337682fe4b50395a724022fe6701be830466763c9b`|
|10|`0x5ab72cb36cdc5a17b637b55dbbf41f2f349b3fea`|`0xc2d03a4eb8b289b7aff8fbf9392a808338f159f9`|`0x47c306943f86cf2a74aeb44eadd4b8f080afe3f254094fa5883c2433cd6f8d9c`|`0x3ad7bca01c48d70925d1c8a52500457e67f674a3`|`0x6b6a8f015765ee30f4e06e03188c0fb8a7d9a8917f9977dae404b1b2fe2b6d96`|

## Gateway screening and two-hop limits

Counts are distinct native recipients in ascending-history pages, stopping once >200. A pageKey means a lower bound; it is not a completed census. Never merge or follow upstream through a gateway.

| chain / funder | native recipients | pages | remaining page | decision |
|---|---:|---:|---|---|
|`base:0x3ad7bca01c48d70925d1c8a52500457e67f674a3`|308|8|True|gateway; stop|
|`base:0x4862a1254405b5e50761ef9ccde9bfdb831ccf0b`|22|1|False|private candidate|
|`base:0x49cb8c4cc78b7523e5d68ffd81ce3037a3ee2be3`|451|1|False|gateway; stop|
|`base:0x697c6cd9b242c736bcd3abce138b0242afe4445d`|38|1|False|private candidate|
|`ethereum:0xc618990a58638b9adbacc2dcd342b9afdc5e8864`|890|1|True|gateway; stop|
|`ethereum:0xd152f549545093347a162dce210e7293f1452150`|980|1|True|gateway; stop|
|`base:0xbefa750ed568cc84970eb4fd506af4ff599c42d0`|715|1|True|gateway; stop|
|`base:0xd42e77f66b864024c6d83292a62a579cfdebba68`|5|1|False|discarded beyond gateway|

The initial 5-page screen of `3ad7bca0…` had only158 recipients but a pageKey. Continuing to page8 found308, so it is a gateway. Its funder `d42e77f6…` was read prematurely; discard that edge and do not use it to group operators. Names of gateway owners were not researched.

## Rank8 → ed989, independent direct links

`4862a125…` (22 native recipients, fully paginated) and `697c6cd9…` (38, fully paginated) were already linked to rank5/rank9. Rank8 solver signers receive direct native funding from them, not just from multisender `49cb8c4c…`. The latter is a451-recipient gateway and is excluded.

| private funder | rank8 signer | direct funding tx |
|---|---|---|
|`0x4862a1254405b5e50761ef9ccde9bfdb831ccf0b`|`0x1ecc10ebeb6851a5644931f69b454a3aba8b7cf9`|`0xd67a81b895cd97a12b574ab981d341694c3348bc8d1c1a33ad9d1f1983d8ce90`|
|`0x4862a1254405b5e50761ef9ccde9bfdb831ccf0b`|`0x55264f509c389d5592510daa2429a20b640491e9`|`0xe593fdf16d09b9de25f2e7cb0df1c01da92b59e314f63df55309490b1a9e120a`|
|`0x697c6cd9b242c736bcd3abce138b0242afe4445d`|`0x1ecc10ebeb6851a5644931f69b454a3aba8b7cf9`|`0x3ed9d8f587a72abd1315d5f9d6fede935f30df1706969ff2f5a37739ef813904`|
|`0x697c6cd9b242c736bcd3abce138b0242afe4445d`|`0xfe5d0060ccef9a031396128725554fe670b2846b`|`0x3f55ebbce74a499c94d358796713133eacb24e6bfd56ad304482f37837bc2832`|
|`0x697c6cd9b242c736bcd3abce138b0242afe4445d`|`0x55264f509c389d5592510daa2429a20b640491e9`|`0xf4235d31e815415f74f6e3662a473a65fa7ea80cbb8f6496e04a857c88beabc5`|
|`0x697c6cd9b242c736bcd3abce138b0242afe4445d`|`0x12f8b13b0407fb57ff8c59e73c4c76326b216621`|`0x6066fcfbc03d5308cc6892228d47545eada38a1cb61e8b79739960051bf28dfb`|
|`0x697c6cd9b242c736bcd3abce138b0242afe4445d`|`0xb902c5e09239da7200232f71bedda0a873118833`|`0xd8c4fe0b07d4aaf8951b211902313628dd8c10389d92d41846e25765a3702cc2`|
|`0x697c6cd9b242c736bcd3abce138b0242afe4445d`|`0xaee9f10244ba05e1bfc4dc368c6ce9be5347c78c`|`0xccda2e25084d8ebe9c4181f0c09b5e0054e5a15defd6f8a73bcc1e25805bc1ff`|

ed989 now includes snapshot ranks5,8,9,43,387: 1,504 events, $13,836,461.16 repaid, $867,676.07 nominal gross. These are coverage-limited gross proxies, not retained profit.

## Payout direction

Rank6 sends native surplus back to its execution senders, while large native transfers to `dadb0d80…` and `4838b106…` are builder payments. Rank7 has WETH withdrawals to its sole sampled sender. Rank8 and rank10 native transfers to `1c6ec845…` are Atlas execution-environment bids, not operator payouts.

| rank | executor → recipient | payout tx | asset / amount |
|---|---|---|---|
|6|`0x29452e8332912533130fb708984722d92184284f` → `0xcdb56817e135d30561ff6b4f05e088fa2c9695c8`|`0x06e1b3a6d5f553edd4fd99f4ae235fd0779e42b3c03167aac6823bd18f8f2f5f`|ETH / 0.006243600664194777|
|6|`0x29452e8332912533130fb708984722d92184284f` → `0xc95049b67979436a5ea577f451aeddefeedde5ad`|`0xc4ed6a30e064854da7aa5afc955b207ca84f63c8bd0f306d1d331c624b4ed0a2`|ETH / 0.000675821547402717|
|6|`0x29452e8332912533130fb708984722d92184284f` → `0x644e2a8e46dea6434a71d0801f3173210693289d`|`0xe19146f363cf460d40f0ae7c824b1da41611e049428a0e4e4f7b3e91bf083e82`|ETH / 0.000121732413983883|
|6|`0x29452e8332912533130fb708984722d92184284f` → `0x3a752524753d8260078a4a4ee071df80997e6fc2`|`0x37c554a104fe58f9a51e50b3cdb7df1afa0283457468c62b40d33d0d702212d9`|ETH / 0.14794102915363505|
|6|`0x29452e8332912533130fb708984722d92184284f` → `0xc61cf79a5c588bb4169a198987e5e5908010c606`|`0x53c1f98c00cab2a976e1925136885e49368e802f5685a9add869ebe5cc8ae99f`|ETH / 0.00015212810776105|
|6|`0x29452e8332912533130fb708984722d92184284f` → `0xe0dd0f41a876d80a579b49dd5d459988404847a8`|`0xfd4f39eeb92f8663ccdd1c61f66c4fe765b16eed64496210fdc4341e14d0ab9c`|ETH / 0.00129145342261373|
|6|`0x29452e8332912533130fb708984722d92184284f` → `0x13c49b02b1ec455953de777bf5ac0e5adadfa234`|`0x075c7830578eeaabf16d3f8e91b625163cbca5a83de5c4082e4965ff46dd25ca`|ETH / 0.000716140883412417|
|7|`0xe14c836bd3b0be1d4b52ac4d4f00c163926ff069` → `0xbe6bbb45c0be7cba3087d345fab9a71ac88af200`|`0x46d051aa93e8b797903a8bd8ba7a47e4ea4a494bb57a7fca2aa7df64de133e22`|WETH / 6.5955554261094e-05|

Rank6 outward hop2 (actual native transfers, not a shared-builder merge):

- `0xcdb56817e135d30561ff6b4f05e088fa2c9695c8` → `0xd01607c3c5ecaba394d8be377a08590149325722`, 0.27561559728922047 ETH, tx `0xc68c826cf2e3694186c268dcde82744e1e1426598b10240df596ae0b552ce067`.
- `0x644e2a8e46dea6434a71d0801f3173210693289d` → `0xc95049b67979436a5ea577f451aeddefeedde5ad`, 0.028926938508713983 ETH, tx `0xf652a64766aa2cc4d55b8d29537c172483f45fec3c134487341fd261d1458875`.
- `0x644e2a8e46dea6434a71d0801f3173210693289d` → `0xcdb56817e135d30561ff6b4f05e088fa2c9695c8`, 0.050701693904028365 ETH, tx `0x8ef267337fab69f8139aba3374ad1033f0808c7f4a5bc021ee77a05e2f832f9f`.
- `0x644e2a8e46dea6434a71d0801f3173210693289d` → `0xe0dd0f41a876d80a579b49dd5d459988404847a8`, 0.002942172018389164 ETH, tx `0xc12b140fe7226b986eb1505f1f763c7b55bc058d8a185638d72b230d7e327b97`.
- `0x644e2a8e46dea6434a71d0801f3173210693289d` → `0xd01607c3c5ecaba394d8be377a08590149325722`, 0.20141752418094397 ETH, tx `0x8599b19d9125f9c996bbe5096c4414f647efeb74cbdd6d3231035a4924234561`.
- `0x3a752524753d8260078a4a4ee071df80997e6fc2` → `0x13c49b02b1ec455953de777bf5ac0e5adadfa234`, 0.050809652401669 ETH, tx `0x709d50c56dd9bfa276453b8d06f42daf73ea3da9bd6b234d2e8f04b9eb8fb7ad`.
- `0x3a752524753d8260078a4a4ee071df80997e6fc2` → `0x9f90916bfd6d0df907d3eecf7b1ff4dcf95f6d77`, 0.03539654678412937 ETH, tx `0x7a3a30a4224acf948d3a271822b4f1eee10b68a80ba0e6067017b62bf47a90db`.
- `0x3a752524753d8260078a4a4ee071df80997e6fc2` → `0xc61cf79a5c588bb4169a198987e5e5908010c606`, 0.03915874808965661 ETH, tx `0x695dad3fe54aace7646c5a5f6af1c004dfc24277016f7f086ab2bf0973dbd379`.
- `0x3a752524753d8260078a4a4ee071df80997e6fc2` → `0xc95049b67979436a5ea577f451aeddefeedde5ad`, 0.030145092028187347 ETH, tx `0x18d8d9846c46c596047596970b5e6e84383022f71d1dad1d9120c065b3de9337`.

Rank7 hop2 is cached in `seeds.json` (sender outgoing transfers) and `extra-transfers.json` (destination screening); staking/token contracts and shared gateways are not operator members. Five legitimate WETH transfers from executor to sender are observed; no additional ranked member was proved. Rank10 payout remains unresolved: its only observed native destination is Atlas. No rank8/rank10 merge is allowed through that destination.

## Privately funded sibling contracts

These are candidates supported by funding edges; a contract receiving gas does not establish that every pool/router it touches is a sibling. `siblings.json` contains every funding link.

| sibling contract | funding tx | observed activity / payout evidence |
|---|---|---|
|`0x0261b1bb0e97d9a31b686253c878d49973feeb04`|`0x645655e01663562f9e35803a2d0433678cf9cfa6d6e7d29311327f1569150360`|Morpho token repayments observed; action needs receipt verification; payout51c-independent ed989 payout `9af4392e…` tx `0xe448501f9cbd95c2b651764122b4f4a0cc6c71fd499533f33898cf2c817b2e35`|
|`0x214f71fcc12f90b11288a45f93218fb8d7a805c7`|`0xdecfa71d8af50a767f8ec21d5ed3fed077cc3c05354d1ae641538a3cfb218790`|activity not yet classified; payout51c-independent ed989 payout `9af4392e…` tx `0x59c296028ab73de49e3c93b52b8ade94fa905e9af05a50c3d9fd159c8f35837f`|
|`0x39b1bc83958973ba5e32b871c0cd9f8f68386ce8`|`0x9a51778b42ad9bfd966c9e0f8c37e95ebfaa9d83bbb4fd28a43c6965c71659df`|Morpho token repayments observed; action needs receipt verification; payout51c-independent ed989 payout `9af4392e…` tx `0xb933fbb6ba1682c574925c76def392e6377de3866253b6097f6af85abe985454`|
|`0x4c0f054ff82accb847d59e3b6b3d46f1ceef19f4`|`0x6637e8545391f70e2aba01d4b8445e8e2088491d2288be1c9ad78db610c54be8`|Morpho token repayments observed; action needs receipt verification; payout51c-independent ed989 payout `9af4392e…` tx `0x6c42c81fcb332c31efe612a9f5ab62f9b5846389fdb479a1fba1f78124b371d1`|
|`0x59f7b3d9e1d592652f4c70ab895dd6c1d4fb17e6`|`0xa8d73974bebc0187994f39d0f34c42d995725117a0e345f97274276ecf2a5f99`|activity not yet classified; payout51c-independent ed989 payout `9af4392e…` tx `0xf7f798ab3f7f42e41e2d5e810251edfaf3cf4058ee5410b1253c8e566f372ac6`|
|`0x8b61f5925f4515edb0b7b76c38036aaf9a818472`|`0x175dd9e480d7cba201a3e6b77503321f5f4037095e74c1a6f90e26d77f5c2429`|Morpho token repayments observed; action needs receipt verification; payout51c-independent ed989 payout `9af4392e…` tx `0xa78868c86ff1739b392024b0ab8bf32db39b32e01a17dc2b7ced127d5f1b337d`|
|`0xbe6d8f0d05cc4be24d5167a3ef062215be6d18a5`|`0x8cb7512f23c8c991ddcfed633f17e569ac24c2ad0bada693cae114beed708496`|activity not yet classified|
|`0xcb3ed6eedc414c164ab673dcd77e1fd447eb7238`|`0xa98dad218e72f63195c3c665fb8d81460256f11f6e07bcdba620d8432582b5ab`|activity not yet classified|

No new missing-source earning class is proved by these transfers. Existing Morpho protocol calls are already indexed. Some sibling activity predates the snapshot and needs receipt classification; do not create zero-history or profit claims from source absence.

## Eligibility correction: oracle age was not an HF window

The earlier `scratch/census-step2/measure.js` read only the last change before C−1. It never checked the borrower state, accrual, or price at C. Thus its long oracle-age values and its no-change cap were not eligibility lower bounds. Attempts1121/1122/1137/1138 and the old slow labels are superseded for those samples.

Reused the exact40 transaction selections (`taker1.json`, `taker5.json`, `t8.json`, `t10.json`). `hfcheck.py` picks the largest valued event of the previously chosen dominant market per tx. `batch-hf.py` then checks **every indexed event for that executor in each sampled tx**, including other markets and borrowers:469 events. Each historical eth_call is a Multicall3 sequence: accrueInterest(actual marketParams), market, actual wrapper.price(), position. Debt = ceil(borrowShares × (totalBorrowAssets+1)/(totalBorrowShares+1e6)); maxDebt = floor(floor(collateral × price/1e36) × LLTV/1e18). Eligibility requires debt > maxDebt and nonzero borrowShares.

Official formula sources: [Morpho.sol](https://raw.githubusercontent.com/morpho-org/morpho-blue/main/src/Morpho.sol), [SharesMathLib.sol](https://raw.githubusercontent.com/morpho-org/morpho-blue/main/src/libraries/SharesMathLib.sol). Six independent direct `liquidate` precheck eth_calls agree with the math: five healthy samples revert `position is healthy`; the parent-eligible dust sample passes that check and reaches `transferFrom reverted`. These are read-only calls, no transaction sent.

| rank | operator | sampled txs | representative median eligibility seconds | all sampled events | healthy at C−1 | parent-eligible nominal gross | sampled nominal gross |
|---|---|---:|---:|---:|---:|---:|---:|
|1|payout51c (Base only)|10|0|171|171|$0.000000|$139,668.09|
|5|ed989|10|0|148|148|$0.000000|$146,041.88|
|8|ed989|10|0|72|69|$0.562117|$77,532.62|
|10|exec5ab7|10|0|78|78|$0.000000|$51,786.58|

466/469 events healthy at C−1, representing $415,028.59 of $415,029.16 sampled nominal gross. Rank8 has three parent-eligible dust events, $4.554120 repaid / $0.562117 nominal gross. Its largest SOL dust event is healthy at C−2 and eligible at C−1: one block/1s, never EV-countable. Its cbBTC dust event crosses between C−8 and C−7:7 blocks/1s, nominal gross $0.008019. The second SOL event has only $0.019171 nominal gross and its exact crossing remains unmeasured. All four representative medians are0s; the combined sampled Base ed989 median (ranks5+8,20 txs) is also0s. Rank9 has no new HF sample; Ethereum payout51c/Aave is not classified by Base samples.

Direct controls (tx hashes and exact parent state in `hf-validation.json`):

| rank | capture block | borrower | HF at parent | capture/parent oracle-price ratio |
|---|---:|---|---:|---:|
|1|54030845|`0xeb87434005fa0db112b90d4f63f0417b76ee5a18`|1.005313377|0.994551992|
|1|56796387|`0xf9778387bdedceb93593c4a970c948196c6eb0bd`|1.002196389|0.997638951|
|5|53642823|`0x79f9f809078442f02dfe9b67613911712d6a4850`|1.001007805|0.994762775|
|8|53799561|`0x41a4d40c04662e12a5f6745942a7307d03c117a1`|1.006421363|0.993432021|
|8|54922702|`0x09f83f39ed57656483777408e49e2557e7326c71`|0.996014030|1.000000000|
|10|54922100|`0xb0516e47a6a5fe2d91ff3c77a64460cd82ded718`|1.002646120|0.994734535|

## Exact continuation

1. Do not build a census-derived slow-market bot from the superseded oracle-age numbers. Earner step2 must use HF eligibility at C−1 before any backward ladder. The existing40 selections are now corrected; sample other ranked takers next.
2. Keep the original coverage and historical-bonus gaps open. Snapshot starts Oct26, not Oct14; cursor-at-head does not repair missing history.
3. Ranks6–10 funding screening is recorded; rank9 preserves its prior link. Rank10 actual payout and several privately funded sibling protocols remain unresolved. Continue from cached transfers, not fresh funding searches. Next new rank batch11–15.
4. No completed step1–3 Japanese report and no purchase proposal: no slow-market candidate survives this corrected sample yet. Today’s non-liquidation breadth was already installed by this instance in attempt1119 (`liquity_v1.redemption`).
