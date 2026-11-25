---
type: method
chains: [base, arbitrum, polygon, avalanche, optimism, bsc, hyperevm, ethereum]
protocols: [uniswap_v2, biswap_v2, frax_swap, bakeryswap, quickswap_dex, sushiswap, dodo]
author: meta/opus
updated: 2026-11-23
---
# Skim-excess sweep: `balance - reserve` in pools is out of scope (S, human 2026-11-23); sweep was empty on 2026-11-22

**Ruling first.** The farm does not take a balance above a pool's booked reserve, whatever created it (rebase, transfer fee, a user's mistaken transfer) and whatever function pays it out (`skim`, DODO `sellBase` / `sellQuote` with nothing sent in, a V2 `swap()` against the surplus). That balance belongs to the pool or its LPs; it leaks because the pool's accounting does not book it, it is not a payout the protocol offers to callers (decision `decisions/human/2026-11-23-s-no-skim-rebase-surplus.md`, same shape as the 11-22 LBP / hLBP pair-harvest finding). Consequences:

- **Scouts**: verdict `unpaid`, one `attempts` row whose reason starts "skim type (S)", no lead.
- **Builders / earners**: not a lead, not a bot, not a one-shot. Lead 415 (sLGNS / DODO, polygon) is `dead_end` for this reason.
- A router's `sweepToken` / `refundETH` leftovers are the same type and stay out.

The rest of this page is kept as a record of the measurement and its pitfalls, which also apply to anyone reading pool reserves for other reasons (pricing, arbitrage).

**Measurement.** A V2-style pair pays any token balance above its stored reserves to whoever calls `skim(to)`. A head sweep of 53 factories / 125,933 pairs on eight chains (run 48d0b9b0, 2026-11-22 00:43-00:58Z, 2,657 relay calls) found **no takeable excess above 1 USD**. Every hit above 1 USD was one of three false positives described below; the largest hit that may be real is 0.80 USD (16.69 BUN above reserves in the Bundles BUN/WETH pair `0x9dd78ea2b7a92b6cb5d4a495dac34f8641070ceb` on ethereum, stable at a pinned block, what `skim` transfers not read: under one ethereum transaction's gas either way).

## How

`scratch/r48d0/skimscan.py <chain> <factory> [max_pairs] [start]`: Multicall3 `aggregate3` (300 calls a batch) over `allPairs(i)` (selector `0x1e3dd18b`, from `cast sig`), then `token0` / `token1` / `getReserves` per pair, then `balanceOf(pair)` on both tokens. A pair with `balance > reserve` is valued through the pair itself: the excess of a priced quote token at its price, plus what the pair pays for the excess of the other token at 0.3 pct fee. Quote tokens = the 8 most common tokens of the factory, priced by coins.llama.fi. `runall.sh <list> <out>` runs a list of `chain factory max_pairs` lines; `verify.py [min_usd]` re-reads every hit at one pinned block and simulates `skim` from a fresh address; `hist.py <chain> <pair>` shows the excess at head and at older blocks; `twamm.py` is the FraxSwap check. Factory addresses came from the KB `protocols` rows (each from a DefiLlama adapter or the protocol's docs). Cost: about 20 calls per 1,000 pairs.

## Three false positives (all three appeared)

1. **Reads at different blocks.** The scan reads reserves and balances in separate `eth_call`s at `latest`. A pair that trades in between shows a fake excess the size of one swap (Biswap SFP/WBNB 58.91 USD, BakerySwap BTCB/WBNB 8.17, Biswap XVS/WBNB 5.85, QuickSwap WMATIC/USDT 3.27: all 0 when re-read at one block tag). A real standing excess has an old `blockTimestampLast` and the same value at every older block. Always confirm with a pinned tag before believing a number.
2. **FraxSwap TWAMM reserves.** A FraxswapPair holds the tokens of running long-term orders outside `reserve0/1`; `skim` pays `balance - reserve - twammReserve`. `getTwammReserves()` (`0x094cf149`) returns `(reserve0, reserve1, ts, twammReserve0, twammReserve1, fee)`. Polygon FraxSwap showed 38.87 USD of "excess" on three pairs; the true excess is exactly 0 on all three. `skim` still succeeds as an `eth_call` (it pays 0), so **a successful simulation is not evidence: read what is transferred**.
3. **Frozen token.** The one real standing excess: Biswap WBNB / rBNB pair `0x35bc766ce9fd393a4050599eb49fefb7d6231d92` on bsc holds 1,566.11 rBNB (`0xf244ffe3d054a6185f0e59ffc72aa7cddda82a31`) above a reserve of 15.82, unchanged since its last sync on 2026-09-05 (`blockTimestampLast` 1788713973). `skim` from a fresh address reverts `Biswap: TRANSFER_FAILED`: the token no longer transfers out of the pair.

## Coverage

| chain | factories | pairs read | of all pairs |
|---|---|---|---|
| bsc | 24 (BabyDoge, Bakery, Biswap, BSCSwap, Definix, Jetswap, JulSwap, MDEX, Orion, Sushi, ... ; not PancakeSwap, not Uniswap) | 17,244 | all |
| base | 6 (BaseSwap, AlienBase, PancakeSwap, RocketSwap, SharkSwap, Sushi) | 31,801 | first 8,000 of PancakeSwap (63,911) and RocketSwap (37,624) |
| polygon | 7 (ApeSwap, Dfyn, JetSwap, QuickSwap, Sushi, Uniswap V2, FraxSwap) | 27,870 | first 8,000 of QuickSwap (136,511), Sushi (11,097), Uniswap (49,941) |
| arbitrum | 3 (SpartaDex, Sushi, Uniswap V2) | 16,008 | first 8,000 of Sushi (32,978) |
| avalanche | 4 (Arena, Trader Joe, Pangolin, Uniswap V2) | 20,735 | first 8,000 of Joe (48,937) and Uniswap (12,265) |
| hyperevm | 3 (HyperSwap V2, Kittenswap legacy, Ramses legacy) | 3,471 | all |
| ethereum | 4 small forks (DeFi Swap, Convergence, Bundles, HOPE) | 121 | all |
| optimism | 2 (Velodrome V1, Uniswap V2) | 8,683 | first 8,000 of Uniswap (13,461) |

No further sweeps: the class is out of scope (ruling above), so the uncovered factories stay uncovered.

## Rebase surplus (2026-11-22, lead 415): the case that led to the ruling

A rebasing token in a pool that books reserves leaves `balance - reserve` after **each rebase**, taken within seconds, so a sweep at head reads 0. Found by the executor route census (attempts:3873): sLGNS on Polygon rebases every 14,400 blocks; the DODO sLGNS / USDT pool `0x51542cbb21b98cf261f415ee77e123a9c0baece5` then holds about 1.08 sLGNS above `_BASE_RESERVE_`, and `sellBase(to)` with nothing sent in pays 0.160 USDT to any caller (`eth_call` from a fresh address at block 97784713; `scratch/r775e/slgns_state.py`, `rebase_block.py`). An arbitrage executor takes it 3-5 s after every rebase. Asked in `inbox/human/2026-11-22-meta-s-ruling-rebase-skim.md`; answered **no** on 2026-11-23. Others taking it does not make it intended: do not copy that actor.
