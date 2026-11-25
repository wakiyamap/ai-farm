---
type: infra
chains: [ethereum, base, arbitrum]
protocols: [olympus_heart, euler_evk]
author: researcher/opus
updated: 2026-11-10
---
# Olympus Heart beat() reward and Euler FeeFlow auctions: two fee/keeper classes, both closed (2026-11-10)

**Conclusion.** Both are dead ends for the farm. Olympus Heart `beat()` is live and pays every 8 h, but the race for the first eligible block is a saturated builder auction (the winner bids ~95 % of the reward to the builder; surplus ~0 USD). Euler V2 FeeFlowController (Dutch auction of protocol fees) has been retired on all three farm chains since April 2026: protocol fee share is 0, so nothing flows in. Ledger source `olympus_heart.reward_issued` is installed so a change in this race shows up without new RPC work.

## Olympus Heart (Ethereum, `0x5824850D8A6E46a473445a5AF214C7EbD46c5ECB`, VERSION 1.7)

- Identity: OlympusDAO/olympus-v3 `src/scripts/env.json` (current.mainnet.olympus.policies.OlympusHeart); live `Beat`/`RewardIssued` logs from this address confirm it.
- Parameters (eth_call at head ~26382930): `frequency()` 28800 s, `auctionDuration()` 1200 s, `maxReward()` 40e9 (40 OHM, 9 decimals). `currentReward()` grows linearly from 0 to 40 OHM over the 1200 s after the slot opens. Slots open at `ts ≡ 14400 mod 28800`, i.e. 04:00, 12:00 and 20:00 UTC.
- Census, 14 days (blocks 26282137-26382937, 42 RewardIssued, `scratch/euler-ff/heart-rows.json`): **40/42 beats landed in the first block after the slot opened** (+11 s, reward 0.3667 OHM). The other 2 landed one block later (+23 s, 0.7667 OHM). Nobody waits.
- Callers: 0x9781b7e5 via contract 0x70e60fbf won 25/42 with 0 priority fee and a direct coinbase payment (block 26377195: 0.00278 ETH to the builder, plus 1.43M gas x 0.107 gwei). 0xd5b71d91 via 0x1b8b73c4 won 8/42 by paying a 1-2 gwei priority fee on ~1.4-2.4M gas. 0xa88e98bb won 6/42. Others (0xb596c007, 0x91583f8e via a multicall, 0x66392c03) won once each. Losers still land in the same block and pay gas (block 26377195: losing calls at indexes 2, 93, 160).
- Economics at OHM 16.90 USD and ETH 2114 USD (DefiLlama coins, 2026-11-10): reward 0.3667 OHM = **6.20 USD**. Incumbent cost = 5.88 USD coinbase + 0.32 USD gas, so **net ~0**. Priority-fee winner: 1.41M x 2.04 gwei = 6.08 USD, so **net ~0.1 USD**. Total pot is about 18.6 USD/day, and it is already bid away.
- Why we can't win: the first block after the slot is a sealed builder auction among at least 4 bots. The farm has no bundle submission (the signer broadcasts publicly) and no builder relationship. Waiting for a bigger reward loses the slot. This is `blocked_infra` at best, and even with bundles the surplus is ~0.
- Reopen if: the ledger source shows beats drifting later than +11 s routinely (the reward grows 0.4 OHM per block), the winner set collapses to one quiet caller, or OHM/maxReward rises enough that bids lag. Check with `ledger query "SELECT block,actor FROM events WHERE source_id='olympus_heart.reward_issued' ORDER BY block DESC LIMIT 20"`.

## Euler V2 FeeFlowController (Ethereum `0xFcd3Db06EA814eB21C84304fC7F90798C00D1e32`, Base `0xbF4906E2F20362c3d746F7eFfF54abB8282902ed`, Arbitrum `0xA1585dc7Cd4EF33f7a855fDE39771b37838B0bFE`)

- Identity: euler-xyz/euler-interfaces `addresses/<chainId>/PeripheryAddresses.json` key `feeFlowController`. Source: euler-xyz/fee-flow `FeeFlowController.sol` (back-to-back Dutch auctions; `buy(assets, receiver, epochId, deadline, maxPayment)` pays `getPrice()` in EUL and sweeps the full balances; the price falls to 0 after `epochPeriod`).
- State at head: `epochPeriod` 14 days on all three chains, and `getPrice()` = 0 on all three. Last epoch start: Ethereum 2026-04-11 (epochId 137), Arbitrum 2026-04-21 (53), Base 2026-05-03 (67).
- Buy events: 0 over the last ~90 d (Ethereum 650k blocks, Base 2M, Arbitrum 10M; topic0 0xd0c183be...). alchemy_getAssetTransfers: the last ERC-20 inflow on every chain was in April 2026 (convertFees mints in the final buy txs).
- Why it is dead: the Ethereum ProtocolConfig `0x4cD6BF1D...` `feeReceiver()` = `protocolFeeConfig(vault)` receiver = 0xcad001c3 (the DAO multisig, also the auction paymentReceiver), and `protocolFeeShare()` = 0 on a sampled vault (eUSDe-6 0x2daca71c). Euler stopped routing protocol fees to the auction. A buy at price 0 would only sweep the leftover dust.
- Reopen if euler-interfaces names a new feeFlowController, or `protocolFeeShare()` becomes nonzero with the receiver set to the auction.
