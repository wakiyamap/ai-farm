---
type: infra
chains: [base, ethereum, hyperevm]
protocols: [morpho_blue, aave_v3, compound_v3]
author: researcher/gpt-6.1-sol
updated: 2026-11-14
---
# Census ranks 16–20: source repair and gateway boundaries

**Conclusion:** no copyable farm route was established. HyperEVM’s old rank16 was a borrower, not a taker: the caller is `0x9be3e318072e0927b089cfed47e4fdb6ff0a5006`. Six captures paid the entry keeper less native value than its gas. Base rank18 shares a payout/inventory contract with payout51c, but that grouping remains provisional. Four newly verified gateways prevent further funding inference.

Run `ac4063445f7047468a67d17cd9aac767`, 2026-11-14. Continued the frozen census cutoff 2026-11-13 13:10:06 UTC, not a fresh valuation or timing exercise. Artifacts: `scratch/census-ac40/`; all chain reads through the research relay, no transactions or fork mutation. Daily breadth already installed today: Across fills (attempt1163, lead168); no duplicate source installed.

## Source correction

Official [Morpho EventsLib](https://github.com/morpho-org/morpho-blue/blob/main/src/libraries/EventsLib.sol#L102) indexes Liquidate as `id, caller, borrower`. The HyperEVM source instead calls those fields `id, borrower, receiver`. Thus historical `fields.borrower` is the caller and `fields.receiver` is the borrower. Principal and nominal valuation are unchanged. Keep actor=tx_from: it identifies the entry keeper, a different role from the executing contract.

Receipt witnesses `0x6497ef6d73859aa20423a2145dc914a033993cf132accfbeec5e9b1c220b699b` and `0xd47d3df91eb3ca24014d9a7331badf00c51dad7cb733751b1e83697b532023c8`: topics[2]=9be3e318, topics[3]=borrower9466140c; callTracer confirms 9be3e318 calls Morpho selector0xd8eabcb8. Frozen export has41 HyperEVM events:32 borrower-grouped rows become19 caller groups; all-chain rows553→540. Corrected frozen artifacts: `corrected-ranked.json`, `corrected-valued-events.json`. Old rank16 becomes6 events/6tx,70,008.25 USD nominal gross; old rank24 becomes caller `0xc93dff93d51c0dcadcf9203ea8319538cda23531`,2 events/2tx,32,363.84 USD gross. Ranking positions16/24 happen to stay the same; their old addresses were wrong.

`ledger add-source` rejected replacement of the existing id. No duplicate id/scan was created; meta repair request `inbox/meta/2026-11-14-hyperevm-morpho-source-attribution.md` contains the exact transformation and corrected spec. Until repaired, never use HyperEVM fields.receiver as a taker.

Independent scratch hazard: `scratch/census-4170/sample-selection.json` has stale rank keys at16/17/18/20. This run selects by chain+executor and asserts cohort counts. Earner scripts `census-r1518/run.py` and `census-r1920/run.py` explicitly select the correct addresses, so their published17–20 timing labels are unaffected.

## Windowed totals

Nominal gross = current-configured-bonus proxy, not retained profit. Receipt fees = gasUsed×effectiveGasPrice + receipt l1Fee; OP operator fees not separately established. Atlas relayer reimbursements mean its fee is not assigned wholly to the solver. No 30-day or daily scaling.

| rank / caller group | chain | first → last event UTC | events / txs | repaid USD | nominal gross USD | receipt fees native | eligibility median / classification |
|---|---|---|---:|---:|---:|---:|---|
|16 / auctioneer6c246928|hyperevm|2026-11-05 15:53:25 → 2026-11-12 08:15:05|6 / 6|552,287.50|70,008.25|0.072216819104 HYPE|timing wanted; permissioned route excluded|
|17 / exec7372825f|base|2026-11-04 03:00:29 → 2026-11-09 11:08:18|25 / 25|1,532,957.00|69,914.63|1.577830602689 ETH|0 s (25 timed txs; prior earner sample)|
|18 / execbd0dd817|base|2026-10-29 01:49:41 → 2026-11-06 07:04:27|52 / 10|540,882.49|61,047.26|0.172114128924 ETH|0 s (10 timed txs; prior earner sample)|
|19 / execbde3e91f|ethereum|2026-10-29 20:48:11 → 2026-11-13 05:00:47|17 / 8|995,859.69|52,486.40|0.146930184868 ETH|0 s (12 Aave events; Compound timing inherited at protocol level, not measured here)|
|20 / exec3e9a355f|base|2026-10-29 20:47:49 → 2026-11-08 21:56:06|12 / 12|1,117,903.54|49,010.38|0.564418281465 ETH|0 s (12 events; prior earner sample)|

Address and operator totals currently coincide within each row; no cross-rank ownership merge is proved. Rank18 is a provisional shared-payout link only. HyperEVM row16 aggregates the same executing caller across six captures (two borrowers); it is not six keeper operators.

## Direct gas-funding links

All61 transactions across the corrected five cohorts are enumerated in `cohort.json`; transaction senders are replaced by SolverOperation.from for Atlas. Relayers are not execution-wallet owners. Native gas links below exclude ERC20 symbol lookalikes.

| rank | execution wallet | execution witness | first native funder | funding witness |
|---|---|---|---|---|
|16|`0x6c246928f16528b0defd0891573da0c02cfc14f7`|`0xd47d3df91eb3ca24014d9a7331badf00c51dad7cb733751b1e83697b532023c8`|`0x1b0bb20d345a2699dd65eb316114c8786ac90761`|`0x80ed91a2ece60491030d9f7130805c3ebd3cd9733594fa92e8add0018dd6773a`|
|17|`0x36633e2bb3af873b356933a8972cf791cd717572`|`0x01b8e21079a5452fb223b46d28a8412bd9fa9fc922b22cd79943228500afef12`|`0xb10dc8bc2846afa3b0e79486dfc41f4b757e399e`|`0x3a93c8f4f74a3cd3e80c3a7220dfae0fc3d652eaf371540dbef3aaed7f1911d6`|
|17|`0x7a9b1c5b9964027b30bc5954bdefcbe064f9f18f`|`0x0bae0e09d084e9aab119f98eaf1016c981800ba88ebb44649e5cc32fb1fa1f4e`|`0xb10dc8bc2846afa3b0e79486dfc41f4b757e399e`|`0x2513e133ae9024e7e384797da5ebef53416cb060d018a6ae1bc1b81f5cfb7d25`|
|17|`0x10696ba0b2313fa54b928d2b154bf3428457c93a`|`0x1359609f4f9079e718cff49eda9a433e58181bc60ea3184574063069e543a262`|`0xb10dc8bc2846afa3b0e79486dfc41f4b757e399e`|`0x18ae1bd39fe68618bc5e2928e2f29312394c98dc28c5c309de3384fa5acf73e2`|
|17|`0xab8c2d99a4c344a8a60bf5a0979678c62dcfe435`|`0x1f9d10772f9fa154e4fb425d4a66967eb2b8c5f5e5caca5c046f0debbc3e7759`|`0xb10dc8bc2846afa3b0e79486dfc41f4b757e399e`|`0xe8646ad25ef777fef90e1eddb1eec7b89880272341214af247d1bbc909d1c3a7`|
|17|`0xe17a3ab874de7e60bc3285e983d2db6e1b1f0cac`|`0x2792d3a89037b1a19241c1c510022c16d521b95f725c5de6526e84e5e5b9385e`|`0xb10dc8bc2846afa3b0e79486dfc41f4b757e399e`|`0x554c772a505248330a94b7f5a91a2e770b61e561089af6fb17f48bf94c37d2fb`|
|17|`0xab15a90f37b5719d14ac0a88a6b7adbd37b43059`|`0x36633ec4a989982ea5af12f41dfb49a801b9d2f133be6a5338cf4a45c664dcc8`|`0xb10dc8bc2846afa3b0e79486dfc41f4b757e399e`|`0x1186699b7ee19585ad733a629379d4dd6cba04cddc9271555d62497ef4e1668c`|
|17|`0xb10dc8bc2846afa3b0e79486dfc41f4b757e399e`|`0x3babcd51559b11c51fe9f25f487a7948d8988b1611ebc099ff31a4be4203ab68`|`0xf9b5b814ebf89b476a79eab0bf1e8e7146f476ba`|`0x091acd8ac4f6dc29758b463569aa0638d1f9faec11f3f4711d593ec055888fb5`|
|17|`0x71ddd2967c319d5c1cccb853f1289be3b4bcc816`|`0x3d3fc60938bb0070cdfa07639381d748c4d90903ec8468fe7c6c828ce4f8cdc4`|`0xb10dc8bc2846afa3b0e79486dfc41f4b757e399e`|`0xfde65b2e1d9e408016a6ed0d74b49024482f6382ee7d94d5dd1a9caec6251db7`|
|17|`0x0e9729b4b792ae6a6032565e9782668ef9b8f05e`|`0xf8d9eb91756b99f7d40f0a3e6cbe59c8c2d9905464b087375e93a08911b7414c`|`0xb10dc8bc2846afa3b0e79486dfc41f4b757e399e`|`0xf4656423be12352601338044a380dc1f7026818e0ebde38472707bc2fe0358d8`|
|17|`0xa01cf56789e0e77dd2e34eff99365e176832be50`|`0x6fa2887a8ea725d7abb89ff28efe0b926fdbe84b30b850cc1f2225ba9be50965`|`0xb10dc8bc2846afa3b0e79486dfc41f4b757e399e`|`0x08194337db7a5501bd901726fbd035abdb43f566dbfee22003937cab290dada4`|
|17|`0x1a9cf9713b79c2e3663e91d574ecdc8fc7d1c2d8`|`0xf457241d7d7ab5c5fb3646d7a80520235be0408e684b990ea6217d9d9572c231`|`0xb10dc8bc2846afa3b0e79486dfc41f4b757e399e`|`0x65f73e751e9ef10b68c800e4a1fd6a094a0e5f0c5667a35432ffff19655dad3c`|
|17|`0xa77eafd1307aadf56936e5c61a9d9bf47b23e69b`|`0xb6e6e2c93880cbd6043dc0ee76e5ea3c195b5305a3a340d801b3d42336c6927f`|`0xb10dc8bc2846afa3b0e79486dfc41f4b757e399e`|`0x003bf06938373489b0fb972380c38c5e8ea0f52abb055614bac0eee9afbd4d26`|
|17|`0x9f1cbf1f40baea255bfec4c1ea5e38265eb94364`|`0x785e6f63b4cc293d1a031aa83a8a543bbbb7c3a9a6b699b575444b1aa4d050e6`|`0xb10dc8bc2846afa3b0e79486dfc41f4b757e399e`|`0x1046b9ac061c5ac791871cf02ac87710cbc96b4f23051cf9f78317e8649b3f1d`|
|17|`0x4535fa612a57360738dc3e5a77cee116ce704211`|`0x9c9935c48a15e12be05b93b08249c22cc519760a738ca488f800c724388d4ddc`|`0xb10dc8bc2846afa3b0e79486dfc41f4b757e399e`|`0xba714052af312d3f8d1aa7def3db11d3e00f719375d746f5ad5b086f862e33b2`|
|17|`0x78c57d30fa6efe0cb150e38a979b55c3a66a61f1`|`0xbabcaa041202e4815b6c8124d02f1be2e8e03b2e7223a4e0127e221fb1436be4`|`0xb10dc8bc2846afa3b0e79486dfc41f4b757e399e`|`0xcde369c3a85a505314e21adc7797fd82e5091215d471c28308c6357962e7eaad`|
|17|`0xb67b043de186137bf11c3ed1a3b6c9236acea6fd`|`0xbfcfebdd79fef64d42cbde989c8bb57204ba7e2fa2df99e77cfc35bf3bc9b9ef`|`0xb10dc8bc2846afa3b0e79486dfc41f4b757e399e`|`0xf4db591a90dcb90e2ce296cd3b1820ff33d4dcfa4299298cca09ae69e5f87af2`|
|17|`0xba945a715b7dfbd3e76f2da38c31e3ffdd83c048`|`0xce9bac0e04e846c1100ca8d0ede9b3d8050fcbf47736016b5ef835799d4be10e`|`0xb10dc8bc2846afa3b0e79486dfc41f4b757e399e`|`0x277cf7fa0814da08781e37372a7cdc7a4c266519439bb9404f3d56ea48e81933`|
|17|`0x8e6d903802b6579800379340f4a885199278b5b8`|`0xd75c925addf1c6533177643a7ebf6ea70b85f727cdb61ca8e1ccde7895ac7a3b`|`0xb10dc8bc2846afa3b0e79486dfc41f4b757e399e`|`0x57ddbf9be66789b42ba38ae3e63cce91190a53613ae52cd439be6e5e2ed2acd5`|
|17|`0x0346870642a0dd43620d33309c6eb3b7649e3452`|`0xe0929538893e417697ae78a98f7d08fc903f6d4d13f96f3a2e5fa1def5ba3d42`|`0xb10dc8bc2846afa3b0e79486dfc41f4b757e399e`|`0x1b4573573b5e59d8b9208ee5b09ba2789c432538e0802139533bed7bd00f8a0c`|
|18|`0xc0b414fce9dabc71cfb3825985ac8ab4795f9f85`|`0x1c2340d408419741c1568ff519ef3f2c325c927185929e5a0843ed8ccd69c716`|`0x714d75577883d54072b888ce9e6d80278f9fa741`|`0x106a4e9429f037ed5cc0346eb9492b57c6d501ef9053739ae1bc986d1192ea27`|
|18|`0x24c04aae27cb252787175fa317b24d7e9b29a2a9`|`0xc555c55c9f9f2b60f0327c6e90cb1d5c5ddd1d59d490f48f7d84e1257800324b`|`0x714d75577883d54072b888ce9e6d80278f9fa741`|`0xf562bf9ec7331330f9e2e4f70848982fcb9971458790cb429a7d88d30f50afaa`|
|18|`0xd02b5853557e8f221727162540d49ecd4b4bb225`|`0x388ef9fe47cd485ed28157468d573647912792eee53da79b28f93511fec9dc13`|`0x714d75577883d54072b888ce9e6d80278f9fa741`|`0x659a6724ce34781bc9735c187462a494662923fe2a1825487a2087d6975a51d7`|
|18|`0x8f3ce52dc1b2721ad61b7dfacfb54f1256b1ae17`|`0x7cca25c5e21f2c72ff96a03f442cf8a0fc6652c4c622b68c42a7188cd8f93a71`|`0x714d75577883d54072b888ce9e6d80278f9fa741`|`0xf3ce21d29ff81e6824fa6e0906f33f326651a0d6ccb38798a73b40622da52d47`|
|18|`0xbe0ece6d7dcab9112daaffb640aac80e3d62d3da`|`0xade57b28fd1f16ea7d302476ef5bb72089759afefe41e488b692490ed4a46a20`|`0x714d75577883d54072b888ce9e6d80278f9fa741`|`0x9480fd20d9b11947c64c943d1d46a80e62fc81d13479238e8efab1a32b0532a9`|
|18|`0xdaf673a781884c9702800d0cb75bbd857cefaace`|`0xfe19e8fd015b833430f97cfc79ae19b988c4c769f07c3ce64f5dc57784632020`|`0x714d75577883d54072b888ce9e6d80278f9fa741`|`0x91c7e815439490988c2d056c06ed4dbd713a361f32d426001fee25aa45934551`|
|19|`0xf87a11ee8ab057952fa83b1de64811e3c4f40709`|`0x2a19798eeed2f8a9d86e24583109303f865c8e0872f5eae35004579107a18633`|`0xdf3af9f0e649c4988fbb8ebe44e2077f890b6303`|`0x5245d2d602d227e5b7e0856ba8cc307fd4e3341081ce0b22c8473bd47c578fb8`|
|19|`0x7606b0118c0e94e7ad9967ead8d2b2981803de7f`|`0xa0eb265b244db1b14dd813161f819a184f3bfa0e88558257615c8df068b4e79a`|`0xdf3af9f0e649c4988fbb8ebe44e2077f890b6303`|`0xcd33123d6c667bd8fb3c9b4f75ad16dfe0da6fd112a24c323c31e6649aecee6d`|
|19|`0x6a3ac06b4a3432d580faed8cd1e1b426030f5444`|`0x3f7109f2873b3082e8a7df7bf226e71afd3ce09f1227a3e1a07de61fc084c9fa`|`0xdf3af9f0e649c4988fbb8ebe44e2077f890b6303`|`0xf4bb7c61eb60c0a37240fd8b6a16d9f30752f0d0a9d0efe0da211bd8669c28ba`|
|19|`0x3c1557217d1438fbde9539f5332a3e13b7edc287`|`0xd9994fea36a57fcb52d4c31c2325e394a79cef8af42e10514277d3961fc5593b`|`0xacc0c1f672b03b9a5fed4535f840f09b85f40e98`|`0xd0703f0ac294aa78fd60a149927fa2ee7a548dbe8751b3f8eeaae062aebde1a0`|
|19|`0x473bac73a83220429c222fae5afbf8cdc4a213e1`|`0xefbad3143bf07a3cf1116f9cc2b4ff3c5147d89c1bc3867a2c373765aa26c16c`|`0xdf3af9f0e649c4988fbb8ebe44e2077f890b6303`|`0xb3119b50d52698c7f710adc08ceb67136eccfbd39cc6c9b6f3b038c7192fc733`|
|20|`0x7ed54f78b96ed04410c05c94a6bb97013ab3de7a`|`0x4572a0e964c3115859892eb45c7bf10ca52935f8932676c45f716429093a2f08`|`0x25735aaac4a0a87fcce58088de9a99c2575d1c8e`|`0x6c924fd88eda3f63a602e94ca69610a31aa2ef5ff6ea898b533b46f32a4cc2fe`|
|20|`0x812c7fa4eaefcb2b84a185fc703ef02045d98aae`|`0x472a75b011278a9ae750cc08c3968af92bf7ea9aa04331c5bb60f7ffc9d8203b`|`0x25735aaac4a0a87fcce58088de9a99c2575d1c8e`|`0x1328fe1416f023eb8b0c2c193c8e0d87d327240d458c20b01a0b995f648c1218`|
|20|`0x81faeb47760758be86aad964d3a1c50bd918eecd`|`0x55b08533f4c53b63b79c7b0dc997eb76c824cf50bc5bf354014759529e6c643d`|`0x25735aaac4a0a87fcce58088de9a99c2575d1c8e`|`0x85753a808a4ecbbfc3ddde704c41ee91b3cc4ec39e5af151c24621e08f876720`|
|20|`0x822ad5b7307648eeb633f06b4820fdec81ad3886`|`0x5c73884e6fc3533f5c0f531d4109c602d3846e7570c46467588a4210a9362482`|`0x25735aaac4a0a87fcce58088de9a99c2575d1c8e`|`0x21684ab8d1b74a159a352043395af84dc3c007ebdf1867a6751d8a60492c0ad8`|
|20|`0x7effb011c81601e98c13a9719e882f6ae8abfd1c`|`0x6acc97869952456f5a1b2919d454dc7c3e492a567bf5a12099b9c54fb34f9d5c`|`0x25735aaac4a0a87fcce58088de9a99c2575d1c8e`|`0x6692c194efd8e938e88168b5f561a322255172b61e2fc44fa20c304ba63b4684`|
|20|`0x7f19292cba7ff89d43b4a6c2003d8a2b4b2f7b05`|`0xf2a6faa63d8c818958cd27acf1be3368ce1f21dc06c2bcb417b56f7df83115ec`|`0x25735aaac4a0a87fcce58088de9a99c2575d1c8e`|`0x1f057df01cae0430183c325795a04574d5485e7a47e1770a10d297f914496b0a`|
|20|`0x8258fb418ddca054471ec0356b3688823e84e4f9`|`0x9ee9ee71c54a3f2930550294cb466f5896aa90b5eb86cfb3cb4ad0bf90b08280`|`0x25735aaac4a0a87fcce58088de9a99c2575d1c8e`|`0x681dc414d257ac306d8d3f4359628e008de96006db23d739ab977022f4dc3b57`|
|20|`0x7f558886f675a50e4e0bdee6eda088933b6c0bd8`|`0xab030f2a2330f879708b40a6cd4992a9aef983c8db57d3b7f5eae7718414c93e`|`0x25735aaac4a0a87fcce58088de9a99c2575d1c8e`|`0x6c924fd88eda3f63a602e94ca69610a31aa2ef5ff6ea898b533b46f32a4cc2fe`|
|20|`0x8220535bc731cef62a9140a9ea51b483411d1ed8`|`0xaf67af00217bf60b2b7564ab56ce8b15a6565ec8b737dc5c3d640221b0055c51`|`0x25735aaac4a0a87fcce58088de9a99c2575d1c8e`|`0xff4771437ce52be62ddbab1c57a0e3d3fe6046ced32c518930e994b7b3b5e723`|
|20|`0x7f2424e72cd4e6625e35a75666753a752886799f`|`0xd656260bf3499260a63b82978022d4ff58c41c0454249eea818c2a5abc3c9406`|`0x25735aaac4a0a87fcce58088de9a99c2575d1c8e`|`0xbe209104e3b2f4defa604b56f7a0efbc8c660cffd75a8ad2cd72c4f90d3042bf`|
|20|`0x7f334ae8a5b08fe69d821c129824c22e43daf995`|`0xea825134a647b9e04b0421dd7360c66d058bc6e557a7047ae18c7133560f2fc7`|`0x25735aaac4a0a87fcce58088de9a99c2575d1c8e`|`0x6692c194efd8e938e88168b5f561a322255172b61e2fc44fa20c304ba63b4684`|

## Funding screens and boundaries

Native external/internal outgoing recipients are counted before following upstream. Native WETH unwraps are not gas funding.

| chain / funder | distinct native recipients | pages | next page | treatment |
|---|---:|---:|---|---|
|`base:0x25735aaac4a0a87fcce58088de9a99c2575d1c8e`|441|1|True|gateway: STOP|
|`base:0x714d75577883d54072b888ce9e6d80278f9fa741`|217|25|True|gateway: STOP|
|`base:0xb10dc8bc2846afa3b0e79486dfc41f4b757e399e`|298|1|False|gateway: STOP|
|`ethereum:0xacc0c1f672b03b9a5fed4535f840f09b85f40e98`|828|1|True|gateway: STOP|
|`ethereum:0xdf3af9f0e649c4988fbb8ebe44e2077f890b6303`|12|1|False|bounded non-gateway screen|
|`ethereum:0xc08b45925a4dd11426093c698d700b9023b4e3dd`|61|1|False|bounded non-gateway screen|
|`hyperevm:0x1b0bb20d345a2699dd65eb316114c8786ac90761`|360|1|True|external-only gateway: STOP|

Rank17 b10dc8bc is itself a cohort execution wallet and a298-recipient funding gateway. Shared executor still groups the observed sending wallets, but do not expand through b10 funding. Its f9b5→ae04 upstream crawl was discarded as beyond that boundary. Rank18 funder714d7557 crosses217 recipients only on page25; earlier10-page83-recipient screens were incomplete. Do not join ranks1/18 through714d. Its previously recorded upstream2466 is excluded from that funding chain. Rank20 funder25735 has441 recipients; rank19 one sender reaches acc0 (828 recipients). STOP at each.

Rank19 private funder df3af9f0:12 recipients, complete. Hop2 c08b4592:61 recipients, complete. Upstream link c08→df3 tx `0xdd29d878d837bc4998d17fdafda492ae478a3dc95ccbe131473d7dc34d6b170f`. Native transfer recipients include contracts/routers as well as EOAs, not73 proven sibling bots. Five bounded probes are cached. The ledger event export often has tx_from=null; absence of a match in that column is not proof of no activity. Known cohort senders are established by actual transaction reads. No missing-source earning mechanism was proved.

HyperEVM alchemy_getAssetTransfers rejects category internal; external-only succeeded. The provider labels native HYPE as ETH: use chain id999 and raw value, not asset labels. Funding tx `0x80ed91a2ece60491030d9f7130805c3ebd3cd9733594fa92e8add0018dd6773a` independently checked by eth_getTransactionByHash: chainId0x3e7, correct from/to/value. Internal funding remains unobserved.

## Payout evidence, not nominal profit

| rank | representative capture | retained or routed transfer | boundary / meaning |
|---|---|---|---|
|16|`0x6497ef6d73859aa20423a2145dc914a033993cf132accfbeec5e9b1c220b699b`|wrapper f231→keeper6c2469 pays0.05741008529516424 HYPE; 279.696599 HYPE is routed elsewhere|keeper bounty and protocol/L1 proceeds are distinct; permissioned P|
|17|`0xb6e6e2c93880cbd6043dc0ee76e5ea3c195b5305a3a340d801b3d42336c6927f`|executor→sending EOA a77eafd1,3.296835193785618 ETH|entry sends0.000000000054923211 ETH; receipt gas still must be subtracted; no miner payment established|
|18|`0x5c9167d0823afa35691ac0ce26220e15229a82a8dcb364a526bde78770878660`|9.480441792000649 ETH→Atlas1c6ec845;0.104797687563522632 WETH→51c72848|separate auction bid and payout/inventory route. 51c also sends tokens into trades; not all its outflows are profit|
|19|`0x1c1e159f08994c25905a2b9209fc6dbe219b52358071215e770f00d3132507d2`|10.34033716516216 ETH→block.miner4838b106;0.053006050399363773 WETH→EOA d61c0e1c|builder payment excluded; WETH payout EOA subsequently gas-funds two sending EOAs|
|20|`0x4572a0e964c3115859892eb45c7bf10ca52935f8932676c45f716429093a2f08`|17,361.531382 canonical USDC→EOA1f9c7415|payout hop2 repeatedly sends native to gateway25735; stop there, no merge via gateway|

Rank19 payout hop2: d61c→3c155721,0.17 ETH tx `0x41fbde96be55c49ed051e81d636b4774e2c0271196ccb997ac292885ad64eb6a`; d61c→473bac73,0.2 ETH tx `0x2711a8091c72e901aa3e6ea7dbe5ed992dec46ad9f1bd37db737617e6cdbe745`. Both are already execution-wallet members, strengthening the same-executor grouping. Rank20 payout1f9c→gateway25735 tx `0xef5c3efd4ee8b0b2f4e049eaaf58f97b7fd9f24d650953f681275bffce14c6a8`. Token-symbol/address lookalikes in transfer results were excluded using category and canonical token address.

### HyperEVM keeper native P&L (all six corrected-row captures)

`hyper-economics.json` plus six complete callTracer trees and actual receipts: native received0.07146981023407634 HYPE; native sent0; gas0.07221681910353506 HYPE; **keeper native net −0.000747008869458726 HYPE**. Five of six native legs are negative after gas. No USD marking is needed to establish the sign. This is keeper-native P&L, not the total operator profit including token inventory or Hyperliquid L1 proceeds. The70,008.25 USD nominal incentive is not paid to that EVM entry wallet. No account, purchase, or farm EV proposal follows.

### Taker types

Rank16 P6 with permissioned wrapper (prior stranger-entry proof in lead145); rank18 O10 via Atlas. Rank19 B1 verified: oracle AnswerUpdated emitter `0x6f3f8d82694d52e6b6171a7b26a88c9554e7999b` updated in tx `0x1dd01005b10baef2682b0b2d679b6c1b824f189191d0eeda20151c1f28a6b6c4` at index7, is called in the capture at index8, plus direct miner payment. Other rank19 cases unknown7. Rank17 unknown25 and rank20 unknown12: their same-block eligibility does not establish B/O by itself. Their published eligibility medians0s still exclude farm expected revenue. No new timing measurements or slow-market lead.

## Continuation

1. Meta: repair the existing HyperEVM source labels and historical fields, preserving actor=tx_from; use the corrected spec, not a duplicate source. Recheck any analysis that treats old receiver as the taker.
2. Next new funding batch: ranks21–25 (rank24 caller identity already corrected, not its funding or timing). Preserve old rank labels when reading older pages.
3. Five cached sibling probes need role classification; use actual tx sender evidence because ledger tx_from can be null. Do not re-scan old funding pages. Payout51c cross-chain internal-recipient pagination remains open, so rank18 linkage stays provisional.
4. Steps1–3 remain incomplete; no Japanese completion report, bot, purchase or risk-limit change.

## Crash lead173 correction (same run)

The exact two slow captures named by attempt1201 were independently read, not re-timed:

| tx | keeper reward HYPE | actual gas HYPE | keeper native net HYPE |
|---|---:|---:|---:|
|`0x35374831e6d970b5c8bce083c3be65d7cd61b63ca0f0cd971ab8927aa7b3f258`|0.015648892847447783|0.016761510528336972|-0.001112617680889188|
|`0xad1a37c000dc6b8386d378443e26a02bd5f189897a7a56571b9998e57ad0ea7a`|0.005585754051857720|0.006507261263983986|-0.000921507212126266|

Both tx.to are auctioneer wrapperf2314753, selector0x9038624a, from6c246928. Existing stranger-entry proof (lead145/attempt920) reverts NOT_AUCTIONEER. Native net totals−0.002034124893015454 HYPE, about−0.14092417 USD at attempt1201’s69.28 USD/HYPE mark. Token inventory/Hyperliquid L1 proceeds remain unknown. The alleged3,112.51 USD net was nominal bonus minus gas, not received keeper profit;43.2 USD/day farm EV is withdrawn. Lead173 is dead_end. No new fork or mainnet send.

Crash totals correction: remove these2 permissioned negative-keeper candidates from the previously reported14/4,415 USD summary. The other12 timed candidates carryapproximately1,302.68 USD of prior nominal-margin-minus-gas proxies over72h (593.4 Base Morpho +23.90 Moonwell +685.38 Exactly). These are not newly verified operator net or a farm EV estimate. Their prior timing/fork findings remain as recorded. Source counts, total repayment/gross and existing type-O percentages do not change. Crash A’s38,023.58 USD HyperEVM mega-capture actual caller isd49a4d98, not borrower2f04ed87; no farm counted timing case from it.
