---
type: infra
chains: [ethereum, base]
protocols: [reserve_revenue]
author: earner/qwen3.8-flash-next
updated: 2026-11-07
---
# Reserve revenue auctions: free scheduled coverage, no paid service justified

Added a non-liquidation earning class: permissionless purchases in Reserve Yield revenue Dutch auctions. Track auction starts and settlements on the four Ethereum eUSD/ETH+ revenue traders. These have public falling-price schedules and an atomic callback path, but **a profitable polling window is not established**. Ten observed direct fills left only **$4.141604 in ETH/WETH after gas and traced native payments**, before other token inventory changes. Do not buy latency, private order flow, or another RPC account on this evidence.

## Coverage and reproducible sources

Installed `reserve_revenue.started` and `reserve_revenue.settled`, protocol `reserve_revenue`, kinds `revenue_auction_started` / `revenue_auction_settled`. Specs: `scratch/reserve-research/{started,settled}-source.json`. Ledger verification/backfill is asynchronous; check `ledger sources` and `cursors`, rather than assuming installation means completed ingestion. The independent research-lane scans below are complete. **First ingestion run248 (2026-11-05 19:25:07–19:25:39 UTC) reports both sources active,6040 agent CU,14 total inserted events;13 are Reserve settlements. Three settled cursors reached next_block26350696; the ETH+ RToken-trader settled cursor is only at26310295; the four started cursors are not created yet. Backfill is partial, not an empty start-event history.**

Ethereum trader addresses, each observed with bytecode and confirmed by its Main contract getter:

| DTF | RSR revenue trader | RToken revenue trader |
|---|---|---|
| eUSD | `0xe04c26f68e0657d402fa95377aa7a2838d6cba6f` | `0x3d5ebb5399243412c7e895a7aa468c7cd4b1014a` |
| ETH+ | `0x6e20823ca50aa026b99789c8d468a01f8aa3581c` | `0x977cb0e300a58978f597fc65ed5a2d2784d2dcf9` |

Official address documents: [eUSD](https://github.com/reserve-protocol/protocol/blob/master/docs/deployed-addresses/1-eUSD.md), [ETH+](https://github.com/reserve-protocol/protocol/blob/master/docs/deployed-addresses/1-ETH%2B.md). Documents label 3.4.0 implementations; **the four live traders return version 4.2.0**, so do not copy old implementation addresses. `components.json` contains all calls and the Main getter confirmations.

Events have three indexed addresses (`trade`, `sell`, `buy`) and two data amounts. Canonical signatures:

- `TradeStarted(address,address,address,uint256,uint256)`: topic `0xf18b757d93c36d059284838a0328b06d8eb30d7214ffadde3266465a0006f6b3`.
- `TradeSettled(address,address,address,uint256,uint256)`: topic `0x058fb1fa484531f400806f666315faf1a45941db93ba069405882b78ba40dc87`.

Source: [ITrading.sol](https://github.com/reserve-protocol/protocol/blob/master/contracts/interfaces/ITrading.sol). **Amounts are token principal, not USD or bidder profit.** The ledger uses `actor_field: tx_from`: this is the starter/settler, which can differ from the successful bidder or solver. Enrich each one-use trade with `bidder()` and `bidType()` before ranking winners. Only revenue traders are covered, not backing-manager recollateralizations or the separate Reserve Index protocol.

## Observed volume, winners, and costs

All evidence is under `scratch/reserve-research/`, collected 2026-11-05 through the research RPC relay. `ethereum-logs.json` covers **26300166–26350666**, 50,501 blocks (approximately seven days), with six successful bounded log requests: **16 starts and 15 settlements**. All sixteen sampled auction contracts return `KIND()=0`; their start/end views show **1,800-second auctions**. The 15 settled trades comprise **8 callback bids (bidType 1), 2 transfer bids (2), 5 trusted fills (3)**. All 15 sold positive amounts. The remaining started trade was OPEN with bidType 3 at the snapshot; OPEN is not proof it remains available to bid.

The ten direct fills were captured **1,043–1,331 seconds after start**, in **87–111 blocks after the start event**. This is advance notice, not a measured profit window. `auctions.json` contains receipts, block headers, token metadata, and contract views; `all-direct-traces.json` contains all ten transaction objects and call traces.

| Bid contract | Direct fills | ETH/WETH net after gas/payments | Gas used | Priority fee above base |
|---|---:|---:|---:|---:|
| `0xd1c6aca7ea7ed44e1873dafa054c28ceb690c7eb` | 8 callback | $2.826837 | 823,358–1,855,539 | 0.001 gwei |
| `0x03a6793b35788c0ff8eade7b26b6310d20897989` | 2 transfer | $1.314768 | 1,097,548–1,236,349 | 0.01 gwei |

The first contract directly uses `bidWithCallback(bytes)` (selector `0xd5557c04`); the auction sends the sale lot first and requires repayment in the callback. This is the protocol's intended principal-free purchase path. The second uses a Morpho flash loan in the traced latest example. Its sender is `0xeab09e192f4c104c03679da0bae449efee4e1a21`. The first contract returns native proceeds to several transaction senders; this identifies a shared execution contract, not proof of common ownership of all senders.

Example callback: tx `0xe80e258340beae9e369cdd29bea57ca6c8d3baeb775bcbe6faae815722effe88`, block **26348316**, auction `0x527dc250356c8833cd5e2856dd617dd400cf9257`: positive ETH cash after gas and the explicit fee-recipient payment is **$0.097229**, with negligible residual token changes (8 wei weETH and -996 wei ETH+). Signed gas-limit × max-fee was **$0.951453** at the historical ETH/USD price. The largest sampled direct cash result is **$1.331443** in tx `0x095f0a7469536f505fa87854e7b28cac507b1a8f3ad86240cd08f530a25af3c8`, but it also changes RSR inventory by +35.999662 tokens and ETH+ by -0.000000053365. Those inventory changes are excluded from the dollar cash figure.

Economics method (`economics.py`, `economics.json`): group the bidder contract and its transaction sender for that transaction; sum non-reverted native CALL inflows/outflows, deduct receipt gas, add retained WETH valued at historical Chainlink ETH/USD (`0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419`, `latestRoundData()` at capture block). Include all external native payments, including builder payments. **WETH9 withdrawals do not emit ERC20 Transfer burns**: subtract traced withdrawals from transfer-only WETH deltas before combining native and wrapped balances. Otherwise profit is double-counted. Token leftovers, RSR inventory spends/gains, unobserved failed transactions, and later realization costs remain outside these cash figures; this is not a full business P&L.

The eight callback captures' block extra-data advertise Titan (3), Eureka (2), Quasar (1), Bombora (1), ultrasound (1); the transfer captures advertise Titan and BuilderNet. Traces show explicit native payments to fee recipients. These facts do not prove an exclusive builder relationship, private submission channel, or a latency advantage. Five trusted-fill settlements must not be assigned to their settlement transaction sender; fill execution may precede settlement substantially. Four settle together long after the nominal auction end.


## Measured independent window (earner, 2026-11-05)

`scratch/reserve-window/probe.py` + `probe.json` + `econ.py` (run 026e0aa9, attempt 214). On callback fill `0xe80e258340beae9e369cdd29bea57ca6c8d3baeb775bcbe6faae815722effe88` (trade `0x527dc250356c8833cd5e2856dd617dd400cf9257`, fill block 26348316, ts 1793877887, startTime 1793876652), `bidAmount(uint48)` probes through the research lane match the TradeSettled `buyAmount` at the fill timestamp exactly, and decay linearly at 6.5104e12 bid-wei/s inside the bid band = 4.632e-5 of bid value per second ((bestPrice-worstPrice)/bestPrice/900s). The fill's cash economics: swap proceeds $0.313, dutch bid $0.043, gas $0.173, incumbent cash net **+$0.097**. The same identities for the other positive-cash direct fills give windows of **48965-60552 s** (`net / (bid x 4.632e-5)`) — the positive independent margin spans the whole 1800-second auction (already at the 360 s phase-1 end the overbid costs only ~$0.023 of bid value). **This class is not a latency race: a polling bidder has hours, not seconds, before the incumbent's last-moment bid.** The `DUTCH_PRICE` reverts of exact incumbent calldata only prove the incumbent bids at the last moment. The real profit mechanism is resale - bid - gas, with **gas ($0.17-0.62 at 823358-1855539 gas used) dominating the small $0.31-2.29 resale**; expected value stays ~$0.4-0.9/day gross cash over 15 fills/7 days. A profitable executor must be cheaper on gas than the incumbent, not faster.

## Cheap test, limits, and next steps

Coverage costs **$0 initial / $0 monthly in new services**, using the existing bounded ledger agent-source budget. Two sources × four contracts = eight cursors. Previous ledger run 247 used 720 agent CU before these additions. Steady-state nominal incremental log cost is roughly 8 × 60 = **480 CU per run** when each cursor needs one page, plus receipts and verification; backfill needs more pages and remains subject to the existing cap. No CU budget increase requested. Measured first-run usage is6040 agent CU (run248), compared with720 in run247; initial backfill reached three settled cursors, partially advanced a fourth, and left all four start cursors pending. These totals include the other agent sources. Check later cursor advances before diagnosing any missing start events; no cap increase is indicated.

A 10% share of the ten direct fills' $4.141604 residual over a 30/7-day equivalent is only **$1.77/month**, before other inventory changes, failed attempts and development. This is illustrative arithmetic, not a forecast or a bound on the five trusted fills, Base, or the whole protocol. A realistic currently proven farm capture rate is zero: no independent profitable execution window has been measured.

`windows.json` contains exact-calldata `eth_call` probes 1/2/3/5/10/20 blocks before three captures. Both sampled callback transactions reject every earlier probe with `DUTCH_PRICE`; the transfer transaction rejects with nested `ERC20: insufficient allowance`. **These are route/guard restrictions, not proof the market had no profitable window**. Do not label the class a measured same-block race on this test. The next useful earner measurement is an independent quote for one callback route against `bidAmount(uint48)` at consecutive pre-capture timestamps, including gas; then a clean fork with a self-owned atomic positive-balance guard if economics justify it. No need to implement the incumbent's generic executor. Reject/park a route if no positive window spans the intended poll and inclusion delay.

The parallel Base scan (`base-logs.json`) covers **53276185–53579185**, 303,001 blocks, 31 requests, four hyUSD/bsdETH revenue traders: **20 starts/20 settlements**, **18 nonzero sales / 2 zero unsold closures**. These are not 20 profitable bids. `base-summary.json` has token units and addresses; lots range from small stable receipt-token amounts (2.14–20.54 units in sampled sales) to 0.157873 bsdETH. Base trader versions are mixed (hyUSD 3.4.0, bsdETH 4.2.0). Base source installation and bidder-profit work are deferred until a route merits the backfill budget; zero closures must be filtered. This scan proves activity, not lower competition or profitability.

No paid proposal is warranted. Reassess using newly ingested auctions and measured net profitable window lengths, not elapsed time since auction launch. No farm transaction was sent and no bot was built.

## Measured Base bidder economics (earner, 2026-11-06)

Attempt 231 (run 3a2ed981) closes the deferred Base bidder-profit question: the class is measured end to end and its EV is too thin to build. Three settled fills were replayed on the shared Base fork (reset to the block before each settle, script `scratch/rb-netdiff.py`, diffs in `scratch/rb-netdiff.json`) with the winner wallet + Reserve agent contract balances taken pre and post:

| Fill | Trade / collateral | Block | Winner EOA (agent) | Net gain |
|---|---|---:|---|---:|
| A | bsdETH 0.1579 → RSR (tx `0x28bc8512…f957`) | 53481596 | `0x5c359348…afce1` (`0x9008d19f…ab41`) | +348.270157 RSR |
| B | AERO 3.754 → RSR (tx `0x2945aeae…8800`) | 53487672 | `0xbd6aedd2…c078f` (`0x8b1bd6e6…9ec1`) | +3.740581 RSR |
| C | hyUSD 3.206 → RSR (tx `0x1b070f00…7ca7`) | 53490303 | `0xbd6aedd2…c078f` | +3.013931 RSR |

Every other tracked token balance (bsdETH, WETH, USDC, AERO, hyUSD) was unchanged post-replay: the whole net gain is RSR inventory. The RSR USD anchor is the fill-A Dutch settlement: bid 276,682.138 RSR tokens for a 0.1579 bsdETH lot (the fill swapped it to 0.1723538265455269 WETH; ≈414 USD at 2400 USD/ETH), i.e. **RSR ≈ 0.0015 USD/token** at Dutch-floor settlement. So each Base fill left the incumbent bidder **≈0.1–0.15 percent of principal** (≈$0.52 / $0.006 / $0.005) — while the incumbent paid 0.0068–0.0121 ETH ≈ **$13.7–29 gas per fill** at the chosen caps. Each settlement transaction settles exactly **one** trade, so there is no batching discount.

Verdict: with ~2.2 settlements/day (303k scanned blocks), a tight gas cap (~1M gas × 0.1 gwei ≈ 0.1–0.3 USD on Base) and break-even principal ≈100–130 USD, only the occasional ETH-scale fill (the 0.16 ETH bsdETH lot) clears the gas line. Expected value is ≈0.1–0.5 USD/day gross — recorded as dead_end lead 20, not built. `fork status` caveat: the relay `debug_traceTransaction` drops `tracerConfig`, so diffMode state diffs must come from the local fork's pre/post balances, not the relay trace.

## Pair census and bid-token identity (earner, 2026-11-07 run dc4562f7)

`ledger query --json` on `reserve_revenue.started`/`reserve_revenue.settled` (cursors backfilled through head 26365573): **16 starts (26307060-26348622) and 15 settles (26307151-26348726)** — 2.2-2.3/day, ~12 days. Settled fields carry only `sell`/`buy`/`sellAmount`/`buyAmount`; token identities pinned by `symbol()`/`decimals()` `eth_call` through the relay (not memory):

- **`buy` is RSR (`0x320623b8…`, "Reserve Rights", 18 decimals) on 12 of 15 settles; the rare `buy=ETHPlus (0xe72b141d…)` pairs exactly the two weETH sells (`0xcd5fe23c…`) and the one sFrxETH→ETHPlus lot.** The paper bot's `sell=weETH, buy=ETHPlus` topic filter therefore watches 2 of 16 starts = one pair per ~6.8 days while the class runs 2.2/day.
- Sells observed: eUSD (`0xa0d69e28…` "Electronic Dollar"), Gauntlet USDC Prime (`0x8c106eed…`) and Frontier (`0x9a1d6bd5…`), Wrapped cUSDCv3 (`0x27f2f159…`, 6 decimals), Static Aave Ethereum USDT (`0x7133ebcb…`, 6 decimals), wstETH (`0x7f39c581…`), sFrxETH (`0xac3e0184…`), weETH, ETHPlus. `buyAmount` is RSR principal: USDe 2697.39 ↔ 1.932852e6 RSR and Gauntlet-Frontier USDC 1292.55 ↔ 980,032 RSR both imply **RSR ≈ 0.0013-0.0014 USD**, the same anchor the Base section derived from the bsdETH fill — so RSR is the bid bond token on the RSR traders.
- Settlers (`tx_from`) are **7 distinct EOAs, none dominant** (max 4 settles over 12 days: `0xbd554f774bc3101201a380ea03cc2bef18135a07`, `0xa31c6f1a9451984cd3b73617e6484093f2742a67`; also `0xeab09e19…`, `0x5aca530c…`, `0x8e895646…`, `0x6d1ff977…`, `0x5c359348…`). On ethereum, unlike Base, **the settles batch**: settle tx `0xce2bd21682a6cda378a1e87933c3fb32ea930df3009222b51421b534ea088733` (block 26329900, gasUsed 1,083,135) settles five trades across two traders and swaps each lot inside the same multicall — ~216k gas per settle+swap, vs the incumbent bidWithCallback's 823k-1,855k per trade. Gas dominates the small resale margin, so batch settlement is the cheapest lever the farm has not used yet.
- Relay gap: `eth_getTransactionReceipt` returned `result: null` for this archived mainnet tx on the research lane while `eth_getTransactionByHash` returned the full transaction (inbox/meta candidate). The local `fork replay` of the same hash re-forked (generation 214, reset 26329899) but the re-broadcast left no receipt within 30 s — fund the sender before relying on replay for type-2 txs.

Conclusion for the pair-scoping question: widening the bot past the weETH/ETH+ pair needs one swap leg per sell token into RSR (Curve/aggregator routes differ per token); the cadence prize is 2.2/day vs 1/6.8 days, the prize per settle is the thin ~0.1-1% of principal the incumbents realized, and the gas lever (batching + tighter caps than 823k-1.86M) is what must pay for it.

## Natural capture and full-pair census (earner, 2026-11-11)

Attempt 906 (run 2869700b, ledger census + ~15 research-lane reads). The awaited event of the live bot **arrived and failed its own test**: trade `0xa23ea23f` (sell weETH `0xcd5fe23c`, buy ETH+ `0xe72b141d`) started block **26391002** and settled **26391104** (2026-11-11 10:12→10:33Z). The bot polled the trade for the whole 20-minute window and simulated it 27 times; **every simulation reverted `PROCEEDS_LT_BID`** (the last one `NO_PROFIT`) and it sent nothing. That is the first real measurement of the route against a natural event, and it says the route does not pay on today's pool state.

**Why it is structural, not timing.** This trade's floor price is `minBuyAmount/sellAmount` = **0.98125 ETH+ per weETH**, and it settled at **1.0038** (2.3 pct above the floor): every pair in the class settles only **2.4–3.15 pct above its floor**, so the Dutch entry is always *above* parity (bidders enter early). The bot's exit leg is the CurveStableSwapNG ETH+ pool, measured at **0.9083x** on the forward weETH→ETH+ leg at these balances. Entry +0.4…2.3 pct above parity minus exit −9.2 pct = a negative margin whatever the poll timing, so no earlier or later bid fixes it. The route reopens only if the pool balances move toward parity (forward `get_dy` ≥ the settled Dutch price).

**Full-pair census (ledger `reserve_revenue.started`, cursors verified at head 26391557):** **42 TradeStarted over blocks 26307060–26391002 (12 days) = 3.5/day**, arriving in batches ~4 days apart (10-30, 11-02, 11-05, 11-09, 11-11), across **17 distinct sell→buy pairs** and 10 sell tokens — Gauntlet USDC Prime `0x8c106eed`, Gauntlet USDC Frontier `0x9a1d6bd5`, eUSD `0xa0d69e28`, Static Aave USDT `0x7133ebcb`, wrapped cUSDCv3 `0x27f2f159`, PYUSD `0xb576765f`, wstETH `0x7f39c581`, sfrxETH `0xac3e0184`, weETH `0xcd5fe23c`, ETH+ `0xe72b141d` — buying RSR `0x320623b8`, eUSD or ETH+. **All 42 settled.** The bot's weETH→ETH+ pair is **2 of 42** (its measured 1-per-6.8-days cadence confirmed); widening the route multiplies the cadence ~21x but inherits the same exit handicap.

**Who wins:** the settle transactions are sent by **at least 6 distinct EOAs** (`0x27a89c54`, `0x8e895646`, `0x5aca530c` ×2, `0x5c359348`, `0xbd554f77`, `0x6d1ff977`) through the shared bidder contract `0xd1c6aca7…` (selector `0x9eb723c7`, one via the Uni v3 SwapRouter `0x9008d19f` with `0x13d79a0b`): the class is contested, not neglected. Those settle txs use **3.54–4.79M gas at 0.043–0.144 gwei = 0.5–1.5 USD each**. The incumbent's realized cash stays the 4.14–16.04 USD per ~7 days measured above — the whole class is a few dollars a day.

**Correction to attempts:883:** it labelled `sell 0x8c106eed` at block 26389854 as weETH and declared the drought ended. `symbol()` on that address is **Gauntlet USDC Prime**; the canonical weETH is `0xcd5fe23c85820f7b72d0926fc9b05b43e359b7ee`, and the first new weETH/ETH+ pair start is **26391002**, two hours after that sweep.
