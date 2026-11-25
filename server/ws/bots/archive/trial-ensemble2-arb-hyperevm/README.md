trial

# trial-ensemble2-arb-hyperevm

Cheap-chain trial (decision 2026-11-17-cheap-chain-trials), attempts:2929. Sibling of
`trial-ensemble-arb-hyperevm` (lead 312), which covers BULL only: it passes the 0.3 % fee tier for VOL, and VOL's
only pool is the 1 % tier.

**What it takes.** Ensemble ("hyper_tokens") leveraged vaults on HyperEVM are ERC-4626 vaults with instant
`deposit` / `redeem` at a NAV read from HyperCore precompiles. Their shares also trade on a HyperSwap V3 pool
against USDC. When the perp price moves the NAV away from the pool by more than the fees, one transaction through
the `TrialVaultArb` executor:

- flash-borrows USDC from Morpho Blue `0x68e37de8...` (no fee),
- **mint side:** `vault.deposit` then sells the shares on the pool, or
  **redeem side:** buys shares on the pool then `vault.redeem`,
- repays, and pays the USDC gain to the bot wallet. It reverts unless the gain is at least `minProfit`.

| | vault (= share token) | pool | fee tier | pool holds (11-20 13:46Z) |
|---|---|---|---|---|
| BEAR | `0xe12f47589a272665203ce727854cf3fef8a8ed94` | `0xfa740246c45f29df3bcda35e3941c225f4b77910` | 3000 | 46,776 USDC + 1,135 shares |
| iBULL | `0xd2778440c4c1934185a2f8cb7e09a9a7a7cc21f0` | `0x66a6d03f6d943092baf4fff4ee7d7ac40608a102` | 3000 | 28,242 USDC + 84 shares |
| iBEAR | `0xb0808ffd220541568f70efe9774c795cd0c310aa` | `0x7579b23c86734d8209a36820603d49d64f97d8b6` | 3000 | 491 USDC + 21,138 shares |
| iVOL | `0x59a72a4b8d632005112f7d2bc0d035e06be043d9` | `0x96a1ef14e88553ab750e166233798e9ec3a6fd97` | 10000 | 579 USDC + 14,418 shares |
| VOL | `0xeb22ec1b402dcc4155b9d8d2e1db2f2d229162cc` | `0x8e26ebc3ac380ff931c6f6731c9289514e62ec21` | 10000 | 32,177 USDC + 719 shares |

Pools from factory `0xff7b3e8c00e57ea31477c32a5b52a58eea47b072` `getPool(vault, USDC, fee)` and `pool.fee()`
(`scratch/r7f51/vaults.py`). Router `0x1ebdfc75ffe3ba3de61e7138a3e8706ac841af9b`, USDC
`0xb88339cb7199b77e23db6e890353e22632ba630f`. Every vault: `asset()` = that USDC, `maxDeposit(fresh address)` =
25,000 USDC.

**How it waits.** The NAV has no event, so the bot polls: one `eth_call` of the executor's `probe()` every 27 s
returns the gain of all 30 candidates (5 vaults x 2 directions x 40 / 120 / 320 USDC). It acts on the best one only
if the gain is at least twice that send's gas cap; `minProfit` is the gas cap in USDC.

## Competition, last 7 days (to 2026-11-20 13:45Z)

Mint / burn census of the two incumbents (`scratch/r7f51/navcensus.py`; a floor, the inventory contract's list was
cut at 1,000 rows per direction):

| vault | mints | burns |
|---|---|---|
| BEAR | 334 | 138 |
| iBULL | 38 | 211 |
| iBEAR | 194 | 111 |
| iVOL | 70 | 85 |
| VOL | 85 | 210 |

| who | how | sampled takes (`scratch/r7f51/takes.json`) | timing, fee |
|---|---|---|---|
| contract `0x4c1e071696dc95e38033c7ffc404e38ffeb2ba83` (driver EOA `0x85be4c45...`) | own USDC inventory, often two vaults in one tx | +0.078 (iBULL), +0.093 (BEAR + iBEAR), +0.103 (VOL + iVOL), +0.194, +0.318, +0.474 USDC | tx index 0-5; 0.4-1.8 gwei; fee 0.00016-0.0019 HYPE |
| executor `0xb54e8debf06c26ca906d7d98eb4e01dabd9aed19` (EOA `0x5d03a3f8...`) | Morpho flash | +0.026 USDC (iVOL), a loss after its 0.00055 HYPE fee | tx index 0, 0.75 gwei |

Blocks to take: historical windows cannot be measured, because HyperCore reads are not archived. On the BULL
sibling one window was measured live: 20 blocks (about 20 s) from the bot's probe to the incumbent's take.
Priority fee level: the floor (0.4 gwei) in part of the sample, up to 1.8 gwei on the larger takes.

Gaps seen while this bot was built (about 4 min of watching): BEAR mint 40 = 0.004-0.012 USDC, VOL mint 40 =
0.014-0.022 USDC. These are under the 2 x gas cap rule, so the bot will skip most gaps and send on the larger moves.

## Loss guard

- Executor: `NoProfit()` unless the USDC balance grew by `minProfit` (> 0); `tx.gasprice <= maxGasPrice`; deadline.
- Bot: gas limit = estimate x 1.2 (max 1.9M), `maxFeePerGas` = base fee x 1.3 + bid, never above 2 gwei; the cap in
  USD (pool HYPE price x 1.15) must be under 0.95 and at most half the simulated gain. Bid at most 20 % of gross.
- A lost attempt: about 500k-620k gas = 0.02-0.04 USD.

## Proof

`scratch/trial-ensemble2-arb-hyperevm/proof.py 600 10000 BEAR,VOL` (2026-11-20 13:50Z, `proof-fork-success.json`):
real fork transactions through this artifact. The anvil fork has no HyperCore precompiles, so the script places a
fork-only replay fixture at the precompile addresses the vaults read; it answers with the bytes the real
precompiles returned through the relay about a second earlier. Nothing else is overridden.

| fork tx (reset at head 51,774,422) | result |
|---|---|
| deploy `0x2ba44173...05dcbe` | executor `0x8f7a45eb...`, 1,169,335 gas |
| success `0x1cc39f9c...c382f2` | VOL (1 % pool) deposit + sell, 40 USDC flash: owner USDC 0 -> 19938 (+0.019938), 494,956 gas; executor balances and all four allowances 0 after |
| nothing to take `0x5de43dc6...d353b8` | reverts (Morpho repayment pull) |
| minProfit 2 x gain `0xbedf07a4...5815c2` | reverts `NoProfit()` |
| non-owner `0xf39bccde...923ee4` | reverts `NotOwner()` |

Control: `probe()` on the fork returned 19937 for that candidate and the live `eth_call` (code override) returned
19937 at the same moment; the vault previews agree.

**A first run is kept but not counted** (`proof-run1-stale-pool.json`): with all five vaults the fork needed 70 s to
fetch state, so its pool state was 107 blocks older than the NAV values. BEAR mint 320 "gained" 0.724 USDC on the
fork while the live probe was 0. It shows the path works on a 0.3 % sibling vault, nothing more. The script now
accepts a success only when the live probe of the same candidate is open. The 0.3 % vaults therefore have no fork
success with a matching live probe yet (BEAR mint 40: 4254 on the fork against 4286 live, not sent because VOL was
the better candidate in that round).

`selftest.py`: the bot's hand encoder equals `cast calldata` for `run()` and `probe()`; one live probe answered for
all 30 candidates.

## Read cost

3,200 polls x 26 CU = 83,200 CU/day, plus about 88 CU per evaluated gap; hard cap 98,000 CU/day in code
(0.052 USD/day at 1M CU = 0.53 USD). No feed filter. Every read, startup included, is inside the loop's handler;
at the cap it sleeps until 00:00 UTC.

## Logs (`logs/bot.jsonl`)

`start` (with `executor=`), `poll` heartbeat, `opportunity`, `opportunity_skip` (reason), `simulate_revert`,
`paper_sim`, live: `send_result` with `result` won / lost, `gas_used`, `send_block`, `winner_block`,
`blocks_after_winner`; `signer_reject`, `read_budget`, `relay_error`, `loop_error`.

## Not checked

- The vaults' CircuitBreaker policy (`authorizeDirectAction`) may limit an account per block or epoch.
- `redeem` pays from the vault's USDC buffer; with a small buffer the redeem side reverts (gas only).
- iBEAR and iVOL pools hold under 600 USDC on the USDC side: the redeem direction (buy shares with USDC) is deep,
  the mint direction (sell shares for USDC) is limited to small sizes there; the probe prices this in.
- A probe with all 30 candidates open would need about 20M gas; the `eth_call` is sent with 30M.
