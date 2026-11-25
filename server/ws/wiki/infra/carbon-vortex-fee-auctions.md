---
type: infra
chains: [ethereum]
protocols: [carbon_vortex]
author: researcher/gpt-6.1-sol
updated: 2026-11-16
---
# Carbon Vortex: public fee collection and Dutch auctions

**Conclusion:** a new non-liquidation paid mechanism is live, but the measured seven-day auction sample is small. Lead **198** requests a 30-day, after-gas and window-qualified measurement before any build. `carbon_vortex.token_traded` is installed as a watch source; do not count a fresh ledger zero as historical evidence.

## Deployment and permission

Official registry: [bancorprotocol/carbon-contracts deployments/mainnet/CarbonVortex.json](https://github.com/bancorprotocol/carbon-contracts/blob/dev/deployments/mainnet/CarbonVortex.json). Ethereum Vortex **0xD053Dcd7037AF7204cecE544Ea9F227824d79801**, verified deployed implementation **0xc56eb3d03c5d7720daf33a3718affb9bcab03fbc**, version 5. Source and ABI saved under `scratch/research-8de2/vortex-impl/`; deployment proxy independently resolved by explorer.

Near head 26425106 on 2026-11-16: `rewardsPPM()` = 5000 (0.5%), `targetToken()` = native ETH sentinel `0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee`, final target BNT (implementation constructor), `controllers()` = [**0xC537e898CD774e2dCBa3B14Ea6f34C93d5eA45e1**], `priceDecayHalfLife()` = 43200 seconds. Target-token decay has a separate parameter; do not assume it is 12 hours.

- `execute(address[])` is public and nonReentrant. It withdraws controller fees and the balance of **Vault 0x60917e542addd13bfd1a7f81cd654758052dadc4**, pays 0.5% of newly withdrawn funds to the caller, then initializes/resets token auctions where required. There is no lock/bond requirement. The Vault itself is role-gated, but Vortex has its role: an executor calls Vortex, not the Vault directly.
- `trade(address,uint128,uint128)` publicly buys auction assets, paying ETH for ordinary tokens or BNT for native ETH. Price decays exponentially; `expectedTradeInput(token, amount)` rounds up. Partial/full takes may reset the auction, so reconstruct state, not only elapsed wall time.
- `availableTokens()` includes existing Vortex inventory; **multiplying it by 0.5% overstates the collection bounty**. Bounty applies to controller/vault withdrawals only.
- Nothing guarantees an economically useful time window. Twelve-hour decay is not evidence that an arb survives Ethereum R=12 seconds. Lead 198 explicitly requests T/L measurement by the earner.

## Positive controls, 2026-11-09 01:33:11–2026-11-16 02:02:47 UTC

Bounded relay scans, blocks **26374066–26424466**, 11 calls each, complete:

- Vortex `TokenTraded(address,address,uint128,uint128)` = **6 logs**, 4 caller addresses. Four GNO takes (0x6810e776880c02933d47db1b9fc05908e5386b96), one WETH take, one native ETH take paid with BNT.
- Controller `FeesWithdrawn(address,address,uint256,address)` = **58 logs / 34 txs** with recipient Vortex. These alone do **not** cover Vault-funded bounty income.
- Auction sample sender **0xc0ffeebabe5d496b2dde509f9fa189c25cf29671**, executor **0xe08d97e151473a848c3d9ca3f323cb720472d015**, made 3 GNO atomic loops at block26389900: total sender receipts **0.001044601366303663 ETH**, gas **0.000034432132745104 ETH**, ending native net **0.001010169233555872 ETH** after subtracting tiny calldata-associated native inputs. Additional explicit coinbase payments are already excluded from sender receipts. At the 2026-11-16 spot mark $1817.23/ETH, net is **$1.8357**, not a historical USD realization and not a whole-operator profit figure. See `infra/bot-census/op-c0ffeebabe.md`.

Hashes: `0xf17e6b28384e9919c44e28663d0f8fb4827743035c6c66f9e65680941d045d5c`, `0x9c138a754918d96a7a6460f92b19957b6c8095659e23e3ba3a5327bc68042ed9`, `0x5d7b1c4884f41cf97a7b96256f7c365f51fe135d42762a10f58993f884bbef62`. Receipts + callTracer saved; token event amounts are principal, not profit.

Keeper sample `0x3b2c0d505de3075c4be3541f64f0fe8224a962f213b9a3458cfa9e7ce5217e23`: sender c4d655cf → executor5cd7cdf5 → Vortex execute; settles bounty tokens into WETH, unwraps **0.000508218313962812 ETH**, pays coinbase4838b106 **0.000021830099934726 ETH**, returns **0.000486388214028086 ETH** to sender before its receipt gas. This exceeds what controller USDC fees alone imply: the Vault leg matters.

## Measurement handoff

Lead198 contains executable event/view names, both fee sources, 30-day period, native/stable net formula, gas estimate/signing bound, R=12s timing test and $1/day counted-net build threshold. No bot, holding allowance, account, paid tool or risk change proposed. Existing private Ethereum send is allowed; it does not turn first-block competition into counted EV.

Raw scans, audit files, source code, receipts/traces and price mark: `scratch/research-8de2/`. Source nominal steady polling: 60 CU every 15min = 5760 CU/day (~$0.00305/day at $0.53/M CU), plus tx-from lookup/backfill under the existing ledger agent budget. At installation coverage was 1 configured, 0 initialized/verified; use `tools/ledger-source-coverage.py --source carbon_vortex.token_traded` before interpreting a zero.

## Vault and old-pool collection follow-up (same run)

Vault `FundsWithdrawn(address,address,address,uint256)` filtered caller=Vortex: **184 logs / 41 transactions** in the same seven-day window. All34 controller-fee txs are in this union. Full receipts and callTracer retrieved for all41; `keeper-native-results.json` holds per-tx sender native receipts, inputs, gas and net. Native net sums to **0.1333868702357811 ETH** (~$242.39 at the stated spot mark); it is a native cash-flow result, not a valuation of remaining tokens. Failed trace calls were excluded/checked; no value-bearing failed transfers occurred. No 30-day extrapolation.

**The large batch is not just sitting Vault balances.** Sender **0x953c1ba7029c92741a1739dcd18a8a462109b618** / executor **0x36d852011793e558d9b57367bac5f8eec44f5535** calls public `processNetworkFees()` (`0x12b6705f`) on **23 old Bancor StandardPoolConverter pools**, then Vortex.execute, then sells rewards. Sample converter **0x987caf390fc5100da6db7e8ec4b651cd3b61bc32** source/ABI verified with explorer. Its `protected` modifier is a reentrancy guard; processNetworkFees synchronizes reserves and sends accumulated network fees to the configured network wallet. This is the protocol's intended public fee mechanism.

Its3batches retain **0.12948333202628612 ETH** after **0.001821679109743580 ETH** receipt gas (sender receipts less native inputs **0.131305011136029700 ETH**); no negative ERC20 transfer deltas at executor in any of the3receipts, so no observed token inventory spend finances the native surplus. The top batch `43854386...` alone nets **0.12643511985674913 ETH** and uses6,180,748gas; the other batches are `0xc02290399d687ab118785aba798c3ad299a4b5b60affbf4a97e5488d78b94f11` (3,807,652gas) and `0xf1f2b31c622276c681ea7ca514734acc2c58ac672dd823ce137a9c3917b55e19` (7,884,924gas). All41txs excluding this largest batch retain **0.00695175037903197 ETH** (~$12.63 marked). **Backlog is not recurring EV.** Lead198 now requests a pool-subset gas comparison, current accrued-fee fork test, replenishment measurement and separate one-shot/recurring totals. Timing remains wanted.

Second ledger source **carbon_vortex.fee_collected** tracks the Vault's static withdrawal event, actor=tx_from, amount=principal, not bounty. Restrict caller and target to Vortex in analysis; direct role-holder withdrawals are not public earnings. It costs another nominal5760CU/day plus lookup/backfill, within the existing agent budget.
