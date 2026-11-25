trial

# trial-dquick-lair-polygon

**What it does.** QuickSwap's DragonLair over the old QUICK token (`0xf28164A485B0B2C90639E47b0f377b4a438a16B1`, share token
dQUICK) is a "bar" vault: `enter(uint256)` / `leave(uint256)` convert at QUICK held / dQUICK supply (1.7513 QUICK per
dQUICK on 2026-11-22), with no fee, no delay and no role. dQUICK also trades in the QuickSwap V2 pair dQUICK / QUICK
`0xb187ad7bb9933bc4152f3da30e18600352d65792` (21.9 QUICK / 12.6 dQUICK, about 400 USD). Holders sell dQUICK into the
pair, its price falls under the vault rate, and whoever buys it back through `leave()` keeps the difference.

One transaction through the `LairPairArb` executor: flash swap dQUICK out of the pair -> `leave()` -> repay the pair
in QUICK -> sell the QUICK left on the QUICK / WPOL V2 pair `0x019ba0325f1988213d448b3472fa1cf8d07618d7` -> unwrap ->
pay the bot wallet in POL. The opposite direction (pair price above the rate: borrow QUICK, `enter()`, repay dQUICK,
`leave()` the rest) is covered by the same call. The executor reverts (`NoProfit`) unless the wallet is paid at least
`minProfit`, and the bot sets `minProfit` = that send's `gasLimit x maxFeePerGas`, so a send either nets a gain or
reverts for gas only.

**Competition, last 5.2 days** (polygon blocks 97,442,387-97,742,387, `scratch/trial-quick-convert-polygon/windows.py`,
`windows.json`): 5 takes by 3 operators, 0.2348 QUICK kept in total (2.18 USD at QUICK 9.30 USD = 0.42 USD/day).

| block | tx | operator EOA -> executor | dQUICK | kept (QUICK / USD) | gas, price | s after the previous pair trade |
|---|---|---|---|---|---|---|
| 97,541,573 (idx 89) | 0x865eabdb...acce8 | 0xd1fe7c6c -> 0xe73814ff | 1.0981 | 0.1533 / 1.43 | 234,939 at 272.6 gwei | 38,495 |
| 97,562,464 (idx 41) | 0xddb16861...3fce2 | 0x3124c160 -> 0xa2674afc | 0.1700 | 0.0044 / 0.04 | 189,676 at 276.7 gwei | 4,675 |
| 97,569,098 (idx 53) | 0x74c792a1...4b749 | 0x3124c160 -> 0xa2674afc | 0.4850 | 0.0317 / 0.29 | 189,688 at 282.4 gwei | 1,693 |
| 97,695,486 (idx 54) | 0x9e1f86ad...c03a9 | 0xd1fe7c6c -> 0xe73814ff | 0.5657 | 0.0425 / 0.40 | 234,929 at 274.8 gwei | 510 |
| 97,728,161 (idx 10) | 0x10242ecb...adbb2 | 0x9db68eba -> 0x0cfe36a4 | 0.1448 | 0.0029 / 0.03 | 331,602 at 354.1 gwei | 18,656 |

Blocks to take: 340 to 25,663 blocks after the trade that opened the gap (min 510 s, median 4,675 s; lower bounds,
some gaps were open longer). Priority-fee level: none beyond the usual, effective gas price 272-354 gwei with the base
fee at 245-250 gwei (tip 28-100 gwei; validators' floor is 25). One attempt costs about 235,000 gas x 280 gwei =
0.066 POL = 0.005 USD (POL 0.0745 USD), so even the smallest take (0.03 USD) is above one attempt's gas. The bot looks
about 1 s after the pair's Sync; it bids at most 1/10 of gross as priority fee (30-300 gwei).

**Trigger and read cost.** Feed `/logs/polygon`, address `0xb187ad7bb9933bc4152f3da30e18600352d65792`, topic0
`Sync(uint112,uint112)` (44 pair logs in 5.2 days, about 8 a day; polygon had 1 of 16 feed filters in use at 03:50Z),
plus a 300 s safety poll (the vault rate also moves when QUICK is sent to the lair, with no pair event), a state re-read
on `gap` / 429 / 503 / connection error, and follow-ups 4 / 15 / 45 s after a look that saw a gain. One look = ONE
`eth_call` of the executor's `probe()` (44 sizes, both directions). Live Alchemy CU/day: 288 safety looks x 26 CU =
7,488, plus about 30 event and follow-up looks and the fee / estimate / guard reads of the few opportunities: about
9,000 CU/day = 0.005 USD/day at 1M CU = 0.53 USD; the feed filter adds a few hundred CU/day. The bot stops reading at
its own cap of 95,000 CU/day and sleeps to 00:00 UTC (every read is inside that handler).

**Fork proof.** `scratch/trial-dquick-lair-polygon/proof.py` (one script, one lease; result
`proof-result-97541572.json`): reset to 97,541,572 = parent of the first take above; success
`0xd6c578ca077fd1a3aef15837f87c252cc72178da1a3ac234feb7b66cecfee05a` (1.1246 dQUICK, 234,909 gas): wallet paid
18.0087 POL, +17.9147 POL after gas (the incumbent kept 0.1533 QUICK = about 18.6 POL); guard revert `NoProfit`
`0x9944b63d...`, non-owner revert `0x861bc078...`, repeat after the take reverts `0xfb66910a...` and every probe size
is 0. Enter direction, staged on the same fork (a stranger buys dQUICK with 4 QUICK): success `0x9db4ed41...`
(+70.90 POL after gas), repeat reverts. Executor leftovers and allowance 0. `selftest.py`: the bot's paper path (relay
`eth_call` with the code override) shows 18.009 / 5.114 / 0.446 POL at the parents of three of the takes above.

**Limits in code** (`bot.py`): send only when gross > 1.3 x the send's cost cap; `maxFeePerGas` <= 3,000 gwei, gas
limit <= 900,000, cap < 0.95 USD at a POL price of 0.25 USD; capital 5 USD of POL, gas only.

**Live.** `EXECUTOR_ADDR_POLYGON` (or `EXECUTOR_ADDR`) is required; the bot exits without it. Sends go through
`farmbot_signer` (`sys.path.append('/opt/farm/lib')`, `my_address()['address']`). Each send logs `send_result` with
won / lost, gas used and the winner's block.
