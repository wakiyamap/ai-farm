trial bot (decision 2026-11-17-cheap-chain-trials): trial-podcycle-base, Peapods pod pair cycles and pFUEGOx bond round trips on Base.

## What it does

A CoW Protocol TWAP order trades PEAS on the Uniswap V3 PEAS/USDC 1 pct pool `0x8f8184bb6d3817910bc2ef91a393d2fe3ca8d774` about every 864 s (GPv2Settlement `0x9008d19f58aabd9ed0d60971565aa8510560ab41`, `settle` 0x13d79a0b, e.g. tx `0x57f3a9e70073949eec7655ed4071341460c7fc7228bfb1a6ce56ba49d4db970d`, block 60,623,884). Every fill moves PEAS against the pods that are priced in PEAS, and two round trips start to pay:

1. **Pool cycle** (no bond): WETH -> pJailbrkPE (Aerodrome V2 WETH pair `0xdd5255ac`) -> PEAS (Aerodrome V2 PEAS pair `0xae7db74c`) -> USDC -> WETH. The pod `0x71e629ffc616436d4000fccfb436865f2e17613b` charges its normal transfer fee on the way; nothing is bypassed.
2. **Bond round trip**: WETH -> FUEGO (Uniswap V3 1 pct `0x2bbfb5a2`) -> `bond()` into pFUEGOx `0xd0b57b784ada47365ab3bda65fdf438b88252360` -> PEAS (Aerodrome V2 pair `0x81518d98`) -> USDC -> WETH.

Six routes (`jb_fwd`, `jb_rev`, `jb_fwd_slip`, `fuego_bond`, `fuego_bond_slip`, `fuego_debond`; `_slip` sells the PEAS on the Aerodrome Slipstream PEAS/USDC pool `0xb0a65b3a` instead). One executor call: Balancer flash loan of 0.001-0.004 WETH, the steps, repay, revert unless the WETH balance grew by `minProfit`, unwrap, pay the bot wallet in native ETH. Executor = `PodArbTake.sol`, the source of the live sibling trial-peapods-arb-base, unchanged (sha256 835323403217bcbf...).

Not used, by human decision 2026-11-21: any route that makes the Uniswap V2 Router02 the recipient to skip a pod's buy fee. Every pod transfer here pays the pod's fee (visible as the pod -> pod and pod -> 0x0 transfers in the fork receipts).

## Competition, measured 2026-11-22 (scratch/trial-podcycle-base: facts.py, trigger.py, fuego.py and their .json)

Pool cycle (txs that swap on both pJailbrkPE pairs): 144 in 600,000 blocks (33.3 h to block 60,664,390) = 104 a day. The last 45 (blocks 60,578,654-60,662,755, 4.67 h): 32 kept WETH, sum 0.001347 WETH, median 0.000034 WETH (0.06 USD at 1,666 USD/ETH).

| operator (tx.to) | takes of 45 | tx index | priority fee, gwei | kept, WETH | fee paid, ETH | when |
|---|---|---|---|---|---|---|
| `0x57266d6c36f7bd64325f86a5209d3b150c2f8b0a` | 17 | 2-17 | 0.0013-0.142 (grows with the gain) | 0.000004-0.000099 | 0.000003-0.000072 (about 70 pct of the gain) | block after the TWAP fill |
| `0xe143175ee1e7aee3639c08f5e57dad0d9e964eb5` | 7 | 7-45 | 0-0.0011 | 0.000008-0.000094 | 0.000002-0.000004 | same block as the fill (index + 1) or the next |
| `0xd8413bf7e7782b536abdeebbcb9e7c4fc481e2e7`, `0x1007fb1b439578423498f46479cd3452706c0e08` | 10 | 2-10 | 0.002-0.142 | paid in another token | 0.000005-0.000068 | same or next block |
| rotating self-call accounts (tx.from = tx.to: `0x5bfa9d49`, `0xb199cc55`, `0x8a82fd28`, `0x3b3617e6`, `0x50151513`) | 5 | 3-17 | 0.002 | 0.000025-0.000047 | 0.000006-0.000011 | 59-850 blocks (12-170 s) after the previous swap on the pod's pairs |

Blocks from the TWAP fill to the first take (12 fills, trigger.json): 0 for 3, 1 for 9: the main gap is gone in 0.2 s and is out of the farm's reach. What the bot aims at is the last row plus the same accounts' bond-only takes on pFUEGOx (`0xa96bdff9`, `0x01f9cd12`, `0x101e470b`): 8 leftover takes in 4.67 h = about 41 a day, 0.00002-0.00005 WETH each (0.03-0.08 USD), sum 0.000247 WETH = about 2.1 USD a day, taken by one slow operator at a 0.002 gwei tip. The other 5 of the 45 are single takes by five more addresses.

pFUEGOx bond takes (pod minted and sold into its pair in one tx): 31 in 13.3 h (blocks 60,423,211-60,662,757): `0x949a7a7c...` 26 (tip 0.0004-0.005 gwei, index 3-74, 0.000002-0.000033 WETH, 1-6 blocks after the fill where checked) and the rotating self-call accounts 5 (0.000021-0.000034 WETH, tip 0.002 gwei).

Paid entries in the last 7 days whose gross exceeds one attempt's gas: yes, e.g. `0xd18aa9651d0c714201bfdf14219d1a0e1a0c6f1b751421b89b65c612612f861a` (+0.000094 WETH for 0.0000041 ETH) and `0x2bb37ee4544cd12dd743796da242827c277a66703e1bf4b766c94cb69e2da578` (+0.000028 WETH for 0.0000085 ETH).

## Fork proof

`python3 scratch/trial-podcycle-base/proof.py 60623884 proof-result-60623884.json` (one Base fork lease: reset, deploy with `--args`, fund, non-owner, guard, success per route, leftovers, repeat, release). Block 60,623,884 holds the TWAP fill; the incumbent `0xe143175e` took the cycle in 60,623,885 (+0.0000943 WETH).

- non-owner `run` reverts NotOwner: `0xd3d3266e70e340676fcb37462cea90e410c34ddc4e9b4fbc4ab2ba1fee280b18`
- guard (minProfit 1 ETH) reverts NoProfit(gain 0.0001049, 1e18): `0x4ff53d85c057c4aa7c4fa78a331df1ef963d2308cb2f7e95e942a71e622c5528`, 812,628 gas, owner -0.0000813 ETH at the fork's 0.1 gwei
- success `jb_fwd` at 0.003 WETH: `0xe4763b0d7227ec670e871873308965fb4b5b224e83913f3c5ac99cb83a89af6b`, fork block 60,623,888, 671,079 gas, gross +0.000104869 ETH, owner +0.0000378 ETH net at the fork's 0.1 gwei (live base fee is 0.005 gwei: gas about 0.000004 ETH)
- success `jb_fwd_slip` at 0.0015 WETH `0xba8b3c6e2c2c3deed949a691f33699d7b467ab3d286468555742120a2c37412e` gross +0.0000389 ETH; `fuego_bond` at 0.001 WETH `0x5e5c92bf3c13773cd3c0dfc25ad1baddd490e0e03de8b6035ecbd0207d6cee92` gross +0.0000337 ETH; `fuego_bond_slip` at 0.0005 WETH `0x88a6ddf10fb9baa2d0efc2592a1a8a59c8804299acacb2088c75ebbd5b802fd9` gross +0.0000171 ETH (each net negative at the fork's 0.1 gwei gas price, positive at the live price)
- after each success the executor holds no native, WETH, USDC, PEAS, pJailbrkPE, pFUEGOx or FUEGO and no allowance; the same call repeated right after reverts
- `jb_rev` and `fuego_debond` (the mirrors) show no gain at this block and are not proven by a success; they use only step kinds that the proven routes use
- `selftest.py 60623884`: the bot's hand ABI encoding equals cast; its own `check()` at that block logs an opportunity and `paper_sim` success (route fuego_bond_slip at 0.002 WETH, gross 0.000127 ETH, cap 0.0000365 ETH)

## Loss bound

Same as the sibling: the bot wallet holds 0.75 USD of ETH and `take()` refuses to sign while the wallet is worth 0.95 USD or more (Base charges the L1 fee at inclusion, so the wallet balance is the enforceable bound). A send needs simulated gain > signed gas cap (gas limit x maxFeePerGas + L1 allowance), `minProfit = cap + 1`. The tip is at most 20 pct of the simulated gross.

## Reads

- Feed: `/logs/base`, address `0x8f8184bb6d3817910bc2ef91a393d2fe3ca8d774`, Swap topic `0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67` (about 400 logs a day; Base had 6 of 16 filters in use at 2026-11-22 04:59Z). A swap or a `gap` triggers one `probe()` eth_call, at most one every 3 s. On 429 / 503 / timeout the 60 s timer keeps reading.
- Timer: one `probe()` eth_call (26 CU) every 60 s = 1,440 x 26 = 37,440 CU a day; feed-triggered probes about 400 x 26 = 10,400 CU; sweeps about 200 CU each. About 50,000 relay CU a day = 0.03 USD at 0.53 USD per million CU; code cap 90,000. Feed CU is metered by the feed.

## Logs

`logs/bot.jsonl`: `start`, `opportunity` (route, sweep, cap), `opportunity_skip`, `paper_sim`, `send`, `send_result` (won / lost, gas used, winner block, blocks after the winner), `signer_reject`, `feed_error`, `read_budget`, `loop_error`.

## After the trial

After 7 days live or when the 0.75 USD is spent: an `attempts` row with sends, wins, net and the blocks after the winner; lead to `measured` or `blocked_infra`.
