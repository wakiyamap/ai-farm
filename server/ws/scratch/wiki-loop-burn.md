---
type: mechanism
chains: [ethereum]
protocols: [loop, reserve_revenue]
---
# Loop weETH burn: shares repay the caller's debt at parity, and pay no cash

**Conclusion.** The "redeem the acquired weETH for ETH" exit leg measured for the Reserve revenue Dutch auctions is *not* a redemption that pays the burner: burning weETH shares on Loop repays the **caller's own PoolV3 debt** at share parity, and a caller without debt receives nothing but a gas bill. Share parity is **1.107851 eETH per weETH share** (median of 71 paired burn/redemption legs, range 1.107791–1.107934, blocks 26392537–26394741, 2026-11-12), above the 1.1053 WETH/weETH cost bound (settled Dutch bid 1.0038 × reverse pool quote 1.1011). So the margin exists (+0.0026 ETH per share) but only for an actor that holds borrowed ETH at Loop — a bot must manufacture the debt leg (deposit the shares as collateral, borrow from PoolV3, burn to repay) inside its transaction.

## The mechanism

Loop is a CDP vault over LRT collateral (LoopFi `loop-contracts` README: `CDPVault.deposit/borrow/repay`, `PoolV3.repayCreditAccount` — borrowers "Loopers" borrow ETH against LRT derivatives). The burn entry point is manager `0xfbfe6b9cee0e555bad7e2e7309effc75200cbe38` (proxy, implementation `0xbe386b1f`), function selector `0xccc143b8`; EOAs call it directly (permissionless, no role). The burn:

1. transfers `N` weETH shares from the caller (token `0xcd5fe23c85820f7b72d0926fc9b05b43e359b7ee`), burns them (`Transfer` to `0x0`),
2. redeems them for eETH from the weETH contract (token `0x35fa164735182de50811e8e2e824cfb9b6118ac2`; the `Transfer` from the weETH contract to the manager fires in every burn — 71/71 paired), and
3. pays the redeemed eETH to the vault leg (`0x7d5706f6…`), reducing the caller's PoolV3 debt by that eETH amount at parity.

## Evidence

Burn example tx `0x0b3751aeb0a5d353bd222c06689635869a8ae86ad45458080bb16909390aaae0` (block 26394058, from EOA `0x233c09204a9bd98d2a80c3bf91a0fb37e9a96b16`): 27.903122 shares burned → 30.914815 eETH redeemed and forwarded (parity 1.107934 at that block). The `callTracer` trace of this tx contains **no internal ETH value transfer at all**, and the burner's ETH balance delta is exactly −gas (0.000193209 ETH = 277148 × 0.697 gwei) — on mainnet and on a fork replay of the same burn. A debtless funded EOA that called `deBT` on the fork likewise ended −gas. So parity is the value of the **debt repaid**, not cash out.

Burners are multiple independent EOAs (e.g. `0xd5f61bfd89…` burned 902.6, 480.4, 144.4 shares in recent blocks; also `0x233c0920…`, `0xdadef1ffbf…`, `0x93a0cfa576…`): long-term Loopers refinancing their borrowed ETH with shares bought cheaply in the Dutch auctions — the auction settled at 1.0038–1.0046 ETH+ per weETH while the burn repays 1.1079 ETH of debt per share.

## Pitfalls when measuring

- The burn pays no `Transfer` on the manager and no ETH; counting "burns" from `eth_getLogs` needs the canonical ERC20 `Transfer` topic0 `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` (`cast keccak "Transfer(address,address,uint256)"`), and the paired leg is the **eETH token's** Transfer from the weETH address, not the manager's.
- The weETH token has no `totalAssets()` and its `getAbsurdEth(uint256)` (`0x02c8dbdd`) reverts at this deployment — parity has to come from the burn/redemption pairing (or the eETH side), not a token getter.
- Parity drifts up slowly with staking yield (+0.00009 per day measured over the window); the cost bound (pool reverse quote × settled bid) drifts too. Measure both at placement, not once and forever.

Numbers, scans and the recipe live in KB attempts 963–964 (chain `ethereum`, lead 126).
