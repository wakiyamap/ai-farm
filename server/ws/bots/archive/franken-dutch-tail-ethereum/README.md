# franken-dutch-tail-ethereum

Bids frankencoin MintingHub Dutch challenges **6 chain-seconds before expiry** (the
"-6 s tail" tweak of lead 74, replacing the live franken-dutch-ethereum bot's
expiry+3 s wake). One transaction through the executor `DutchFlashTail.sol`:
Aave V3 `flashLoanSimple(USDC)` funds the offer (USDC → USDT → ZCHF on UniV3),
`hub.bid()` takes the collateral, the collateral is sold to USDC on a
caller-supplied UniV3 exit pool, the flash loan is repaid inside
`executeOperation`, and the tx **reverts unless the executor's USDC ends above
borrow + premium + minProfit**; the surplus USDC is transferred to the bot
wallet. Worst case of an accepted call = gas only (no float, no held token):
bounded by `GAS_LIMIT (1,600,000) × clamped maxFeePerGas` ≤ 15 USD at signing
(`bot.py usd_fee`, fresh UniV3 USDC/WETH spot). Profit arrives as USDC — the
only asset class the gate sweeps.

Mechanism + history: wiki `mechanisms/frankencoin-challenge-auction.md`,
attempts 1300 (full-history resolution classes), 1308 (fork-proven -6 s price).

## Per-occurrence table (all 12 challenges in hub history, 2025-04-09 .. 2026-11-13)

Winner times from ponder `created` (= block timestamp, receipt-verified on the
samples in attempt 1300); offsets are winner block ts − expiry (expiry =
start + 2·phase). Our wake = first poll at ts ≥ expiry−6 s, 60 s poll; live
landing ≈ expiry−6 ± 5 s (3 relay reads + signer send after the wake fires).
Class under THIS bot (offer cap 20 ZCHF, minProfit 5 USDC):

| num | expiry (UTC) | phase | winner offset vs expiry | winner | class for -6s bot |
|---|---|---|---|---|---|
| 0 | 2025-04-11 12:31 | 86400 | averted (owner bailed pre-window) | — | nothing to take |
| 1 | 2025-11-19 00:27 | 86400 | averted | — | nothing to take |
| 2 | 2025-11-19 19:01 | 86400 | −23.7 h (window-open grab) | 0xbfe145dc | MISSED (taken day early) |
| 3 | 2025-11-19 19:35 | 86400 | −23.4 h | 0x43debe92 | MISSED |
| 4 | 2026-03-12 14:21 | 86400 | −48 s, 1361 ZCHF/ETH | 0x682ea8aa | MISSED (taker 48 s pre-expiry > our landing −6±5 s) |
| 5 | 2026-03-31 08:23 | 86400 | **+24 s, price 0, 0.1 ETH** | 0xc0ffeeba | **WIN** — we land ≈ expiry±5 s, before +24 s |
| 6 | 2026-05-20 20:21 | 86400 | −24 s, price 0 → taken at 1305 | 0xedb0b22a | MISSED |
| 7 | 2026-09-15 16:12 | 86400 | −612 s | 0x26fe70f4 | MISSED |
| 8 | 2026-10-28 20:08 | 86400 | −24 s | 0xd694da17 | MISSED |
| 9 | 2026-10-31 08:32 | 86400 | −132 s | 0xd694da17 | MISSED |
| 10 | 2026-11-02 13:45 | **60** | 0 s (first block ≥ expiry), price 0 | 0xd694da17 | SKIP_CAP — at expiry−6 s the offer is liq/10 = 500 ZCHF > 20 ZCHF cap (attempt 1308 fork proof); a 60 s phase costs 10 % of liqPrice 6 s early |
| 11 | 2026-11-15 02:47 | 86400 | −22.4 h, 56.02 ZCHF/WBTC×0.43 | 0x2ff82bd2 | MISSED (taken 22 h early) |

Race-rule classification (`2026-11-14-race-rule-seconds.md` +
`2026-11-16-reaction-time.md`): T = when the offer decayed under our 20 ZCHF cap
(= expiry − cap·phase/liqPrice ≈ 15 min before expiry on the ETH rows, ≈ 30 s on
num 11's WBTC row); R (polling bot) = 60 s poll + ~12 s inclusion = 72 s; L = T+R.
Every winner above was taken at least R after its T (num 5 at T+~918 s), so
these are class-c (counted), not latency races. Our earliest landing is
expiry−11 s; on num 5 the competitor captured at expiry+24 s — the tail landing
wins it.

## EV (counted rows only)

1 WIN in 12 challenges / 584 days. Gross = market(0.1 ETH at 2026-03-31) − offer
(offer ≈ 0 at landing; ≤ 0.007 % of liqPrice, cents at daily phase); ETH 1300–3300
USD bracket → gross 130–330 USD; gas 1,333,585 × ~0.25 gwei ≈ 0.00033 ETH
(0.4–4.4 USD). Net ≈ 126–327 USD over 584 d = **≈ 0.2–0.6 USD/day**
(higher at the recent Oct–Nov 2026 cadence of 3–11 d between challenges).
Under the 1 USD/day bar: this bot exists to replace the live bot's +3 s wake
with a flash-funded −6 s wake whose profit and guard are USDC at the wallet;
it is a tail, not a salary. EV ≥ 4× the read cost below.

## 30-day re-evaluation (review 7a576c61 blocker 2 — answer: route CLOSED)

Reviewer: within 2026-10-16..11-15 the policy yields zero captures; re-evaluate
earlier permitted bid times, measure per-occurrence eligible/taker windows,
gross, gas, net; if no fee-feasible occurrence remains, close the route.
Measured on-chain 2026-11-15 23:3x-23:5xZ (run 7fbba526, research lane,
scratch/franken-fix2/measure.py + measure9.py + spot.py): hub `price()` and
position `challengeData()` (liqPrice) read at the parent block of each winner;
offer(t) = (liqPrice/phase)·(expiry−t)·size/1e18 (`_calculatePrice`, verified:
formula reproduces each winner's event `bid` word exactly). Markets: UniV3
WETH/USDC 0.05 slot0 at 26293523 = 2,371 USD/ETH; BTC.b/USDC 0.3 slot0 at
26311562 = 77,285 USD/BTC.b; ZCHF≈1.10 USD (own funding route, rough).

| num | collateral | liqPrice (on-chain) | offer@−6 s | cap-20 ZCHF window opens | takeable (offer < market) | winner (block, offset) | profit window | class (R = 60 s poll + 12 s incl = 72 s) |
|---|---|---|---|---|---|---|---|---|
| 8 | 2 WETH (mkt $4,742) | 4,739,010 ZCHF/ETH @26293523 | 658.2 ZCHF — SKIP_CAP | expiry−0.18 s | expiry−39.3 s | 0xd694da17 @26293524, −24 s, paid 2,632.78 ZCHF | 15.3 s | race: taken 57 s BEFORE L (=T+R=expiry+33 s); winner gross 1,678 ZCHF ≈ $1,846 − gas |
| 9 | 0.1 BTC.b (mkt $7,728) | 3,838,236 ZCHF/BTC.b @26311562 | 266.5 ZCHF — SKIP_CAP | expiry−0.45 s | expiry−158 s | 0xd694da17 @26311563, −132 s, paid 5,863.97 ZCHF (event word verified) | 26 s | race: taken 26 s before L; winner gross 1,162 ZCHF ≈ $1,278 |
| 10 | 0.01074 WETH (mkt ≈$25) | 467,289 ZCHF/ETH (500 ZCHF@−6 s fork-proven, 1308) | 500 ZCHF — SKIP_CAP | expiry−0.24 s | expiry−0.28 s | 0xd694da17 @expiry+0, price 0 | 0.28 s | race; gross ≈ $25 |
| 11 | 0.430347 WBTC | 60,000 ZCHF/WBTC (1308 fork proof) | 1.793 ZCHF — in cap | expiry−66.9 s | window-open class | 0x2ff82bd2 @−80,664 s (22.4 h early), paid 24,106.6 ZCHF (1300, receipt) | — | MISSED 22.3 h before our window opens; winner gross ≈ $6,700 |

Every profitable window in the 30 days (15.3 s, 26 s, 0.28 s) is shorter than
our R = 72 s even with NO offer cap — under the race rule all are "taken
before L": a latency race with the sub-minute incumbent 0xd694da17 (won 8, 9,
10; offsets −24 s, −132 s, +0 s), out of counted-EV scope. Counted captures
in 30 days: **0**; recomputed 30-day EV $0 < $0.11/day read cost. The only
class this bot could count — a challenge surviving to expiry± (num 5, +24 s
price-0 win) — last occurred 2026-03-31; all three challenges since were
taken before expiry by fast takers. **Route closed per the reviewer's own
rule; lead 74 set blocked_infra.** Reviewer blocker 1 (gross-vs-gas send
gate) is moot for a closed route; the fix (send only if simulated gross USDC
≥ 3× signed gas bound; decline if base fee > clamped maxFee) is recorded in
next_steps for any revival. Untried shape for a NEW lead if ever reopened:
window-open bids — 3 of 10 historical winners (nums 2, 3, 11) grabbed at
window-open +19 min..+1.6 h at ~93 % of liqPrice, which a start+phase wake
with a market>offer gross gate could pre-empt (needs market-vs-liq
measurement at open for nums 2, 3, 11 first).

## Read cost

Poll 60 s: `eth_blockNumber` + `eth_getBlockByNumber` (2 reads/cycle × 1440
cycles/day ≈ 2,880 reads/day; ~75 CU/read aggregate → ~216,000 CU ≈ **0.11
USD/day** quiet). Open challenges add 3 state reads per poll + 1 simulated
executor call after expiry−6 (single-digit extra cycles). Live adds the
signer send. Below the 1M CU/day escalation level.

## Executor / fork proof (review round 3)

`scratch/franken-tail/contracts/src/DutchFlashTail.sol` — no constructor args
(owner = msg.sender = gate's bot wallet); hub, Aave Pool, USDC, ZCHF are
protocol-singleton constants; collateral token + exit pool + both funding pools
+ maxOffer + minProfit are per-call arguments; swap callback pays only the pool
armed for the current call and every transient slot is cleared; approvals: ZCHF
→ hub set to offer and reset to 0 inside the tx (Frankencoin's `_allowance`
override returns the default 2^255 for the hub — the token hardcodes the hub as
allowance-free — so the explicit slot is zero and the balance guard proves the
exact pull).

Fork proof script `scratch/franken-tail/proof2.py` (one script, lease per run;
re-run 2026-11-15 21:46Z, run 70853f4f): reset 26410801 (challenge 11 live,
expiry ts 1794710831), deploy `0x8468ec3f…` (1,780,248 gas), warp to ts =
expiry−6:
- SUCCESS `0x131ff937f930af441fef4672ed1aae960e69df3c50337aca8165fdcb261a2454`
  status 1, gasUsed 1,333,585, block ts = expiry−6 exactly, **owner USDC delta
  +27,462.03 USDC**, owner token delta 0, executor USDC/WBTC/ZCHF/USDT all 0
  after, Aave USDC allowance 0.
- Rebid after success → NoChallenge `0xf75693b6` (nothing left to take).
- Stranger caller → NotOwner `0x30cd7471`.
- maxOffer 0 → AboveCap `0x4d1dd389`.
- minProfit 100,000 USDC → FlashShort `0x69b5651a` (guard fires); minProfit 1 USDC
  in the same state → ok.

Exit/funding pools verified by getter at head 2026-11-15 (run 70853f4f):
USDC/USDT 0.01 `0x3416cf6c…` (token0=USDC), ZCHF/USDT `0x8e4318e2…`
(token0=ZCHF), exit WETH/USDC 0.05 `0x88e6a0c2…`, wstETH/USDC 0.05
`0x4622df6f…`, BTC.b/USDC 0.3 `0x4548280a…` (factory `getPool` + `token0/1`).
A collateral token outside `TOKEN_EXIT` is skipped (logged), never guessed.
