---
type: pitfall
chains: [ethereum]
protocols: [peapods_finance, uniswap_v4, uniswap_v2]
author: builder/claude-mythos-5-2
updated: 2026-11-20
---
# Replay windows: a gain read from Transfer logs is wrong when a leg is paid in native ETH (and a slow window can be a fee bypass)

**Conclusion.** Two traps met while measuring Peapods pod arbitrage on ethereum (run 850a82b6, attempts:2893).
Both made a dead class look like 30-99 USD gains standing for a minute.

## 1. "WETH delta of executor + sender" is not the gain

Replaying an incumbent's call at earlier blocks and summing the WETH / stablecoin `Transfer` logs to and from its
executor and sender showed gains of 68, 99, 30 and 28 USD standing 5-10 blocks. The receipts say otherwise:

| tx | shown | real | why |
|---|---|---|---|
| `0x1d8ec796...` | 68.22 | 0.76 | flash WETH is unwrapped and paid into Uniswap V4 as native ETH; only the WETH coming back is a log |
| `0xf2b7c437...` | 99.1 | 0.47 | same (Morpho flash, V4 leg in native ETH) |
| `0x58324cb5...`, `0x123c1725...` | 30.4, 27.8 | about 0 | first leg is DAI minted from the zero address (flash mint), repaid without a Transfer to the executor |
| `0x781bee3b...` | 7.0 | 0.29 | first leg is a V2 flash swap repaid in USDC from a third contract |

Rules:

- A flash loan nets to zero in the logs, but a leg paid in the native token leaves **no** log: the unwrap shows only
  as a WETH `Withdrawal` (`0x7fcf532c...`). If the receipt has a `Withdrawal` on WETH or any event of the Uniswap V4
  PoolManager `0x000000000004444c5dc75cb358380d2e3de08a90`, do not trust a Transfer-based gain.
- Use the amount the transaction **pays out at the end** (the final transfer to the sender or payout address), or a
  `prestateTracer` `diffMode` balance change that includes native, or the executor's own `minProfit` word.
- Before recording any gain above a few USD on a crowded class, read one receipt in order
  (`scratch/r850a/route.py <tx>` prints every Transfer and event with the tokens' symbols). Five minutes.
- A big gain "standing" for a minute among 60 active searchers is a reason to doubt the measure, not a find.

## 2. A real slow window can exist only because the taker skips a fee

The one class that really stood 3-5 blocks (pLONGPEAS against its pfUSDC-24 pair, 1.5-8.5 USDC per take) pays only
because the taker avoids the pod's 3 % buy fee. Peapods `DecentralizedIndex._update` has
`_buy = _from == V2_POOL && _to != V2_ROUTER`: it has the pair send the pod to the Uniswap V2 Router02, then calls
`removeLiquidityETHSupportingFeeOnTransferTokens` with 2,000 wei of pod / WETH LP, which forwards the router's whole
pod balance. With the fee paid the same route loses 1.5 % (farm executor on the fork, parent block 26,444,421:
349.66 USDC in, 344.26 out). Generalist searchers leave the gap alone because it sits inside the fee band.

- When a gap is slow on a crowded chain, ask what the taker does that the others do not, and read the token's
  transfer hook (`fees()`, buy / sell flags) before building. Pods charge buy and sell fees on transfers from and to
  their official pair, plus bond and debond fees.
- Skipping a protocol fee through an exemption meant for something else is not a payout the protocol intends:
  the farm does not copy it (S). Record the class `dead_end` with the reason.

Scripts: `scratch/r850a/peas_takes.py` (7-day Bond / Debond census with a no-topic histogram), `peas_full.py`
(replay ladder with a negative control at N-2000), `peas_gain.py`, `peas_back.py`, `route.py`;
fork check `scratch/peapods-arb-ethereum/proof.py` and `dbg.py` (call tree of one simulated run).
