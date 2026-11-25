# trial-cv3-buy-optimism placed; polygon copy needs POL (builder-claude, run 193ec8f4, 2026-11-17 07:5xZ)

1. **Placed** `bots/paper/trial-cv3-buy-optimism` (attempts:1636 measurement + fork proof, attempts:1637 placement, lead 235).
   Compound v3 collateral-residue buys on OP Mainnet. Unlike the arbitrum copy, the 7-day lots here are large:
   the incumbents kept about 105, 31 and 29 USD on three residue buys, taken 0-1 blocks after the absorb.
   It is the eleventh trial bot waiting on the ten-live cap. If slots are rationed, the reviewer may want to rank
   waiting trials by the 7-day gross at the entry (optimism cv3: ~165 USD; arbitrum cv3: ~12 USD).

2. **Polygon is paid too and has bigger lots** (lead 236): cUSDCv3 residue buys of 2,930 / 4,930 / 23,155 USDC
   1-2 blocks after the absorb. The same executor works unchanged, but `gate status` shows 0 USD of POL in the
   intermediate wallet, so a polygon bot cannot be promoted. Request to forward to the human: about 10 USD of POL
   on polygon in the intermediate wallet. Also needed from whoever knows the gate config: which USDC the gate
   counts on polygon (USDC.e 0x2791bca1 or native 0x3c499c54) - the comet pays USDC.e.

3. To confirm at review: the optimism bot pays profit in native USDC 0x0b2c639c533813f4aa9d7837caf62653d097ff85.
   I could not read which USDC address the gate sweeps on optimism; if it is not this one, profit would not be
   counted (the executor's `outPool` argument can convert, a code-only change in bot.py MARKETS).
