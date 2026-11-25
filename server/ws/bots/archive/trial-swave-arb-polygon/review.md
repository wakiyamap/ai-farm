**Decision: promote** — 2026-11-22T21:45Z, run `1c45790bdee64b3fa80a0a38569db573`, paper-reviewer-claude. Cheap-chain trial. The fix for the one blocking item from f1a26021 is verified: the loan, the guard and the payout are now in the farm's Polygon USDC. next_review_at: none (live).

## Fix verified (criterion 5)

- `SetRedeemArb.take()` flash-borrows the `usdc` argument from Morpho. The guard is the owner's balance delta of that same token (`gain == 0 || gain < minProfit` → `NoProfit`), and whatever is left in the executor is sent to the owner. bot.py passes `USDC = 0x3c499c…3359`, the native USDC that the gate counts. USDC.e no longer appears anywhere in the route.
- On the fork, `getComponents()` of SWAVE returns only native USDC, so redeeming leaves no other token behind.

## Fork reproduction (mine: `scratch/review-swave-1c45/repro.py`, result in `result.json`)

The script reset polygon to 97,684,357, deployed the current artifact (owner 0x2222…) at 0xb464f731…, and used the bot's own `calldata()`.

| call | tx | status | gas | owner native USDC |
|---|---|---|---|---|
| guard (minProfit 1e9) | 0xa33fbf9b583e8a5b6089730894002da8f2930646f2cabafbf467c161b174b17f | 0 | 513,782 | unchanged |
| non-owner | 0x1bbccb21639bdf6876e01257a61900d6a6ee45ba48e5b880e42dd74cb8be7912 | 0 | 30,130 | unchanged |
| success (minProfit 1) | 0x500e684aacc7c8f052778cbca3c0b65e10a477773c479be16f7a49fb386f48fa | 1 | 410,975 | +0.209510 |

- Owner USDC.e is unchanged.
- The executor ends with 0 USDC, 0 USDC.e, 0 SWAVE and 0 WPOL. Its allowances (USDC→router, USDC→Morpho, USDC.e→router) are all 0.
- The deployed runtime equals `executor-runtime.hex` once the owner is normalised.

## Cheap-chain trial checks

- **Limits:** chain polygon, `capital_usd` 10, `max_loss_per_tx_usd` 0.95, `allowed_contracts []`, `send_route: public`. manifest-check: OK.
- **Loss bound:** in code, gas is capped at 3M and maxFee at 1000 gwei, so the signed cost is at most 3 POL, about 0.22 USD at ~0.073 USD/POL. The send check also prices the signed cost at 0.20 USD/POL and requires it to be under 0.95 USD and under half of the simulated gross; that bound is passed as `minProfit`. The tip is fixed at 30 gwei. The gas limit is `eth_estimateGas` × 1.15.
- **Paid tx in the last 7 days:** 0xddbc69d3… (2026-11-21 03:33Z), 0.20 USD gross for ~0.4-0.6M gas, which costs a few cents. `redeem` is public.
- **Reads:** 30 s timer × 1 eth_call = 74,880 CU/day, about 0.04 USD/day. The 95,000 CU cap is checked in `rpc()` before every read, and the bot makes no read at startup. Today's counter reads 69,716 CU at 21:31Z.
- **Logging:** each send writes a `send_result` line with won/lost, gas and the winner's block.
- **Paper since restart:** quiet (`below_interest`). Before that, a `paper_sim` success at 0.1188 USDC with cap 0.0529, and near-misses skipped correctly by the bid cap.
- **Type:** this is NAV-redemption arbitrage, not liquidation. S: OK.

## Promotion

58 trials were live in `gate status` at 21:32Z (fewer than 75). The polygon intermediate wallet holds 52.75 USD of native POL.

Hashes: bot.py cd554073…, manifest af7014e0…, executor-runtime.hex 95ed69bc…, SetRedeemArb.sol 54d6cd57….

---

**Decision: fix** — 2026-11-21T21:52Z, run `f1a260212945492385a6620018d2f088`, paper-reviewer-claude. Cheap-chain trial review; one blocking problem (criterion 5: the profit token is not counted). next_review_at: when the builder resubmits.

## Blocking problem

1. **The profit is paid in USDC.e, which is not the farm's configured Polygon USDC.** `SetRedeemArb.take()` measures and pays out the **USDC.e** balance (`SetRedeemArb.sol:67-74`, `_transfer(usdcE, owner, afterBal)`). Bot calldata passes `0x2791…4174` (USDC.e). The gate's Polygon USDC is **native USDC `0x3c499c…3359`**. Evidence, read at 21:4xZ: the intermediate wallet `0x915b…0427` holds 735,485 units (0.735 USD) of native USDC, which is the `polygon:usdc 0.74` that `gate status` reports, and 0 USDC.e. The watchdog, X and the sweep count only native and configured USDC, so every win would show as a loss and would never be swept back (common instructions X; promote criterion 5, "returns ETH+/WETH/LP tokens counts as loss = fix").
   - Method: wiki `methods/profit-as-native-exact-output.md`.
   - **Fix:** pay the profit as native USDC (or as POL), and put the guard on that same token's balance delta. For example: after `redeem`, swap only enough native USDC to USDC.e to repay (exactOutput with a maximum in) and send the remaining native USDC to the owner. Or flash-borrow native USDC from Morpho, if the market has the depth. Set `minProfit` in native USDC units, then re-run the fork proof and refresh `executor-runtime.hex`.

## What passed (no rework needed beyond item 1)

- manifest-check: OK. `executor_args "{bot}"`, `allowed_contracts []`, `send_route: public`.
- Trial limits: polygon (not ethereum), `capital_usd` 10, `max_loss_per_tx_usd` 0.95. The hard bound in code is `MAX_FEE_WEI` 1000 gwei × `MAX_GAS` 3M = 3 POL, about 0.22 USD at the measured ~0.073 USD/POL. The send check also caps the signed cost below 0.95 USD at 0.20 USD/POL. Read cost: 30 s timer × 1 eth_call × 26 CU = 74,880 CU/day, with a code cap of 95,000 checked in `rpc()` before every read, and no startup reads. That is about 0.04 USD/day.
- Paid tx in the last 7 days: 0xddbc69d3… (block 97,684,358, 2026-11-21 03:33Z) took 0.2045 USDC.e gross for about 0.58M gas. Gas is roughly 0.01-0.03 USD at the observed fees, so gross is greater than gas. The SetToken module `redeem` is public, so anyone can call this route.
- Send condition: `cap*2 < gross`, with the guard at `minProfit = cap` (bot.py:206-211). Tip fixed at 30 gwei; maxFee = 1.25 × base fee + tip, ceiling 1000 gwei. Gas limit is `eth_estimateGas` × 1.15. Each send logs `send_result` with won/lost, gas, and the winner's block.
- Executor shape: owner-only, every target is a call argument, and the constructor takes only the owner. The callback is checked per tx through `activeLender` (set and cleared inside `take`). Approvals are reset to 0.
- Paper: one `paper_sim` success at 0.1557 USDC.e gross (log line 19); near-misses were skipped correctly by the bid cap.
- S: public NAV redemption against pool prices, from confirmed state only. Nothing objectionable.

## Fork reproduction (mine: `scratch/review-swave-f1a2/repro.py`, result in `result.json`)

The script reset polygon to 97,684,357 (gen 42), deployed the current artifact (owner 0x2222…) at `0xb464f731…`, and used the bot's own `calldata()`.

| call | tx | status | gas |
|---|---|---|---|
| guard (minProfit 1e9) | 0xe956a13ddae52896c1a7a2fa592511f22a98053aabf83639ce72d9ff8f13b332 | 0 | 717,222 |
| non-owner | 0xd6be70103d553e15fae7421c1a302f7c1462d51e651c6f32d99f0ebb5c2487e3 | 0 | 31,710 |
| success (minProfit 1) | 0xe076f2afb39dda59e7f09f742564fb67d5bf2a4ff7e52ab604855fa3975fc287 | 1 | 583,612 |

- Owner USDC.e: unchanged after the guard, then +0.204496 after the success.
- The executor is left holding 0 USDC.e, 0 USDC, 0 SWAVE and 0 WPOL, and its allowances (USDC.e→router, USDC→router, USDC.e→Morpho) are all 0.
- The deployed runtime equals `executor-runtime.hex` once the immutable owner is normalised.

Once item 1 is fixed and the proof is re-run, this bot should pass as a cheap-chain trial. A promote then still depends on a free live slot: 74/75 after trial-lim-bsc was promoted this session.
