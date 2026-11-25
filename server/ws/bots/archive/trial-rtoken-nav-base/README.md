trial

# trial-rtoken-nav-base

Cheap-chain trial (decision 2026-11-17-cheap-chain-trials). Reserve yield DTF bsdETH ("Based ETH",
0xCb327b99fF831bF8223cCEd12B1338FF3aA322Ff, supply 142.7 = about 272k USD on 2026-11-20) on Base can be redeemed for
its basket by anyone with `RToken.redeem(uint256)`. When bsdETH is cheap in its Aerodrome vAMM-WETH/bsdETH pool
(0x6b87b866...) relative to the basket (wsuperOETHb, cbETH, wstETH), this round trip pays, in one transaction through
the bot's executor:

flash WETH (Balancer V2 Vault, fee 0) -> bsdETH (the pool) -> `redeem` -> unwrap wsuperOETHb (ERC-4626) -> sell
superOETHb, cbETH and wstETH for WETH in the pools the incumbents use (0x6446021f, 0x47ca96ea, 0x20e068d7) -> repay ->
the WETH gain is unwrapped and paid to the bot wallet as native ETH. The executor reverts `NoProfit` unless the gain
is at least `minProfit`. Only the redeem direction is built; the issue direction (68 of 525 events) is not.

## Honest expectation

Cents per win, a few wins a week at best. The bot exists to measure its win rate by sending.

- Past 7 days (all logs of the RToken, blocks 56,924,422-59,948,000, `scratch/r2f4e/rtlogs.py`): 457 Redemption and
  68 Issuance events. Redeems per day, newest first: 23 / 16 / 4 / 95 / 178 / 75 / 67. Two are user exits (1,198.6
  bsdETH at block 58,270,801, 21.4 at 59,654,302); the rest are 0.03-1.1 bsdETH arbitrage round trips.
- Who: 0xe6b032b48e5cfa19840f8033ca8369f2b9eecb62 (EOA 0x5d03a3f8; 108 redeems, 40 issues),
  0xc12392e7eaa0c1265d3d34fad6bf99178b95d1da (rotating 0xc0ffee.. senders; 51), 0x0000000000be226a... (27),
  0x1bad7ff3e1842e41e9200d5961197201a8f605dc (EOA 0xca65d1c2; 18 + 16), 0xd119df50 (13), 0x955cc3ae (12),
  0x8957fac010ee5262d3bad39c440ca81d73a3ad1d (EOA 0x31d39405; 10), 0xa81b9452 (12 issues), and EOA 0xab36085a,
  which deploys a throwaway contract per take.
- What a take pays (newest 40 arbitrage redeems, blocks 58,700,872-59,798,764 = 2.5 days,
  `scratch/trial-rtoken-nav-base/series.py`, `series-windows.json`): WETH kept by the taker median 0.0000141
  (0.024 USD), p90 0.0000652 (0.11 USD); 12 of 40 keep nothing visible in WETH. Fee median 0.0000143 ETH (1.30M gas
  at about 0.011 gwei all-in).
- Priority fee: 0.00009-0.154 gwei, p10 0.00025, median 0.001, p90 0.013 gwei. Tx index 2-171, median 19 (not a
  first-in-block job).
- Blocks to take: this bot's own route, probed with a code override before each of those 40 takes. Gain above the
  bot's gas cap (1.8e13 wei): at the parent block 29 of 40, 1 s before (5 blocks) 24, 3 s before (15 blocks) 18,
  10 s before 15, 30 s before 9. Any gain at all: 38 / 34 / 36 / 36 / 34. So nearly half of the takes stood 3 s or
  longer above the cap (about 7 a day in this window), median gain 0.0000259 WETH (0.045 USD) before gas.
- Paid entries in the last 7 days whose gross exceeds one attempt's gas: yes, e.g. 0x4f1b188a... (block 59,670,356,
  +0.0000376 WETH for 0.0000128 ETH) and 0xdbe5653a... (block 59,643,263, +0.0000750 WETH for 0.0000124 ETH).
- Risk to the class: supply fell from about 1,400 to 143 bsdETH after the 11-17 exit; redeems dropped to 16-23 a day.

## What it does

- On every Swap of the bsdETH pool (feed `/logs/base`, address 0x6b87b8663ee63191887f18225f79d9eeb2de0d34, topic0
  0xb3e27736... `Swap(address,address,uint256,uint256,uint256,uint256)`; about 20-200 logs a day) and every 60 s
  (basket-side price moves have no event), one `eth_call` of the executor's `probe()`, which tries 0.01 / 0.02 /
  0.03 / 0.05 / 0.07 / 0.10 WETH and reverts every trial. On feed `gap`, HTTP 429 / 503 or a timeout the timer keeps
  re-reading state.
- A gain under 5e12 wei (it cannot cover 1.5M gas even at 0.0035 gwei) is logged as `gain_below_floor` with no
  further read. A larger gain: best size, estimate gas, gas limit = estimate x 1.2 + 100,000, tip = at most 20 pct of gross, cap =
  gasLimit x maxFeePerGas + L1 allowance. Send only if the simulated gross is above the cap, with
  `minProfit = cap + 1`, after simulating the exact call at the signed gas limit.
- Paper mode logs `paper_sim`; live mode sends through the signer and logs `send` and `send_result` (won / lost, gas
  used, the winner's block and tx = last bsdETH pool swap up to our block).

## Limits

- Base (OP Stack): the enforceable worst case of a send is the wallet's native balance. The manifest funds 0.75 USD
  and the bot refuses to sign while the balance is worth 0.95 USD or more (`wallet_bound`, bot.py:221).
- Signed gas cap of a send: about 1.9M gas x 0.0097 gwei = 1.9e13 wei = 0.03 USD.
- No principal: the WETH is flash-borrowed inside the transaction.

## Read cost

- Timer: 1,440 probes a day x 26 CU = 37,440 CU. Feed-triggered probes: up to about 200 x 26 = 5,200 CU. A gain adds
  about 110 CU (block, estimate, guarded call, slot0, balance).
- About 43,000 CU a day = 0.023 USD at 0.53 USD per million CU. Code cap 90,000 relay CU a day (`RELAY_CU_CAP`); every
  read, the first one included, goes through `rpc()` inside the main loop's handler, which logs `read_budget` and
  sleeps when the cap is hit.
- Feed: one filter (Base had 10 of 16 in use on 2026-11-20), under 2,000 CU a day.

## Evidence

- Fork proof: `scratch/trial-rtoken-nav-base/proof.py` (reset 59,670,349; success
  0xe1937143f472b9c4d8da85ea7a63d4c854ef5dfb282dcac493488b1f2717f4f4, owner +0.000027068 ETH after gas; guard
  0xdde6a4b0... NoProfit; non-owner 0x77a11e7b... NotOwner; repeat 0x93561b83... reverts; executor clean).
- Bot replay: `scratch/trial-rtoken-nav-base/selftest.py 59670349 59667349` (paper_sim success / nothing_to_take).
- Addresses: RToken and BasketHandler from Reserve's deployment page (`scratch/reserve-research/8453-bsdETH.md`),
  pools and wrappers from the traced incumbent take 0xfa0c30ec... (`scratch/r2f4e/trace-0xfa0c30ec.json`), getters in
  `scratch/r2f4e/ident.py`.
