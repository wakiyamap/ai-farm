trial: Bounce.Tech leveraged tokens (HYPE5L, HYPE3L, NVDA5L, BTC5L) public mint / redeem at NAV versus their Hyperswap V2 pairs on HyperEVM

# trial-levtoken-arb-hyperevm

Cheap-chain trial (decision `2026-11-17-cheap-chain-trials.md`): capital 20 USD, at most 1 USD per send, the win
rate is measured by sending. KB: attempts:3120 (measurement), protocols:378 (bounce_tech).

## What it does

Each Bounce.Tech leveraged token has a public `mint(to, usdc, minOut)` (no fee, at least 10 USDC) and a public
`redeem(to, amount, minBase)` (fee 0.3 % x leverage), both at `exchangeRate()`, a NAV computed from the token's USDC
and its HyperCore account value. The tokens also trade on Hyperswap V2 pairs. When the perp price moves, the NAV
leaves the pair price. One transaction through the `LtArb` executor then

- mint side: flash-borrows USDC on Morpho Blue, mints the token straight into the pair, takes the pair's other side
  (ALT is sold for USDC on the ALT/USDC 1 % V3 pool; a USDC pair pays USDC directly), repays;
- redeem side: flash-borrows USDC, buys the token on the pair (through ALT if needed), redeems it, repays;

and pays the USDC gain to the bot wallet. It reverts unless the gain is at least `minProfit`, so a lost attempt
costs gas only.

| route | token | pair | sizes (USDC) |
|---|---|---|---|
| HYPE5L-ALT | 0x18b8539261cf9e760e7fec4a8a73c50f0ae7babe | 0x4e3e10d8dcaa19b830df71d16528027ec106ee77 (about 5.4k USD a side), then ALT/USDC V3 0xc2065d7ca9c8c612334eccbc5abc4de57097e45a | 10, 15, 20 (the ALT/USDC pool is shallow: on the fork 10 gained 0.188 USDC where 20 gained 0.029 and 40 nothing) |
| HYPE5L-USDC | same | 0x0dc5ff5ee49525ce100868184f355929c41c7882 (8.6 USDC) | 10 |
| HYPE3L-USDC | 0x9a51b0dc3545cb8e9b0382b42c91f9e39a92efd6 | 0xe1607fd124f254b5f4b58887ca87d1fa8c2fcfc5 (77 USDC) | 10 |
| NVDA5L-USDC | 0xae3782e28f34dd4d12395187f2e0cb3444fcc3c8 | 0xf4b2c1e258a3a24d3a195469512ac8d62d4e87d0 (9 USDC) | 10 |
| BTC5L-USDC | 0xbe4e97a8fceeb1b82d64349fba6ff29b65ad3b7d | 0x2cfdbba775e0d4b0b9cca857ab746a99d944c073 (6 USDC) | 10 |

Each route in both directions: 14 candidates, all in one `probe()` eth_call every 27 s.

## Competition, last 7 days (blocks 51,209,568-51,814,368, `scratch/r403a/measure.py`, `lt-measure.json`)

- HYPE5L: 3,166 mints (112,502 USDC) and 2,473 redeems (80,533 USDC). HYPE3L 23 mints, NVDA5L 29, BTC5L 14.
- Executor `0xcc029db0386cd36cae20d4b7373d4bc669588f54` (EOA `0xc875f2277a5112364cc1e5ee9d9247a5d37dcefb`): 1,595
  HYPE5L mints. Sample of 37 takes: gain sum 1.3755 USDC, median 0.0109, max 0.3833; fee sum 0.018458 HYPE
  (1.12 USD); median 291,090 gas at 0.718 gwei; tx index median 5.
- Executor `0xbf724fd409cbb2cb77cea0b1a840c7dc67bfcca1` (EOA `0x454c16ca9e6b817f4b6ff86292783c14db07a7e4`): 1,213
  HYPE5L mints. Sample of 26 takes: gain sum 0.6498 USDC, median 0.0162, max 0.0851; fee sum 0.0066 HYPE (0.40 USD);
  median 341,879 gas at 0.487 gwei; tx index median 5.
- Others: `0xc657be0b4e302a6f67a5fbcca2713f494ee1a7d1` 93 mints, `0x693f12e9e6b35b34458793546065e8b08e0299d6` 71.
- Both leaders hold inventory (10 USDC a take) and bid most of the gain as priority fee (0.5-1.8 gwei against a
  0.1 gwei base). Takes come in bursts when HYPE moves: e.g. 9 mints inside 120 blocks, then none for 30 minutes.
- Blocks to take: cannot be measured from history (HyperCore values are not archived). The live sends measure it:
  each `send_result` row logs the winner's block.
- Example takes: `0xc4c0d30ba5498bccecf2bbf2e62629c587d4ad2834bfcf364d8a2edc9a45a095` (+0.027182 USDC, 288,196 gas
  at 0.845 gwei), `0x1d65b4839dd1c78195c345233a617465079986e9e5da1e54ffbf53cbb141f52d` (+0.040058),
  `0x5a3815d97faa127da49c2a77c5204707d3156f60a01fbb74b2af2623ec7a30ae` (HYPE3L, +0.063688).

Honest expectation: the median take is 1-2 cents gross, about the size of the fee. The bot sends only when the
simulated gain is at least 1.5 x its own gas cap, so it will send on the larger moves only; the trial measures
whether it wins any of them against two bidding bots.

## Send rule and loss guard

- `eth_estimateGas` x 1.2 = gas limit (at most 1,900,000). `maxFeePerGas` = base fee x 1.3 + bid, never above
  2 gwei. Worst case 1.9M x 2 gwei = 0.0038 HYPE = 0.23 USD at HYPE 60.7.
- No send unless the gas cap, valued at the WHYPE/USDT0 pool price x 1.15, is under 0.95 USD and the simulated USDC
  gain is at least 1.5 x that cap. `minProfit` = the cap in USDC, so an included transaction either gains more than
  its own gas cap or reverts.
- Priority-fee bid: at most 40 % of the simulated gross (the incumbents pay 50-80 % of theirs; their route needs
  290k-340k gas against about 475k for the flash route, so the bot is the weaker bidder at equal gross).
- The executor also checks `tx.gasprice <= maxGasPrice` and a 60 s deadline.

## Read cost

- One `eth_call` per 27 s: 3,200 x 26 CU = 83,200 CU/day; about 88 CU more per evaluated gap. Hard cap 98,000
  CU/day in code, then it sleeps to 00:00 UTC. 98,000 CU = 0.052 USD/day. No feed filter (the NAV has no event).

## Logs (`logs/bot.jsonl`)

`start`, `poll` (heartbeat every 40 polls), `opportunity_skip` (reason), `opportunity`, `paper_sim`,
`simulate_revert`, `send_result` (won / lost, gas used, winner block, blocks after the winner), `signer_reject`,
`read_budget`, `relay_error`, `loop_error`.

## Fork proof (scripts in `scratch/trial-levtoken-arb-hyperevm/`)

The tokens read HyperCore precompiles, which the anvil fork lacks, so every fork run uses the fork-only replay
fixture `mock/src/PrecompileReplay.sol` at the precompile addresses (wiki
`pitfalls/hyperevm-precompile-contracts-no-fork.md`). Nothing else is overridden.

1. `proof_old.py` (main, repeatable, natural gap): precompile answers from the trace of the incumbent's take
   `0xc4c0d30b...` (block 51,812,906, gain 0.027182 USDC), fork reset to its parent block 51,812,905. The executor's
   mint of 10 USDC gains **+0.032130 USDC** (`0x4e90eb33...`, 474,400 gas); nothing-to-take, 2 x minProfit and
   non-owner all revert. Output `proof-old.json`.
2. `proof.py 300 3000 induce` (head state, live precompile values, gap made by a fork-only third-party trade on the
   pair): +0.187920 USDC (`0x2285595d...`), same three reverts. Not a mainnet gain. Output `proof-induced.json`.
3. `proof.py 1700 3000` (head state, waits for a live gap): watched 7 min + 5 min in this session, no gap opened
   (the incumbents were idle from 00:17Z), then stopped because run 1 already gives a natural gap. No `proof.json`.

The gap in run 1 was open at the end of the parent block, and the incumbent's take sat at tx index 9 of the next
block: the take was at least one block (about 1 s) late, not a first-in-block race.

## Notes

- `debug_traceCall` on hyperevm does not run the HyperCore precompiles; `eth_call` does. Diagnose with `eth_call`.
- Paper mode uses the fork deployment's runtime (`executor-runtime.hex`) as an `eth_call` code override at a codeless
  address; live mode needs `EXECUTOR_ADDR_HYPEREVM` or `EXECUTOR_ADDR`.
