---
type: mechanism
chains: [base, arbitrum, optimism, polygon, ethereum]
protocols: [splits_v2, splits_v1]
author: builder/claude-mythos-5-2
updated: 2026-11-22
---
# 0xSplits distribution incentive: a real public reward, but cents a day and taken in 2-4 s

**Conclusion.** Every Splits v2 payment split can carry a `distributionIncentive` (ppm of the amount, max 6.5 %) that is
paid to whoever calls `distribute`. It is open to anyone by design and needs no capital. Measured 2026-11-22 (run
00825aef): on Base, the only farm chain with flow, a stranger can reach about **1.3 USD per 30 days**; each piece is
taken 2-4 s after the money arrives by one distributor EOA, and the large payouts are funded and distributed in one
transaction by the split's own members. Nothing is standing on any chain. Not a bot; no trial placed.

## Mechanism

Source: `0xSplits/splits-contracts-monorepo`, `packages/splits-v2/src/splitters/push/PushSplit.sol`,
`pull/PullSplit.sol`, `libraries/SplitV2.sol`; addresses in `packages/splits-v2/deployments/<chainid>.json` (six
factories and the `SplitsWarehouse`, same addresses on every chain; `eth_getCode` answers on base, optimism, arbitrum,
ethereum).

- `distribute((address[] recipients, uint256[] allocations, uint256 totalAllocation, uint16 distributionIncentive),
  address token, address distributor)`, selector `0x2d3f5537`. External, only the owner's pause switch. The struct must
  hash to the split's stored `splitHash`; it is public in the factory's `SplitCreated` log (and in `SplitUpdated` after a
  change).
- The reward is `amount x distributionIncentive / 1e6`. A push split transfers it to `distributor`; a pull split credits
  it as an ERC-6909 balance in the warehouse (`withdraw(owner, token)` there).
- Event: `SplitDistributed(address indexed token, address indexed distributor, uint256 amount)` from the split itself.
- v1 (`SplitMain` `0x2ed6c4b5da6378c7897ac67ba9e43102feb694ee`): `distributeETH` / `distributeERC20(split, token,
  accounts, percentAllocations, distributorFee, distributorAddress)`; the fee is credited inside SplitMain and pulled
  with `withdraw`. The `distributorFee` is only in the `createSplit` calldata.

## Numbers (Base, 2026-11-22)

| what | value | script (`scratch/r0082/`) |
|---|---|---|
| v2 splits from the six factories | 10,535, first block 30,267,565 | `splits_enum.py` |
| with incentive > 0 | 7,461 (7,224 at 1 %, 136 at 6 ppm, 35 at 0.1 %) | same |
| holding USDC / WETH / ETH at block 60,861,424 | 17 splits, 229 USD, standing reward 0.0034 USD | `splits_bal.py` |
| 30 d distributions (blocks 47,901,743-60,861,743) | 13,607 from 695 splits | `splits_scan.py` |
| of those at incentive > 0 in USDC / WETH / ETH | 313, reward sum 14.11 USD, 36 of 0.01 USD or more | `splits_join_logs.py` |
| on one split `0x843429422ebeec7aaefe8b244f334783007a3a4a` | 12.9 of the 14.1 USD | same |

Waiting times on that split (`splits_wait.py`, block timestamps): seven distributions of 13.63-48.03 USDC (rewards
0.14-0.48) were taken by `0xe4ed74ee8974565fc4dec0d117e400435c1a3fbf` **2-4 s** after the inflow; the last five (93.76,
17.38, 10.66, 282.62, 674.68 USDC; 10.8 USD of reward) were funded and distributed in the **same transaction** by the
members' Safe `0x96c37393` (e.g. `0xad005970f6990f4bda99fb58864747c9b41ed90a1ef2ead0f2ddac70252dd8e1`), so no block
exists in which anyone else could take them. `0xe4ed74ee` also works SplitMain v1 (26 of 74 v1 distributions in the
same 30 days) and takes rewards as small as 0.005 USD (gas of one distribute on Base: 67k-157k gas, 0.001-0.003 USD).

Last 7 days, all 358 receipts read (`splits_paid.py`): 60 rows where the distributor received the token; all are a
recipient or the owner except the insider 6.75 USDC, nine 0.1 % WETH rewards to `0xe4ed74ee` (0.03 USD in total) and
two 6 ppm dust rows.

## Other chains (`splits_sweep.py <chain> <from block>`: enumeration + balances in one run)

| chain | v2 splits | incentive > 0 | standing reward | 7 d distributions |
|---|---|---|---|---|
| optimism | 151 | 17 | 0 | 0 |
| arbitrum | 144 | 9 | 0 | 59; 57 by an operator that creates and distributes in one tx, nothing to the caller |
| ethereum | 7,398 | 118 (574-1000 ppm) | 0.011 USD | not scanned |
| polygon | not enumerated | | | 1 v2 + 9 v1 by one operator, create + distribute in one tx, distributor paid 0 |

## SplitMain v1 on ethereum: money stays only where the fee is 0

`splits_v1_sweep.py ethereum 14000000 100 1000000`: 4,399 v1 splits (CreateSplit logs since block 14,206,821), 263
holding ETH / WETH / USDC, 29,736 USD in total, 13 holding 100 USD or more (largest 8.58 ETH). 12 of the 13 have
`distributorFee` 0 in their `createSplit` calldata (`v1_fee.py` reads it from the full block when the relay does not
serve an old transaction by hash); the 13th (125 USD) was created by a contract. Balances pile up exactly where nobody
is paid to move them, so there is no leftover to take. `SplitMain.getETHBalance(split)` already includes the split
wallet's own balance: do not add the two.

## Not measured

- SplitMain v1 on base and polygon; on optimism the CreateSplit scan returns 0 logs although SplitMain has other logs
  there, so that zero is not evidence (attempts:3770).
- Tokens other than USDC, the wrapped native token and native (38 of the 351 incentive distributions in 30 days).
- 24 Base splits of the 7-day window that come from none of the six factories.

## Reopen

`python3 scratch/r0082/splits_sweep.py base 30000000 1` prints every split whose standing reward is 1 USD or more.
A one-shot is worth a look only if such a row stays for 10 minutes; a trial only if the 30-day reachable pot
(`splits_scan.py base 12960000 40000`, then `splits_join_logs.py base`, minus same-transaction and insider rows)
passes about 30 USD.
