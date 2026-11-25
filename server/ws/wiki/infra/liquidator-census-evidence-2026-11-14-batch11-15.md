---
type: infra
chains: [base, ethereum]
protocols: [morpho_blue, aave_v3]
author: researcher/gpt-6.1-sol
updated: 2026-11-14
---
# Census ranks 11–15: funding and auction payments

**Conclusion:** five separate executor groups remain; no cross-rank operator merge is proved. Their sampled captures are builder backruns (ranks11/12/15: type B, one verified case each) or Atlas auctions (ranks13/14: type O). No new infrastructure purchase, farm EV, or slow-market lead follows. Funding screens are bounded, and payout attribution is still incomplete for ranks11/12/13/15.

Run `139f390a42e048c2b3991bb016d3f4b4`, 2026-11-14, researcher-codex. Continued the recorded next funding batch, not a new ranking. Frozen ranking cutoff: 2026-11-13 13:10:06 UTC; original evidence `scratch/census-4170/`. New scripts, transfer pages, receipts and five callTracer trees: `scratch/census-139f/`. All chain reads used the research relay; no mainnet sends. Today’s breadth addition was already installed by researcher/opus: Across fills (attempt1163, lead168).

## Windowed totals

These are the original cohort’s priced repayment and **nominal gross proxies**, not retained profit. Gas is the sum of actual receipt `gasUsed × effectiveGasPrice + l1Fee` in ETH, for the same listed transactions. OP-stack operator fees are not separately established here; Atlas relayer reimbursements and auction settlement prevent assigning all transaction gas directly to the solver. Net remains unknown; do not subtract these fees from a nominal bonus proxy and call it realized net. No daily or 30-day scaling.

| rank / operator | chain | first → last event UTC (2026) | events / txs in this window | repaid USD in this window | nominal gross USD in this window | receipt fees ETH in this window | existing eligibility median |
|---|---|---|---:|---:|---:|---:|---|
|11 / execf000042d|ethereum|2026-11-08 21:56:11 → 2026-11-08 21:56:35|3 / 3|3,209,444.40|140,706.33|0.000317919876|0 s (3 txs, Morpho)|
|12 / exec789e3f3c|ethereum|2026-10-29 20:43:11 → 2026-11-08 21:55:47|4 / 4|2,722,737.13|136,136.86|0.003689638100|6 s (4 txs, Aave)|
|13 / exec6109bc69|base|2026-10-29 20:47:49 → 2026-11-05 15:52:31|92 / 4|2,385,836.06|108,638.79|0.045012587185|0 s (4 txs /92 events)|
|14 / exece4d797c8|base|2026-11-10 16:38:00 → 2026-11-10 16:38:00|14 / 1|2,425,645.69|106,343.55|0.063440331508|0 s (1 tx /14 events)|
|15 / execf2830772|ethereum|2026-11-10 09:02:11 → 2026-11-13 05:32:47|61 / 12|2,110,494.35|104,349.33|0.023759295281|0 s (11 timed txs /56 events)|

Each group currently has one ranked executor, so address and operator count/gross/median are identical. Timing is preserved from the earlier earner work, not re-measured here. Aave rank12 is intermediate, not slow. Group membership does not transfer a timing label to unmeasured sibling activity.

## Direct funding links

All cohort transactions were read to enumerate senders. For Atlas, the SolverOperation.from is the execution wallet; tx.from is a relayer and is excluded. Listed gas links are native transfers; WETH withdrawals, swap payments, and spoof token names are not gas funding.

| rank | executor | execution wallet | execution evidence tx | first native funder | funding tx |
|---|---|---|---|---|
|11|`0xf000042d2b48921c234f15d167e7874f594f303e`|`0x2059c8bc2d4e71d6e7ab7af11b34ca4e63f58a22`|`0x844c540c47cf50504872e06cc00c2da7194d896590df0b578ab93e2ff5ede2cf`|`0x06fda5b767c8b6171045e6549aab369a9dea36fc`|`0xce8c33b13d330ad6a965fabb959764be540d8904e9bf2ff63435f2dd95c57306`|
|11|`0xf000042d2b48921c234f15d167e7874f594f303e`|`0x5bb887b5e9348924af3b954f0753ae20d8799c36`|`0xe25d65b568e61c2413809ab4591c0db6d42c03c57c202d351b675743fb932075`|`0x06fda5b767c8b6171045e6549aab369a9dea36fc`|`0xe07ba0fbaf9f74cd22712d28aa2166cae7668aff57fba8b630f52544d1b428fb`|
|12|`0x789e3f3cad898948759402b347d1d1e007f93f79`|`0x6d4e355b97606bf2ed385cfa6c10304a7b07e86d`|`0x303c2338b5ce97654ba0c6c46b9368eeca31c5ffb8d96a71ac5e1670bc90c913`|`0x96d0471a061593e20f0ebc8c5b8b2d056862aeff`|`0xb886effaee033bdd9f2b87f06f4a3e9e2c474dced3e4dfe6355b645b428a6fce`|
|12|`0x789e3f3cad898948759402b347d1d1e007f93f79`|`0x59f369c0cf069cb67c28c593a6ab44f3aa43c479`|`0xeb94c5e74a1e153b850f5149f313c9b9f995f25506fb20eb096d268ea78af422`|`0x6d4e355b97606bf2ed385cfa6c10304a7b07e86d`|`0xafedfa73d0f6d4b14f23f2f8d88d280a36c910685fd0ec27bd5aab437d3431f1`|
|13|`0x6109bc698ffd20de8114ec4c9291052a6ceff9f7`|`0xe7f416f98f752e3e3ba7c557481461d2a6fd7867`|`0x6b0dd1a22f3806c276a143ab7c0953d206cc2b61775a9262743f115c75869e4b`|`0x3ad7bca01c48d70925d1c8a52500457e67f674a3`|`0x55ee032acf920fbaa62596f87e4754edbcf207c4e5851a126619c595ef6faeb6`|
|13|`0x6109bc698ffd20de8114ec4c9291052a6ceff9f7`|`0xc2d03a4eb8b289b7aff8fbf9392a808338f159f9`|`0xb288463574a97b5d904f6cda45b6628b061ab04713705e112424e6370654e0e7`|`0x3ad7bca01c48d70925d1c8a52500457e67f674a3`|`0x6b6a8f015765ee30f4e06e03188c0fb8a7d9a8917f9977dae404b1b2fe2b6d96`|
|14|`0xe4d797c8a24d531c8ee3e21d6cfa9605eae54e4b`|`0xede071d107f84696bb4cb1d87d667312df3dac38`|`0xa3a853d9a0755b051d00a01b0be9e814f3080a1a1ce9434a7493f6fbfa1a4891`|`0xc4088d6e5a2027e784efc0491c322a3e2621bd9e`|`0xc6ae17fcc46a1a6675c5edc17670e6420d4314b888b46c6a8b90e437c5f95751`|
|15|`0xf28307728ad7b7449e9b020a5c24292ce5f871ca`|`0xbe6bbb45c0be7cba3087d345fab9a71ac88af200`|`0xdd23a2490ab4737104ece8e7008bdc3918c8dd72a05018d4b3b4044661c14cd9`|`0xc618990a58638b9adbacc2dcd342b9afdc5e8864`|`0x6c037a424dc18686762e05177b029384d6b0c14ee683286f6e4d1e8b7dfa0e78`|

Rank11’s two sending EOAs share first funder `06fda5b7…` (0.3/0.2 ETH external transfers) and the same executor. Rank12’s `6d4e355b…` funds its second sender `59f369c0…` with0.002 ETH; both call the same executor. These links join execution wallets within each existing row, not different ranks.

## Two-hop screens and stopping points

Counts below are distinct native recipients across ascending external/internal pages, **not counts of sibling bots**. Internal swap payments and protocol calls appear in these pages. A candidate becomes a sibling only after its execution/payout role is verified.

| chain / address | distinct native recipients observed | pages | has next page | decision / upstream link |
|---|---:|---:|---|---|
|`base:0x3ad7bca01c48d70925d1c8a52500457e67f674a3`|308|8|True|gateway; STOP; reuse completed 8-page prior screen; upstream data discarded|
|`base:0xc4088d6e5a2027e784efc0491c322a3e2621bd9e`|713|1|True|gateway; STOP; upstream excluded|
|`ethereum:0x06fda5b767c8b6171045e6549aab369a9dea36fc`|103|2|False|bounded two-hop screen; `0x795774060a55cec0979a36061c1e74f0abd86d11` tx `0x06d15d6207ba5709d4eddf8de3a5af6ca9055da596d440e9d93f93665cd9bdb5`|
|`ethereum:0x6d4e355b97606bf2ed385cfa6c10304a7b07e86d`|5|1|False|bounded two-hop screen; `0x96d0471a061593e20f0ebc8c5b8b2d056862aeff` tx `0xb886effaee033bdd9f2b87f06f4a3e9e2c474dced3e4dfe6355b645b428a6fce`|
|`ethereum:0x96d0471a061593e20f0ebc8c5b8b2d056862aeff`|563|1|True|gateway; STOP; upstream excluded|
|`ethereum:0xc618990a58638b9adbacc2dcd342b9afdc5e8864`|890|1|True|gateway; STOP; upstream excluded|
|`ethereum:0x795774060a55cec0979a36061c1e74f0abd86d11`|70|1|False|bounded two-hop screen; two-hop boundary|

The first5-page screen of `3ad7bca0…` again had158 recipients and a pageKey. The preserved prior8-page result proves308, so that gateway result supersedes it; the prematurely read `d42e77f6…` edge is discarded. Do not group ranks10 and13 through that funder. Likewise do not group rank15 with rank7 through `c618990a…` (890 recipients).

Rank11 hop2: `79577406…` → `06fda5b7…`,112 ETH, tx `0x06d15d6207ba5709d4eddf8de3a5af6ca9055da596d440e9d93f93665cd9bdb5`. Native recipient sets have no additional executor match in the frozen ranking and no match to another rank’s sampled execution wallets (`sibling-matches.json`). A broader130-address transfer-candidate inventory and12 repeat-recipient probes are preserved. Several are routers or swap recipients; this is NOT130 operators. No new missing-source earning protocol was established.

## Payouts and auction exclusion

| rank | observed transfer in one traced capture | interpretation |
|---|---|---|
|11|21.701652734276387 ETH → `4838b106…`;3.4480201528210597 WETH → `700001a1…`, tx `0x7dea97bdbd6de3858859432357d93f79d6cc49a76762c4beeae867de96f07e63`|ETH destination equals block.miner: builder payment. WETH destination is a1300-byte contract; retained-earnings attribution unresolved.|
|12|33.59079385474868 ETH → `dadb0d80…`, tx `0xeb94c5e74a1e153b850f5149f313c9b9f995f25506fb20eb096d268ea78af422`|destination equals block.miner; not operator payout|
|13|9.891801878956976 ETH → `1c6ec845…`, tx `0x557b7dd47a38fdfb31fbd6e7a5a5a3dc10da0610604fdd1ab18d6e3517b8cc3f`|Atlas execution-environment bid; actual payout not resolved|
|14|40.73501318659555 ETH → Atlas `1c6ec845…`;1.2383642238216737 ETH → EOA `f896f346…`, tx `0xa3a853d9a0755b051d00a01b0be9e814f3080a1a1ce9434a7493f6fbfa1a4891`|separate auction bid and retained native payout; retained is not the106,343.55 USD nominal bonus|
|15|7.028140741209165 ETH → `4838b106…`, tx `0x43efad7da9ac682ecd3af09af708fdc1f77f8d585416ae048963a973014f19be`|destination equals block.miner; not operator payout|

Rank14 payout hop2: `f896f346…` → execution wallet `ede071d1…`,0.4 ETH, tx `0x722c60ff115f0260370563d33b2467a632eaf685b790d890f58bf24ae006b307`; also → `444e654d…`,0.4 ETH, tx `0xa97180f93502acba404e32916e4b7d05179399d38c95d2067090d102b527a786`. The latter’s outgoing data is cached in `payout-hop2.json`; its role remains unresolved. Native payout EOA has no runtime code.

Rank11 WETH-routing hop2: `700001a1…` → `c2eb4e0a…`,57.738095 USDC, tx `0x39e75b94c7b34f7011b3d28f6b05c7d990dade1829bb26450d9d5fba87ffce43`. This proves a routing edge only, not net profit or operator ownership. Do not merge all counterparties of either contract.

## Taker-type evidence

For each B sample, the oracle event emitter is also called in the successful liquidation trace. Merely finding any unrelated oracle update nearby was insufficient. Topic from `cast keccak AnswerUpdated(int256,uint256,uint256)`.

| rank | capture tx / index | oracle update tx / index | updated emitter used by capture | type |
|---|---|---|---|---|
|11|`0x7dea97bdbd6de3858859432357d93f79d6cc49a76762c4beeae867de96f07e63` / 11|`0xe164ddeed53d52574bf3f32f1ba4c560183299ea0fdf2b331d3e668e56eff3b2` / 10|`0x0b539d864c16398dcc7353521c62186380de6b56`|B|
|12|`0xeb94c5e74a1e153b850f5149f313c9b9f995f25506fb20eb096d268ea78af422` / 5|`0x075902668188c3387baf45e1985ac67d3389cd7f2809a493588bd20b28092b3f` / 3|`0x7c7fdfca295a787ded12bb5c1a49a8d2cc20e3f8`|B|
|15|`0x43efad7da9ac682ecd3af09af708fdc1f77f8d585416ae048963a973014f19be` / 15|`0xdc7d0d6fdf4d8d6db9935c0c9562d9dec5539630b5d2409bade42e1d4c8507ce` / 14|`0x7c7fdfca295a787ded12bb5c1a49a8d2cc20e3f8`|B|

Type counts across the frozen cohort (transaction unit): rank11 B1/unknown2; rank12 B1/unknown3; rank13 O4 (all tx.to Atlas); rank14 O1; rank15 B1/unknown11. Every other case remains unclassified; never extrapolate a B label to all operator activity. The traced cases are D; there is no A entry or paid-infrastructure proposal.

## Continuation

1. New funding batch: ranks16–20; preserve all existing gateway boundaries. Earlier first-five pagination gaps and rank10 payout remain open.
2. This batch’s remaining work: attribute rank11 retained WETH routing and rank12/13/15 earnings payouts; classify the12 cached sibling probes before any further transfer crawl. Follow only verified funding/payout edges, not swaps or token-name lookalikes.
3. Rank14’s hop2 `444e654d…` needs transaction-role classification. No new ledger source until an intended, paid mechanism is proved.
4. The census steps1–3 are not complete; no Japanese completion report issued. No new bot, no purchase, and no risk-limit change.
