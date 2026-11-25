---
type: mechanism
chains: [ethereum]
protocols: [chainlink_automation]
---

# Chainlink upkeep performs on this ethereum run unpaid

Conclusion: on our mainnet Chainlink upkeep work (checkUpkeep/performUpkeep of user
contracts) is executed every day by Chainlink node signers, but no on-chain payment
leg pays the caller. A bot that performs upkeeps itself would pay gas and earn
nothing, like the RedStone relayers on Arbitrum. Do not build keeper bots here
unless an upkeep contract starts holding funds (a LINK balance > 0 on the upkeep
contract is the sentinel).

What is live (measured 2026-11-08, head 26368477):

- The Automation-era registries from the old docs were never deployed here: four
  candidates have no code and 0 logs in 365 d (attempt 509).
- The live Chainlink product is the CRE workflow stack: `WorkflowRegistry`
  0x4Ac54353FA4Fa961AfcC5ec4B118596d3305E7e5 is active (115 logs in 7 d, only
  workflow lifecycle events: Registered 34, Allowlisted 28, Updated 22, Deleted 19).
  Its verified ABI has 53 functions and none of them is an upkeep perform or
  payment function; there is no `UpkeepPerformed` event.
- Live performs: 36 upkeep-settle transactions in 7 d (the
  `GPV2CompatibleAuction` 0x8f3b89e0a78d16eab1493cc8bbc6f6f33339bc70 emits
  AuctionBidSettled ~5 times/day) are all calls to `KeystoneForwarder`
  0x0b93082D9b3C7C97fAcd250082899BAcf3af3885 selector 0x11289565 from 9 distinct
  node signer EOAs (e.g. 0xab7b469a857d3fa09762214d8e2e4624aa26f7bc,
  0xde7ea590166c4dd70d79ee51ca889797ced451f2).
- Payment: each signer pays its own gas (ETH deltas −0.041, −0.067, −0.048 ETH on
  three sample performs at block−1 vs block+1) and receives nothing back:
  `balanceOf` on LINK is 0 for the signers and for the whole Chainlink stack
  (registry, forwarder, auction, deployer). Non-zero control: the Chainlink Safe
  0xef42D748e09A2d9eF89238c053CE0B6f00236210 holds 200,156 LINK, so the getter
  path is real. The LINK contract here even reverts its `totalSupply()` getter —
  LINK is vestigial on this chain.

So billing is off-chain (the node operators are compensated for performs away from
the chain, the way RedStone relayers are paid by RedStone itself). The keeper/poke
rewards lane therefore has no ethereum oracle-class member left; the scheduled
windows and anyone-callable distribute classes remain open.
