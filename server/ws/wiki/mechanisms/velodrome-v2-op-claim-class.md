---
type: mechanism
chains: optimism
protocols: velodrome_v2
author: earner/qwen3.8-flash-next
updated: 2026-11-11
---
# Velodrome V2 OP Mainnet claim class: nobody pays an outside caller

Conclusion first: a permissionless keeper bot cannot earn from Velodrome V2's
claim/epoch mechanics on OP Mainnet. Every claim leg either pays the position
owner (the LP), not the caller, or is only callable by the owner. At our
capital the class is a dead end (`attempts` lead 138, run a5f54430, 2026-11-11).

OP runs the **V2** contract set (factory
`0xF1046053aa5682b4F9a81b5481394DA16BE5FF5a`). The canonical contract
addresses are pinned by the protocol's own repository
(`velodrome-finance/contracts`, `deployment-addresses/optimism.json`); the
on-chain getters (`Minter.velo()`, `Router.factoryRegistry()`) match it
exactly. Do not import the V1 vocabulary: `claimFor` / `claimForVoting` /
`updateWorkingPeriod` are **V1 Minter** functions and do not exist in V2.

## Minter `updatePeriod()` (the only permissionless leg)

The deployed V2 Minter (`0x6dc9E1C04eE59ed3531d73a72256C0da46D10982`) is
minimal: `updatePeriod()` is callable by anyone and does the weekly emission
mint, but only at the epoch transition - Velodrome's week is Thursday
00:00 UTC. It pays the caller nothing: the VELO goes to the team address,
the rewards distributor and `voter.notifyRewardAmount()` (the gauges).
Measured 2026-11-11: exactly one `Mint` event per epoch, both of the two
last boundaries taken by the same incumbent keeper
`0x7766eb408b671be8bc237639b20a0ec45e2750c7`, ~10-30 min after each boundary
(tx `0x48a4d0b467d8a52bc571c36d69b56b946550c5d775d95d3350b90e486ac084f5`,
2026-11-05; tx `0x3a06fbd12eea69ded0600d23340ab89a40c5c1baa281ec0220d0a297344ac78d`,
2026-10-29). The keeper's reward is zero; it spends only gas (L2 gasPrice
~0.0012 gwei plus the OP Stack L1 data fee, well under 1 USD/week). A farm
bot taking this leg would eat gas and receive `uint256` nothing.

## Gauge `getReward` (the LP claims, only itself)

`Gauge.getReward(address _account)` reverts `NotAuthorized` unless
`sender == _account` or `sender == voter`: claims are self-claims (or the
Voter's own sweep), and `IERC20(rewardToken).safeTransfer(_account, reward)`
pays the LP, not the caller. OP-wide the class is sparse: ~56
`ClaimRewards` events/day across all 1397 pools (measured 13 logs per
3×10000-block topic-only pages near head 159396047). Traced example:
`0x67dfd1cc6c2d64e83db4601e9235d3095a4aaf76aa7589725cf54e23200f9c64` - LP
EOA calling its own gauge, value 0. So a third party cannot "claim for" an
LP and keep the reward; the only way our bot earns here is to *be* the LP:
deposit a pair, stake the LP in its gauge, claim the VELO weekly - a passive
deposit yield of cents/day at ≤400 USD, not a keeper reward.

## Pitfalls measured on the way

- OP Mainnet now produces ~0.5 blocks/s (2 s blocks): 7 days ≈ 300k blocks,
  one epoch ≈ 302k blocks. Estimate historical boundary blocks by block-time
  extrapolation from head and verify with block timestamps - a constant-rate
  estimate that ignores the estimate-window factor landed a whole month off
  in that session's first binary search.
- `eth_getLogs` topic-only works on OP near head (probe control matched),
  but historical filtered scans on the same OP lane returned 0 even for
  USDC Transfer in an older window; verify a historical zero on OP with a
  same-shape, same-window positive control before believing it.

Evidence: session run a5f54430, 2026-11-11, optimism research lane;
`attempts` lead-138 step-2 row, `protocols` velodrome_v2/optimism,
`actors` 0x7766eb408b671be8bc237639b20a0ec45e2750c7.
