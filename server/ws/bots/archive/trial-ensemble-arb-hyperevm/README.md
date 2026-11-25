trial

# trial-ensemble-arb-hyperevm

Cheap-chain trial (decision 2026-11-17-cheap-chain-trials), lead 312, attempts:2717.

**What it takes.** Ensemble ("hyper_tokens") leveraged vaults on HyperEVM are ERC-4626 vaults with instant
`deposit` / `redeem` at a NAV read from HyperCore precompiles. Their shares also trade on a 0.3 % HyperSwap V3 pool.
When the perp price moves the NAV away from the pool by more than the fees (vault 0.2 % each way, pool 0.3 %), one
transaction through the `TrialVaultArb` executor:

- flash-borrows USDC from Morpho Blue `0x68e37de8...` (no fee),
- **mint side:** `vault.deposit` then sells the shares on the pool, or
  **redeem side:** buys shares on the pool then `vault.redeem`,
- repays, and pays the USDC gain to the bot wallet. It reverts unless the gain is at least `minProfit`.

| | vault (= share token) | pool |
|---|---|---|
| BULL | `0x2d561b24e754b105bb0df34a3345aac1fe805210` | `0x1ccdbc56a9235d59c1d001aa2724d31a10b38af4` |
| VOL | `0xeb22ec1b402dcc4155b9d8d2e1db2f2d229162cc` | `0x8e26ebc3ac380ff931c6f6731c9289514e62ec21` |

Router `0x1ebdfc75ffe3ba3de61e7138a3e8706ac841af9b`, USDC `0xb88339cb7199b77e23db6e890353e22632ba630f`.

**How it waits.** The NAV has no event, so the bot polls: one `eth_call` of the executor's `probe()` every 27 s
returns the gain of all 16 candidates (2 vaults x 2 directions x 40 / 80 / 160 / 320 USDC). It acts on the best one
only if the gain is above that send's gas cap; `minProfit` is the gas cap in USDC.

## Competition, last 7 days (to block 51,730,945, 2026-11-20 02:00Z)

| who | how | fills | per fill | timing, fee |
|---|---|---|---|---|
| contract `0x4c1e071696dc95e38033c7ffc404e38ffeb2ba83` (driver EOA `0x85be4c45...`) | own USDC inventory, both vaults in one tx | 1,248 on BULL (948 in the last 3 d = 316/day) | gain median 0.079, mean 0.153, max 0.579 USDC (14 sampled) | tx index 0-11; 0.4 gwei floor in 9 of 14, up to 1.6 gwei; fee median 0.000178 HYPE |
| executor `0xb54e8debf06c26ca906d7d98eb4e01dabd9aed19` (EOA `0x5d03a3f8...`) | Morpho flash, 40 / 80 / 160 USDC | 52 in 3 d | 0.07-0.14 USDC | checks on chain every 20-25 s, floor gas price |

Blocks to take: historical windows cannot be measured, because HyperCore reads are not archived (a NAV read at a
block older than a few hundred reverts `PrecompileCallFailed`). One window measured live: the bot's route simulated
+0.2119 USDC at block 51,730,878 and the incumbent took it at block 51,730,898, 20 blocks (about 20 s) later.
652 of the incumbent's 948 fills had no swap by anyone else on the pool in the 30 blocks before: the trigger is the
NAV, not a pool trade. Nobody bids a priority fee.

The trial measures: how many of the bot's sends land before the incumbent, at a 27 s poll.

## Loss guard

- Executor: `NoProfit()` unless the USDC balance grew by `minProfit` (> 0); `tx.gasprice <= maxGasPrice`; deadline.
- Bot: gas limit = estimate x 1.2 (max 1.9M), `maxFeePerGas` = base fee x 1.3 + bid, never above 2 gwei; the cap in
  USD (pool HYPE price x 1.15) must be under 0.95 and at most half the simulated gain. Bid at most 20 % of gross.
  Checked on a live gap (`selftest_eval.py`): BULL mint 40 USDC, gain 0.0156 USDC against a gas cap of 0.0125 USD
  (727k gas limit, 0.23 gwei): too thin, skipped under the 2x rule.
- A lost attempt: about 620k gas = 0.02-0.04 USD.

## Proof

`scratch/trial-ensemble-arb-hyperevm/proof_fork_success.py` (2026-11-20 04:05Z, `proof-fork-success.json`): a real
fork transaction through this artifact. The anvil fork has no HyperCore precompiles, so the script places a
fork-only replay fixture at the two precompile addresses the vaults read (`0x080f`, `0x0801`); it answers with the
bytes the real precompiles returned through the relay about a second earlier. Nothing else is overridden.

| fork tx (reset at head 51,738,681) | result |
|---|---|
| deploy `0x3e9145b8...0961f8` | executor `0x8f7a45eb...`, 1,169,335 gas |
| success `0xe58406f7...fefb4bb` | BULL deposit + sell, 40 USDC flash: owner USDC 0 -> 22279 (+0.022279), 494,598 gas; executor balances and all four allowances 0 after |
| nothing to take `0xa03e4a8e...4395c` | reverts (Morpho repayment pull) |
| minProfit 2 x gain `0xd37e0012...1a08` | reverts `NoProfit()` |
| non-owner `0x2096b94d...b327` | reverts `NotOwner()` |

Controls: the vaults' previews on the fork equal the live ones, and `probe()` on the fork returned 22279 / 15450
where the live `eth_call` (code override) returned 22278 / 15449 at the same moment. The proof needs a gap open on
mainnet when it runs, so a re-run waits for the next one and reports other hashes. `proof.py live` (relay
`eth_call` with a code override, +0.211948 USDC at block 51,730,878) is the earlier, second line of evidence.
Details in `fork_evidence`.

## Read cost

3,200 polls x 26 CU = 83,200 CU/day, plus about 88 CU per evaluated gap; hard cap 98,000 CU/day in code
(0.052 USD/day at 1M CU = 0.53 USD). No feed filter. Every read, startup included, is inside the loop's handler;
at the cap it sleeps until 00:00 UTC.

## Logs (`logs/bot.jsonl`)

`start` (with `executor=`), `poll` heartbeat, `opportunity`, `opportunity_skip` (reason), `simulate_revert`,
`paper_sim`, live: `send_result` with `result` won / lost, `gas_used`, `send_block`, `winner_block`,
`blocks_after_winner`; `signer_reject`, `read_budget`, `relay_error`, `loop_error`.

## Not checked

- The vault's CircuitBreaker policy (`authorizeDirectAction`) may limit an account per block or epoch; the
  flash executor `0xb54e8deb` passes it, and so does the code-override simulation.
- `redeem` pays from the vault's USDC buffer; with a small buffer the redeem side reverts (gas only).
