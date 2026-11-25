trial

# trial-exactly-optimism

Cheap-chain trial (decision `2026-11-17-cheap-chain-trials.md`): Exactly Protocol liquidations of USDC debt on OP Mainnet,
flash-funded, one transaction through the executor `TrialExactlyLiquidator`. Win rate is measured by sending.

## Mechanism

- `Market.liquidate(borrower, maxAssets, seizeMarket)` on exaUSDC `0x6926B434CCe9b5b7966aE1BfEef6D0A7DCF3A8bb` is open to
  anyone on OP Mainnet. (The Base deployment is allowlist-gated by a Firewall: attempts:1726. OP has no `firewall()`.)
- The liquidator pays the repaid USDC plus 0.25 % for lenders and receives the seized collateral as the underlying token
  worth repaid x 1.0525 at Chainlink prices: 5 % gross.
- Executor: Morpho flash loan (USDC) -> `liquidate` -> UniV3 single-hop collateral -> USDC -> repay; reverts `NoProfit`
  unless its USDC balance grew by `minProfit`; pays the gain to the bot wallet as USDC.
- Prices are plain Chainlink proxies read at call time, so an account flips in the block of a Chainlink round or by
  interest accrual.

## Last 7 days of competition (blocks 159357984-159660384, scratch/trial-exactly-optimism/op-census.json)

- 115 `Liquidate` events, all with exaUSDC as the debt market, 113 borrowers, 14,627 USDC repaid. Median repay 0.04 USDC
  (dust), 32 events >= 1 USDC, 16 >= 20 USDC, 10 >= 250 USDC, largest 6,896 USDC.
- Seized: WETH 70, OP 30, USDC 12, wstETH 2 (not routed by this bot), WBTC 1.
- Six receiver contracts: `0x092aa488` 24 events / 9,730 USDC (takes in the block of the Chainlink round),
  `0x5ac9bc14` 11 / 4,460, `0x8a4efd06` 1 / 434, `0xa24b73b8` 72 dust events / 2 USDC (5 EOAs), `0x230be3ed` 4, `0xc76da7fe` 3.
- Blocks to take (Auditor.checkLiquidation at the capture's parent blocks, 45 captures): already takeable 1 block (2 s)
  before 18, 2 blocks before 8, 5 blocks (10 s) before 6, 30 blocks (60 s) before 3. Of the 23 probed captures >= 5 USDC
  only 4 were takeable one block before; the other 19 flipped inside the capture block.
- Priority-fee level (25 receipts): effective gas price 944 wei to 20 gwei, median 0.0025 gwei; the 6,896 USDC take paid
  20 gwei x 1.2M gas (about 0.044 USD); gas used median 949k; L1 fee median 1.4e-8 ETH; cost median 2.2e-6 ETH (0.004 USD).

## What the bot does

- Feed: `GET /logs/optimism?address=<ETH/USD aggregator>,<OP/USD aggregator>&topic0=AnswerUpdated` (aggregators read from
  the proxies `0x13e3Ee69...` and `0x0D276FC1...` every 30 min; 328 + 354 events per day on 2026-11-17). On a lower answer it
  re-reads the near list (accounts whose adjusted collateral is under 1.03 x adjusted debt) with one Multicall and tries
  the ones under water. On `gap`, a removed log or a feed error it re-reads the debtors through the relay.
- Safety polls: exaUSDC debtors every 10 min, every known borrower every 6 h, new borrowers from `Borrow` /
  `BorrowAtMaturity` logs every 30 min. Seed: borrowers of the last 400 days plus the 7 d liquidated accounts.
- Per account under water: `checkLiquidation` for the five routed seize markets, executor simulation for the two largest
  (full and half size, each fee tier), `eth_estimateGas`, then send only when simulated gross > signed gas cap.
- Send guard: `maxFeePerGas x gasLimit + 0.02 USD < 0.90 USD`, never above 0.5 gwei; priority bid at most 50 % of gross;
  `minProfit` = the gas cap in USDC.
- Log rows (`logs/bot.jsonl`): `start`, `discover`, `scan`, `round`, `opportunity`, `opportunity_skip`, `simulate_revert`,
  `round_no_take`, `paper_sim`, `send`, `send_result` (won/lost, gas used, winner block and tx, blocks after the winner),
  `signer_reject`, `read_budget`, `feed_error`.

## Read cost

About 48,000 relay CU/day (debtor scan 22,464; price rounds 8,840; discovery 9,312; full scan 3,120; attempts about 4,000)
plus about 24,000 feed CU/day (682 events x 654 bytes x 0.04 = 17,840; idle long-polls about 5,800): about 72,000 CU/day =
0.04 USD/day at 0.53 USD per 1M CU. Relay reads stop at 65,000 CU per UTC day in code.

## Proof

`scratch/trial-exactly-optimism/proof.py` (fork, reset 159512296): success +22.020528 USDC, gas 1,018,339; NoProfit,
NotOwner and nothing-to-take reverts. `selftest.py`: the bot's own calldata and simulation reproduce 22.020528 USDC at the
same block through the relay.

## Live

Needs `EXECUTOR_ADDR_OPTIMISM` (or `EXECUTOR_ADDR`); exits without it. Wallet holds gas only (15 USD).
