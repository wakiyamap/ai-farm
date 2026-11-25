trial: Dolomite liquidations on Arbitrum One, native USDC debt, through Dolomite's own liquidator proxy (zero capital)

# trial-dolomite-arbitrum

Cheap-chain trial bot (decision 2026-11-17-cheap-chain-trials). It measures by sending whether the farm can win
Dolomite liquidations against the keepers that take them today. Lead 276, attempts 2179.

## Mechanism

When a Dolomite account's adjusted collateral value falls under its adjusted debt x (1 + margin ratio), anyone may
take over its debt and receive collateral worth the debt plus the liquidation spread (about 5%). Dolomite ships a
verified proxy for this, `LiquidatorProxyV2WithExternalLiquidity` 0xcc24caa605375c011a4f7e6be7f6c2a3e377f368:
`liquidate(solid, liquid, owedMarket, heldMarket, expiry, paraswapCallData)` liquidates into the caller's own
Dolomite account and sells the seized collateral for the debt token through Paraswap Augustus V5 inside the same
`DolomiteMargin.operate`. The caller needs no balance: the surplus of the sale stays as a positive debt-token
balance in the caller's account.

Executor `DoloTake.take(TakeParams)` (owner-only, everything a call argument):
1. builds the Augustus `directUniV3Swap` calldata (fromAmount = sellAmount, beneficiary = the proxy, UniV3 path
   passed in) and calls `proxy.liquidate({executor, 0}, liquid, 17, heldMarket, 0, calldata)`;
2. `DolomiteMargin.operate` with one Withdraw (target 0) of the debt market to the bot wallet;
3. reverts `no profit` unless the bot wallet's USDC grew by at least `minProfit`.

Sizing: the proxy approves exactly the seized collateral amount and sells what Augustus pulls. A sell amount above
the seized amount reverts in the pull; a smaller one leaves the rest in the proxy. The bot finds the seized amount
by simulation (the whole collateral balance first; otherwise the oracle prices and the USDC debt give an estimate
and a short bisect over `eth_call` gives the largest pullable amount; on the fork this is exactly what the
incumbent sold in the next block) and sells 99.9% of it.

An account stays liquidatable after its first piece is taken: DolomiteMargin marks it `Liquid`
(`getAccountStatus` = 1) and the proxy accepts it above the threshold until the owner acts. The scan reads the
status too, so the later pieces of an unwind (8 and 15 blocks after the first one in the census) are tried.

Harness (scratch/trial-dolomite-arbitrum/harness.out): the bot's own scan and attempt path at the parent block of
the 19 past takes with owed market 17 finds an opportunity on 10 (1.63 to 1,703.43 USDC, gas cap 0.13-0.16 USD);
the other 9 are 5 dust cases under 20 USD of debt, one with collateral market 30 (no route) and 3 pieces of one
bad-debt account.

## Competition, 8.24 days to 2026-11-18 (blocks 522,929,803-525,349,803, scratch/dolo-arb-0e51/census.json)

- 30 `LogLiquidate` on DolomiteMargin 0x6Bd780E7fDf01D77e4d475c821f1e7AE05409072; 17 with native USDC as the debt;
  18 with debt of 20 USD or more; 65,454 USD of debt taken over in total (about 5% of it is the spread).
- Takers: EOA 0xd9fffdf0c4b18fb7e225da15b2af9f88e55676c3 19 (calls the proxy directly, the path this bot copies),
  EOA 0x1ff6b8e1192eb0369006bbad76da9068b68961b2 10 (own wrapper 0x8564f36e, 6-7M gas), EOA
  0x54cc312d1e45bb300ba94f3a53ad434a44f2dc30 1.
- Blocks to take: in the clean cases the account was liquidatable 8-40 blocks (2-10 s) before the take
  (tx 0x83022eac: unliquidatable at -12, takeable at -8; tx 0x8e7af72b: unliquidatable at -40, takeable at -12).
  Three takes at 523,801,783-808 were liquidatable for at least an hour before. One account's three pieces went
  to two operators 8 and 15 blocks apart (524,190,585 / 593 / 600).
- Priority fee level: none. Tx 0x8e7af72b paid 0.020002 gwei effective (base 0.02), tx index 3, 2,141,840 gas
  = about 0.08-0.13 USD. Arbitrum orders first come, first served; this bot bids no priority fee.
- Aim: the takes the keepers leave for more than one poll interval (45 s) and one piece of a multi-piece unwind.

## Loss bound

- Executor: `require(bal1 >= bal0 + minProfit && bal1 > bal0, "no profit")` (DoloTake.sol:127); a lost attempt
  costs gas only. No principal, no flash loan, no approval; the bot wallet holds gas only.
- Bot: `maxFeePerGas x gasLimit` < 0.90 USD and at most 50% of the simulated gross (bot.py, `fee_ceiling`);
  gasLimit = `eth_estimateGas` x 1.2; `minProfit` = the signed gas cap in USDC; skip when the gross is not above it.

## Reads (live, Alchemy CU/day)

- near scan: every 45 s one Multicall `eth_call` (150 accounts): 1,920 x 26 = 49,920
- discovery: every 10 min `eth_blockNumber` + `eth_getLogs` on DolomiteMargin (5 balance events): 144 x 85 = 12,240
- full scan: hourly, 2 Multicall calls (154 accounts): 24 x 2 x 26 = 1,248; margin ratio hourly 624;
  re-checks of dust accounts left marked Liquid (6 h cooldown) about 2,000
- per under-water account, per 60 s: about 15-25 `eth_call` (balances, prices, sizing, simulations), estimate, gas price
- Total about 66,000 CU/day = 0.035 USD/day at 0.53 USD per 1M CU. The code stops at 90,000 CU per UTC day.
- No feed filter: the trigger is an oracle price, not a log of one contract; the timer is the 45 s near scan.

## Scope

- Debt market 17 (native USDC) only, so the profit is USDC with no second swap. Collateral markets with a Uniswap
  V3 route to USDC in `routes.json` (pools checked on-chain by scratch/trial-dolomite-arbitrum/seed.py).
- Not covered: isolation-mode / wrapped collateral the proxy is not whitelisted for, expiry liquidations, other
  debt tokens, accounts whose last borrow event is older than the seed window (120 days, 154 accounts owing USDC at seed time; discovery adds new ones).

## Files

- `bot.py`, `run.sh`; `executor-runtime.hex` (fork deployment runtime, paper code override only);
  `seed-accounts.json` (accounts owing USDC at seed time); `routes.json`.
- Logs: `logs/bot.jsonl` (`start`, `scan`, `discover`, `opportunity`, `opportunity_skip`, `simulate_revert`,
  `paper_sim`, `send`, `send_result` with won / lost, gas used, winner block, `signer_reject`, `read_budget`).
- Live: executor address from `EXECUTOR_ADDR_ARBITRUM` or `EXECUTOR_ADDR` only.
