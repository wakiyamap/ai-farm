trial

# trial-usdxl-gsm-hyperevm

USDXL (`0xca79db4b49f608ef54a5cb813fbed3a6387bc645`) is HypurrFi's GHO-fork stablecoin on HyperEVM. Its GSM
`0xcb17105f6a7a75d1f1c91317a4621d9aaafe96fd` (verified `GsmWithHyFiPool`, implementation `0xdc6ed783...`) has the
public `buyAsset(uint256 minAmount, address receiver)`: burn USDXL, receive USDT0 at 1:1 less a 1 % fee, i.e.
1.01 USDXL per USDT0. That is USDXL's price floor. The USDT0/USDXL pools are thin (20-1,160 USDT0 each), so a sale
of USDXL pushes a pool under the floor, and one transaction earns the difference:

pool.swap (USDT0 in, USDXL out) -> inside the swap callback: `GSM.buyAsset` (USDXL -> USDT0), pay the pool ->
sell the USDT0 that is left for WHYPE (WHYPE/USDT0 0.05 % pool) -> unwrap -> native HYPE to the wallet.

No flash loan and no principal: the pool's own swap is the loan. The executor (`UsdxlGsmArb`) reverts unless the
native paid out is at least `minProfit`, so a lost attempt costs gas only.

## Competition, last 7 days (blocks 51,206,000-51,810,768; scratch/rcdd0/takes-hyperevm-0xcb17105f.json)

65 redemption transactions (GSM `BuyAsset` logs), gross 5.38 USDT0, gas 0.0146 HYPE = 0.89 USD.

| sender (EOA) | contract | takes | gross USDT0 | gas HYPE |
|---|---|---|---|---|
| 0xf2e752f616ab9e82099409cf853aff4575d02ee5 | 0x097faafa12f9292d2b74aecfc1cc1cb2a6afd605, later 0x1ed7d6ff207170ed15e0a29071f0d3c87a19a5c3 | 59 | 4.82 | 0.0088 |
| 0x13a71b29bccacb2d3d16d045aee2e02fa8183e1f | 0x3f33be5978e6b26bb35cb6cd30bbdee98c15ad92 | 2 | 0.174 | 0.0005 |
| 0x43637877fb1d10d9a751817f5cde1406ef69af21 | 0x0418f78085f1f2949657e3441c05f34d42d403e1 | 1 | 0.186 | 0.0011 |
| 0x0b8d87ee4ee429a60e8f5738c3a2d7d6e8ad8471 | 0x7b9836a3fa0824572c2f7e69beb19c351d80548b | 1 | 0.174 | 0.0015 |
| 0x4be71355aa244eecaa31080fd7b48bafc4964f36 | 0x366a68ada2c873f66f459adc899fd7d7fdaa95af | 1 | 0.022 | 0.0001 |
| 0x9240b56ee52b82ab2df5fcb7b599561a55e99d28 | 0x0418f78085f1f2949657e3441c05f34d42d403e1 | 1 | 0.0 seen | 0.0027 |

Gross per take: median 0.047, max 0.276 USDT0. Sizes 10 / 25 / 50 USDT0 (one 187). Tx index 0-21, median 3. Gas
price: median 0.13 gwei (the base fee floor is 0.1 gwei); the three first-block takes of 11-20 (blocks
51,777,956-960, 0.17-0.19 USDT0) bid 2.2-5.8 gwei. Bursts: 36 takes in the first 24 h after 11-15 about 23:55Z, none
for two days, 4 in the fourth 24 h, 25 in the last 24 h (to 11-20 23:45Z).

Blocks to take (scratch/trial-usdxl-gsm-hyperevm/series.py -> series.json; this bot's own scan run as a code
override at blocks before each of the last 22 takes; a block is about 1 s): a gain of 0.00005 HYPE or more already
stood 1 block before for 20 of 22, 5 blocks before for 18, 10 for 15, 30 for 15, 100 for 13; the control 2,000
blocks before shows it on 3 and exactly 0 on 13. The main taker acts on a gap only once it clears its gas, tens of
seconds after it opened. Priority-fee level: none in normal takes (0.1-0.5 gwei effective), 2-6 gwei on the rare
first-block ones.

## What the bot does

- Every 30 s: one `eth_call` of the executor's `scan()` with 25 candidates (5 pools x 5 / 10 / 25 / 50 / 100 USDT0).
- Best candidate at 0.00004 HYPE or more: gas estimate, fee cap, then the exact-bytes `eth_call`.
- Sends only if the simulated native gain is at least 1.1 x this send's gas cap (gas limit x maxFeePerGas, under
  0.95 USD). `minProfit` = that cap + 1 wei, so a mined success always ends with more native than it started.
  Priority-fee bid: at most 20 % of the simulated gain. A gap that fails the gas test is looked at again after 5 min.
- Log `logs/bot.jsonl`: `start`, `poll` (heartbeat), `opportunity`, `opportunity_skip`, `simulate_revert`,
  `paper_sim`, `send_result` (won / lost, gas used, send block, nearest block where someone else redeemed).

## Read cost

2,880 scans x 26 CU = 74,880 CU/day, about 90 CU per evaluated gap, hard cap 96,000 CU/day in code (0.051 USD/day
at 0.53 USD per 1M CU). No feed filter: five pools would need five filters for cents.

## Size, honestly

The whole class nets about 4.5 USD in 7 days (0.64 USD a day); a take is 0.004-0.06 USD after gas. This trial
measures whether the farm can take the gaps before the slow incumbent; it will not move J by itself. Not covered:
routes through the feUSD/USDXL and WHYPE/USDXL pools (the incumbent's 2-3 leg takes) and the GSM's sell side
(5 `SellAsset` in 21 days).

## Limits and risks

- The GSM can be frozen or seized by its roles, or run out of USDT0 exposure; then every probe reverts and the bot idles.
- The fee (1 %) is a strategy contract the configurator can change; the bot never assumes it: the scan runs the real redeem.
- Redemption leaves under 1e12 wei of USDXL (6-decimal rounding); the executor sends that dust to the owner.

## Proof

`scratch/trial-usdxl-gsm-hyperevm/proof.py 51397086 b` (fork, parent of take 0x81474b12... in block 51,397,087):
owner +0.000878685 HYPE before gas with 25 USDT0 on the 0.02 % pool, 520,495 gas; reverts for a non-owner, for
minProfit 10 HYPE, for the same run repeated and on a pool with nothing to take; executor holds nothing afterwards.
`selftest.py`: encoder equals `cast calldata`, selectors equal `cast sig`, runtime equals the fork deployment,
scan answers through the relay in 0.16 s.
