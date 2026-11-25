---
type: infra
chains: [any]
protocols: [aave_v3, morpho_blue]
---
# Chain selection: which new chain to add, Alchemy-supported candidates scored on the human's 5 tests

Working table for `decisions/human/2026-11-13-chain-selection.md`. Test 2 is the replaced version (`2026-11-13-chain-selection-windows.md`): on one major liquidation protocol, at least 5 captures in 30 d taken >= 3 s after they became takeable, with gross >= 500 USD in total. Never fill a cell from memory: 未確認 = not measured.

**State after run 2685a085 (2026-11-13, researcher-claude). Report written: `inbox/human/2026-11-13-chain-selection.md`.**
- **No candidate chain gets 5 ○, or 4 ○ plus 1 未確認.**
- **Robinhood Chain is the near-miss.** It scores ○ on tests 1, 3, 4 and 5 and × on test 2. Its feed-driven captures are taken 0-2 s after the oracle update; only dust waits >= 3 s.
- **Monad and Mantle have large books but almost no liquidations.** Monad's Aave V3 paid 1 liquidation in 30 d (43 USD) and its Morpho 10 (9.4k USD). Mantle's Aave V3 paid 2 (292 USD). **Plasma** is close behind: 19 liquidations, 3.5k USD.
- **Arc stays 未確認.** Its public RPC allows at most 1000 blocks per getLogs and answers 429, and the explorer API sits behind a Cloudflare challenge.
- **Among the current farm chains only base gets 5 ○.**

## Method for test 2 (window)

- **Aave chains (Monad):** `scratch/chainsel-2685-aavewin.py`. It reads the HF from `getUserAccountData` at B-1, backs off exponentially, then bisects to the first block of the HF<1 run (this needs an archive public RPC; rpc2.monad.xyz has one). Window = ts(B) - ts(first HF<1 block).
- **Robinhood Chain:** the public RPC keeps historical state for only ~1000-10000 blocks (minutes), so state bisection is impossible. Window = ts(capture) - ts(last `AnswerUpdated` on the market's oracle feeds/aggregators before the capture) (`scratch/chainsel-2685-rh2.py`), the same publish->capture metric as base lead 157 (attempt 1076). This is an upper bound when the crossing came from interest accrual. Gross proxy = repaid x (LIF-1), with Morpho LIF = min(1.15, 1/(1-0.3(1-lltv))), USDG loans only.
- **Gross-bound shortcut:** when the 30 d repaid total x the maximum bonus is < 500 USD, test 2 is × whatever the windows are (Plasma, Mantle).

## Candidates (EVM mainnets on Alchemy, not in the farm)

Every one of them has Alchemy HTTP + WS (`eth_subscribe`) + debug per the feature matrix, so test 5 is ○ throughout. Block times were measured over 2000 blocks through the public RPC.

| chain | borrows (DefiLlama) | main lender 30 d liquidations | block s | 1 | 2 | 3 | 4 | 5 | note |
|---|---|---|---|---|---|---|---|---|---|
| Robinhood Chain | 470.6M | Morpho 0x9D53d5E3...: 160 events, 532,022 USDG repaid (141 USDG-loan events), gross proxy 42.5k USD (31.6k of it one NVDA whale, 6.5k one USDe whale) | 0.105 | ○ (borrows; liq 0.53M < 1M) | × | ○ | ○ (top-1 25/160 = 16%, 49 callers) | ○ | test 2: 34/160 captures have a feed-anchored window: 0-block 7, <3 s 20, >=3 s 7 with gross 5.47 USD (dust: syrupUSDG/Steer/Index). Feed-driven captures of size are taken 0-2 s after the update (WETH 2586 USDG at 0 s, GOOGL 390 at 2 s, TSLA 145 at 2 s, MSTR 66 at 2 s). The other 126 (89% of gross) sit on non-ChainlinkOracleV2 or Uniswap-pool-price oracles with no event to anchor on. The 249k NVDA whale (block 112577832): its proxy feed RHNVDA/USD 0xc9d16e4f updated inside the capture block, so treat it as same-block. Test 3: the shared pre-Morpho emitter 0x2bd3d596 in the capture txs is the AdaptiveCurveIrm (MORPHO() = Morpho; BorrowRateUpdate per market), not a gate. Liquidations are direct public `Morpho.liquidate` by 49 callers. Oracles: Chainlink-style "Robinhood <stock> / USD" feeds for tokenized stocks (NVDA, TSLA, GOOGL, MSTR, AAPL, INTC), ETH/USD, USDG/USD. |
| Plasma | 797.7M | Aave V3: 19 events, 3,532 USD | 1.000 | ○ (borrows) / × (liq) | × (gross bound: 3,532 x <=10% < 500) | 未確認 | ○ (37%) | ○ | |
| Monad | 792.4M | Aave V3 0x69a5F9AD: 1 event, 43 USD (blocks 113304445-121825715, 29.9 d). Morpho 0xd5d960e8: 10 events, 9,449.78 USDC + 7.83 AUSD + 1.04 USDT0 | 0.304 | ○ (borrows) / × (liq 9.5k) | 未確認 (at most 11 events in 30 d; gross <= ~1.4k even at the 15% LIF cap; windows not measured for Morpho) | 未確認 | ○ (Morpho top-1 3/10) | ○ | rpc2.monad.xyz: getLogs <= 10000 blocks plus archive state (rpc/rpc1/rpc3/monadinfra/drpc: <= 100 blocks). Aave window: the 1 event was healthy at B-1 (0 s) |
| Arc (chainId 5042, docs.arc.network connect page; RPC https://rpc.mainnet.arc.io; gas token USDC) | 274.5M | 未確認 | 0.507 | ○ (borrows) | 未確認 | 未確認 | 未確認 | ○ | Morpho on Arc 0x34CD04070dD72b14E241112F6d83812Df5Af7fCD (Morpho docs addresses page). Public RPC: getLogs <= 1000 blocks, 429 within a few calls. explorer.arc.io API returns a Cloudflare challenge (not bypassed). Next: a keyed provider (Alchemy has Arc) |
| Mantle | 110.9M | Aave V3: 2 events, 292 USD | 2.000 | ○ (borrows) / × (liq) | × (gross bound) | 未確認 | ○ | ○ | |
| Ink | 57.1M | Tydro (Aave V3 fork): 未確認 | 1.000 | ○ (borrows) | 未確認 | 未確認 | 未確認 | ○ | Tydro pool address not pinned yet |
| X Layer | 49.7M | | 1.000 | × (0.3M short) | | | | ○ | |
| Pharos 35.8M, Gnosis 30.0M (5.075 s), Sonic 26.3M (2.155 s), Stable 24.1M, Berachain 13.9M, Katana 10.8M, World Chain 10.7M, Citrea 9.2M, Sei 8.4M, Linea 5.7M (11.1 s), MegaETH 4.7M, Unichain 1.4M, Celo 1.9M (1.000 s, forno.celo.org), Tempo 0.1M | | | | × | | | | ○ | below 50M borrows |

Below 1M USD borrows, or no DefiLlama borrows: see wiki history (rev 55afb35) for the full list. Non-EVM chains are excluded.

## Current farm chains (comparison)

| chain | borrows | block s | 1 | 2 | 3 | 4 | 5 | evidence |
|---|---|---|---|---|---|---|---|---|
| base | 2689.8M | 0.200 | ○ | ○ | ○ | ○ (morpho top-1 1161/9459 = 12%) | ○ | test 2: lead 157 / attempt 1076, 11/11 sampled farm-band Morpho captures with windows 10-8200+ s, gross ~164 USD on the 11 alone, out of 9,459 Morpho liquidations in 30 d (ledger); moonwell whale windows of 3-6 h (attempt 1074) |
| ethereum | 19142.5M | 12.036 | ○ | 未確認 | ○ (attempt 1096: public liquidationCall, no SVR gate) | ○ (aave top-1 70/391 = 18%) | ○ | farm-band Aave: 8 of 14 captures with windows >= 1 block (>= 12 s), but 263.72 USD gross for all 14 in 16.1 d; captures above 1500 USD not measured |
| arbitrum | 1076.5M | 0.286 | ○ | × | 未確認 | ○ (aave top-1 108/253 = 43%) | ○ | attempt 1064: 30 Aave captures, 27 same-block, windows 0.7/1.3/149 s, the only >= 3 s one 0.04 USD |
| hyperevm | 630.7M (incl. HyperCore) | 0.984 | ○ | 未確認 | × (attempt 1084: incumbent wrapper auctioneer-gated) | ○ (morpho top-1 21/41 = 51%) | × (farm: no trace; matrix: WS yes) | |
| bsc | 816.8M | 0.451 | ○ | 未確認 | 未確認 | 未確認 | ○ | no farm ledger source for its lenders |
| avalanche | 321.2M | 0.962 | ○ | 未確認 | 未確認 | 未確認 | ○ | |
| optimism | 86.3M | 2.000 | ○ | × (lead 120: lending liquidation cadence dead) | 未確認 | 未確認 | ○ | |
| polygon | 73.8M | 1.500 | ○ | × (lead 154: morpho dead) | 未確認 | 未確認 | ○ | |
| elysium | none | 0.118 | × | × | | | ○ | |

Test 5 for the farm chains follows Alchemy's matrix (WS everywhere). The hyperevm × is a farm-measured trace gap, not a WS gap: strictly that is ○ on WS.

## Threshold notes (for the report)

- **Test 1 on borrows alone lets in books that never liquidate.** Mantle (111M) paid 292 USD in 30 d, Plasma (798M) 3.5k, Monad (792M) 9.5k. Scoring on 30 d liquidations repaid would drop all three.
- **Test 2 (3 s) is the binding line for Robinhood Chain**, the only new book with real flow (160 liquidations, 49 callers, top-1 16%). There, size is taken 0-2 s after the oracle update. Lowering the line to 2 s would count GOOGL/TSLA/MSTR (75 USD) and still fail 500 USD. So the line does not drop a promising chain by a small margin.
- **The window metric is weak where oracles emit no event** (fixed-rate/exchange-rate wrappers, Uniswap pool-price oracles: 126/160 on Robinhood). Those crossings are accrual- or swap-driven. Measuring them needs archive state, which Robinhood's public RPC lacks (Alchemy has Robinhood Chain, but the farm cannot read it).

## Next steps (if the human wants more)

1. Arc: liquidation flow and windows need a keyed provider or Arc on the relay. The public RPC is too limited.
2. Ink Tydro: pin the pool (Tydro docs), then run `scratch/chainsel-2685-aavewin.py` against an Ink public RPC.
3. Ethereum test 2 on all capture sizes (the >1500 USD Aave captures).

## Progress log

- 2026-11-12 meta: page created (structure only).
- 2026-11-13 run 8534d4c8: candidate list, Alchemy matrix, borrows and block times for all candidates. 30 d liquidations for Mantle and Plasma Aave V3 and Robinhood Morpho.
- 2026-11-13 run 2685a085: test 2 re-scored on the windows rule. Robinhood: window classes plus market/oracle map (`scratch/chainsel-2685-rh-windows.json`). Monad: Aave and Morpho 30 d. Arc: chainId and RPC limits. Farm-chain tests 2/3/4 copied from KB attempts 1064/1074/1076/1084/1096 and the ledger. Report written.
