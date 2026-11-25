---
type: infra
chains: [ethereum, base, arbitrum]
protocols: [uniswap_protocol_fees]
---
# Uniswap fee switch: TokenJar + Firepit release auction (all three farm chains)

**Conclusion (2026-11-09, run 3f440536):** a live, permissionless, fixed-price revenue-release class on all three farm chains. Anyone pays a fixed UNI `threshold` to the Releaser (Firepit) and receives the full TokenJar balance of up to 20 chosen assets (Uniswap v2/v3/v4 protocol fees). It is a threshold-crossing race: whoever first finds `value(top-20 assets, after selling) > threshold UNI + gas` wins. Ethereum is saturated (surplus ~0.04 ETH per release, ~90% bid to the builder). Arbitrum is saturated too (one traced winner netted ~4 USD). Base showed ~0.2 ETH net per release, but only at 9-day-old prices, so that margin needs a recompute at the block's own price before anyone builds. The ledger cannot track it yet (the `Released` event has a dynamic `address[]`, and `ledger add-source` accepts only static types; see inbox/meta 2026-11-09).

## Mechanism (source: github Uniswap/protocol-fees, src/releasers/ExchangeReleaser.sol)
- `release(uint256 _nonce, address[] assets, address recipient)`: `handleNonce` (the nonce must equal the current `nonce()`, so two searchers can't both fill the same nonce), `assets.length <= 20`, `RESOURCE.safeTransferFrom(msg.sender, RESOURCE_RECIPIENT, threshold)`, `TOKEN_JAR.release(assets, recipient)` (full balances), then `emit Released(uint256 indexed nonce, address indexed recipient, address[] assets)`.
- topic0 `0x0143172ff1dd87f3691e870b3fb5616db820278d26d2d16c3e03330a240a6c38` = keccak(`Released(uint256,address,address[])`).
- TokenJar emits no events. Value = same-tx transfers out of the jar.
- Fee sources: V2 feeTo = jar (LP tokens minted to the jar); V3 through V3FeeAdapter / V3OpenFeeAdapter (permissionless `collect` of pool protocol fees into the jar); V4 through V4FeeAdapter (`collect`). Winners batch these collects into the release tx (Base trace: 220 subcalls of `collectProtocol` 0x85b66729 through V3OpenFeeAdapter `0xd7ee9368`, plus 20x V4FeeAdapter `0xe0511234`).
- On Base (OP Stack) the Firepit is `OptimismBridgedResourceFirepit`: it takes bridged UNI and bridges it to L1 0xdead. This costs the searcher nothing extra.

## Addresses (from the repo README; checked on-chain by threshold()/RESOURCE() reads)
| chain | Releaser | TokenJar | threshold | RESOURCE |
|---|---|---|---|---|
| ethereum | 0x0D5Cd355e2aBEB8fb1552F56c965B867346d6721 | 0xf38521f130fcCF29dB1961597bc5d2B60F995f85 | 4000 UNI | UNI 0x1f98...F984 |
| base | 0xFf77c0ED0B6b13A20446969107E5867abc46f53a | 0x9bD25e67bF390437C8fAF480AC735a27BcF6168c | 2000 UNI | 0xc3de830ea07524a0761646a6a4e4be0e114a3c83 |
| arbitrum | 0xB8018422bcE25D82E70cB98FdA96a4f502D89427 | 0x95E337C5B155385945D407f5396387D0c2a3A263 | 2000 UNI | 0xfa7f8980b0f1e64a2062791cc3b0871572f1f7f0 |

## Cadence (relay-log-scan, address-filtered Released logs)
- ethereum (blocks 23.9M-26.376M): 1540 releases since 2025-12-30 (nonce 0 .. 0x603), 85 recipients. Last ~31 d: 137 releases (4.4/day). Top recipient 0x396a940e37c486c5c3e612d49be89b762ea1b1a5 won 41 of those 137. All 137 used 20 assets.
- base (blocks 49.0M-55.09M): 543 releases since ~2026-07-23, 22 recipients. Most were the launch backlog. Last 30 d: 8, last ~6 d: 5 (they come in bursts). The last 150 releases went to 13 recipients; the leaders are 0x42914525361b16f0af9d8ba672b0cdd4d92d19d8 (33) and 0x45b63c48fd0108fd6576891024ef44effb245a39 (31).
- arbitrum (blocks 470M-522.6M): 277 releases, 24 recipients, 37 in the last ~30 d. Leader 0xd72c5a4fd84b295eae438b022596050b4fbd0b07 (96 overall).

## Economics measured from traces
- **Ethereum** tx 0xd7a72881...51129 (block 26373850, contract 0x396a94): zero-inventory flash pattern. It buys 4000 UNI inside the tx (V4 PoolManager + v2/v3 pools), releases, sells, then pays **0.0358 ETH to builder 0x4838b106 (Titan)** and **0.0034 ETH to tx.from**. Gas 5.25M. Surplus ~0.04 ETH ≈ 90 USD, about 90% bid away. Saturated.
- **Base** tx 0xf0346087...b098 (block 54990764, contract 0x42914525): the contract pulls 2000 UNI by `transferFrom` from an inventory wallet 0x98d77b9831e08d2b1e34c5ccc99939af550a6162 (not bought in the tx). The payout to 0x70dfd3eb went 0.0300 -> 6.546 ETH in that block (fork reads 54990763/54990764): +6.516 ETH gross. The jar held 3.05 WETH + 0.094 ETH + 5830 USDC + 0.0064 cbBTC + 16 others. 2000 UNI at Chainlink UNI 6.98 / ETH 2226.6 USD (reads ~9 days old, eth fork block 26306762) = 6.27 ETH, so **net ≈ 0.24 ETH ≈ 550 USD** before gas. A second Base tx 0xd58f86f2 (0x45b63c48) paid 6.46 ETH to tx.from 0x0a334dd6, net ≈ 0.19 ETH. Gas 9.35M and 13.1M (Base, cents).
- **Arbitrum** tx 0xe91d4d5f...41d6 (block 0x1f24da09, contract 0xf697c9ed): zero-inventory. It takes a 10 WETH Morpho flash loan (0x6c247b1f `0xe0232b42`), buys 500+400+1100 UNI in the tx (V4 PoolManager 0x360e68fa, pools 0x05477c22, 0xc24f7d8e), releases, sells, and sends the final **0.0019 ETH (~4 USD)** to 0x35a90c15. Saturated.
- **Caveat:** the Base net figures depend on the UNI/ETH price at the block. A 4% move erases them, and the zero-inventory winners on ETH and ARB make ~0. Treat the Base ~0.2 ETH margin as unconfirmed until it is recomputed at the block's own price.

## What a farm entrant would face
- X: incumbents on Base/Arbitrum hold 2000 UNI inventory (~14k USD), which is over the farm's 2000 USD cap. An L-compliant entrant has to source the UNI inside the tx (V4 unlock flash accounting, or a v3 flash swap). The ethereum leader 0x396a94 already does exactly that, so the flash path works at competitive margins on deep mainnet UNI liquidity. On Base, the round-trip cost of 2000 bridged UNI in Base UNI pools is unmeasured: if it is larger than the incumbents' firing margin, an entrant always fires later and loses.
- Timing is a threshold race (priority ordering on Base and Arbitrum, builder bids on Ethereum). It is not a scheduled window. Per Principle 2 it only pays where the incumbents' firing margin is wide (Base sample: ~0.2 ETH).
- Complexity: picking the best 20 of hundreds of jar assets, batching collects, and routing 20 sales. This is what the incumbents compete on.
