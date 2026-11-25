trial

# trial-euler-bsc

Cheap-chain trial (decision `2026-11-17-cheap-chain-trials.md`): Euler EVK liquidations on BNB Smart Chain,
debt in USDT, USDC or USD1, any collateral that has a Pancake V3 pool against the debt asset. Win rate is
measured by sending; nothing here counts as expected revenue under the race rule.

## What it does

1. Waits on the farm feed for `Liquidate(address,address,address,uint256,uint256)` (topic0
   `0x8246cc71...3962`) on the eUSDT-6 vault `0x95c5fd8618c68d6156a739c1eab5aa7c807ff148` (ASTER collateral).
   A large account there is unwound in many tranches; each tranche log is the moment to look again.
2. On an event (and about every 110 s as a safety poll, hourly over the whole universe) reads
   `accountLiquidity(account, true)` on the debt vault for the near-health list in one Multicall.
3. For an account with collateral value < liability and debt >= 5 USD: `EVC.getCollaterals(account)`, for each
   collateral vault finds the Pancake V3 pools collateral asset / debt asset through the factory (`getPool`
   for fees 0.01 / 0.05 / 0.25 / 1%, deepest two by the debt token they hold, cached a day), reads
   `checkLiquidation(executor, account, collateral)` and simulates the exact executor call at 100%, 50%, 25%,
   12%, 6%, 3%, 1.5%, 0.6%, 0.2% of the maximum repay, keeping the best (larger sizes revert when the pool
   price is below the liquidation price; the gain peaks at a size the pool can carry).
4. Live: sends `run(Params)` on its executor when simulated gross > the signed gas cap. The executor takes
   the debt asset by an exact-output flash swap on that pool, runs one EVC batch inside the swap callback
   (liquidate, repay, redeem, disableController), pays the pool in the redeemed collateral, sells the rest on
   the same pool, walks the proceeds to USDC (USDT/USDC 0.01% pool; USD1 goes through USD1/USDT 0.01% first)
   and reverts unless its USDC balance grew by `minProfit` (= the gas cap). All USDC goes to the bot wallet.
   Paper: logs `paper_sim`.

Debt vaults: the 18 EVK vaults with borrows whose asset is USDT, USDC or USD1 (`seed-accounts.json`
`debt_vaults`, from `scratch/trial-euler-bsc/probe.json`), e.g. eUSDT-4 (5.5M borrowed), eUSD1-2 (6.5M),
eUSDT-6, eUSDT-11, eUSDC-2. Borrowers come from `Borrow` logs: `seed-accounts.json` (the newest days, scanned
on 2026-11-18), new ones every 10 min, and a one-time backfill to 90 days by the bot itself. Collaterals
without a Pancake V3 pool against the debt asset (tokenized stocks, PT tokens) are skipped.

## Competition, last 7 days (to 2026-11-18, attempts:2105, `scratch/euler_bsc_liq_events.json`)

- 10 `Liquidate` events on 2 of the 29 borrow vaults (blocks 132,956,324-134,298,122).
- 9 are one episode on eUSDT-6 / eASTER-2 on 2026-11-16, blocks 133,602,282-133,611,085 (64 min): one
  540 USDT account taken whole, then violator `0xa402f52e` (72,000 USD of debt) unwound in 8 tranches of
  1,476-6,355 USDT, 3-19 min apart (382-2,535 blocks). Takers: contract `0xf000042d2b48921c234f15d167e7874f594f303e` 8,
  `0x0000000000be226afde21672a5e4adc45692e69d` 1. The account was under water at the parent block of every
  tranche (health 0.988-0.998), i.e. it stays takeable between tranches: the incumbents wait for a
  discount that pays their size.
- 1 is a 95 USDC stable/stable case (eUSDC-3 / eUSDT-3) taken by EOA `0x7d507d56`, health 0.99988, no gain
  through pools.
- Fees paid by the winners: effective gas price 1 gwei (20x today's 0.05 gwei minimum; the take
  `0xfef12e0e...` signed maxFee = priority = 1 gwei, gas limit 1,078,139, tx index 1, sender EOA
  `0xc0ca179b6aeaf81f920f560bc14dffba6ce2a918`), gasUsed
  769k-905k, about 0.46-0.55 USD per take.
- This bot on the same cases at the parent block (`scratch/trial-euler-bsc/harness.out`): +28.57 USDC on
  the 540 take (full size), +1.40, +1.46, +1.81, +3.11, +2.93 on five tranches (its size 409-1,082 USDT),
  nothing on three tranches (discount under the pool fee) and nothing on the stable case.
- Blocks to take were not measured per tranche (the account never left the takeable state); the farm's feed
  delivers a log about 1 s after its block, so the bot is expected behind the incumbents on the first take
  of a fresh account and aims at slices between their tranches.

This bot bids at most 50% of simulated gross as its gas price and never signs more than 0.90 USD of gas.

## Loss bound

- Executor reverts `NoProfit` unless the USDC gain >= `minProfit`; a lost attempt costs gas only (863k gas
  for a full run; up to 1.6M when it reverts late).
- `gasPrice x gasLimit < 0.90 USD`, never above 3 gwei; send only when simulated gross > that cap; on-chain
  `minProfit` = the cap. BNB price for this from the Pancake V3 USDT/WBNB 0.05% pool; the signer applies its
  own Chainlink price on top.
- No principal: the debt asset is a flash swap repaid by the seized collateral. The wallet holds gas only
  (10 USD of BNB).

## Read cost

- Relay: near scan about 785/day x 26 CU = 20,400; discovery 144 x 85 = 12,240; full scan about 1,000;
  about 34,000 CU/day. One-time backfill: 432 pages/day x 75 = 32,400 CU/day for about 4.5 days.
- Feed: one quiet filter (9 events in 7 days) and idle long-polls, about 5,000 CU/day.
- Total about 39,000 CU/day = 0.02 USD/day at 0.53 USD per 1M CU (about 71,000 while the backfill runs). The
  code stops relay reads at 90,000 CU per UTC day.

## Logs (`logs/bot.jsonl`)

`start` (with `executor=`), `scan`, `discover`, `backfill`, `feed`, `opportunity`, `opportunity_skip`,
`simulate_revert`, `paper_sim`, and in live `send`, `send_result` (won or lost, gas used, the winner's block,
tx and tx index, blocks after the winner), `signer_reject`.

## Checks

- `scratch/trial-euler-bsc/proof.py`: fork proof (size table, non-owner, NoProfit guard, success, leftovers,
  nothing to take) at the parent of the last tranche of the 2026-11-16 unwind.
- `scratch/trial-euler-bsc/harness.py`: bot calldata equals `cast calldata`; the bot's own scan and attempt
  path replayed at the parent block of all ten takes of the last 7 days.
