# The money path now covers all eight chains (phase 10b, human, 2026-11-10)

`gate promote`, the signer and the watchdog work on bsc, polygon, avalanche, optimism and hyperevm
as on the first three. What changed for bots and manifests:

- Funding still comes from the intermediate wallet on each chain. It holds nothing on the new
  chains until the human deposits, so the first promote there is refused with the usual
  "intermediate wallet on <chain> has less than ..." message. Put the needed amount in
  `inbox/human/` (native gas and, if any, USDC per chain).
- Prices: every chain uses its Chainlink native/USD Standard feed (BNB, POL, AVAX, ETH, HYPE).
  L is checked in USD with that price.
- USDC on bsc has 18 decimals; the gate, signer and watchdog now use each chain's decimals.
- optimism has the same 18 USD gas wallet cap as base (OP Stack L1 data fee).
- hyperevm: every transaction must fit in 2,000,000 gas (small blocks). The gate refuses a
  promote whose executor deployment would need more, before any funds move; the signer refuses
  bot transactions above it.
- The signer only treats the bot's own chain's USDC address as "the USDC token".

common.md says the same. Please bring TOOLS.md and the role files in line where they still say
the new chains cannot be promoted.
