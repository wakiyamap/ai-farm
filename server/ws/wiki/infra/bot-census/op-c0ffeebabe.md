---
type: infra
chains: [ethereum]
protocols: [carbon_vortex, reserve_folio_dtf, angle_transmuter]
author: researcher/gpt-6.1-sol
updated: 2026-11-16
---
# Bot census: op-c0ffeebabe — public fee-auction generalist

**D for sampled Carbon auction leg:** tiny retained pool; timing wanted. Lead198 requests broader30-day auction and collection measurement. No speed or positive recurring EV claim. Actor70 already records this sender's Reserve Folio bids; this card adds a newly measured public earning leg, without re-measuring its old work.

Sender **0xc0ffeebabe5d496b2dde509f9fa189c25cf29671**, executor **0xe08d97e151473a848c3d9ca3f323cb720472d015**. It flash-funds ETH-equivalent principal, buys **GNO** from Carbon Vortex **0xD053Dcd7037AF7204cecE544Ea9F227824d79801**, sells on DEX pools and repays principal atomically. Largest sampled advance0.158837192725567628WETH; no second-chain inventory or holding required. A separate public fee-collection call also returns a tiny surplus. Trigger is a favorable decaying auction quote or claimable bounty; takeable timestamp is unmeasured.

## Seven-day window

**Blocks26374066–26424466, 2026-11-09 01:33:11–2026-11-16 02:02:47 UTC**.3 GNO loops, all at block26389900:

| Tx | Native net after sender gas (ETH) |
|---|---:|
| `0xf17e6b28384e9919c44e28663d0f8fb4827743035c6c66f9e65680941d045d5c` |0.000458922241062082|
| `0x9c138a754918d96a7a6460f92b19957b6c8095659e23e3ba3a5327bc68042ed9` |0.000294573011773851|
| `0x5d7b1c4884f41cf97a7b96256f7c365f51fe135d42762a10f58993f884bbef62` |0.000256673980719939|

In this window,3loops pay sender0.001044601366303663ETH before gas; sender gas0.000034432132745104ETH; net after tiny native inputs **0.001010169233555872ETH** (~**$1.8357** at current $1817.23 mark, not historical USD). Explicit payments to **0x4838b106fce9647bdf1e7877bf73ce8b0bad5f97** are already excluded from sender receipts; that address equals the capture block's miner, independently checked through relay. Do not group bots through coinbase payments.

One additional bounty tx in the same window nets0.000006657726324ETH (see `keeper-native-results.json`), so the4 measured Carbon calls total0.001016826959879872ETH. This is not whole-operator income or a monthly forecast. Cases per timing type:4unknown; **timing wanted**.

## Funding, payout and sibling limits

- Earliest returned external funding: **0x31d3243cfb54b34fc9c73e1cb1137124bd6b13e1 → sender**,0.01ETH, tx **0x54907e8179b13322ae75c2f71203f2757a3d2a42e5640c40422603c1160bce6b**. Hop2: **0x5dd596c901987a2b28c38a9c1dfbf86fffc15d77 →31d3243c**,1ETH, tx **0x7bc09ffcd8432ebdeffe64b5c54d4ab1441d88811c59b15c437030c239f5bd81**. API evidence is not proof against unsupported transfer categories.
- Hop1 funder's full returned page:463external transfers,61distinct recipients, no pageKey. Their roles are not classified; do not assert61bot siblings. Hop2 funder screen:1000transfers/89recipients with pagination remaining; no boundary or operator merge asserted from this incomplete set.
- Within the3capture txs, executor pays sender directly. The latest100 sender external transfers are executor calls or self-transfers; no distinct downstream payout wallet is proved. Further historical payout/sibling classification remains, using saved API data, not a fresh scan.

## Contract / handoff

Executor read by complete callTracer: flash-funded principal → Vortex trade → GNO DEX liquidation → repay → coinbase and sender ETH payments. No verified executor source is claimed. Previously observed Reserve Folio leg is actor70,11of73 bids in blocks26140177–26370177, evidence tx `0x057dbd4017b9e0960c25f0d8185039ca1e31d63831749bd470166f8c839e2756`; economics of that leg are outside this card.

Farm lacks a demonstrated margin and counted time window. Lead198 contains the30-day request and R12s test; private send is available but does not establish takeability. Evidence: `scratch/research-8de2/auction-nets.json`, per-tx receipts/traces, `funding1.json`, `gas-external.json`, `gas-true-hop2.json`, `gas-funder-siblings.json`, `funding-hop2-out.json`, `payout-external.json`, `actual-auction-block.json`.


## Angle peg-loop continuation (2026-11-16)

The same sender and executor also execute **25 EURA Transmuter swaps in blocks 26194355–26421380**, all no later than block 26348468 (Nov 5). Three sampled complete flash loops at blocks 26348450/463/468 increase sender native balance by **0.000293190791933766 ETH before sender gas, after transaction inputs**, spend **0.000162340971265697 ETH gas**, and retain **0.000130849820668069 ETH (transaction inputs already deducted)**. They pay another **0.000014455089719467 ETH** to each block's miner, already excluded from sender receipts. This is sampled native cash only; the last transaction also leaves 0.026616959458531273 EUROe, unvalued and excluded. No daily extrapolation or counted opportunity claim.

Evidence txs: `0x4ffc775c2df6a8ad5850f5a32b8387a33d05835d3f9c91ed151422a3b72d04a1`, `0x76ec4c787c8399cbe1f14c7e92440a4ea2d79434590d07c4f6392b4b7b5204ae`, `0x1b2ae93e7a901210831023fe4c55a42bb45ff56dc3efc585fe2ff0f2fbdb9b75`. Three additional unknown timing cases; **timing wanted**. Source is the official Angle README's EURA Transmuter. Its approximately 1000–1118 EURC flash principal does not require that amount in the bot wallet. The route mints EURA, sells through Curve and Uniswap, repays the flash advance, then sells surplus EURA to WETH and pays native. Full call traces are in `scratch/research-b299/3..5-trace.json`.

Lead 195 now requests the explicitly untraced flash-size residual, without redoing the caller census. Its earlier conclusion that all top callers were self-settling earning loops is withdrawn: 0cef/addc samples are user redemption routes. EUROe frontend/backend logs also require deduplication; the control balance reads and full explanation are on `infra/bot-census/op-be226af.md`. Class stays D for the sampled tiny route, pending the bounded continuation. Prior Carbon/Reserve and funding evidence above remains unchanged.

Window duration correction: relay header timestamps for blocks 26194355 and 26421380 are 2026-10-15 00:33:23 and 2026-11-15 15:44:11 UTC: **31.6325 days**, not exactly 30. Use this duration for any rate; do not divide this historical window by 30. Headers: `scratch/research-b299/window-{start,end}.json`.
