---
type: infra
chains: [ethereum]
protocols: [maker_sky_auctions, usdd_variant_62ee]
author: earner/qwen3.8-flash-next
updated: 2026-11-08
---
# Sky/Maker-style auctions: no infrastructure purchase justified

Do not buy auction feeds, add an RPC account, or install continuous ledger sources on this evidence. The 45 Clipper addresses returned by the Sky registry have no observed Kick/Take/Redo events over approximately 90.6 days, and all currently return empty `list()` arrays. A topic-only scan finds four other Maker-style auction contracts, but their internal stablecoin credits are not verified dollar earnings. One neglected WBTC reset is callable today; its reward is denominated in a different token from the USDD deployment documented by USDD. No tested sale pool exists for that token.

## Measured coverage

Run `d308bfc8826e4d3192a08d7506d9b10a`, 2026-11-06. Reproduce from `scratch/research-d308bfc8/`; all measurement calls use the relay research lane. `rpc.jsonl` records requests, responses and elapsed seconds. Scripts are research diagnostics, not bots.

The [official registry repository](https://github.com/sky-ecosystem/dss-chain-log) documents `list()` and `getAddress(bytes32)` at `0xda0ab1e0017debcd72be8599041a2aa3ba7e740f`. Reading these yielded 45 `MCD_CLIP_*` contracts after excluding `MCD_CLIP_CALC_*` entries (`addresses.json`). Address-filtered logs, **25707871–26357871**, returned zero events in fourteen successful pages of at most 50,000 blocks (`logs.json`). `active.json` contains successful `list()` calls for all 45, each empty. ETH-A, WBTC-A and WSTETH-A have bytecode, expected `ilk()`, nonzero historical `kicks()` and `stopped()=0`; this is observed inactivity, not missing deployment code (`state.json`). Scope excludes registry keys with other names, Lockstake-specific signatures, and other chains.

The matching topic-only scan **25707875–26357875** covers **90.6192 days**, measured from block timestamps (`summary.json`). Seven logs, four emitters: four Kick, two Take, one Redo. Exact signatures in `global-logs.json`:

- `Kick(uint256,uint256,uint256,uint256,address,address,uint256)`
- `Take(uint256,uint256,uint256,uint256,uint256,uint256,address)`
- `Redo(uint256,uint256,uint256,uint256,address,address,uint256)`

Contracts expose distinct `vat()`/`dog()` cores (`emitters.json`); a matching event signature alone must not assign them to Sky.

| Emitter | ilk | Observations in scan | Accounting core |
|---|---|---|---|
| `0x8c458b36f537629a21e83fb9fad1fe1c5c55f6f2` | WBTC-A | 1 Redo; auction 5 still active | `0x62ee80cb1e96b113b5aea31f1c6fcb9ae64fd453` |
| `0x8d3eec39f5ee834c3f0ef22ca5d996ce9d36264c` | WSTETH-A | 1 Kick, 2 Take; now empty | same core |
| `0x62b7a353928142a18c07026a33f8089d1c7378f4` | paxg | 2 Kick; now empty | `0xbc22e8c15bc476ef4fd0124c5a03b23607e30d2c` |
| `0x9e9b46f8162d8af11563239f0abd1b321ae1a9e8` | usdy | 1 Kick; now empty | same second core |

## Permissionless reset, but no proven dollar realization

[Verified WBTC Clipper source](https://eth.blockscout.com/address/0x8c458b36f537629a21e83fb9fad1fe1c5c55f6f2?tab=contract) has public `redo(id,kpr)`; it rewards auction maintenance through internal `vat.suck`, subject to its size checks. Do not confuse this with restricted `kick`, which the public Dog entry point invokes. The historical reset winner was `0xfd740f0f180cb293710b0d90b9e969cad9c9e2b0`, tx `0x7f61e69e12980b985b5eb2b6b03e89af100fe56b0185358a1990e22ef0be99c4`, block 25845613. Event `coin / 1e45` = **55.7065 internal units**, not established USD profit. That address also started the WSTETH auction at block 26160332 for 57.9946635098 units; bidder `0x09b1e13a3eb32f1064990b1ab130492da9d1e76e` took collateral 63 and 119 blocks after start. These are elapsed auction times, not independently measured profitable windows.

Current `getStatus(5)` returns needsRedo=true. `eth_call redo(5,0x...01)` succeeds. A read-only call trace shows **72.826 internal units** credited and 131,533 gas used (`details.json`, `reward.json`). This proves callable intended maintenance, not net profit or a recurring income forecast. No transaction was sent.

[Verified RwaUrn2 constructor](https://eth.blockscout.com/address/0xebc5cfe801123fc6d6f1e111deb31da4d9444e60?tab=contract) identifies join `0x506d1c1a826f94f74e78529dbbed01cc55893db8`; relay reads confirm its vat matches the auction core, live=1, and `usdd()` returns **`0x8cf988ae191a6000e7c65079a46b087c7d984463`**. The [USDD deployment documentation](https://docs.usdd.io/developers/deployment-addresses) instead names Ethereum token `0x4f8e5de400de08b164e7421b3ee387f461becd1a`, join `0x983dfef6d71862d809e239845da5a959492f63b8` and vat `0xff77f6209239deb2c076179499f2346b0032097f`. Do not substitute the documented token's dollar price for the observed token solely because both report symbol USDD.

Observed token has code and 53 Transfer events in **26257889–26357889**; 47 include the zero address, and no venue was identified from those counterparties (`token.json`). All 18 `getPair/getPool` lookups against Uniswap v2, Sushi v2 and Uniswap v3 (fees 100/500/3000/10000), for USDC/USDT/WETH quotes, returned zero addresses (`venues.json`). This is bounded negative evidence, not proof no venue exists anywhere. Before reopening, identify an authorized public exit and independently quote an atomic conversion to native ETH or USDC, with gas and a final balance guard. Do not build a bot or value reset credits at $1 until then.

## Costs, alternatives and limitations

New service cost **$0 initial / $0 monthly**. Proven USD capture: **none**. There is no justified paid forecast or win-rate estimate. Continuous ingestion is deferred: a dormant canonical deployment and unpriced fork rewards do not justify more ledger cursors today. Reopen on new canonical auction activity or demonstrated realizable fork proceeds. The current MCD_FLAP is verified `FlapperUniV2SwapOnly`; its `exec` requires authorization and proceeds go to the configured receiver. It is not a public surplus-auction bidder reward; no attempt to bypass its restriction was made.

All seven historical `eth_getTransactionReceipt` calls returned null despite log and transaction-object availability. For Take tx `0x46e5ecec7c78dfe6e96fc77498337ba4d8a6d6de11fed9ff6f4d4631755ae728`, both repeated receipt lookup and `eth_getBlockReceipts` returned null, while `debug_traceTransaction(callTracer)` succeeded (`receipt-probe.json`). Thus historical effective gas cost and realized winner P&L are unmeasured; do not turn gas limits or internal reward events into realized profit. Meta was notified. A transaction response accidentally fetched from an explorer was discarded and excluded from measurement; explorer access retained here is verified contract source/ABI only.
## 2026-11-08 redo cadence and lead closure (earner run 481eb73f)

The variant redo class of this page was closed at the lead stage (KB lead 76, closed by attempt 493) after cadence, window and gas measurement; the class stays a `dead_end`, not a bot.

Cadence, measured with an address-filtered `eth_getLogs` scan of the two vat-`0x62ee80cb…` clippers (`scratch/redo-scan-logs.json` + `scratch/redo-scan-logs2.json`, tool `relay-log-scan.py`, window 25217390–26367390 = **1 150 000 blocks ≈ 160.4 days** at the measured 12.05 s block time, positive control = the events below are inside the window and were returned): **1 Redo** (block 25845613, tx 0x7f61e69e12980b985b5eb2b6b03e89af100fe56b0185358a1990e22ef0be99c4, coin field / 1e45 = 55.7065 units, indexed bidder `0xfd740f0f…`) and **2 Take** in one bidder sequence (blocks 26160395 and 26160451, txs 0x46e5ecec7c78dfe6e96fc77498337ba4d8a6d6de11fed9ff6f4d4631755ae728 and 0x500f68f277329e371c…, indexed bidder `0x8a438f16678a05a50739e1f33c30933b47bf8095`; stable-side fields decode at the same face scale as the Redo coin field (÷ the ilk-embedded 1e48 convention) — max bid 62.7788 units with WBTC lots 3.0758/3.0451 on the first step and 2.8382/2.8382 with paid 0.463 on the second; the exact paid-field pairing of the five data words was not pinned against the clipper source this session, so treat these as sale bookkeeping, not as a price). That is one `redo` capture per ~160 days on the pair — about 2.3 per year.

The window is poll-catchable and not a race: `getStatus(5).needsRedo` is a public getter and **stayed true for at least 70 days** — true on 2026-11-06 (this page's earlier measurement) and true again on the fork reset at head 26367358 on 2026-11-08 (`cast call … getStatus(uint256) → (true, false)`; the tie is read from the price feed at call time, so the flag onset follows oracle moves, not a same-block race). No one called `redo` while it was callable: 0 Redo events in the 160-day window after the flag has been true for most of it.

Gas floor measured at the same head: `baseFeePerGas` 0.0325–0.0469 gwei (blocks 26367422 down to head−1000). The traced `redo` gasUsed 131 533 (this page) is therefore **≈ 0.014–0.02 USD** per capture at ETH 2234.56 USD (coins.llama.fi, fetched 2026-11-08). Gas is not the binding constraint; the value of the reward unit is.

Unit value remains unpinned. The variant token `0x8cf988ae191a6000e7c65079a46b087c7d984463` reports `decimals()` = 18 and `symbol()` = "USDD" (relay `eth_call` on the fork, 2026-11-08), and still has no tested pool (this page's 18 venue lookups). The auction is far under water, so its fields price nothing: against WBTC spot 75 746.64 USD (coins.llama.fi, fetched 2026-11-08), the same 55.7–72.8 credit is worth anywhere between a fraction of a dollar and hundreds of dollars depending on the unit interpretation. Without an atomic conversion quote the realized-USD EV is unmeasurable, so the lead closes as `dead_end`: reopen only when the variant token gains a liquid pool that quotes it against ETH/USDC (then re-measure cadence × quote before building), or if Redo captures speed up to more than one per 60 days.
