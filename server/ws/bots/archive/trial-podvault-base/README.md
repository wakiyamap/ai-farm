trial bot (decision 2026-11-17-cheap-chain-trials): trial-podvault-base, Peapods pods paired against lending-vault shares on Base.

## What it does

Three Peapods pods on Base trade in a Uniswap V2 pair (factory `0x8909dc15e40173ff4699343b6eb8132c65e18ec6`, fee 30 bps) against an ERC4626 lending-vault share instead of a plain token:

| pod | pair | vault share in the pair | vault asset |
|---|---|---|---|
| pPEAS `0x9dbf562a65590c03e5400854d498844915c25944` | `0x8444c479777e9662eeec4a301349be26e90c64de` | pfWETH-12 `0x23574154842bc86cf5bbc5f99376cfa1e2f82497` | WETH |
| pTibbeas `0x35ed7afef147857fc4d1b64fcb98b64e107145c3` (underlying TIBBIR) | `0xd2bd8d1b22ddc1befbf888d90f98f20a6761ac64` | pfpPEAS-186 `0xa6ddb3c027c9882780a4c1544a93757674b9f393` | pPEAS |
| pBTC.pLeasE `0x7a148e0711beaaeeb8fe569877b21ff6c22f126b` (underlying cbBTC) | `0x287fdd1cffec8e6f8773e2c8eba757eb8605cc99` | pfpPEAS-145 `0xbf93c406a7d36da1facc2dbc6809be75c119cd7b` | pPEAS |

When PEAS, TIBBIR or a pair moves, a round trip pays. Six routes, each one executor call (Balancer V2 flash loan of 0.001-0.016 WETH, fee 0; the steps; repay; revert unless the WETH balance grew by `minProfit`; unwrap; pay the bot wallet in native ETH):

- `pfw_fwd`: WETH -> deposit pfWETH-12 -> pPEAS (pair) -> debond PEAS -> USDC (Aerodrome Slipstream `0xb0a65b3a`) -> WETH (Uniswap V3 0.01 pct `0xb4cb8009`)
- `pfw_rev`: WETH -> USDC -> PEAS -> bond pPEAS -> pfWETH-12 (pair) -> redeem WETH
- `tib_fwd`: WETH -> TIBBIR (Slipstream `0x0f664aff`) -> bond pTibbeas -> pfpPEAS-186 (pair) -> redeem pPEAS -> debond PEAS -> USDC -> WETH
- `tib_rev`: WETH -> USDC -> PEAS -> bond pPEAS -> deposit pfpPEAS-186 -> pTibbeas (pair) -> debond TIBBIR -> WETH
- `btc_fwd`: WETH -> cbBTC (Uniswap V3 0.05 pct `0x7aea2e8a`) -> bond pBTC.pLeasE -> pfpPEAS-145 (pair) -> redeem pPEAS -> debond PEAS -> USDC -> WETH
- `btc_rev`: the mirror of `btc_fwd`

Executor = `PodArbTake.sol`, the source of the live siblings trial-peapods-arb-base and trial-podcycle-base, unchanged (sha256 835323403217bcbf32c7c97d5c846aba854cea45edfbcdb726e09d3972d04245); its ERC4626 deposit / redeem step kinds (4, 5) are used here for the first time and are fork-proven below. Addresses come from the incumbent's receipts (`scratch/r1805/steps.py`) and were checked with getters (`scratch/trial-podvault-base/facts.py`, `facts.json`: token0 / token1 / factory / fee of every pool and pair, asset() of every vault). The incumbent sells WETH/USDC and WETH/cbBTC on PancakeSwap V3 pools; the bot uses the Uniswap V3 pools (the executor has the Uniswap callback only).

Not used, by human decision 2026-11-21: any route that makes the Uniswap V2 Router02 the recipient to skip a pod's buy fee. The executor is the recipient of every swap and pays every pod fee.

## Competition, 7 days to 2026-11-22 10:47Z (blocks 57,748,159-60,770,293)

How it was found: all native payouts to `0xc0ffeefeed8b9d271445cf5d1d24d74d2ca4235e` (the payout address of the operator behind the ICHI and pod bots the farm already copies) by `alchemy_getAssetTransfers`, grouped by the paying contract (`scratch/r1805/routes.py`, `payouts.json`, `routes.json`): 5,749 payouts from 339 per-route contracts, 0.935 ETH in 7 days. The contracts on these three pods (`scratch/trial-podvault-base/series.py`, `series-windows.json`; a take = a payout above 0.000002 ETH):

| route | executor (tx.to), senders are rotating 0xc0ffee... EOAs | takes 7 d | kept, ETH | median | max |
|---|---|---|---|---|---|
| pfw_fwd | `0x0b725e3828f9664c3c649a933629f1bb8a8f3f9c` | 17 | 0.00596 | 0.000089 | 0.0032 |
| pfw_fwd | `0x5817c0e2bdddcdb3ca24f60fe05efd74bda0a0e6` | 23 | 0.00584 | 0.000127 | 0.0019 |
| pfw_fwd | `0x0d42f51aa0038245920369f41dca45918681a5be` | 3 | 0.00364 | 0.00043 | 0.0031 |
| pfw_rev | `0x26532d44c942d5f051421adbc575b3560fdc95ee` | 11 | 0.2278 | 0.000197 | 0.2258 |
| tib_fwd | `0x96b2f4fc0be373c1f164fff5b9ea43a363514d8d` | 135 | 0.00478 | 0.000024 | 0.00029 |
| tib_rev | `0x25b1787cd778de5c654b01865d78290083c24ca4` | 292 | 0.01324 | 0.000025 | 0.00034 |
| tib_rev | `0x85f251b01e1a6fc030bde9cce84d56c540f16ea2` | 214 | 0.3296 | 0.000061 | 0.2870 |
| btc_fwd | `0x5b855858f2fdb940eb4cd7aacf82d313bab7f54a`, `0xa1cc75077e70c0452b87813a2f8bcbec277599cd` | 21 | 0.00743 | 0.000076 | 0.0035 |
| btc_rev | `0xe372249717d24fa6f467962cc61878e7492156a2`, `0x11c2e636f5e358d7bf7c1290b4c24f5e66b1ddb7` | 40 | 0.0246 | 0.00007-0.00009 | 0.0147 |

756 takes, 0.623 ETH. Two takes made 0.513 ETH of it in one PEAS move (`pfw_rev` in block 59,104,693, `tib_rev` in 59,104,699) and one `btc_rev` take kept 0.0147; the other 753 kept 0.095 ETH (about 157 USD at 1,647 USD/ETH, 22 USD a day), median 0.00002-0.0001 ETH (0.04-0.2 USD) a take.

Blocks to take (43 takes, the 4 most recent of each executor; the bot's own `probe()` at 0.001 WETH run with a code override N blocks before the take; 0.2 s blocks):

| a gain was visible | 1 block before | 2 | 5 (1 s) | 15 (3 s) | 50 (10 s) | 150 (30 s) | 450 (90 s) |
|---|---|---|---|---|---|---|---|
| takes of 43 | 38 | 38 | 20 | 18 | 10 | 11 | 11 |
| with a gain of 0.00002 ETH or more (above a typical gas cap) | | | | 8 | 4 | 2 | 1 |

So most gaps open one or two blocks before the incumbent takes them and are out of reach; about 1 in 10 of the takes was a gain above gas that had stood 10 s or longer (e.g. `btc_fwd` take `0xf345c6c8...` at block 59,561,545: 0.000108 ETH visible for 90 s or more; `btc_rev` take `0xb262c301...` at 59,389,474: 0.000073 ETH for 10 s). Those are what this trial sends at.

Priority fee level: the incumbent pays 0.003-0.25 gwei over the base fee, growing with the gain (0.004-0.02 gwei on gains under 0.0001 ETH, 0.09-0.25 gwei on gains of 0.001 ETH or more); takes sit at transaction index 2-37. The bot bids at most 20 pct of its simulated gross, spread over its gas limit, between 0.0001 and 0.05 gwei.

Paid entries in the last 7 days whose gross exceeds one attempt's gas: yes, e.g. `0x5c0f474cb399ee0b9f5d3331b59e1eef2c8fb4d5078542129d3bb36dd1e860d6` (block 60,679,614, 2026-11-22 05:46:02Z, kept 0.0032 ETH for 954,276 gas at 0.098 gwei = 0.000093 ETH) and `0xf345c6c87472a7679a603612da035f0ca9d1de949069bcfe12338a42e5119797` (kept 0.000083 ETH for 903,131 gas at 0.0093 gwei).

## Fork proof

`python3 scratch/trial-podvault-base/proof.py <parent> <result file>` (one Base fork lease: reset, deploy the artifact with `--args`, fund, non-owner, guard, success per route, leftovers, repeat, release).

Reset 60,679,613, the parent of the incumbent's `pfw_fwd` takes in blocks 60,679,614 and 60,679,615 (`proof-result-60679613.json`):

- non-owner `run` reverts NotOwner: `0xaf58365343885374a62052bbd3a1c1e256767fc0e99979b0a69ffa070bf090d0`
- guard (minProfit 1 ETH) reverts NoProfit(gain 0.001525, 1e18): `0x2a647df438fc799dbe8308fa67cc12c3bf2bcbbd66df4f210dea57ca747ace56`, 1,025,137 gas, owner -0.0001025 ETH at the fork's 0.1 gwei
- success `pfw_fwd` at 0.005 WETH: `0xc737cb507463284fbfee90ee3554e645f2690bbca483d5bba69de70914232616`, fork block 60,679,617, 847,055 gas, gross +0.001525241 ETH, owner +0.001440536 ETH net at the fork's 0.1 gwei (the incumbent kept 0.0032 and 0.0019 ETH in those two blocks); the same call repeated reverts NoProfit
- success `tib_fwd` at 0.001 WETH: `0xd42a6a40012f28294966766cb75d8b37d29247a704cdee937c28d805b3c0ad1a`, 1,075,075 gas, gross +0.000160993 ETH, owner +0.000053485 ETH net; repeat reverts
- success `btc_fwd` at 0.0005 WETH: `0x513d775a7e72c6c48c3db2a69159306b9ec76d3d26c22f8dd310c8e7b7be2d3b`, 1,014,696 gas, gross +0.000032448 ETH (net negative at the fork's 0.1 gwei gas price; at the live 0.005 gwei base fee the gas is about 0.000005 ETH); repeat reverts

Reset 59,104,692, the parent of the incumbent's largest `pfw_rev` take `0xdacf2f5c...` (block 59,104,693, kept 0.2258 ETH) (`proof-result-59104692.json`):

- non-owner revert `0xc6677af182d22848ce97da4f4a8c2e7e5e43e74939c25efe7f75c3823f9ed8ab`; guard NoProfit `0x7443033f66bc57a0842bd542d6532fe0601a27aad870e5e143e6fffd14ad7270`
- success `pfw_rev` at 0.005 WETH: `0xe040b6e1a107c4f0c6af171a2445ed1a278ced634774b464ca4764d2e35f1af2`, 807,852 gas, gross +0.234709 ETH
- success `tib_rev` at 0.005 WETH: `0x40f31251fe54df7f4df2040e441d3ad3f7573b1fa39a4dcb81282bd0d57406c8`, 1,104,845 gas, gross +0.248567 ETH
- success `btc_rev` at 0.005 WETH: `0x330611a5cc69c85c17e86f257ca09930a1d87e334ab2a5ef90bf01c712babbc9`, 1,255,549 gas, gross +0.202326 ETH
- at this block the gap is so wide that the repeated calls still pay (the incumbent also took it in several transactions); the three routes share the PEAS leg, so live they are one opportunity, not three

After each of the six successes the executor holds no native and none of the 11 route tokens (WETH, USDC, PEAS, pPEAS, pfWETH-12, pTibbeas, TIBBIR, pfpPEAS-186, pBTC.pLeasE, cbBTC, pfpPEAS-145) and no allowance to any of the 14 spenders. `probe()` answers for the owner and reverts for a stranger.

`selftest.py 60679613`: the bot's hand ABI encoding of `run()` (all six routes) and `probe()` equals `cast calldata`; its own `check()` at that block logs an opportunity and `paper_sim` success (`pfw_fwd` at 0.008 WETH, gross 0.001962 ETH, gas cap 0.000103 ETH, tip 0.05 gwei; `selftest-60679613.jsonl`).

## Loss bound

Same as the siblings: Base charges the L1 data fee at inclusion, so the enforceable worst case of one send is the bot wallet's native balance. The wallet holds 0.75 USD of ETH and `take()` refuses to sign while the wallet is worth 0.95 USD or more. A send needs simulated gain > signed gas cap (gas limit x maxFeePerGas + L1 allowance), `minProfit = cap + 1`, gas limit at most 3.2m, maxFeePerGas at most 0.1 gwei. Known limit of this design: one win above about 0.2 USD lifts the wallet over 0.95 USD and the bot then logs `wallet_at_or_above_usd_bound` and sends nothing more until the wallet is swept; that is a result to report, not a fault.

## Reads

- Feed: `/logs/base`, address `0x8f8184bb6d3817910bc2ef91a393d2fe3ca8d774` (Uniswap V3 PEAS/USDC, where a CoW TWAP order trades PEAS about every 864 s), Swap topic `0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67`, about 400 logs a day. It is the filter trial-podcycle-base already holds (Base had 7 of 16 filters in use at 2026-11-22 10:52Z). A swap or a `gap` triggers one `probe()` eth_call, at most one every 3 s. On 429 / 503 / timeout the 60 s timer keeps reading.
- Timer: one `probe()` eth_call (26 CU, six routes inside) every 60 s = 1,440 x 26 = 37,440 CU a day; feed-triggered probes about 400 x 26 = 10,400 CU; a sweep is about 250 CU. About 50,000 relay CU a day = 0.03 USD at 0.53 USD per million CU; code cap 90,000. Feed CU is metered by the feed.

## Logs

`logs/bot.jsonl`: `start`, `check`, `opportunity` (route, sweep, cap), `opportunity_skip`, `paper_sim`, `send`, `send_result` (won / lost, gas used, winner block, blocks after the winner), `signer_reject`, `feed_error`, `read_budget`, `loop_error`.

## After the trial

After 7 days live or when the 0.75 USD is spent: an `attempts` row with sends, wins, net and the blocks after the winner; lead to `measured` or `blocked_infra`.
