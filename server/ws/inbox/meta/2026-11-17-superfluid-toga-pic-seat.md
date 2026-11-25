# Superfluid TOGA PIC seat on Base: pays, fork-proven, but needs a risk-rule exception (please forward to the human)

From: builder-claude, run 56e8c1cec061466ba6730062b671c9cb, 2026-11-17. KB: attempts:1820, lead 248, wiki `mechanisms/superfluid-toga-pic.md`.

## What to forward

A request for one decision: may a bot post a **bond of 120-400 USD (USDC wrapped 1:1 to USDCx) that comes back only as a stream over at least 7 days**, or at once when a rival outbids it?

- **What it earns**: the holder of the "PIC" seat for USDCx in Superfluid's TOGA contract on Base receives the deposit of every stream liquidated in its first 30 critical minutes. Last 28 days: 113.69 USDCx (weeks 10.84 / 0.50 / 81.75 / 20.60), so at most 4.06 USD/day if every reward were ours. The share we would get against the one incumbent (`0xac8f3481...`) is unknown until tried.
- **Why it suits the farm**: critical times are known hours to weeks ahead (no block race), and it is open to anyone.
- **Why it is outside today's rules**: the bond leaves in one transaction and does not return in it (rule L), and it cannot be sold to USDC in one transaction at any time, and exceeds 100 USD (holding frame).
- **Loss cases**: outbid = gas only, the whole bond is returned in the rival's transaction (measured on the fork: 400.000000 USDC before and after). Sender tops up before the critical time = no reward, the bond idles until streamed back. Superfluid contract risk on the bond. The watchdog would see the bond as a loss while it sits in TOGA, so the live-loss stop would also need to know about it.

## Not done / open

- A patrician liquidation crediting a stranger's bond was not run on the fork.
- A second outbid sent seconds after the first reverted twice (877,336 gas) and succeeded about 40 s later; cause not traced.
- 28-day count of seat changes on Base: the 30-day `eth_getLogs` scan failed (below).

## Tool notes from this session

- Research lane, polygon: an address-less `eth_getLogs` over 769 blocks failed with `all providers failed: public: HTTP 400 "ranges over 10000 blocks are not supported on free plan"`. Looked like the Alchemy budget was spent and the public node rejects the request shape; not reproduced with `relay-probe`.
- Research lane, base: `eth_getLogs` on old ranges (blocks 45.7M+) failed with `public: HTTP 403 "Archive requests require a personal token"`; the Base fork showed the same error on some `eth_getTransactionReceipt` reads right after a reset at head (the transactions themselves had gone through).
- Paper slots are 12 / 12, all `wait` for the trial live cap. A builder session cannot place anything new until some are promoted or archived; this session scouted instead.
