trial

# trial-angle-liq-arbitrum

Angle's Borrow module on Arbitrum holds vaults that borrowed EURA against WBTC, WETH or USDC.e. Anyone may call
`liquidate(uint256[] vaultIDs, uint256[] amounts, address from, address to)` on a VaultManager: the caller's EURA is
burned and the vault's collateral is paid out at the oracle price divided by a discount (down to 0.90, i.e. up to
10 pct). EURA has almost no DEX liquidity on Arbitrum, which is why vaults sit liquidatable for hours: the takers get
EURA by buying stEUR (Angle's savings token, ERC-4626 over EURA) on its Camelot stEUR/USDC pool and redeeming it. One
transaction does:

    Morpho Blue flash USDC -> Camelot USDC -> stEUR -> stEUR.redeem -> EURA -> VaultManager.liquidate
      -> WBTC / WETH / USDC.e -> Uniswap V3 -> USDC -> (EURA left over -> stEUR -> USDC) -> repay

and the executor reverts unless its USDC grew by `minProfit`. The gain is paid to the bot wallet as USDC.

## Competition, last 7 days (blocks 523,759,167-526,178,367; `scratch/r6b90/pool.py` on both managers)

| block | tx | sender -> target | vault | flash | repaid (EURA) | kept (USDC) | gas | tx index | liquidatable before the take |
|---|---|---|---|---|---|---|---|---|---|
| 526,052,183 | 0xb0bd703b19a8... | 0xf49ca3d9 -> 0x7cc97d1c | WETH 941 | Aave 880 USDC | 786.73 | 42.74 | 2,695,284 x 0.0202 gwei | 15 | at least 10,564 s (42,000 blocks); healthy at -31,680 s |
| 526,137,643 | 0xa7c899f63e26... | 0x753c056b -> 0x3c6917f8 | WBTC 92 | Morpho 107.78 USDC | 97.78 | 4.56 | 956,516 x 0.07 gwei | 5 | more than 95,300 s (345,600 blocks) |

Two operators, two takes, both on 2026-11-20/21, none in the six days before. Priority fee: none (Arbitrum orders by
arrival). Blocks to take: tens of thousands to hundreds of thousands (`scratch/r6b90/window.py`: `checkLiquidation`
at -1, -4, -12, -40, -120, -400, -1,200, -4,000, -12,000, -40,000, -120,000 and -345,600 blocks; results in
`window-92.json`, `window-941.json`, `window-21.json`). WBTC vault 21 (26.78 EURA to repay, discount 5.7 pct) has been
liquidatable for more than 26 hours and neither operator has taken it; the bot's check at head 526,180,392
(2026-11-21 07:53 UTC) simulates +1.774 USDC for it. This is not a speed contest.

About 37 more vaults are "liquidatable" with 0.0006-0.02 EURA to repay: dust, skipped (under 1 EURA).

## What the bot does

- At start and every 6 h: `vaultIDCount()` and one Multicall3 `vaultData` call per 400 ids on each of the three
  managers -> the vaults with debt (516 on 2026-11-21: 8 WBTC, 174 WETH, 334 USDC.e).
- Every 300 s: one Multicall3 `checkLiquidation(id, executor)` call per 300 of those vaults (4 eth_calls). A healthy
  vault reverts `HealthyVault()`; a priced one returns (max EURA to repay, max collateral, threshold, discount, debt).
- For each of the three largest priced vaults with at least 1 EURA to repay: one `probe()` eth_call with 7-9 USDC
  flash sizes (1.08-1.35 USDC per EURA of the maximum repay; for a vault that allows partial repay also 1/4 and 1/2).
- Best gain >= 0.05 USDC: read the base fee, `eth_estimateGas` the take (Arbitrum: never a constant), gas limit =
  estimate x 1.2, cap = gas limit x (base fee x 1.25), in USD at a conservative 4,000 USD per ETH. Send only when the
  gain is above that cap, with `minProfit` = the cap in USDC, after re-simulating the exact call.
- Paper: logs `paper_sim`. Live: sends through the signer and logs `send_result` with won / lost, gas used and the
  winner's block (the newest `LiquidatedVaults` on that manager).

## Addresses (each read with a getter, `scratch/trial-angle-liq-arbitrum/setup.sh`, `discover.py`)

| what | address | check |
|---|---|---|
| Treasury (EURA) | 0x0d710512e100c171139d2cf5708f22c680eccf52 | `treasury()` of the WBTC manager; `stablecoin()` = EURA; `vaultManagerList(0..4)` |
| WBTC VaultManager | 0xF664118E79C0B34f1Ed20e6606a0068d213839b9 | name "Angle Protocol wBTC-EUR Vault", `collateral()` = WBTC, 100 ids |
| WETH VaultManager | 0xe9f183FC656656f1F17af1F2b0dF79b8fF9ad8eD | "Angle Protocol wETH-EUR Vault", `collateral()` = WETH, 942 ids |
| USDC.e VaultManager | 0x04437E94aF860AFBb0429A7D36B9C00a5a5173B9 | "Angle Protocol USDC-EUR Vault", `collateral()` = USDC.e, 2,785 ids |
| EURA | 0xFA5Ed56A203466CbBC2430a43c66b9D8723528E7 | Treasury `stablecoin()`, stEUR `asset()` |
| stEUR | 0x004626A008B1aCdC4c74ab51644093b155e59A23 | `asset()` = EURA |
| stEUR/USDC Algebra pool | 0xcc4e4c18bad7e1cc63bb98915eeb3f412939955e | `token0()` = stEUR, `token1()` = USDC, `factory()` = 0x1a3c9b1d... |
| Camelot router | 0x1F721E2E82F6676FCE4eA07A5958cF098D339e18 | `factory()` = the pool's factory |
| Uniswap V3 SwapRouter02 | 0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45 | `factory()` = 0x1F98431c...; WBTC/USDC 500 pool 0x0e483131..., WETH/USDC 500 pool 0xc6962004... |
| Morpho Blue | 0x6c247b1F6182318877311737BaC0844bAa518F5e | holds 286,722 USDC; the incumbent's flash source |

The two other managers of the Treasury (staked Curve LP collateral, one vault with debt each) are left out.

## Loss bound

`StepArb.take` is owner-only and reverts `NoProfit` unless the executor's USDC grew by `minProfit` after the flash
loan was repaid; a lost attempt costs gas only. Gas cap per send: under 0.95 USD (in practice about 0.06 USD at the
real ETH price). `capital_usd` 5 is gas money; no principal.

## Read cost

288 scans a day x 4 eth_calls x 26 CU = about 30,000 CU; rebuilding the vault list 4 x 364 CU; a standing vault adds
92 CU per scan (probe, block, estimate, guard). 31,400-57,900 CU/day = 0.017-0.031 USD/day at 0.53 USD per million
CU. Code cap 95,000 CU/day; every read is inside the loop's handler, which sleeps to 00:00 UTC at the cap.

## Fork proof

`python3 scratch/trial-angle-liq-arbitrum/proof.py 526137642 wbtc 92` (results in `proof-result-526137642.json`):
success `0x6082c500c5660fbffebfbb11335c3ed89a8ec851f795df1347185ca15fa1794c`, +4.889767 USDC to the owner, 1,017,004
gas; guard revert `0x9331675fc8a0fc2a9ba6e30c629856cd4844e1546a8b9e6cf3690f08f2fced8f` (NoProfit); non-owner revert
`0xbdbe45cd5b842e553212c71ee057eee1eb435cf7b385dab1b605c70f5b1d6f41`; the same take again reverts (vault healthy).

## Answer to the review of 2026-11-21 08:01Z (run bb453a4a, decision fix)

That review was written at 08:01:57Z, while the building session was still copying files in (manifest.yaml
08:01:41Z, README.md 08:02:10Z, `paper start` 08:07:42Z). Nothing in the code had to change. Each point, checked
again by run 1a11076c at 08:45Z:

- manifest: present, `tools/manifest-check.py` prints OK.
- README: this file.
- named Solidity executor artifact: `scratch/trial-angle-liq-arbitrum/contracts/out/StepArb.sol/StepArb.json`
  (source `contracts/src/StepArb.sol`), manifest `executor` line.
- evidence: manifest `fork_evidence`, `scratch/trial-angle-liq-arbitrum/proof.py` and
  `proof-result-526137642.json`.
- paper service: active/running since 08:07:42Z, 0 restarts; `logs/bot.jsonl` has `opportunity` and
  `paper_sim success` rows for WBTC vault 21 every 300 s (gross 1.80-1.85 USDC, cap 0.138 USDC).

## Not done / limits

- A vault larger than the stEUR pool can fill (about 800 USDC moved its price 2 pct) is only taken when a smaller
  flash still clears the gas cap; vaults with a threshold (dust rule) need the full amount.
- EURA is sourced only through the stEUR pool; the first incumbent also used a USDC.e/EURA pool (0x5cd95bc1...).
- New VaultManagers added to the Treasury are not picked up automatically (`VMS` in bot.py).
