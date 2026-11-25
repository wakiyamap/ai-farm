trial (cheap-chain trial bot, decision 2026-11-17-cheap-chain-trials): HypurrFi pooled-market liquidations on HyperEVM, WHYPE / USDT0 / USDC debt.

# trial-hypurrfi-hyperevm

## What it does
HypurrFi Pool `0xcecce0eb9dd2ef7996e01e25dd70e461f918a14b` (Aave v3 fork; provider `0xa73ff12d...`, market id
"HypurrFi Mainnet") is in wind-down: 16 of 19 reserves are frozen and the borrow caps are hit, but 2.21M USD of debt
is still open (WHYPE 86 %), and `liquidationCall` is open to anyone. For a borrower with WHYPE, USDT0 or USDC debt
and kHYPE, wstHYPE, WHYPE, USDT0 or USDC collateral whose health factor is under 1, the bot calls its executor once:
Morpho Blue flash loan of the debt token -> `liquidationCall` -> sell the seized collateral on UniV3-style pools ->
repay -> swap the gain to USDC -> revert unless the USDC balance grew by `minProfit` -> pay the gain to the bot
wallet as USDC. No principal; the wallet holds HYPE for gas only.

Triggers: the farm feed (`/logs/hyperevm`, Pool `LiquidationCall`, topic0 `0xe413a321...`; 67 events in 7 d, not a
busy event) and a ~55 s safety scan of the 200 health factors nearest to 1. After a feed event the near list is
rescanned 8 times, 2 s apart. Universe: the 2,172 debtors with at least 0.4 USD of debt (`seed-users.json`, from
every Borrow log the pool ever emitted, scanned at block 51,547,364), extended every 10 min from Borrow/Withdraw
logs; full scan hourly.

Routes (pools of factory `0xff7b3e8c...` except kHYPE/WHYPE): kHYPE -> WHYPE `0xbe352daf`, wstHYPE -> WHYPE
`0xff0a1d68` (thin: about 38 WHYPE), WHYPE <-> USDC `0x6c9a33e3`, WHYPE <-> USDT0 `0xbd19e19e`, USDC <-> USDT0
`0x94291bea`. Not covered: USDXL debt (Morpho holds none), USDH / UBTC / UETH debt, thBILL collateral; such users
are logged `opportunity_skip unsupported_assets`.

## Last 7 days of competition (blocks 50,931,683-51,536,483, `scratch/trial-hypurrfi/takes7d.json`)
- 67 `LiquidationCall` by 9 liquidator contracts: 0x372f8541 24, 0x86885a82 15, 0x5ac9bc14 12, 0x31401a47 5,
  0x429b6057 3, 0x72a3fcb2 3, 0x6aa43db6 3, 0x6af220c1 1, 0xd7a31895 1.
- Debt of the takes: USDXL 27, USDT0 10, USDH 9, wstHYPE 5, USOL 4, feUSD 2, UBTC 2, UETH 2, USDC 1, WHYPE 1,
  thBILL 1, others 3. In scope of this executor (debt and collateral both supported): 8, among them the 191.45 USDC
  and 13.11 USDT0 takes (both wstHYPE collateral); the other 6 are under 0.4 USD.
- Size: the 49 takes with stable debt covered 315 USD in total; the largest were 191.45 USDC (wstHYPE collateral,
  block 51,209,783) and 71.31 USDH; 13 takes of at least 1 USD, 28 of at least 0.2 USD.
- Blocks to take: not measured per take in the build session (the archive health-factor replay of
  `scratch/trial-hyperlend/scan.py` was not rerun for this pool). On HyperLend, the neighbouring pool with partly
  the same takers, real size was taken within 3-9 s and only dust waited a minute.
- Priority-fee level: the six sampled takes (`winners.py`) paid an effective gas price of 0.12-1.15 gwei
  (base fee about 0.1 gwei), tx index 0-8, 0.44-0.97M gas: quiet-time takes carry almost no bid.
- At head 51,547,364 (`head-scan.json`): 493 debtors with 1.05M USD of debt at HF 1.00-1.05 (largest: 142k USD on
  kHYPE collateral at HF 1.009); 355 under water, of which 353 are dust or bad debt without collateral and one is a
  thBILL position the incumbents only nibble.
- What this means for the trial: with the trial cap of 1 USD per transaction the bot can pay about 20 gwei at
  600k gas. It can win small and medium positions in quiet times; burst cases with a high base fee are logged as
  `opportunity_skip` (`gross_not_above_gas_cap`) and not sent.

## Evidence that the executor pays (`scratch/trial-hypurrfi/`)
- `proof_head.py` (fork at head 51,547,619; two existing borrowers trimmed to HF 1.00003 and aged 24-48 h):
  case A WHYPE collateral / WHYPE debt: success `0xb02ac64f...` +20.161193 USDC for 473,545 gas;
  case B kHYPE collateral / WHYPE debt: success `0xa6c82c6e...` +10.641796 USDC for 649,862 gas;
  healthy / non-owner / NoProfit / nothing-left reverts in both.
- `selftest_bot.py`: the bot's calldata equals `cast calldata` for all 15 (collateral, debt) pairs; the bot's bytes
  with the code override reach the pool and revert Aave error '45' for healthy borrowers.
- `proof_routes.py` (fork at head 51,548,001; four more existing borrowers, same guards): wstHYPE / WHYPE
  +0.399095 USDC (20 USD debt), WHYPE / USDT0 +1.164919 (42 USD), USDC / WHYPE +4.606903 (214 USD),
  wstHYPE / USDT0 through two pools +2.231692 (127 USD); 590-865k gas each.
- Not fork-proven: USDC debt (the path without an exit swap) and the kHYPE two-pool routes to USDT0 / USDC. The bot
  simulates the exact bytes before every send, so an unproven route can only produce `simulate_revert`, not a loss.

## Loss guard
- Executor reverts `NoProfit()` unless USDC grew by `minProfit` (= the signed gas cap in USDC); a lost attempt
  costs gas only.
- `maxFeePerGas x gasLimit < 0.90 USD` at the pool oracle's HYPE price; gas limit = estimate x 1.25, never above
  1,900,000 (HyperEVM limit 2,000,000).
- Sends only when simulated gross > that gas cap. Priority bid at most 50 % of gross.
- Capital 10 USD of HYPE, no top-up.

## Logs (`logs/bot.jsonl`, one JSON object per line)
`start` (with `executor=`), `scan`, `discover`, `feed`, `opportunity`, `opportunity_skip`, `simulate_revert`,
`paper_sim`, `send`, `send_result` (won / lost, `gas_used`, `send_block`, `winner_block`, `blocks_after_winner`),
`signer_reject`, `read_budget`.

## Read cost (live = paper)
- near scan: 1 Multicall `eth_call` per ~55 s = 1,570 x 26 CU = 40,800 CU/day
- full scan: 11 calls per hour = 264 x 26 = 6,900 CU/day
- discovery: `eth_getLogs` + `eth_blockNumber` every 10 min = 144 x 70 = 10,100 CU/day
- burst rescans: 8 x 26 CU per feed batch, about 10 events/day = 2,100 CU/day
- per opportunity: about 8-30 calls (up to 800 CU); a user with no gain on any route cools down for 6 h
- total about 60,000 relay CU/day + feed about 5,000 CU/day = 65,000 CU/day = 0.034 USD/day at 0.53 USD per 1M CU.
  The code stops relay reads at 75,000 CU per UTC day.

## Live
`EXECUTOR_ADDR_HYPEREVM` or `EXECUTOR_ADDR` must be set (the bot exits otherwise); the fork address is used only in
paper mode with a code override. Sends go through `farmbot_signer` (`/opt/farm/lib` is appended to `sys.path`).
