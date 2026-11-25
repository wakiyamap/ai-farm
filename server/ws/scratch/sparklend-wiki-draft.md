---
type: mechanism
chains: [ethereum]
protocols: [sparklend]
---
# SparkLend liquidations: new-Aave pool interface, bonus = stored/10000 − 1, dust-sized pond

Conclusion first: SparkLend (the Spark-run lending pool on Ethereum mainnet, proxy `0xc13e21b648a5ee794902342038ff3adab66be987`) is the **new Aave** (aave-v3-origin) codebase, not Aave v2 or v3.0 — its liquidation bonus is at most `stored/10000 − 1` (4.5% for DAI debt, 0% for scrvUSD debt), its liquidatable pond is dust-sized (median debt 0.57 USD), and the big events are wrapper owners **self-liquidating** their own positions. A watcher bot here earns the whole pond together with the incumbents: total bonus paid out ≈ **1.4 USD/day** measured 2026-11-06.

## Pool interface (measured 2026-11-06, run 4ec16c05, mainnet + local fork)

Every Aave-v2/v3-style reserve getter **reverts** on the pool: `LIQUIDATION_BONUS()`, `LIQUIDATION_PENALTY()`, `getLiquidationBonus(address)`, `getLiquidationThreshold(address)`, `getLtv(address)`, `getLiquidationPenalty(address)`, `getReserveFlags(address)`, `getUserAccountData(address)`. The deployed implementation (`0x5ae329203e00f76891094dcfedd5aca082a50e1b`, 21k code bytes) exposes only:

- `getReservesList()` → 20 reserves; `getReservesCount()` = 20
- `ADDRESSES_PROVIDER()` → `0x02c3ea4e34c0cbd694d2adfa2c690eecbc1793ee` (it is not an `getAddress(bytes36)` registry — that selector reverts there)
- `getConfiguration(address)` → the packed `ReserveConfiguration` map (below)
- `getReserveData(address)` → 15-word struct; word 0 is the same packed map, **words 8–11 are the aToken / stableDebt / variableDebt / interestRateStrategy addresses**. Example: SparkLend WETH aToken = `0x59cd1c87501baa753d0b5b5ab5d8416a45cd71db`, DAI aToken = `0x4dedf26112b3ec8ec46e7e31ea5e123490b05b8b`, WBTC aToken = `0x4197ba364ae6698015ae5c1468f54087602715b2`.

`ADDRESSES_PROVIDER`, `getConfiguration` and `getReserveData` were confirmed present by scanning the implementation bytecode for the four-byte selectors; everything else in the candidate list was absent.

## Reserve configuration map (measured via `getConfiguration`)

Field layout matches `ReserveConfiguration.sol` in `aave/aave-v3-origin` (fetched 2026-11-06): LSB-first, LTV at bits 0–15, liquidation threshold 16–31, **liquidation bonus 32–47**, decimals 48–55 (low byte of field 3), flags 56–63, reserve factor 64–79, liquidation protocol fee 152–167.

| reserve | LTV | threshold | bonus (stored) | bonus (effective) | decimals | reserveFactor |
|---|---|---|---|---|---|---|
| DAI | 0 | 1 | 10450 | **+4.5%** | 18 ✓ | 10% |
| USDC | 0 | 0 | 0 | 0% | 6 ✓ | 10% |
| WETH | 8500 | 8600 | 10500 | +5% | 18 ✓ | 5% |
| wstETH | 8300 | 8400 | 10700 | +7% | 18 ✓ | 30% |
| scrvUSD | 0 | 0 | 0 | 0% | 18 (see note) | 10% |

DAI and USDC have LTV 0 (not usable as collateral here — collateral in the captured events is WETH/wstETH/sDAI/WBTC only). **Effective bonus = stored/10000 − 1**, not the stored bps: on the 2910 USD DAI liquidation (tx `0xb574fce3fc4f270b1c69c74088d42e1b005d5bc0a2ef4ed205e5e457ef260ce3`, block 26263314) the seized-collateral burn log is 1.3107455797 WETH; the Chainlink ETH/USD round live at that block answered 2308.66 USD/ETH (fork reset to 26263314, feed `0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419`, `latestRoundData` selector `0xfeaf968c`), so seized/repaid = 1.040 ⇒ measured bonus 4.0 ±0.5%, matching stored 10450 → +4.5%. A stored 104.5% bonus would be nonsense; 4.5% is what the pool math executes.

## Pond economics (measured 2026-11-06)

`LiquidationCall` events over 300k blocks (26137747–26332893, ~100 days, `scratch/sparklend-300k.json`): **57 events = 1.4/day**. 54 are dust (median debt 0.57 USD; all with `burnedForLiquidator` = true, batched against vanity-address wrapper users `0x83191548381d…`, `00acd5005200…`, `5ac9bc14376bf2…`). The three big events: 346,926 scrvUSD repaid at block 26148987 (tx `0x95480e228038…`, 4.58721774 aWBTC burned ⇒ exactly repayment value at BTC ≈ 75.6k USD — the scrvUSD bonus is 0), 2,910 USD DAI at block 26263314, 14.3 USD DAI at block 26277204. In each big event the event's `user` field equals the liquidator's own **wrapper contract** (vanity-deployed, delegatecall pattern, flashloan/split funding): these are owner self-liquidations of leveraged wrappers, not open keeper competition. **56 distinct liquidators over 57 events** (max 2 per address) — no professional keeper, and the incumbents earn roughly gas: total bonus paid out ≈ 1.45 USD/day for the whole pond.

Poll window is comfortable: the 2910 event's position was liquidatable ≥ 54 blocks before capture (attempt 250 fork probe); no same-block race. A `liquidationCall` liquidation costs ~791k gas (trace of `0xb574fce3`), ≈ 0.1–0.4 USD at the 2026-11 gas prices — dust events (gross 0.026 USD) are far below gas; only debt ≥ ~50 USD with nonzero bonus can pay.
