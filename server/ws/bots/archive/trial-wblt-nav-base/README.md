trial

# trial-wblt-nav-base

Cheap-chain trial (decision `2026-11-17-cheap-chain-trials.md`). Round trips between the public mint / redeem of BMX's
wBLT at the vault price and the BNKR / wBLT Uniswap v4 hook pool on Base. No principal: Morpho flash loan of USDC,
profit in USDC.

## Mechanism

- **The door.** BLT is the liquidity token of BMX's GMX-style vault. RewardRouter
  `0x49a97680938b4f1f73816d1b70c3ab801fad124b`: `mintAndStakeGlp(token, amount, 0, 0)` (the token approved to the
  GlpManager `0x9fac7b75f367d5b35a6d6d0a09572efcc3d406c5`) and `unstakeAndRedeemGlp(tokenOut, amount, 0, receiver)`,
  both open to anyone at the vault's price less its mint / redeem fee. `cooldownDuration()` is 0, so the staked BLT
  `0x64755939a80bc89e1d2d0f93a312908d348bc8de` moves in the same transaction. wBLT
  `0x4e74d4db6c0726ccded4656d0bce448876bb4c7a` is a Yearn-style vault over it: `deposit(amount, to)`,
  `withdraw(shares, to)`, `pricePerShare()` about 3.01.
- **The pool.** wBLT trades against BNKR `0x22af33fe49fd1fa80c7149773dde5890d3c76f3b` on a Uniswap v4 pool (fee 8000,
  tick spacing 1, hook `0x95afbc0fccf974b41380f24e562f15b6dd90fac8`). The hook holds the curve: the pool manager's
  slot0 shows price 1 and liquidity 0, so the price cannot be read from pool state. BNKR -> WETH on the V3-style
  pool `0xaec085e5…` (1 pct), WETH -> USDC on `0xb2cc224c…`.
- **The take**, one transaction through the executor `NavVaultArb`:
  redeem: flash USDC -> WETH -> BNKR -> wBLT, `withdraw`, `unstakeAndRedeemGlp` -> USDC, repay;
  mint: flash USDC -> `mintAndStakeGlp`, `deposit` -> wBLT -> BNKR -> WETH -> USDC, repay.
  `NoProfit` revert unless the USDC balance grew by `minProfit`; all USDC goes to the bot wallet.
- **The screen.** `quote(P)` on the executor runs the same round trip and always reverts with `Quote(gain)`. Each
  look is ONE `eth_call`: Multicall3 `aggregate3` of four quotes (both directions x 20 and 50 USDC). Only when one
  shows 0.03 USDC or more: one more call for six sizes (10-90 USDC), then `eth_estimateGas` and the exact `run()`.

## Competition, last 7 days (blocks 57,889,534-60,913,534, to 2026-11-22 18:44Z)

`scratch/r8b26/takes.py` -> `takes.json` (every wBLT mint and burn: 130 logs, 76 txs, 40 atomic takes).

| operator (executor) | takes | kept | size | gas price, tx index |
|---|---|---|---|---|
| A: payout 0xc0ffeefe…, rotating 0xc0ffee… keys (0x162e2b48, 0xbfc4e870, 0x3c47df92 redeem; 0x84296b84 mint) | 16 redeem + 7 mint | 0.00384 ETH = 6.6 USD (0.0001-0.0012 ETH each) | always about 30 USDC (70 wBLT) | 0.006-0.12 gwei, index 2-240 |
| B: EOA 0xf62b10b2 (0x071a60da) | 4 mint + 1 redeem | not sized | 37-84 wBLT | 0.006 gwei, index 45-155 |
| users through aggregators / ERC-4337 | 12 | - | 0.4-75 wBLT | 0.006 gwei |

Blocks to take: not measured per take (trial). What the take list shows: takes come in runs at one fixed size (three
in 46 s at blocks 58,176,658-886; 59,994,578 then 59,995,983, 281 s apart), so part of a gap stays open after the
first take. Priority fee level: most takes at the base fee (0.006 gwei) plus almost nothing; the largest redeem
(240 wBLT, block 59,670,995) paid 0.12 gwei at tx index 2. One attempt costs 2.0-2.2M gas = about 0.02 USD.

## Read cost

One `eth_call` (26 CU) every 30 s = 2,880 calls = 74,900 CU a day = 0.04 USD at 1M CU = 0.53 USD; a gap adds
3 calls (sizes, estimate, guard) and a block read. Hard cap in the bot: 95,000 CU a day, then it sleeps to 00:00 UTC.
No feed filter: nothing on chain marks the moment the hook pool's price moves (BNKR's own pool is a busy event).

## Loss bound

Gas only: at most 3.2M gas x 0.11 gwei = 0.000352 ETH (0.88 USD at the 2,500 USD reference) a send; the transaction's
`minProfit` is that send's own gas cap in USDC. Capital 5 USD of gas, no top-up.

## Proof

`scratch/trial-wblt-nav-base/proof.py` (both directions at the parents of two incumbent takes: redeem +0.191020 USDC
on 30 USDC at 59,994,577, mint +0.332945 USDC on 45 USDC at 60,389,127; NotOwner, NoProfit and losing-direction
reverts; no leftovers), `selftest.py` (paper path through the relay), `getters.py` (address controls).
