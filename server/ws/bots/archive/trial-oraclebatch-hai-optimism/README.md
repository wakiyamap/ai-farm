# trial-oraclebatch-hai-optimism

**試行 / TRIAL bot** (decision `decisions/human/2026-11-17-cheap-chain-trials.md`; lead 213).
The race rule, the EV floor and paper captures are waived; the win rate is measured live.
X / n / L / S and the executor rules (one transaction, revert unless the balance grows) apply.

## Mechanism

HAI (OP Mainnet) pays **0.05 HAI** to anyone calling
`OracleJob.workUpdateCollateralPrice(bytes32 cType)` once per collateral item per 3600 s.
Five items (OP, RETH, TBTC, VELO, WETH) are due in the same second every hour, and
HAIAERO + MSETH share another second. The incumbents take such a cluster in one transaction.
This bot does the same through its executor: all jobs of the cluster → `CoinJoin.exit` → sell
the HAI on the UniV3 HAI/WETH pool (passed in the call, not stored in the executor) → unwrap → ETH to the bot wallet, reverting unless the
ETH gained is at least `minProfit`. Single-item windows are left to the sibling
`trial-oraclejob-hai-optimism` (this bot only takes windows with 2 or more items).

## Competition, last 12 h before placement (`scratch/trial-oraclebatch-hai/census.json`)

5-item window, blocks 159614939–159634739, 12 of 12 windows taken, all in the block whose
timestamp equals `due`, transaction index 1 (blocks from takeable to taken: 0):

| keeper executor | sender | wins | priority fee |
|---|---|---|---|
| `0xc9dfc714…` | `0x99ec6b16…` | 7 | 0.188–0.191 gwei (one at 0.022) |
| `0x82c1ff92…` | `0xd4a2f192…` | 4 | 0.188–0.190 gwei |
| `0xa88e2855…` | `0x9ab1daea…` | 1 | 0.080 gwei |

3 keeper addresses. Their usual bid, 0.19 gwei on 657–683k gas, is a fee of 1.24–1.29e-4 ETH,
74 % of what the 0.25 HAI sells for (1.687e-4 ETH); the two top operators raise it by about
0.0005 gwei per win. Two of the 12 windows were won cheaply (0.022 and 0.08 gwei). The
7-day picture of the whole job (2,520 rewards, 5 keepers) is in attempts:1439.

**What this bot can and cannot do.** Our path also sells the HAI, so it peaks at 870k gas
before refunds (777,667 used) and needs a 950k limit. Under the trial rule "expected gross >
signed gas cap" the most we can sign is about 0.177 gwei, below the usual 0.19. So the bot
does not try to outbid the top bidders: it bids a fixed **0.10 gwei** (46 % of gross at the
gas used, never more than 50 %) and wins only when they are absent or bid low — 2 of 12
windows in the sample. A win nets about 9.1e-5 ETH (0.167 USD); a lost attempt ends at the
view probe for 35,940 gas = 3.6e-6 ETH (0.007 USD), so the break-even win rate is about 3.5 %.
If the 17 % held: about 0.56 USD/day. That is an observation, not a counted EV.

## What the bot does

Timer, no polling. At start and hourly it reads each item's DelayedOracle
(`OracleRelayer.cParams(cType)` word 0), `lastUpdateTime()` and `updateDelay()`; an item is
due at `lastUpdateTime + updateDelay`. Items due within 3 s form a window; the bot takes the
earliest window with at least 2 items. 15 s before `due` it quotes the gross on the pool
(`slot0`), sets priority = min(0.10 gwei, 50 % of gross / estimated gas), maxFee = 2 × base +
priority (ceiling 0.11 gwei), gas limit = 300k + 130k per item with a 700k floor (950k for 5, 700k for the 2-item window,
whose jobs needed up to 563,705 gas in total on 2026-11-17 01:04Z), and sends only if
gross > limit × maxFee + L1 estimate (5e-8 ETH). `minProfit` = that same amount + 1 goes to
the executor, with `minItems` = all items, `probe` = the first item's oracle and `pool` = the
HAI/WETH pool (`POOL` in `bot.py`; the executor accepts its swap callback only during that call). It simulates
the call at head with the block time set to `due`, sleeps to `due − lead` (2.4 s at first,
self-adjusting 1.6–3.4 s from where the transaction landed) and sends once. Then it logs
`receipt` and `window_result`: win / lose, gas used, fee, the taker's transaction, block, index
and priority fee, and `our_block_minus_taker_block`.

Paper mode sends nothing: it simulates with a code override of the fork deployment
(`executor-runtime.hex`) and logs each window's taker and `would_outbid_taker`.

## Loss bound

Per send: 950,000 × 0.11 gwei = 1.045e-4 ETH (0.19 USD at ETH 1826) at the ceiling, plus the
OP L1 data fee (4.4e-9 ETH on the fork). The executor reverts unless ETH gained ≥ `minProfit`
(`HaiOracleBatchTrial.sol:94`), unless all items paid (`:74`), and at the view probe when the
first item is already taken (`:61`). Capital 3 USD is the whole budget (about 500 lost attempts).

## Read cost

About **27k CU/day** (0.014 USD at 0.53 USD per 1M CU): 48 windows/day × ~216 CU (slot0 26,
block 16, sim 26, taker getLogs 75, receipt 15, block 16, re-reads) ≈ 10.4k; hourly schedule
re-read 15 × 24 × 26 = 9.4k; 10-minute safety re-read 3.7k; live receipt polling ≈ 3k.
Under the 100k CU/day trial cap. No feed filter (the time is known in advance).

## Fork evidence

`scratch/trial-oraclebatch-hai/proof.py 950000 100100000` (one lease, reset optimism
159623936, output in the manifest's `fork_evidence`): 5-item success, already-taken revert,
NoProfit guard revert, a stranger taking one item first, 4-of-5 success, a wrong pool
(BadPool), the swap callback called outside `act` (NotActivePool), a non-owner (NotBot).

## Overlap with the sibling bot

`trial-oraclejob-hai-optimism` sends one item of the same 5-item window at 0.03 gwei. If both
land in the due block, this bot's higher bid goes first and the sibling's call reverts on its
job (its usual lost attempt). If the sibling ever lands first, this bot's probe or `minItems`
reverts for 36k–108k gas. Reported to meta (`inbox/meta/`).
