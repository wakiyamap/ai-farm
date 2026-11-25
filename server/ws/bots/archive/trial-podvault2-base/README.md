trial bot (decision 2026-11-17-cheap-chain-trials): trial-podvault2-base, three more Peapods pods paired against lending-vault shares on Base.

## What it does

The sibling trial-podvault-base covers pPEAS / pfWETH-12, pTibbeas / pfpPEAS-186 and pBTC.pLeasE / pfpPEAS-145. The same operator takes the same kind of gap on three more pods that no farm bot covers. Each trades in a Uniswap V2 pair (factory `0x8909dc15e40173ff4699343b6eb8132c65e18ec6`, fee 30 bps) against an ERC4626 lending-vault share:

| pod | pair | vault share in the pair | vault asset |
|---|---|---|---|
| pCircle `0x55a81da2a319dd60fb028c53cb4419493b56f6c0` (underlying CIRCLE `0x5babfc2f240bc5de90eb7e19d789412db1dec402`) | `0x6879a79baba7cd4b595b70088cdfe671b9a0005e` | pfUSDC-89 `0x8e792b54a8ff4d6441db65e9c52dce35249732f4` | USDC |
| peaPEAS `0x821a80ca29f52216dae0e919412cbbb0a4cb9631` (underlying PEAS) | `0x9684bf7aae39a126d42f84361c0891f751f225d2` | pfpOHMo-27 `0x70e0a9f7923988886d62da8b13415e31ce27ebb2` | pod pOHMo `0x2dc1e8dcb74b260567cff4b0937e1848efbdd1c2` (underlying OHM) |
| pETHY `0x223a5e818063408891d27ac5a67b68862e5e433a` (underlying ETHY `0xc44141a684f6aa4e36cd9264ab55550b03c88643`) | `0x505e81eaa909b4945672c1f233944cdb1657771b` | pfUSDC-135 `0x301b6a2596dba7868e4fabf77065e8bd5d56af90` | USDC |

Six routes, each one executor call (Balancer V2 flash loan of 0.001-0.016 WETH, fee 0; the steps; repay; revert unless the WETH balance grew by `minProfit`; unwrap; pay the bot wallet in native ETH):

- `cir_fwd`: WETH -> USDC (Uniswap V3 0.01 pct `0xb4cb8009`) -> deposit pfUSDC-89 -> pCircle (pair) -> debond CIRCLE -> WETH (Uniswap V3 1 pct `0xda679706`)
- `cir_rev`: WETH -> CIRCLE -> bond pCircle -> pfUSDC-89 (pair) -> redeem USDC -> WETH
- `ohm_fwd`: WETH -> USDC -> PEAS (Aerodrome Slipstream `0xb0a65b3a`) -> bond peaPEAS -> pfpOHMo-27 (pair) -> redeem pOHMo -> debond OHM -> WETH (Uniswap V3 1 pct `0xe17c1678`)
- `ohm_rev`: WETH -> OHM -> bond pOHMo -> deposit pfpOHMo-27 -> peaPEAS (pair) -> debond PEAS -> USDC -> WETH
- `ethy_fwd`: WETH -> VIRTUAL (Aerodrome Slipstream `0x3f0296bf`) -> ETHY (Uniswap V2 `0x47006dcf`) -> bond pETHY -> pfUSDC-135 (pair) -> redeem USDC -> WETH
- `ethy_rev`: WETH -> USDC -> deposit pfUSDC-135 -> pETHY (pair) -> debond ETHY -> VIRTUAL -> WETH

Executor = `PodArbTake.sol`, the source of the live siblings trial-peapods-arb-base, trial-podcycle-base and trial-podvault-base, unchanged (sha256 835323403217bcbf32c7c97d5c846aba854cea45edfbcdb726e09d3972d04245), compiled in this bot's own scratch directory. Addresses come from the incumbent's receipts (`scratch/r1805/steps.py` on four takes) and were checked with getters (`scratch/trial-podvault2-base/facts.py`, `facts.json`: token0 / token1 / factory / fee of every pool and pair, asset() of every vault). The incumbent sells WETH/USDC on a PancakeSwap V3 pool; the bot uses the Uniswap V3 0.01 pct pool (the executor has the Uniswap callback only).

Not used, by human decision 2026-11-21: any route that makes the Uniswap V2 Router02 the recipient to skip a pod's buy fee. The executor is the recipient of every swap and pays every pod fee.

Limits of the routes: the pairs are small (at block 60,804,842 the pCircle pair holds 26.5 pfUSDC-89, about 34 USD a side; the pfpOHMo-27 / peaPEAS pair 2.09 pfpOHMo-27; the pETHY pair 653 pfUSDC-135, about 810 USD a side), and a redeem from a pfUSDC vault reverts `InsufficientAssetsInContract` while its USDC is lent out, so `ethy_fwd` and `cir_rev` are takeable only while the vault holds idle USDC (the probe simply shows no gain then).

## Competition, 7 days to 2026-11-22 10:47Z (blocks 57,748,159-60,770,293)

How it was found: the payout census of `0xc0ffeefeed8b9d271445cf5d1d24d74d2ca4235e` (the operator behind the ICHI and pod bots the farm already copies; `scratch/r1805/routes.json`, `payouts.json`), routes that attempts:3692 listed as not built. The contracts on these three pods (`scratch/trial-podvault2-base/series.py`, `series-windows.json`; a take = a payout above 0.000002 ETH):

| route | executor (tx.to), senders are rotating 0xc0ffee... EOAs | takes 7 d | kept, ETH | median | max | last take |
|---|---|---|---|---|---|---|
| cir_fwd | `0x663561b9804beb7e3341dcca68afb132e2d31031` | 11 | 0.04765 | 0.0011 | 0.0215 | all on 2026-11-20 |
| cir_fwd | `0x043854d8784c038440a612c0a43101d63564be17` | 21 | 0.01775 | 0.00034 | 0.0040 | block 60,069,706, 2026-11-20 19:51:56Z |
| ohm_fwd | `0x67b45727964df17f770bd403a5f5266d10fca96a` | 15 | 0.00813 | 0.000023 | 0.00736 | block 60,156,449, 2026-11-21 00:41:05Z |
| ethy_fwd | `0xdf0ffea59f4efea9664c1f109f1f9c23461a6457` | 2 | 0.00458 | 0.0019 | 0.00268 | block 59,812,108, 2026-11-20 05:33:17Z |

49 takes, 0.0781 ETH (about 133 USD at 1,704 USD/ETH). No mirror-route executor paid out in the window; the mirrors are in the bot because the same gap opens the other way when the underlying moves the other way (as on the sibling's pods).

Blocks to take (20 takes, the 6 most recent of each executor; the bot's own `probe()` at 0.001 WETH run with a code override N blocks before the take; 0.2 s blocks):

| a gain was visible | 1 block before | 2 | 5 (1 s) | 15 (3 s) | 50 (10 s) | 150 (30 s) | 450 (90 s) |
|---|---|---|---|---|---|---|---|
| takes of 20 | 18 | 18 | 10 | 9 | 8 | 6 | 9 |
| with a gain of 0.00002 ETH or more (above a typical gas cap) | 17 | 17 | 5 | 4 | 4 | 4 | 4 |

The pCircle and pETHY gaps open one or two blocks before the incumbent takes them (tx index 2-5, priority 0.06-0.2 gwei) and are mostly out of reach. The peaPEAS / pOHMo gaps are different: 4 of the 6 sampled `ohm_fwd` takes had stood 90 s or longer at 0.00006-0.00021 ETH before the incumbent took them at tx index 4-30 for 0.0007-0.0105 gwei (e.g. `0xb8c0efce...` at block 59,394,088 kept 0.000218 ETH, 0.000214 visible 90 s before; `0x34d128df...` at block 60,014,923 kept 0.000139 ETH, 0.00015 visible 90 s before). Those are what this trial mainly sends at.

Priority fee level: 0.2 gwei on gains of 0.0003 ETH or more, 0.06-0.09 gwei on smaller pCircle gains, 0.0007-0.0105 gwei on the OHM route. The bot bids at most 20 pct of its simulated gross, spread over its gas limit, between 0.0001 and 0.05 gwei.

Paid entries in the last 7 days whose gross exceeds one attempt's gas: yes, e.g. `0x0375e70e44b2315c5530b8565e4427af34a681cdcff171555e73b9a6d4614484` (cir_fwd, block 60,068,180, kept 0.0215 ETH for 512,423 gas at 0.205 gwei = 0.000105 ETH), `0x4a2def4d67e92d3952a46a92cc98a42e29722c239bce2568aa62123e37778953` (ohm_fwd, block 59,104,695, kept 0.00736 ETH for 685,319 gas at 0.255 gwei) and `0xb750cc17d9e931a4752e55a03c317516d53cdecb99e4e2164823156d68652380` (ethy_fwd, block 59,812,106, kept 0.00268 ETH for 622,775 gas at 0.205 gwei).

## Fork proof

`python3 scratch/trial-podvault2-base/proof.py <parent> <result file>` (one Base fork lease: reset, deploy the artifact with `--args`, fund, non-owner, guard, success per route that pays at that block, leftovers, repeat, release). Three parents, one per incumbent take; the fork deployment is `0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352` each time.

Reset 59,104,694, the parent of the incumbent's `ohm_fwd` take `0x4a2def4d...` (block 59,104,695) (`proof-result-59104694.json`):

- non-owner `run` reverts NotOwner: `0x432c84a3ed1b38b33f727da15492d6d5ee72062815de436e05cb19ae6ac735c4`
- guard (minProfit 1 ETH) reverts NoProfit(gain 0.00627, 1e18): `0xb25d9ec5ebca301faa833d6b48f0c1fc153fe94fadf4e091bf984fcdfdce78c9`, 1,405,110 gas, owner -0.000140517 ETH at the fork's 0.1 gwei
- success `ohm_fwd` at 0.005 WETH: `0xc66d81f4d6eb10c4de4063ba51129b30ef6b10c513c7b0b195158986f993c7a3`, fork block 59,104,698, 1,157,308 gas, gross +0.006270799 ETH, owner +0.006155069 ETH net at the fork's 0.1 gwei (the incumbent kept 0.00736 ETH); the same call repeated reverts NoProfit (`0x1fc16ca33a759807e2e35005651a735b88a7c4af97f07028b825224b47252e27`)

Reset 60,068,179, the parent of the incumbent's `cir_fwd` take `0x0375e70e...` (block 60,068,180) (`proof-result-60068179.json`):

- non-owner revert `0x327379d7204945a6d53c7a65d07683004f08358c416362f43b4dbe2b7f0108c1`; guard NoProfit `0x4cb0a5191ec3ab28b939d93bb29b4d22bd01a14d37a31a0c98c339c6f78b3be9` (926,499 gas)
- success `cir_fwd` at 0.005 WETH: `0x2ebe0c983b099dc0aba3a2d38ed9d4b8942dd2ca5c3fdd046bf5966d036882d1`, fork block 60,068,183, 768,723 gas, gross +0.004471932 ETH, owner +0.004395060 ETH net (the gap at that block is wide enough that the repeated call still pays; the incumbent also took it in several transactions)

Reset 59,812,105, the parent of the incumbent's `ethy_fwd` take `0xb750cc17...` (block 59,812,106) (`proof-result-59812105.json`):

- non-owner revert `0x99d95039cdcb4b1441cdada0b94938616f96145f0ab31ae4eee60a0e69cb1acf`; guard NoProfit `0x637fcea3bc3279d27c600dc598aac87030b4b73c0cb3b54df1a236f1fbecd018`
- success `ohm_rev` at 0.0005 WETH: `0x34dc3d52a85c97b92f1c806fa27c4ac200156e1c4fe743bb445b918690e53fbf`, fork block 59,812,109, 1,180,106 gas, gross +0.000013836 ETH (net negative at the fork's 0.1 gwei gas price: it proves the mirror route's mechanics, not a paying take; the bot would not send it); repeat reverts (`0x24ca3f64b15ca2cfdb6de153abddc7eba22c99983a854bdfc1b3d006f433ae6e`)
- success `ethy_fwd` at 0.005 WETH: `0xbf25bcae9428012eb732d8f6926a15546938c1304968255e92d90edb3fa8a0c3`, fork block 59,812,111, 767,754 gas, gross +0.001318770 ETH, owner +0.001241995 ETH net (the repeated call still pays)

After each of the four successes the executor holds no native and none of the 14 route tokens (WETH, USDC, PEAS, pCircle, CIRCLE, pfUSDC-89, peaPEAS, pOHMo, OHM, pfpOHMo-27, pETHY, ETHY, VIRTUAL, pfUSDC-135) and no allowance to any of the 17 spenders. `probe()` answers for the owner and reverts for a stranger.

**Not proven with a success: `cir_rev` and `ethy_rev`.** No block in the 7 days was found where they pay (the incumbent has no payout on them either). `diag.py` sent both on the fork state left by the third run: every step executes (swap, bond or deposit, pair swap, redeem or debond, swaps back) and the transaction reverts only at the last step, the WETH repayment to the Balancer vault, because the round trip lost money (`diag-trace-cir_rev.json`, `diag-trace-ethy_rev.json`). They use the same step kinds as the four proven routes on the same contracts. If the reviewer wants only success-proven routes live, deleting the two entries from `ROUTES` is the whole change.

`selftest.py 60068179`: the bot's hand ABI encoding of `run()` (all six routes) and `probe()` equals `cast calldata`; its own `check()` at that block logs an opportunity and `paper_sim` success (`cir_fwd` at 0.016 WETH, gross 0.012384 ETH, gas cap 0.000084 ETH, tip 0.05 gwei).

## Loss bound

Same as the siblings: Base charges the L1 data fee at inclusion, so the enforceable worst case of one send is the bot wallet's native balance. The wallet holds 0.75 USD of ETH and `take()` refuses to sign while the wallet is worth 0.95 USD or more. A send needs simulated gain > signed gas cap (gas limit x maxFeePerGas + L1 allowance), `minProfit = cap + 1`, gas limit at most 3.2m, maxFeePerGas at most 0.1 gwei. Known limit of this design: one win above about 0.2 USD lifts the wallet over 0.95 USD and the bot then logs `wallet_at_or_above_usd_bound` and sends nothing more until the wallet is swept; that is a result to report, not a fault.

## Reads

- Feed: `/logs/base`, address `0x8f8184bb6d3817910bc2ef91a393d2fe3ca8d774` (Uniswap V3 PEAS/USDC, where a CoW TWAP order trades PEAS about every 864 s; PEAS is a leg of both OHM routes), Swap topic `0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67`, about 400 logs a day. It is the filter trial-podcycle-base and trial-podvault-base already hold, so no new filter. A swap or a `gap` triggers one `probe()` eth_call, at most one every 3 s. On 429 / 503 / timeout the timer keeps reading.
- Timer: one `probe()` eth_call (26 CU, six routes inside) every 40 s = 2,160 x 26 = 56,160 CU a day (40 s, not 60 s, because the gaps this trial aims at stand for tens of seconds and no pool event of CIRCLE, OHM or ETHY is subscribed); feed-triggered probes about 400 x 26 = 10,400 CU; a sweep is about 250 CU. About 68,000 relay CU a day = 0.036 USD at 0.53 USD per million CU; code cap 90,000. Feed CU is metered by the feed.

## Logs

`logs/bot.jsonl`: `start`, `check`, `opportunity` (route, sweep, cap), `opportunity_skip`, `paper_sim`, `send`, `send_result` (won / lost, gas used, winner block = the last Swap of the route's pod pair, blocks after the winner), `signer_reject`, `feed_error`, `read_budget`, `loop_error`.

## After the trial

After 7 days live or when the 0.75 USD is spent: an `attempts` row with sends, wins, net and the blocks after the winner; lead to `measured` or `blocked_infra`.
