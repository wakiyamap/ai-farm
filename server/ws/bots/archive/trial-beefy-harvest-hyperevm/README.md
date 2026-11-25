trial (cheap-chain trial bot, decision 2026-11-17-cheap-chain-trials): Beefy CLM strategy harvest caller fee on HyperEVM.

# trial-beefy-harvest-hyperevm

## What it does

Each of the 9 active Beefy cowcentrated (CLM) strategies on HyperEVM pays a WHYPE caller fee to
whoever calls its public `harvest(address callFeeRecipient)`. The fee grows with the pool's trading
volume since the last harvest. One transaction through the executor `BeefyHarvestTake`:

1. calls `strategy.harvest(executor)`,
2. unwraps the WHYPE fee,
3. pays it to the bot wallet as **native HYPE**,
4. reverts `NoProfit` unless the wallet gained at least `minProfitWei`.

The bot sets `minProfitWei` to that send's whole gas cap (gas limit x maxFeePerGas), so a lost
attempt costs gas only (0.003-0.007 USD).

This is a threshold contest, not a speed race: the incumbent waits until fee / its gas is about
1.24 at 0.115 gwei (about 1.43 x gas at the 0.1 gwei base fee). The bot sends at priority 0 as soon
as the fee exceeds its gas cap (about 1.07 x pre-refund gas at the base fee; storage refunds make
the gas actually paid about 0.82 x pre-refund), which is reached earlier.

## Last 7 days of competition (blocks 51143000-51748200, to 2026-11-20 06:45Z; attempts:2797)

232 `ChargedFees` receipts on the 9 strategies (`scratch/trial-beefy-harvest-hyperevm/rows.json`):

| caller | route | harvests | caller fees (WHYPE) | gas (HYPE) | fee > gas | gas price |
|---|---|---|---|---|---|---|
| EOA 0xde3af1d882b714f0afb46724ab22761d53f0efac | direct `harvest(address)` | 200 | 0.029371 | 0.023001 | 198 | 0.115 gwei (base 0.1 + priority 0.015), tx index 0-3 |
| EOA 0x03d9964f4d93a24b58c0fc3a8df3474b59ba8557 | direct, about daily per strategy (hygiene) | 29 | 0.001498 | 0.006361 | 2 | 0.1-0.12 gwei |
| EOA 0x2e8d0cc9ab070d1336188c907b565565f9c03bb5 | via contract 0x457f35b4 (selector 0x7d14bb51) | 3 | 0.001029 | 0.000487 | 3 | - |

- Blocks to take: not a block race. The fee crosses a caller's own threshold gradually; strategies
  0x6DD1C86d and 0xaacd20Da are harvested about every 5,700-6,400 blocks (1.7 h, minimum 1,450),
  0x92E3B9AB about every 10,650, the other six about every 82,000 (daily).
- Priority-fee level: 0.015 gwei fixed by the incumbent; no fee auction.
- Fee per harvest: median 0.00013 WHYPE, max 0.00078; gasUsed 0.82-0.92M.
- Scale: whole class gross 0.032 WHYPE / 7 d (about 2.1 USD). The bot can make at most about
  0.05-0.07 USD/day; the trial measures whether a lower threshold wins the harvests.

## Evidence

- Fork proof: `scratch/trial-beefy-harvest-hyperevm/proof.py` (result `proof-result.json`), head fork
  51748539 with the base fee set to mainnet's 0.1 gwei. Success
  `0x5ae79167d6a23b527605c2df62d7d45d4084e61e0f39611436068de563838656`: gross +0.000116003 HYPE, gas
  0.0000837046, owner delta +0.0000322985 HYPE with minProfit = the gas cap. Reverts: not owner,
  minProfit above the fee, expired deadline, and the same call again after the take.
- At head 4 of 9 strategies revert inside harvest (0xaacd20Da `0x26c87876` at that moment; 0x2CdC,
  0x2bBC, 0x9609 in their reward swaps). The bot logs `sim_revert` and re-checks them every 30 min.

## Files

- `bot.py`: timer loop; per strategy an `eth_call` of the exact `take()` (paper: code override of
  the fork deployment), next check where the accrual rate puts the fee at the threshold (30 s to
  30 min). Live: `EXECUTOR_ADDR` (or `EXECUTOR_ADDR_HYPEREVM`) is required; sends through the signer.
- `executor-runtime.hex`: `eth_getCode` of the fork deployment, paper only.
- `logs/bot.jsonl`: `start`, `sim`, `sim_revert`, `opportunity`, `paper_sim`, `send_result`
  (won/lost, gas_used, send_block, winner_block), `signer_reject`, `read_budget`.

## Read cost

About 500 strategy checks/day x (eth_call 26 + eth_getBlockByNumber 20 CU) plus re-simulations:
about 25,000 CU/day = 0.013 USD/day at 1M CU = 0.53 USD. Hard cap 90,000 CU/day in code; every
read is inside the handler that catches the cap and sleeps. No feed filter.

## Loss guard

- Executor: owner-only, `tx.gasprice <= maxGasPrice`, deadline, reverts unless the wallet gains
  `minProfitWei`.
- Bot: gas limit = (simulated gas + 30,000) x 1.04, at most 1,950,000; maxFeePerGas = base fee x
  1.03 + priority, at most 0.5 gwei (worst case 0.000975 HYPE per send); priority bid at most 20% of
  the surplus over the base-fee gas cap; no send unless simulated fee > gas limit x maxFeePerGas.
