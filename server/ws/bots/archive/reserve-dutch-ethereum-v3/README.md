# reserve-dutch-ethereum-v3

Rebuild of reserve-dutch-ethereum-v2 under a new id per `decisions/human/2026-11-12-live-bots-zero-sends.md` item 1 (the human stopped v2 on 2026-11-12 with `gate stop` after its first natural capture reverted all 27 live sims with `PROCEEDS_LT_BID`, zero sends — attempt 906). No code change: `bot.js`, `run.sh`, the executor artifact and the runtime pin are copied from `bots/archive/reserve-dutch-ethereum-v2/` (its `state/executor.json` left out per the copy rule). The strategy, executor and every loss bound are the archived bot's (see `manifest.yaml` fork_evidence + review_note10).

## Why v2 was stopped (structural, not timing)

The Reserve revenue Dutch auctions settle only **2.4–3.15 % above their floor** (the captured trade 0xa23ea23f settled at 1.0038 ETH+ per weETH over a 0.98125 floor), while the executor's sell-side venue — the CurveStableSwapNG ETH+ pool `0x2c683fAd51da2cd17793219CC86439C1875c353e` — sits about **9 % away from parity**: forward `WETH -> ETH+` ≈ 0.9083 at the capture balances. Entry above parity minus exit below parity is negative whatever the poll timing, so the class is stopped until the pool moves toward parity. The route reopens only when the forward `get_dy` reaches the settled Dutch price (about parity).

## Exit exchange rate, measured with numbers (decision 2026-11-12 item 1)

Pool `get_dy` reads against the pool's 1e18 units (research-lane `eth_call`, selector `0x5e0d443f`):

- 2026-11-11T21:3xZ, head 26395103 (run 51c94d8d): forward `WETH -> ETH+` **0.90781x**, reverse `ETH+ -> WETH` **1.10109x**. The pool has not moved toward parity since the capture; the route is closed today.
- 2026-11-11T23:0xZ, head 26394836 (run 5036b3b0, this fix session; `get_dy(i,j,dx)` is the 3-arg form `0x5e0d443f(i,j,dx)` with dx 1e18 — the 2-arg call reverts): forward **0.907811x**, reverse **1.10109x** — unchanged since placement; the route is still closed (settled prices ~1.004).
- 2026-11-11 10:1x–10:3xZ, trade 0xa23ea23f balances (attempt 906): forward **0.9083x** — below the 1.0038 settled price; every live sim reverted `PROCEEDS_LT_BID`.
- 2026-11-10 fork state at reset 26348315 (fork_evidence): forward leg **0.9083x**, reverse `get_dy 0->1` **1.1006x** — the payout converts the surplus at 1.1006, the round trip cancels to ≈ 1.0; the settled-price proof is green on that state.

## Past settled auctions and the settled-price fork proof (success + revert)

- Trade `0x527dc250` (sell weETH, buy ETH+): settled block **26348316** at **1.0046 ETH+/weETH** (1.3767 ETH+ for 1.3704 weETH, ledger `reserve_revenue.settled`). Fork proof on the shared ethereum fork at reset **26348315** (the trade unsettled, the executor bids the live Dutch price ≈ the settled price): success tx **0xdf8aacea3f05e86b0c2e9c8bf7db84aaaf26999b6b73261041d101326bd93af6** status 1, owner wallet credited **+79598335709697 wei native ETH in the same tx** (balance delta positive, executor left at 0 — success paid as native, not ETH+). Zero-profit revert tx **0x11456e2005460027319a1e2f2ec257d1dafb73f8** (`minProfitBuy 1e27`): `NO_PROFIT` reverts BEFORE settlement, executor balance 0. Both re-verified with the current artifact and runtime pin by the rerunnable `scratch/reserve-bot/proof.py` payoutVariant 0 (rerun 2026-11-10T19:0xZ, run 706b7b07).
- The newest settled auction (trade `0xa23ea23f`, block 26391002 → 26391104, settled **1.0038**) reverted at its own settled price against the live pool on 2026-11-11: the 27 live sims' `PROCEEDS_LT_BID` reverts are the on-site revert case at the newest settled price; the route reopens when the pool forward rate reaches parity (measured 0.9078 today: not yet).

## Time from liquidatable to actually taken (decision 2026-11-12 item 2, per-event blocks and seconds)

Ten incumbent direct fills, **listed per occurrence** (eligibility = the trade's TradeStarted block — the Dutch bid is eligible from the start; take = the settled/fill block; blocks = take − start; seconds = fill-block timestamp − start-block timestamp; data `scratch/reserve-research/fill_windows.json`, run 5036b3b0, built from `auctions.json` start blocks + block headers and `all-direct-traces.json` fill-tx `blockTimestamp`):

| Fill tx | Start block | Take block | Blocks | Seconds |
|---|---:|---:|---:|---:|
| `0xf52b39ff…dd5c7` | 26307060 | 26307151 | 91 | 1092 |
| `0xb311a572…62e1d` | 26307060 | 26307161 | 101 | 1212 |
| `0x6327ef86…64652` | 26329006 | 26329093 | 87 | 1044 |
| `0xee225601…888b0e` | 26329006 | 26329094 | 88 | 1056 |
| `0x095f0a74…af3c8` | 26347756 | 26347857 | 101 | 1224 |
| `0xe80e2583…ffe88` | 26348213 | 26348316 | 103 | 1236 |
| `0x4566dcdf…e81fd` | 26348213 | 26348316 | 103 | 1236 |
| `0xc0cfbbf2…dc734` | 26348213 | 26348323 | 110 | 1320 |
| `0xb1cca461…d896b` | 26348213 | 26348324 | 111 | 1332 |
| `0x6d538bbd…073fc` | 26348622 | 26348726 | 104 | 1248 |

**Minimum 87 blocks ≈ 1044 s, median 102 blocks ≈ 1230 s** (n = 10; several fills share batched starts, the ledger's `reserve_revenue.started` carries each trade's own start). Auctions run 1800 s. The bot polls every **180 s** (widened from 45 s 2026-11-11T23:1xZ per the review's cheap-polling blocker; the table above is what justifies the interval) and a simulate + send lands in ~5–6 blocks: worst-case detection-to-inclusion ~240–300 s after the pair start, still ≥700 s ahead of the earliest measured incumbent take, so **every counted occurrence is poll-catchable** under the decision's condition (the class is not a same-block race; the live failure was margin, not speed). A later bid is also strictly cheaper: the Dutch price decays at 4.632e-5 of bid value per second (attempt 214), and the positive independent margin spans the whole 1800 s auction (windows 48965–60552 s, wiki `infra/reserve-revenue-auctions.md`).

## Target pair count over 12 days (decision 2026-11-12 item 1)

Ledger `reserve_revenue.started`, cursors verified at head 26391557 (attempt 906 census): **42 TradeStarted over blocks 26307060–26391002 (12 days, 3.5/day), of which the bot's sell=weETH `0xcd5fe23c` / buy=ETH+ `0xe72b141d` pair is 2** (cadence 1 per 6.8 days; both settled, at 1.0046 and 1.0038 ETH+/weETH). The class runs 17 distinct sell→buy pairs across 10 sell tokens; widening past weETH/ETH+ multiplies the cadence ~21x but inherits the same exit handicap (one swap leg per sell token into the buy token).

## RPC and Alchemy cost per day (decision 2026-11-12 item 6)

Poll cycle every 180 s (was 45 s; widened in this fix session per the review's "make the closed-state polling cheap enough" blocker): one `eth_blockNumber` (~26 CU) + two `eth_getLogs` cursor pages (~200 CU each) + `eth_gasPrice` + one oracle `eth_call` (~30 CU each) per cycle ≈ 480 cycles/day: **~100k CU/day ≈ 0.05 USD/day at 1M CU ≈ 0.53 USD** (was ~400k CU/day ≈ 0.21 USD/day). Expected value, counted only on the decision-item-2 windows above: the pair pays ~1 event per 6.8 days; the class realized 4.14–16.04 USD per ~7 days across all bidders (lead 19) — ≈0.2–0.4 USD gross per fill at incumbent entry — and a bot bidding early in the 1800 s decay pays less per event than the incumbent, capped at ~1 pct of the lot (attempt 214): at the pair's ~1.37 ETH lots that is a per-event gross of cents to tens of USD, so **pair EV ≈ 0.03–0.1 USD/day while the pool is at parity and $0/day while it is imbalanced** (measured forward 0.9078 today). The waiting cost is now ~0.05 USD/day: at or below the pool-open EV, an order of magnitude below it at 45 s polling. Promotion must wait for a paper capture that shows a positive `min_profit_wei` sim (i.e. the pool reopened); this session changes only the poll interval and the derived staleness cap — the executor, artifact, runtime pin and loss bound are untouched.

## Reviewer notes

- Paper log semantics: with the pool at 0.9078, a capture that settles while the pool is imbalanced must show `simulate` reverts with `PROCEEDS_LT_BID` at settlement — a correct guard against the pool state, not a detection failure. An `ok` sim must carry `min_profit_wei >= 2 x 1050000 x gas_price_wei`.
- Fork: `scratch/reserve-bot/proof.py [payoutVariant]` self-leases the shared ethereum fork, releases at exit, and re-takes `executor-runtime.hex` from the deployed fork instance (`pitfalls/executor-paper-sim-override`).
