---
type: mechanism
chains: [arbitrum]
protocols: [gmx_v2]
---

# GMX v2 Arbitrum liquidation execution and fee destination

Conclusion: a keeper liquidation is EOA -> permissionless keeper wrapper ("batch adapter") -> live
LiquidationHandler 0xa5d2d45228ee2e3a18ab122b2ce84997d008f4eb (executeLiquidation selector 0xc6561b45,
module delegatecall 0x2b19a6ab35). The wrapper (not the handler) is the caller the RoleStore gate checks,
and the wrapper pays the liquidation fee in wMATIC (0x82af4944d3737c675258ad75173cc70629489378) to ITS OWN
configured recipient - not to msg.sender and not in the position's collateral token. A bot earning through
an incumbent wrapper therefore earns NOTHING (the fee goes to the wrapper's recipient); earning requires a
farm-owned wrapper deployment whose recipient points at the farm. Wrapper membership in LIQUIDATION_KEEPER
(RoleStore 0x3c3d99FD298f679DBC2CEcd132b4eC4d0F5e6e72) is granted by the RoleManager admin (timelock).

Order of the money legs (measured dust capture tx 0xb70b29cf at block 521666037, collateral USDC):
1. seized collateral USDC 587168 wei is pulled through the deposit adapter to the swap adapter;
2. the wrapper receives the swap output in wMATIC (2.56e14 wei);
3. the wrapper repays the Vault 31ef83a530fde1b38ee9a18093a333d8bbbc40d5 first (1.526e14 wMATIC);
4. the fee portion goes to the wrapper's configured recipient (5.69e13 wMATIC to
   0xda1b841a21fef1ad1fcd5e19c1a9d682fb675258 for wrapper 0x5503b99308db6923758f9a22d118207d633c4e87);
5. the residual is refunded to the liquidated account.
A second wrapper pattern (capture tx 0xc200bd688bf0493d6c0a786d1242e07c4d029621d038fe9bc3a72afacfcd35c7,
wrapper 0x7de39ff2) shows only the Vault repay inside the capture tx: keepers differ in whether the swap
and fee legs run in the same transaction, so a watcher cannot assume a fee transfer exists in the capture.

A guard contract measuring the recipient's wMATIC delta (>= minProfit) is the enforceable loss bound;
measuring the collateral token balance is wrong. Raw handler replay of captured calldata at the parent
block reverts in module 0x2b19a6ab35 (the deposit-call configuration is validated): the replayable
surface is the wrapper entry with its full batch calldata (entry selector 0x0427ef5f: timestamps,
chainId 42161, swap path, GLV deposit provider 0x408e8e83d4b8ac4bdeffdf896b49268a5fe5ef44, magic bytes
gmx:1:0:0000:00:0:1), so an executor must forward the captured calldata bytes, not a decoded struct.

Evidence: callTracer relay traces scratch/gmx-exec/cand1-trace.json (batch adapter 0xde433ff3 with fee
recipient 0x09f94b5fc68e227c323a6fbae3bd98c97fd8c849 receiving several wMATIC transfers), scratch/gmx-liq-arb/trace.json
(dust capture above), scratch/gmx-exec/cand2-trace.json (fee legs outside the capture). Fee size: 0.2-0.315 pct
of liquidated size x 37 pct receiver factor (DataStore LIQUIDATION_FEE_RECEIVER_FACTOR); median capture ~4 USD.
Executor + rerun recipe: scratch/gmx-exec/proof.sh (bots/paper/gmx-liquidation-arbitrum manifest).
Attempts 246/256/257/265, runs 188c26a3, 9f56cce8, eb1e9821.
