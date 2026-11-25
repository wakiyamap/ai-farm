# bold-redeem-tail-ethereum

Liquity V2 BOLD redemption tail-block bot (lead 117). When a redemption burst
fires (Redemption events at the 6 TroveManagers), redeem in a block after the
last one: buy BOLD at a discount via Morpho WETH flash -> UniV3 WETH/USDC ->
Curve-ng BOLD/USDC, call CollateralRegistry.redeemCollateral, sell wstETH
and weETH back, repay; the executor reverts unless WETH rose by minProfit, so
a failed attempt costs only gas (no builder bid; the winner pays ~130 USD to
coinbase per tail tx, attempts:1298).

Detection: eth_getLogs poll (10 s) over the 6 managers; act when the burst's
last block is behind head (first 1-poll pause; landing T + 18.06 s = poll +
measured send-to-inclusion, infra/reaction-time.md). The 30-day window table
below shows the tail is usually gone by T + 12 s already (absorbed inside the
burst), so detection speed is not the binding constraint - the tail mostly
does not exist after the burst.

Simulation: `eth_call` of the executor **with `from` = the sender** (owner) at
relay `latest`, with a code override = `eth_getCode` of the proven fork
deployment 0x8f7a45ebde059392e46a46dcc14ab24681a961ea (executor-runtime.hex,
sha256 93223618334912f2). The owner-only guard therefore passes in exactly the
live shape (review 2026-11-15 18:12Z fix #1; proofE case C: at head the
from=owner call gets past the guard and reverts at minProfit, proof the
authorisation path works).

**Send gate vs gas (review fix #2):** `redeem()` returns the gross profit
(uint256 WETH). The bot sends only when returned gross > gasLimit x maxFeePerGas
(1,500,000 x 7 gwei = 0.0105 ETH ~ 35 USD at signing price, within the 42 USD
max_loss_per_tx_usd); the guard protects
tokens, gas is paid in native, so without this gate a flat-discount success
could still lose the gas cap (promote criterion for token-balance guards).

Route facts (all pinned, see attempts:1312): exact-input UniV3 = POSITIVE
amountSpecified; callback must PUSH the input token; strict SPL pools need
limits strictly inside (MIN,MAX); weETH/wstETH are token0 of their f100 pools
(sell = zeroForOne true). Registry 0xf949982B91C8c61e952B3bA942cbbfaef5386684.
wstETH/WETH f100 pool 0x109830a1aaad605bbf02a9dfa7b0b92ec2fb7daa (40 hex;
token0()/token1() verified live), weETH/WETH f100 pool
0x553e9C493678d8606d6a5ba284643dB2110Df823 (token0 = weETH verified).
NOTE: the earlier bot.py had a truncated 39-digit wstETH pool address - fixed
this round; the proofD/proofE scripts always had the correct one.

## Capture windows and counted EV (per-occurrence measure, reviews e64be614/7a576c61/d814f7a3)

Method (scratch/bold-redeem-tail/sweep30d_v3.py -> table30d_v3.json, 454
research-lane reads; full per-burst rows in windows30d.md): every recorded
burst (2,430 Redemption events, 30 d, gap<=3-block grouping -> 228 bursts) is
probed with the 1-tx route eth_call (code override, minProfit=0) at **b_hi+1**
(the first block after the burst's last block, T+12 s) and at our **landing
block** (first block with ts >= T+18.06 s: poll 10 s + send-to-inclusion 8.06
s; decision 2026-11-16-reaction-time.md sets R_ethereum = 12 s). gross > 0 at
a block = the route is takeable in that block (check 5). A revert = the
executor ends with less WETH than the flash: fork trace at block 26206627
(anvil debug_traceCall, callTracer, run e59ec4e5a) shows the full route
execute and the final Morpho repayment transferFrom revert on insufficient
balance - i.e. "no profit at this block", not route breakage.

**Per-occurrence table (one row per candidate occurrence, review d814f7a3 fix
1): gross, transaction gas and net at landing L, plus the measured close and
race class, in one place.** gross = executor-route eth_call return at L
(minProfit=0, code override); gas = measured proof gasUsed 1,080,111 x (L
baseFee + 0.5 gwei tip est) (sweep30d.py:9,111); close = first block after L
where the route reverts (close_probe.json); USD at 3,300 USD/ETH.

| burst blocks | T (UTC) | L (landing) | gross at L (ETH) | gas at L (ETH) | net (ETH) | L baseFee (gwei) | fee-feasible (7 gwei cap) | close blk | T->close | close-L | race class (bot R = 18.06 s) | in counted EV |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 26300839 | 10-29 20:38:11 | 26300841 | +0.088917 | 0.001357 | **+0.087560** (+289 USD) | 0.76 | yes | 26300844 | 60 s | 36 s | counted (close >= R after L) | **yes** |
| 26300886-87 | 10-29 20:47:59 | 26300889 | +0.059589 | 0.067246 | -0.007658 | 61.8 | no | 26300890 | 36 s | 12 s | trial (close < R after L) | no (net < 0, fee-gated) |
| 26300895 | 10-29 20:49:35 | 26300897 | +0.054675 | 0.142585 | -0.087910 | 131.5 | no | 26300899 | 48 s | 24 s | counted class | no (net < 0, fee-gated) |
| 26300993 | 10-29 21:09:23 | 26300995 | +0.073137 | 0.176228 | -0.103091 | 162.7 | no | 26300996 | 36 s | 12 s | trial (close < R after L) | no (net < 0, fee-gated) |
| 224 IN-BURST bursts (rest of 30 d) | - | b_hi+1 | <= 0 at b_hi+1 | - | - | - | - | inside burst | < 12 s | n/a | race (taken before L) | no |

Counted EV = 1 occurrence / 30 d = **+0.087560 ETH = +289 USD = $9.63/day**
(n = 1 independent event-day; quiet days ~0), above the $0.34/day live read
cost. Only row 1 is both counted-class and fee-feasible AND net-positive: its
close is 36 s after L, >= both this bot's R = 18.06 s (10 s poll + 8.06 s
send-to-inclusion) and the decision 2026-11-16-reaction-time.md farm R for
ethereum (12 s); rows 2-4 land at 62-163 gwei crash-day base fees where a
7 gwei signed cap cannot include, and each is net-negative at its landing base
fee even ignoring that gate. Median/minimum eligible-to-taken window of the
counted row: 60 s (n = 1).

Actual closing transaction per occurrence:
- **224 of 228 bursts: route <= 0 already at b_hi+1.** No tail existed after
  the burst's last block; the discount was absorbed by the burst's own
  redemption transactions at b_hi. Nothing outside the burst had to close it:
  the next Redemption burst is structurally > 3 blocks later (measured min 48
  s, median 3,744 s after T). Taken before our earliest block L (T+12 s <
  R = 18.06 s): latency race, not counted. Incumbents: 0x7672b6 et al.
  (attempts:1298), e.g. 0xe0b715.. and 0xd77c74.. in the 26421613 burst.
- **4 bursts (all on 2026-10-29, the 2.1M-BOLD rush day) were open at b_hi+1
  AND at landing. Actual closes measured per occurrence**
  (scratch/bold-redeem-tail/close_probe.py -> close_probe.json, 26
  research-lane eth_call probes, 2026-11-15, review 7a576c61 fix): the route
  first reverts at blocks 26300844 / 26300890 / 26300899 / 26300996 =
  **T+60 / T+36 / T+48 / T+36 s** (first revert after landing = the take time;
  for 26300839 the probe reproduces the reviewer's independent gross values
  exactly: +0.08891749 ETH at L = 26300841, +0.10522600 at 26300842,
  +0.10625818 at 26300843, revert at 26300844 ts 1793306351). Eligible-to-taken
  windows = 60/36/48/36 s (median 42, min 36); close-minus-L = 36/12/24/12 s.
  Race-rule class (bot R = 18.06 s): rows 1 and 3 closed >= R after L (counted
  class); rows 2 and 4 closed < R after L (feed-bot trial class). The earlier
  "24 s (T to L)" was the landing delay, not a measured capture.
- Closing transaction of the fee-feasible row (26300839): block 26300844
  carries exactly three swaps of the route's sell pools (logs 51/364/1185, txs
  0x1be2ca726d26fbff80b5fa061d68672922a26f6785dbf.., 0x4b05ebfde0cdfedd4f2f..,
  0x9018546df179e0d01f53..; callers 0x0c8c5891, 0xbeef02961503 flow,
  0x77f40a04c3f5 flow) and **no Liquity V2 redemption** (raw 30-d getLogs
  sweep and the ledger both show zero Redemption events 26300840-26300862,
  next burst +23 blocks): the tail was closed by collateral-pool sell price
  correction, not by a competing redeemer taking it. Block-granularity caveat:
  which of the three swaps flips gross first needs intra-block replay;
  together they leave the reverting state the probe sees.

Fee feasibility at L: the four landing blocks carried base fees 0.8 / 62 / 132
/ 163 gwei (crash-day fee spike). With the signed cap maxFee 7 gwei x 1.5M gas
(= the $35 L bound at $3,300/ETH; L itself refuses ~62 gwei x 1.5M = 0.093 ETH
= $307), only the first send can include in time; bot.py's new skip_fee_gate
logs the others instead of parking them in the mempool. **Counted EV = 1
occurrence per 30 d: 0.0889 gross - 0.00136 gas = +0.0876 ETH = +289 USD =
~$9.6/day, n = 1 independent event** (one rush day; quiet days contribute ~0).
The counted row's close (26300844, T+60 s = L + 36 s >= R) puts it in the
counted class of the race rule; its measured window is 60 s (median = min = 60
s, n = 1 fee-feasible counted row).
Read cost ~0.32-0.6 USD/day (604,800 CU quiet polls, reviewer arithmetic)
clears it, but the sample is one day.

Rush-day competition inside the window: burst 26300839's route gross decayed
0.1513 ETH at b_hi+1 -> 0.0889 ETH at landing with **no Redemption event in
between** (next burst +23 blocks) - non-redemption transactions ate ~0.06 ETH
of discount per block during the rush. The tail is not free even there.

Superseded: the first README claim (110 counted occurrences, $40/day)
extrapolated the fork rate across all multi-block bursts; v2 showed landing
gross, v3/v4 the actual close block and class per occurrence; v5 (this round,
review d814f7a3 fix 1) merges gross, per-transaction gas, net, close timing
and race class into the single per-occurrence table above - no numbers
changed, only their presentation and the fee-paragraph base-fee rounding (the
exact landing base fees are 0.76 / 61.8 / 131.5 / 162.7 gwei).

Fork proof (proofE.sh, scratch/bold-redeem-tail/): reset
26417352, deploy, fund owner, redeem. Success tx
0x4e613e92191e6eddc320bf1c18f462d1e8a5e2d3b72a485864ca665582b38480 (status 1,
gas 1,080,253, OWNER WALLET +0.00589231 ETH, all executor token balances and
allowances 0 after, eth_call return 0x...14ef07f2924315 = 0.00589232 ETH
matching). Guard-revert tx
0x39462d35183b187c6c39c22b356b9c8730d5f2a1c97b11320b35f3777f080d9f (minProfit
50 ETH, status 0, wallet delta 0 = gas only). Live-shape case C: from=owner
eth_call at head passes the owner guard (reverts only at "minProfit not met"
with string data).

Detection reproduction (review e64be614 fix 2):
scratch/bold-redeem-tail/replay_detector.py runs the CURRENT bot.py source
(exec'd unmodified, RPC stubbed, head +1 block per poll) over the full 30-day
Redemption log set: all 430 event blocks are detected in exactly one burst
unit, every burst total equals the raw-log sum, nothing is finalized while its
last block is still head, and the reviewer's block 26421613 - mis-summed as
5e-14 BOLD by the old build - is detected as 49,292.136 BOLD and triggers
act() (output scratch/bold-redeem-tail/replay_detector.out, REPLAY PASS). The
detector emits 296 burst units where the offline sweep merges gap<=3 into 228:
the bot acts at the first 1-poll pause, so a multi-block burst can split into
several units across poll phases. That is an earlier, strictly more frequent
trigger (extra units probe mid-burst states where the route reverts and
nothing is sent); the window table above uses the conservative offline
grouping. Ledger + relay show no Redemption event after 26421613 up to head,
so no live paper observation exists yet; the replay is the reproduction.
