trial — cheap-chain trial bot (decision 2026-11-17-cheap-chain-trials.md): Moonwell OP Mainnet liquidations of mUSDC debt, taken through the OP/USD feed's OEV wrapper in the 10 s after a Chainlink round.

# trial-moonwell-optimism

## Mechanism

Moonwell's OP Mainnet oracle reads OP, WETH, WBTC, USDC, USDT, DAI and VELO through `ChainlinkOEVWrapper`
contracts (moonwell-contracts-v2 `src/oracles/ChainlinkOEVWrapper.sol`; OP wrapper
`0xcf6b619f3ebf8fc52998431d1798cdaf9259fd28`, `liquidatorFeeBps` 3000, `maxRoundDelay` 10 s, read on-chain).

- For 10 s after a new Chainlink round, `latestRoundData()` still returns the previous round, so
  `getAccountLiquidity` and a plain `mUSDC.liquidateBorrow` do not see the new price.
- In those 10 s, anyone may call `updatePriceEarlyAndLiquidate(borrower, repay, mTokenCollateral, mTokenLoan)`
  on the collateral feed's wrapper. It pulls the repay, liquidates at the new round and sends the caller mTokens
  worth the repay plus 30 % of the bonus; 70 % goes to the protocol. Net for the liquidator: about 2 % of the repay.
- The unlock is per wrapper and per call: a borrower who needs two fresh feeds (OP and WETH collateral, both
  falling) cannot be taken early. That is the 308.5 USDC case of 2026-11-14 (tx `0x6ade5d65...`), taken on the
  plain path in the first block after the 10 s for a 3.8 gwei priority fee.

The bot waits on the farm feed for `AnswerUpdated` of the Chainlink OP/USD aggregator. On a lower answer it
re-reads the mUSDC borrowers (one Multicall), and for those within 1.5 x the price drop of the edge it simulates
the executor call: Morpho flash loan of USDC -> wrapper liquidation -> `mOP.redeem` -> UniV3 OP/USDC 0.3 % ->
repay. It sends when the simulated gross exceeds the signed gas cap. A 5 min scan takes accounts that are
visibly under water on the plain path (full 7 % bonus), which in practice means leftovers.

## Last 7 days of competition (blocks 159356037-159658437, `scratch/trial-moonwell-optimism/windows.json`)

| Path | Takes | Takers | Blocks from takeable to taken | Priority fee |
|---|---|---|---|---|
| OEV wrapper (early window) | 14 (13 OP feed, 1 WETH feed), 82 USD repaid | 1 operator: EOA `0xd9fffdf0...` -> wallet `0x5ac9bc14...` | 1 block (2 s) x 12, 2 blocks x 1, 4 blocks x 1 | 0.0001-0.05 gwei (0.05 gwei on the four takes of 18 USD and more) |
| Plain liquidateBorrow | 224 events, 394 USD repaid, mostly dust | `0xc425ead3` 99, `0x3dd78e6b` 62, `0x7b62f2ab` 26, `0x27ead500` 18, `0x5ac9bc14` 13 | the one sizeable case (308.5 USDC) went in the first block after the 10 s delay, tx index 1 | 3.8 gwei on that case |

Wrapper takes with USDC debt of 3 USD and more: 18.63, 25.90, 18.41, 3.03 USDC repaid; the 25.90 one kept
0.505 USDC for 1.32M gas at 0.05 gwei (0.12 USD). The class is small: about 1.5 USD of liquidator gross in the
week. The trial measures whether the farm lands in the block after the round (feed delivery about 1 s, then
3 relay reads) and what fee wins it.

## Loss bound

- Executor `TrialMoonwellOevLiquidator` (owner-only) reverts `NoProfit` unless its USDC balance grew by
  `minProfit`, then pays the gain to the bot wallet. No principal: Morpho flash loan, repaid in the tx.
- `minProfit` = the signed gas cap in USD; the bot sends only when simulated gross > gas cap;
  gas cap = gasLimit x maxFeePerGas x (1.15 x oracle ETH price) + 0.02 USD L1 allowance < 0.90 USD.
- Priority fee bid: at most 50 % of the simulated gross.
- Wallet: 10 USD of ETH (OP Stack cap is 18 USD).

## Read cost

About 61,000 CU/day = 0.03 USD/day (1M CU = 0.53 USD):

- relay about 36,000: scan 288 x 26; discovery 144 x 96; gas and ETH price 144 x 46; lower rounds 180 x 26;
  simulations and attempts about 3,500. Hard stop in code at 65,000 relay CU per UTC day.
- feed about 25,000: filter address = Chainlink OP/USD aggregator `0x07c15082440a5e435ba15fe9ab704daead84897a`,
  topic0 `AnswerUpdated(int256,uint256,uint256)` `0x0559884f...`, 361 logs in the last 24 h at about 55 CU each,
  plus the idle subscription. On `gap`, 429, 503 or a connection error the bot re-reads every borrower through
  the relay; the 5 min scan is the safety poll.

## Files

- `bot.py`, `run.sh`: the bot (paper: relay `eth_call` with a code override at the fork address, sends nothing;
  live: `EXECUTOR_ADDR_OPTIMISM` / `EXECUTOR_ADDR`, signer).
- `executor-runtime.hex`: `eth_getCode` of the fork deployment (paper override only).
- `seed-users.json`: 81 mUSDC borrowers from 60 days of Borrow / LiquidateBorrow logs; new ones are added from
  Borrow logs every 10 min.
- Proof and self-test: `scratch/trial-moonwell-optimism/proof.py`, `selftest.py`.

## Log rows (`logs/bot.jsonl`)

`start`, `discover`, `scan`, `round` (answer, prev, action, feed_lag_s, tried), `round_no_take`, `opportunity`
(path wrapper or direct, gross_usd, gas_cap_usd), `paper_sim`, `send`, `send_result` (won / lost, gas_used,
winner_block, blocks_after_winner), `opportunity_skip`, `simulate_revert`, `signer_reject`, `feed_error`,
`read_budget`, `aggregator`.

## Limits known at placement

- Only the OP/USD round is watched; WETH- or WBTC-collateral accounts are taken on the plain path by the scan only.
- Only mUSDC debt (83 % of the 7-day repaid USD); profit is paid out in USDC.
- One UniV3 pool per collateral (OP/USDC 0.3 % holds about 6k USDC): above about 150 USDC of repay the bot also
  tries half the size and keeps the better one.
