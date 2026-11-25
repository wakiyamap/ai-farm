# morpho-farmband-base — Base Morpho Blue farm-band liquidation (paper)

Lead 157. Morpho Blue (0xbbbb..cb) on Base: whale-farm borrowers in the
100–1500 USD "farm band" get liquidated when a Chainlink price drop makes
their small loop position underwater; anyone liquidates and seizes at the
oracle price with the protocol bonus, repaying via Morpho's own flash loan
(fee 0, repaid in the same tx). One executor tx: liquidate + dual/single-hop
swap of seized collateral back to the loan asset, reverting unless the
executor's loan balance ended >= minProfit higher (worst case = gas only).

## Capture windows (eligibility -> capture), from `scratch/mb157-window.json`

Base blocks run ~0.2 s (measured from block timestamps: 2982 blocks = 596 s),
so a 15 s poll is ~75 blocks and send-to-inclusion is ~2 s. All windows below
are publish (last AnswerUpdated drop matched to the capture) -> capture block.

Historic band captures (census `scratch/mb157-window.json`; these markets are
now dormant or dead — the two "cbXRP" rows were market 0x73527ddd..., collateral
cbd06e5a, NOT our pinned cbXRP market):

| capture block | market | eligible->taken | net USD | counted? |
|---|---|---|---|---|
| 56245267 | cbZEC (dead) | 155 blocks / 30 s | 5.58 | yes, market dead |
| 56242285 | cbZEC (dead) | 24 blocks / 5 s | 4.86 | NO — under 15 s poll + inclusion |
| 55986767 | cbZEC (dead) | 155 blocks / 30 s | 7.54 | yes, market dead |
| 55691587 | 0x73527ddd (not pinned) | 153 blocks / 30 s | 12.04 | market not in our executor ctor |
| 55675682 | cbZEC (dead) | 153 blocks / 30 s | 13.99 | yes, market dead |
| 55691524 | cbBTC (pinned) | 16 blocks / 3 s | 9.39 | NO — speed race |
| 55675686 | cbBTC (pinned) | 13 blocks / 2 s | 4.48 | NO — speed race |

RE-MEASURED 2026-11-12 (run 0ee85e97, fix round 3) on the CURRENTLY VIABLE
monitored markets, every recent occurrence with its measured window:

* pinned cbBTC 0x9103c3b4: captured 7 borrowers on the 2026-11-12 burst day
  (ledger blocks 56470016/56470018; repaid 1883.39/22.27/32.80/25.87/6.21/5.45/
  3.92 USD, callers 0x9cbb82b9/0x96684a32/0x20f63594/0x5ac9bc14/0xc84b2f26 - all
  ledger-top incumbents). Feed 0xeb3ad439... dropped at block 56470013 ->
  capture: **window 3-5 blocks (~1 s): speed race.** Its two historic
  census windows were 13/16 blocks: every cbBTC window ever measured is a race.
* pinned WETH-USD 0x8793cf30: 3 dust captures 56374332/56377187/56381105
  (repaid 29.60/3.09/0.32 USD, one borrower). Feed 0x83f3425a... drops at
  56374255/56377106/56380563 -> **windows 77/81/542 blocks (15.4/16.2/108 s)**:
  the 77/81-block windows are under the 15 s poll + send/inclusion (race);
  the only poll-catchable occurrence measured anywhere is the 542-block one,
  worth 12.6 % x 0.32 USD = **0.04 USD**.
* other active-band markets (not in our ctor collateral whitelist):
  0x9125d0fa (coll cb17c9db..) captured 6 on 2026-11-12 (repaid 21-34206 USD):
  window 36 blocks (~7 s) - race; 0x73527ddd (coll cbd06e5a..) captured 7 in
  block 56470030 with no feed drop in its census feed; 0xd7520ad1 109.73 USD.

**EV after the latency filter (poll 15 s + send-to-inclusion): cents per day.**
Per capture the take is 12.6 % of repaid (fork proof +21.67 USD on 172.14
repaid) and gas is ~0.01-0.10 USD, so each occurrence is worth 4.5-237 USD -
but every window measured on a currently-viable monitored market since the
2026-11-12 re-measurement is 3-81 blocks (~1-16 s, under poll + inclusion).
Only the 0.04 USD dust capture was poll-catchable. The 153-block (~30 s)
windows that a 15 s poll could take belong to the now-dead cbZEC market and a
collateral market outside our executor constructor.

## Who earns this now

Ledger `morpho_blue.liquidate`: 221 incumbent caller wallets; captures
repaid 100–1500 USD: 1762 cumulative (the lead census figure — cumulative
since deployment, not a recent rate). The band regime is bursty (crash days):
the 2026-11-04 crash burst (5 in-band captures 109–483 USD + a 9.74M/1.39M/
157k USD mega on other markets) and the 2026-11-12 burst day (measured
2026-11-12 run 0ee85e97: ledger blocks 56463494–56477050, ~15 captures
repaid 100–1883 USD across markets 0x9125d0fa (6, up to 34206 USD), 0x73527ddd
(7 in one block), 0xd7520ad1 (109.73) and our pinned cbBTC (7 borrowers,
1883.39 repaid)). The incumbents took each 1–36 blocks after the matching
feed drop — a same-block snipe class, not a poll class. Between burst days
the flow is drought (42 h at the 2026-11-09 measurement; 8 days between the
bursts). Per capture after gas: 4.5–14 USD at incumbent net (window.json),
12.6 % of repaid at the fork-proven executor. After the latency filter the
route's after-gas EV at our poll rate is cents/day, not 1–2 USD/day.

The old cbZEC collateral token 0xb200…b2ec self-destructed after its last
capture (0 code at head, balanceOf reverts). The pinned cbXRP market
0xd4a903dc… captured zero since block ~55.7M (dead since 2026-August) and its
oracle never matched a Chainlink feed in discovery — dropped from the pin set
in fix round 3; the census "cbXRP" captures belonged to market 0x73527ddd
(collateral 0xcbd06e5a…, a different market outside the executor ctor).

## Read cost

Poll every ~15 s (16-block gate; Base blocks are ~0.2 s so the gate is always
open and the 15 s sleep sets the rate): ~5700 eth_blockNumber/day (~230K CU) +
~2700 AnswerUpdated eth_getLogs over the 3 pinned feeds (~270K CU). Safety
full scan every 32nd cycle (~170/day): 2 x market(bytes32) + 2 x oracle price()
+ 16 x position(bytes32,address) getter = ~20 reads (~306K CU); price-drop
scans add the same per triggered market. Estimate ~0.8M CU/day ~= 0.42 USD at
1M CU = 0.53 USD — under the 1M human threshold. The paper simulation runs
against the LOCAL base fork (bot.js `FORK_BASE_URL`), it costs no relay CU.

## Route status after fix rounds 2-3 (runs f2c9dff7 + 0ee85e97, 2026-11-12)

Review 993 blockers fixed in this round:

1. Detection reads: accrueInterest is out (0x151c1ade is the incumbent's CALL
   selector, reverts as a getter), totals now come from the deployed
   market(bytes32) 0x5c60e39a getter (verified at head AND at a block tag, run
   50db6b24) and every seeded position from the deployed position(bytes32,address)
   0x93c52062 getter (verified at head). The positions-storage slot route (lead
   157 learning 5) is abandoned: the slot scan found no base slot (run 50db6b24,
   slots 0..48/0..79 empty) and the getter is the deployed ground truth.
2. Aggregator discovery: the topic-only AnswerUpdated scan runs over 40
   consecutive 64-block windows back from head (Chainlink FX feeds heartbeat
   ~1/h so a short window catches none; near-head topic-only scans also cap at
   ~125 blocks and silently return [] above it - that, plus trailing null
   topics, is why agg discovery kept printing {}). Scale-ratio matching
   (oracle price() vs feed answer, 2% band) is NOT unique - several Chainlink
   feeds track the same underlying - so the bot pins ALL matching candidate
   feeds per oracle and monitors them as a superset trigger (a few extra
   scans/day, never a missed drop of a caught feed; restarts re-scan).
3. Payout: the executor sweeps its full profit to the owner (bot wallet) IN the
   liquidation tx (MorphoFarmLiquidator.sol:163 transfer(owner, profit), revert
   SWEEP_FAILED); the re-run fork proof measures the WALLET delta +21.674726
   USD with executor leftover 0. The market pin moved from the dead cbZEC
   market to the live WETH-USD market (single-hop swap on the whitelisted
   UniV3 WETH/USDC pool, which is also the cbXRP dual-hop leg 2 - both are
   constructor immutables now; the dormant cbBTC pool needs setPoolAllowed).
4. Paper simulation (blocker 5): paper mode deploys the final artifact to the
   shared local base fork (owner = PAPER_WALLET 0x1111..1111, redeployed after
   any external fork reset) and simulates eth_call from that wallet at the
   owner-only entrypoint with the real detected calldata, measuring the wallet
   USDC delta inside the call and a minProfit-x100 guard-revert variant.
   Head-time captures revert on the fork for protocol-state reasons (the fork
   sits at whatever block the last lease reset it to) - the log records it.

Remaining gaps — the latency verdict (fix round 3, run 0ee85e97, review-998
blocker 2): the re-measurement above found NO poll-catchable occurrence on a
currently-viable monitored market except one 0.04 USD dust capture. Per the
review-998 instruction and decision 2026-11-12 (speed race), this route is an
archive candidate for the paper-reviewer rather than another fix round: the
farm-band class is alive (burst days) but its captures are taken 1-36 blocks
after the feed drop by same-block incumbents. A 5 s poll (~25 blocks) would
cover the 77/81-block WETH windows; at this poll rate that is ~2.5M CU/day
(over the 1M human threshold) for ~0.04 USD/day of EV — not promotable.

Fix round 3 changes (review 998 blockers 1/3): feed answers persist as strings
and restore as BigInt (no more `cycle error: Do not know how to serialize a
BigInt`; the block cursor advances through feed updates); the pinned capture
feeds are VERIFIED and pinned in markets.json (cbBTC -> 0xeb3ad439... whose
56470013 drop matches the 56470016 capture, plus the 1e8-scale BTC/USD feed
0x13723399... as a superset trigger; WETH-USD -> 0x83f3425a... whose three
drops match the three dust captures), the ratio-discovery is only a fallback;
the cursor advances before the log scan so a relay range failure cannot strand
it; each restart seeds each feed's last answer as of the persisted cursor, so
a restart still fires the drop a capture matched (paper logs now show a logged
`AnswerUpdated ... drops` cycle triggering real cbBTC borrower checks); the
paper executor deploy re-funds the paper wallet with `anvil_setBalance` after
a shared-fork reset took its fake funds.

`run.sh` -> `node bot.js` for both paper and live; live sends the executor
call through the signer (`$SIGNER_SOCK`, `EXECUTOR_ADDR`/`state/executor.json`).
