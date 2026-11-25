trial

# trial-ichi-vault-hyperevm

Cheap-chain trial (decision 2026-11-17-cheap-chain-trials), attempts:3014. The class was opened by the human in
`decisions/human/2026-11-21-ichi-yes-peapods-fee-no.md` (section 1): it is arbitrage between an ICHI vault's
deposit / withdraw pricing and the market, not an attack on the vault's accounting; attempts:2964 is withdrawn.

**What it takes.** ICHI vault IV-NEST-16-USDC-WHYPE `0xb792f94ed56ed0ba163e5ba139e2bd0029a81d0a` (verified source)
holds USDC + WHYPE in Nest's Algebra WHYPE/USDC pool `0xbe512f5881b85c48d9c17bc5bb2be047d156d696`. Its public
`deposit(0, usdc, to)` mints shares at that pool's own price (spot / TWAP, the conservative one of them);
`withdraw(shares, to)` pays the pro-rata USDC + WHYPE. Pool `0x586304481f7be6cb7738bbb913a693dfdd801480` (WHYPE/USDC,
UniV3-style `swap`) prices swaps from HyperCore read precompiles (`0x..0808`, `0x..080e`). When the HyperCore HYPE
price is above the Nest pool's price, one transaction through the `IchiVaultArb` executor:

- flash-borrows USDC from Morpho Blue `0x68e37de8d93d3496ae143f2e900490f6280c57cd` (no fee),
- `vault.deposit` (USDC only), `vault.withdraw` of the shares just minted,
- sells the WHYPE that came back on the HyperCore-priced pool,
- repays, and pays the USDC gain to the bot wallet. It reverts unless the gain is at least `minProfit`.

In effect the caller buys the vault's WHYPE at the Nest pool's (lagging) price and sells it at the HyperCore price.
The size is limited by the sell pool's USDC (about 9.6k USDC at block 51,781,938).

**How it waits.** The gap has no event of its own, so the bot polls: one `eth_call` of the executor's `scan()` every
27 s returns the gain of 6 flash sizes (20k / 60k / 180k / 500k / 1.2M / 3M USDC) from the same state. It acts on the
best one only if the gain is at least 1.2 x that send's gas cap; `minProfit` is the gas cap in USDC.

Only this vault. Not covered: IV-NEST-2 and IV-NEST-17 (WHYPE deposit: the incumbents close through venue
`0xed2ef1b02f2d82d238d6af17e6404a4977b0fefa`, no adapter here), IV-NEST-20 (USDT0, not a token the farm counts).

## Competition, last 7 days (blocks 51,172,538-51,792,538, to 2026-11-20 18:47Z)

`scratch/trial-ichi-vault-hyperevm/measure7.py` -> `measure7.json` (share mints of the vault that are burned in the
same transaction; gain = net USDC to the sender or its contract, a floor: 8 contracts keep it where the script
does not see it).

- 248 round trips = 35 a day. Measured gain 112.96 USDC; median 0.0215, max 13.52 USDC.
- 46 takes of 0.5 USDC or more, 100.01 USDC together. Their tx index: 0 in 13, 1-4 in 19, 5 or later in 14.
- Fee as a share of gross on those 46: median 17 %; gas price median 5.98 gwei (all takes: 0.89 gwei).

| taker contract (EOA) | takes | gain USDC | fees USD |
|---|---|---|---|
| `0x30e81e4d8790fd5203072ebba81f8e5d85f513a3` (`0x454c16ca...`) | 109 | 48.98 | 6.45 |
| `0x7b9836a3fa0824572c2f7e69beb19c351d80548b` (`0x0b8d87ee...`) | 30 | 37.52 | 16.14 |
| `0x79350c4b4f09650af22d4755c32727bd87878ea8` (`0x867b39b6...`) | 16 | 13.04 | 1.66 |
| `0xff6ca52f959d1d887d30f99aadaa8a96b243539f` (`0x4933a267...`) | 2 | 5.53 | 0.30 |
| about 18 more contracts | 91 | 7.9 measured | 20.1 |

Blocks to take: not measurable from history (HyperCore reads are not archived, so the block where a gap opened
cannot be reconstructed). What history shows: 33 of the 46 larger takes are not the first transaction of their
block, and takes come in runs (blocks 51,780,536 / 538 / 550 and 51,781,939 / 940 / 942: +3.72, +0.33, +1.90, +1.00
and +8.17, +0.87, +0.92 USDC), so a gap is often taken in several pieces over seconds. Priority-fee level: the base
fee plus little on small takes; 23-75 gwei on the largest (8.17 USDC for 0.041 HYPE; 3.72 USDC for 0.047 HYPE).
This bot's fee ceiling is about 13-17 gwei (0.95 USD cap), so it cannot outbid those and aims at the pieces left.

## Loss guard

- Executor: `require(profit > 0 && profit >= minProfit)` after the flash loan is repaid; a losing route already fails
  at Morpho's repayment pull; deadline.
- Bot: gas limit = estimate x 1.25 (max 1.9M); `maxFeePerGas` = base fee x 1.3 + bid, never above the fee at which
  gas limit x fee is 0.95 USD (HYPE at the WHYPE/USDT0 pool price x 1.15); no send unless the simulated gain is at
  least 1.2 x that cap. Bid at most 35 % of gross.
- A lost attempt: up to about 880k gas = 0.005 USD at the 0.1 gwei floor, 0.08 USD at the 1.5 gwei seen 18:49Z,
  never more than 0.95 USD.

## Proof

`python3 scratch/trial-ichi-vault-hyperevm/proof.py` (2026-11-20, `proof.json`): real fork transactions through this
artifact, fork reset at 51,781,938 = the parent of incumbent take
`0xcd7b75eb3282676f5fdc0da9c57c6e8e1ab7d9f6b5f3b8465565748c106dad61` (block 51,781,939, tx index 0, +8.172130 USDC).
The anvil fork has no HyperCore precompiles, so the script places a fork-only replay fixture
(`mock/src/PrecompileReplay.sol`) at `0x..0808` and `0x..080e`; it answers with the bytes the real precompiles
returned inside the incumbent's transaction (its mainnet callTracer trace, `trace-cd7b.json`). Nothing else is
overridden. Owner `0x1111111111111111111111111111111111111111`.

| fork tx | result |
|---|---|
| deploy `0xfacaba50feebfaa59154a50aa28875752f4ef8ae8d7a6b6469ddfd85987fcad5` | executor `0x8f7a45eb...`, 1,188,466 gas |
| non-owner `0x01ef9cc07efdb093d5d61af7345a9732c4aa7aebe25797d3c09beb2072badd10` | reverts (`owner`) |
| minProfit 100 USDC `0x60da9b3bd8a0fe2121fc30314f8ee42d616b874964a884f82f46ba5c2ae8926f` | reverts (`no profit`) |
| success `0xda0b33c001147ebf933355ade33b7381ef3f13ca3417d2204bc9d5af27b6fcb2` (block 51,781,944) | 496,911.53 USDC flash (the incumbent's size): owner USDC 0 -> 8,172,130 (+8.172130, the incumbent's gain to the unit), 734,418 gas; executor holds 0 USDC, 0 WHYPE, 0 shares, allowances 0 |
| the same again `0xcf06dc41ea737e6a91671273b4e48f0797002fd8cd015856a553e4905ea4e8a6` | reverts (nothing left: Morpho's repayment pull fails) |

`scan()` on the fork before the take: 49.7k -> 2.547815, 165.6k -> 5.600383, 496.9k -> 8.172130, 1.49M -> 0 (the sell
pool runs out of USDC); after the take: 0 for all four.

`selftest.py`: the bot's hand encoder equals `cast calldata` for `run()` and `scan()`; the paper runtime equals the
artifact's runtime with the owner filled in; one live scan answered for all 6 sizes (all 0 at 18:49Z).
`control.py` (positive control for that zero): through the same relay call shape `owner()` answers and `run()` at
`latest` executes deposit, withdraw and the swap and fails only at Morpho's repayment pull (`transferFrom
reverted`), i.e. the route ran and simply lost money at that moment. `scanloop.py`: 8 of 8 scans answered.

## Read cost

3,200 polls x 26 CU = 83,200 CU/day, plus about 88 CU per evaluated gap; hard cap 98,000 CU/day in code
(0.052 USD/day at 1M CU = 0.53 USD). No feed filter. Every read, startup included, is inside the loop's handler; at
the cap it sleeps until 00:00 UTC.

## Logs (`logs/bot.jsonl`)

`start` (with `executor=`), `poll` heartbeat, `opportunity`, `opportunity_skip` (reason), `simulate_revert`,
`paper_sim`, live: `send_result` with `result` won / lost, `gas_used`, `send_block`, `winner_block`,
`blocks_after_winner`; `signer_reject`, `read_budget`, `relay_error`, `loop_error`.

## Not checked

- No gap was open while the bot was built, so no paper `opportunity` row exists yet; the live path beyond the scan
  is covered by the fork proof and by reading, not by a paper capture.
- The sell pool `0x586304...` and its helper `0xa760b68d812ee3cf9a9c169e820d56495b58261d` are unverified; the bot
  relies only on what the swap pays inside the transaction (the executor reverts otherwise).
- The vault owner can change `hysteresis`, `deposit1Max` or the TWAP periods; then `deposit` reverts (gas only when
  sent; the scan shows 0 first).
- The HYPE base fee moves a lot (0.1 to 12 gwei on 11-20); at 12 gwei one attempt costs about 0.6 USD and only
  gains above about 0.75 USD pass the 1.2 x rule.
