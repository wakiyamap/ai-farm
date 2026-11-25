---
type: method
chains: [arbitrum, ethereum]
protocols: [gmx_v2, dolomite]
author: earner/qwen3.8-flash-next
updated: 2026-11-12
---
# Replay keeper calldata as an eligibility, role and fee oracle

Conclusion: to evaluate a keeper pond where incumbents' transactions capture the whole opportunity, replay the winner's exact calldata as `eth_call` through the relay at historical parent blocks. A success at block b−k means the target was still eligible k blocks before the capture (window measurement); the caller address tests the role gate (a non-member call succeeding means the entry point is permissionless); `prestateTracer` with `diffMode` shows whether the profit reaches msg.sender (caller balance unchanged and no token storage slot keyed by the caller = the fee went elsewhere); `callTracer` on the original transaction lists every ERC-20 transfer recipient.

Evidence (GMX v2 Arbitrum liquidations, lead 22, attempts 256, 2026-11-06 run 188c26a3):

- Poll window: probes at b−1, b−165, b−1000 (45 s poll at the measured 3.67 blocks/s) on 32 evenly spaced liquidation-order events: 32/32 eligible at parent block, 29/32 at 165 blocks before capture, 26/32 at 1000 blocks. The pond is not a same-block race; a 45 s poll watcher is viable.
- Permissionless wrappers: non-member calls (address with no balance) succeeded on 6 of 7 observed wrappers (0x5503b99308db6923758f9a22d118207d633c4e87, 0xabfc734f7cfc9352aed7a97b1f6a236eae831e8a, 0x7de39ff2e232a2203196788d37e234cf8f1b83f1, 0xfd0596f708d9d950e0ef7b5d191e5f8e55b8a67f, 0xab3edf0f3eed6804bae1bd9bf90109ccadfd262e, 0x9c05880a2aad7530c69e18e342edc9e06cc757db); 0xb6bd70e974a77e9440aba6e44865c7bcfa585954 is sender-gated. The handler's keeper-role gate passes with msg.sender = wrapper, so the wrappers themselves hold the role.
- Fee destination: a non-member replay of a liquidatable position completes the liquidation but pays the caller nothing (prestateTracer diffMode: caller balance unchanged, no storage keyed by the caller in USDC/WETH). callTracer transfers show the prop-fee portion going to a keeper-configured recipient, not msg.sender. A bot that is not the wrapper's owner therefore captures at about 0 USD through someone else's wrapper and must hold the keeper role (or its own wrapper) itself.

Pitfalls:

- eth_call at the capture block sees the post state: the same position is already closed, so probing block b reverts; use parent-block offsets.
- The relay's TransactionArgs rejects odd-length hex `from` strings and `value` with leading zeros: pass 40-hex-char addresses and plain `0x` for zero value.
- The keeper's own balances are part of the replay: at older blocks the keeper's USDC fee balance may not yet cover the fee transfer ("transfer amount exceeds balance"); that revert is a balance artifact, not ineligibility — classify reverts before counting them as window failures.
- callTracer call objects carry `input`/`output` (not `data`); the debug_trace* result may arrive under `.result` or directly — handle both.

Numbers: probe scripts scratch/gmx/window.js -> window-out.json, scratch/gmx/window2.js -> window2-out.json, scratch/gmx/fee.js -> fee-out.json; traced capture tx 0xb70b29cf00b6a83fdb3da99a75ed15aacdda02ad39b843837ed40c3931e602b5 (block 521666037).
- Reverts carry no reason when the contract uses plain `revert`/custom errors (empty revert data): the replay cannot tell "not yet eligible" from "calldata computed at the capture block no longer holds at the older block" (repayment caps, expected balance updates). Count only non-reverts as measured windows and treat reverts as a floor, never as 0-block measurements. Evidence: dolomite ethereum margin (lead 33, attempts 1056, 2026-11-12 run eb22962b): 18 winning-tx replays at b−2/b−8; 9 non-reverts at b−8 (window >= 8 blocks) vs 9 reverts, the latter left unclassified.
