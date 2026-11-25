# trial: trial-cv3-buy-optimism

**Trial bot** (decision 2026-11-17-cheap-chain-trials): cheap chain, race rule and EV floor
waived, the win rate is measured live by sending. OP Mainnet copy of `trial-cv3-buy-arbitrum`
(same author, same executor design, own copy of everything).

After anyone absorbs an underwater account on Compound v3 OP Mainnet (cUSDCv3
0x2e44e174f7d53f0212823acc11c01a11d58c5bcb, cUSDTv3 0x995e394b8b2437ac8ce61ee0bc610d617962b214;
addresses from compound-finance/comet `deployments/optimism/*/roots.json`), the collateral sits
in the comet's reserves and anyone may `buyCollateral()` it at the comet's discount (both comets
are below `targetReserves`, so the sale is on). The executor `Cv3FlashBuyOut` does it with no
principal, in one transaction: flash-swap on a UniV3 {collateral, base} pool (sell exactly the
quoted collateral), pay the comet from the pool's base token inside the callback, sell a USDT
surplus to USDC on the UniV3 USDT/USDC 0.01 % pool, revert unless the USDC surplus exceeds
`minProfit`, send the USDC (native USDC 0x0b2c639c..ff85) to the bot wallet.

## Competition, last 7 days (eth_getLogs, blocks 159,348,859-159,651,259, `scratch/cv3x/scan.json`)

- 9 absorb txs; 21 BuyCollateral, 9 of them inside the absorb tx; 12 residue buys by 6 buyers
  (0xf000042d, 0xa499fac1, 0x4661f836, 0x5ac9bc14, 0x3dd78e6b, 0xc425ead3). 7 are dust (< 1 USDC).
  cWETHv3 0xE36A30D2..b6Fd had no event and is not covered.
- The 5 non-dust residue buys (receipts in `scratch/trial-cv3-buy-optimism/discover.json`):

| buy tx | block | blocks after absorb | executor | paid | kept (gross) | gas used | priority fee | cost |
|---|---|---|---|---|---|---|---|---|
| 0x2ec85415..3857 | 159,470,695 | 1 (2 s) | 0xf000042d | 2032.82 USDC (WBTC) | 0.05742 WETH (~105 USD) | 656,819 | 3.00 gwei | 0.00197 ETH |
| 0x25d1a267..e754 | 159,470,695 | 1 (2 s) | 0xf000042d | 741.15 USDC (WETH) | 0.01596 WETH (~29 USD) | 456,248 | 1.02 gwei | 0.000467 ETH |
| 0xdb2688d1..2e8b | 159,470,694 | 0 (idx 4 -> 19) | 0xa499fac1 | 15.45 USDC (OP) | 0.00100 WETH | 452,583 | 0.11 gwei | 0.00005 ETH |
| 0xd98d9772..5daa | 159,533,751 | 1 (2 s) | 0xa499fac1 | 4.72 USDC (OP) | 0.00032 WETH | 453,776 | 0.034 gwei | 0.000015 ETH |
| 0x6ffb468a..6f7c | 159,545,444 | 0 (idx 105 -> 141) | 0xa499fac1 | 234.12 USDC (OP) | 0.01704 WETH (~31 USD) | 457,437 | 1.52 gwei | 0.000694 ETH |

- Blocks to take: 0-1 (0-2 s). Priority fee level: 0.03-3.0 gwei, 3-5 % of gross; base fee
  1,000-24,000 wei; L1 data fee 6e9-3e10 wei (under 0.0001 USD).
- This bot wakes on the feed after the absorb block and lands one block later at best, bidding
  up to 25 % of gross but never more than the per-send cap (about 0.7 gwei at a 500k gas limit).
  It expects to lose to 0xa499fac1's same-block buys and to win only where 0xf000042d is late,
  absent or outbid on a small lot; that share is what the trial measures.

## Fork proof (`scratch/trial-cv3-buy-optimism/proof.py`, optimism fork gen 28-29, output `proof.out`)

One script: lease, reset, deploy with constructor arg = owner, checks, release.

Case A, reset 159,470,694 (the absorb block of 0x3821a38e, parent of the first two table rows),
cUSDCv3, no out pool:

- DEPLOY 0x28f54608af091ef1d9a0f3ee6ecfa95e8635a30d58004ab82597bd9cc796e305 gas 950,161
- NON-OWNER 0x966b116ac3ad4b7b345ca66c65efab86075d4e9f3ced44c6df80f96f9e9ebd2b status 0
- GUARD (minProfit 1e12) 0x6f6cd60c95562971099e3b08e4f75437e0214c57daa76b5aca5ac60aa629114c
  status 0, NoProfit, owner USDC delta 0
- SUCCESS WBTC via UniV3 WBTC/USDC 0.05 % 0x394a9fcb..2f69:
  0x6ddc4183e91783da57872c192a9d2c2aa1be219b2b33964506c16cd90bfb8b47 status 1, gas 317,964,
  block 159,470,698 (reset + deploy + two reverted checks): paid 2023.738074 USDC for the WBTC
  residue, **owner wallet +116.181202 USDC** (= the eth_call simulation). Executor afterwards:
  0 USDC, 0 WBTC, 0 native, allowance to the comet 0.
- NOTHING-LEFT (same call again) 0xc47be457414010898c814a745f3c3c05a0331816ea513bb985710528128eab76
  status 0, owner USDC delta 0.
- SUCCESS WETH via UniV3 WETH/USDC 0.05 % 0x1fb3cf6e..db7b:
  0x80ca553022ea26ed58ad7c6cd5524fdfbd686ad3bd08e88da296ce7a8e9cb08c gas 339,581,
  **owner wallet +31.284237 USDC**; NOTHING-LEFT 0x3cbda8bc54ca82a30981b1431e1de2b67480ee0e8406ef636ff68a3d16ca4b47 status 0.

Case B, reset 159,533,811 (parent of the incumbent's absorb+buy 0x6ac3de17), cUSDTv3. No USDT
residue was left on-chain in the 7 days, so the residue is made the way it arises: a stranger
calls the public `absorb()` on the same borrower (0xecec6d5920a0ad82089845d806a2bac149ee36080dc45a9e9770fc7713c48039,
status 1), then the executor buys the 409.4 OP via UniV3 OP/USDT 0.3 % 0xb2ac2e5a..114d and
sells the USDT surplus on USDT/USDC 0.01 % 0xa73c628e..0e8e:

- GUARD 0x18fa40ff58c5f884b5bab71b4aab56e75451344a68044f15aa56c6dd641d1729 status 0
- SUCCESS 0xa223d7558d8bb48612f046e8a5e73b64c5f57f146409eb8f316635fce1e4d5b4 gas 422,048,
  **owner wallet +3.022947 USDC**, executor empty
- NOTHING-LEFT 0x2157711baaaf9d343e030e0f303bc5f2729a7106d8fdf1564c5db6931bcd1b86 status 0

`scratch/trial-cv3-buy-optimism/paper_selftest.py` runs this bot's own `check()` on the fork at
159,470,694: the Multicall scan finds 2033.91 USD of WBTC and 741.15 USD of WETH in cUSDCv3,
simulated gross 116.181202 and 31.284237 USDC, gas limits 486,584 and 541,104 (estimate x 1.25),
gas cap 0.95 USD each, `paper_sim` success twice (`selftest.out`).

Paper mode simulates the exact call with `eth_call` and a code override (the fork runtime,
`executor-runtime.hex`) at the fork address 0xfe00ddfe..8e9a (no code on mainnet), from the
owner baked into that runtime (0xc0ffee..02). Live mode uses the signer's address and
`EXECUTOR_ADDR`.

## What the bot waits for

- Feed `/logs/optimism`, address = the two comets, topic0 = AbsorbCollateral
  `0x9850ab1af75177e4a9201c65a2cf7976d5d28e40ef63494b44366f86b2f9412e` (9 absorb txs / 7 d, bursty).
- On `gap`, `removed`, HTTP 429 / 503 / 400 or a connection error: re-read the reserves
  through the relay (at most once a minute while the feed is down), then continue.
- Safety poll of the reserves every 10 min (one Multicall3 `eth_call` for all routes).
- Routes: cUSDCv3 WETH (0.05 % and 0.3 % pools), WBTC (0.05 % and 0.3 %), OP (0.3 %);
  cUSDTv3 WETH, WBTC, OP, wstETH (one pool each). Pools are UniV3 factory 0x1f98431c..f984
  `getPool` results with their depth read on 2026-11-17 (`discover.py`); the best simulated
  pool is used; a lot too big for the pool is retried at 50 % and 20 %. wstETH on cUSDCv3 and
  wUSDM have no usable direct pool and are not tried.

## Send rule and loss bound

Send only when the simulated USDC surplus is above that send's gas cap:
`gasLimit x maxFeePerGas x ETH price + 0.02 USD (L1 data fee allowance)`, with
`gasLimit = eth_estimateGas x 1.25` (refused above 900,000), `maxFeePerGas = min(fee cap,
2 x base fee + priority)`, priority = at most 25 % of gross, and the fee cap chosen so the
whole expression never exceeds 0.95 USD. The ETH price is max(2,500 USD, 1.15 x the price the
comet itself quotes WETH at), re-read at every check (ETH is ~1,820 USD today). `minProfit` in
the call is that cap, so a mined transaction either nets more than its gas cap or reverts
(`Cv3FlashBuyOut.sol` NoProfit check). Worst case per send = gas. OP Stack: the native wallet
gets 10 USD, under the 18 USD cap; principal comes from the flash swap. Every send logs
`send_result` with won / lost, gas used, gas cost, the winner's block and how many blocks after
it we landed.

## Reads

Safety poll: 144 Multicall `eth_call`/day x 26 CU = 3.7k CU. Absorb wakes: ~1.3/day x (1 scan +
up to 6 sims + estimate + gasPrice) = under 1k CU. Feed: ~4 CU/min subscription = 5.8k CU plus
~35 CU per event. Total ~10k CU/day = 0.005 USD/day at 0.53 USD per 1M CU; the bot stops
reading at 60k relay CU/day (`CU_CAP`).
