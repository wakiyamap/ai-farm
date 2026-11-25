trial — CMI SetToken issue / redeem versus its QuickSwap V2 pair on Polygon (lead 349)

## What it does

CMI (`0x83c92e1a4a824cd42f94012b7b50aff372e4d25f`, a Set Protocol SetToken, supply 91.3) holds per token
0.011883 WETH + 0.00089384 WBTC + 41.156 USDC.e (about 111 USD). The BasicIssuanceModule issues and redeems it
for anyone at exactly those amounts (no fee, no issuance hook). Its only market is one QuickSwap V2 pair with
USDC.e (669 USDC.e + 6.09 CMI) that nobody quotes: when ETH / BTC move, the pair price is left away from the
component value. One transaction through the executor (StepArb), funded by a Morpho Blue WPOL flash loan:

- `issue` (pair above value): WPOL -> USDC.e, buy the exact WETH and WBTC amounts, `issue`, sell CMI on the pair,
  USDC.e -> WPOL, repay.
- `redeem` (pair below value): WPOL -> USDC.e, buy exact CMI on the pair, `redeem`, sell WETH and WBTC,
  USDC.e -> WPOL, repay.

The executor reverts unless its WPOL balance grew by `minProfit` (= the send's gas cap), then unwraps and pays POL
to the bot wallet. The bot sends only when the simulated gross is above twice the gas cap.

## Competition, last 7 days (blocks 97,287,152-97,690,351; scratch/s349/takes.json)

One operator: EOA `0xc3afb378b3e50a5134b6c0b597dcf31c20c50bbd` through `0x91a7fbaec1d8f0a4d2dcdde5e3319349ef209428`
(Balancer flash of 10 USDC.e, issue 0.088 CMI). All five atomic takes were in the issue direction.

| block | tx | kept USDC.e | gas | priority fee gwei | tx index | blocks the gain stood above our line (about 1.0 POL) |
|---|---|---|---|---|---|---|
| 97,304,761 | 0xaaff1538... | 0.139447 | 1,241,452 | 25.3 | 100 | >= 1,000 (1.18 WPOL at -1,000; 0.96 at -3,000) |
| 97,325,446 | 0xd11f5d18... | 0.138573 | 1,176,012 | 33.7 | 88 | >= 1,000 (1.38 at -1,000; 0.43 at -3,000) |
| 97,654,787 | 0xdfbb7e5e... | 0.150661 | 1,241,440 | 90.1 | 10 | >= 1,000 (1.08 at -1,000; 0.79 at -3,000) |
| 97,663,571 | 0xb844cfd5... | 0.158980 | 1,145,855 | 161.3 | 3 | >= 3,000 (1.27 at -3,000) |
| 97,685,669 | 0x147b059f... | 0.149651 | 1,233,844 | 26.1 | 203 | >= 100 (1.02 at -100; 0.87 at -300) |

The operator waits until the gain is about 1.5-2.0 WPOL (its takes kept 0.139-0.159 USDC.e), 30 minutes to hours
after the gain passed 1.0 WPOL. This bot's send line is lower (2 x gas cap, about 1.0-1.1 POL), so it is a
threshold contest, not a speed race. The same EOA also made 8 direct module calls (181.7k gas, inventory issue /
redeem) in the window. Window series: `scratch/trial-cmi-arb-polygon/selftest.py series` -> `series-windows.json`.

## Addresses (each read with a getter, scratch/trial-cmi-arb-polygon/reads.py)

- CMI SetToken `0x83c92e1a...` (`getComponents()` = WETH, WBTC, USDC.e; lead 349 scan of the module's logs)
- BasicIssuanceModule `0x38E5462BBE6A72F79606c1A0007468aA4334A92b` (Controller `0x75fbbdea...` `getModules()`;
  `getRequiredComponentUnitsForIssue` answers; `managerIssuanceHook(CMI)` = 0)
- QuickSwap V2 router `0xa5E0829C...`, pair `0x8a1d216e...` (`factory()` = QuickSwap `0x57573714...`)
- Uniswap V3 SwapRouter02 `0x68b34658...`; 0.05 pct pools USDC.e/WETH `0x45dda9cb...`, WBTC/USDC.e `0xeef1a950...`,
  WPOL/USDC.e `0xa3740945...` (`factory()` = `0x1F98431c...`, `fee()` = 500)
- Morpho Blue `0x1bF0c254...` (1.0M WPOL; flash loans are free)

## Loss bound

A lost send costs only gas: gas limit = estimate x 1.2 (max 2.4M), max fee = base x 1.25 + 30 gwei (max 1,500
gwei), typical cap 0.5 POL = 0.04 USD; hard maximum 3.6 POL. Capital 5 USD = about 100 lost sends.

## Read cost

Timer bot, one probe `eth_call` per 120 s (all 14 candidates in one call): 720 x 26 = 18,700 CU; sizing reads
(units + 3 x slot0) every 30 min = 5,000 CU; opportunity reads about 2,500 CU. About 26,000 CU/day = 0.014 USD/day
at 1M CU = 0.53 USD. No feed filter (the gap opens by price drift, not by an event on the pair). Code cap 95,000.

## Logs (`logs/bot.jsonl`)

`start`, `check` (no_gain / below_send_line), `opportunity`, `opportunity_skip`, `simulate_revert`, `paper_sim`,
`send_result` (won / lost, gas_used, send_block, winner_block, tx_index, net_wei), `signer_reject`, `read_budget`,
`loop_error`.

## After the trial

After 7 days live or when the capital is spent: write sends / wins / net as an `attempts` row and set lead 349
`measured` (win rate, net/day) or `blocked_infra` (how many blocks late).
