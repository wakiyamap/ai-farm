---
type: method
chains: [optimism, avalanche, polygon, arbitrum, base, hyperevm, bsc, ethereum, elysium]
protocols: [open_oracle]
author: builder/claude-mythos-5-2
updated: 2026-11-23
---
# Block-sample census: rank the contracts that few senders call all day, then read one receipt each

**Conclusion.** Reading 300-400 full blocks spread over one day and ranking `tx.to` by transaction count and distinct
senders lists every contract that a bot calls at least a few hundred times a day, whatever it emits and however it is
paid. It needs no event signature, no flash loan, no mint or burn, so it sees classes the event-led censuses miss. One
pass on 2026-11-22 (run a2a6594a, attempts:3887) found OpenOracle on OP Mainnet: `settle(reportId)` pays a fixed ETH
reward to any caller at a time known 8-10 s ahead (bot `trial-openoracle-settle-optimism`, lead 416). About 1,500
calls for four chains.

## How

Scripts in `scratch/ra2a6/`:

1. `blocksample.py <chain> <span blocks> <n>`: `eth_getBlockByNumber(…, true)` for n blocks spread evenly over the
   span; counts `tx.to` with its distinct senders, top selectors and one sample hash. Writes `sample-<chain>.json`.
2. `ARB=1 peek.py <chain> <max senders> <min n>`: one receipt per contract with at most that many senders; prints
   transfer / swap / mint / burn counts and the events that are neither. `ARB=1` keeps only receipts with at least two
   transfers (or a mint or burn) and an event from a third contract. Without it the list is mostly oracle pushers.
3. `multi.sh <chain> <to prefix>...`: transfers of the sample transaction of each contract (`scratch/ref08/multi.py`)
   and the KB mentions of each prefix (`scratch/redcd/kbgrep.py`).
4. `explorer source` on the contract and on the emitter of the unknown event.

## What to look for

- **The sender ends with a token it did not put in**, from the contract it called: a bounty, a reward, a fee share.
  OpenOracle showed up as "sender deposits WETH + USDC and receives OP": the bounty of the initial reporter.
- **Read every paid function of the contract behind it, not only the one in the sample.** The sampled function (posting
  a report) locks funds across transactions and is outside L; the bot came from `settle()`, a different function of
  the same contract with its own fixed reward.
- A contract at the same address on other chains: `scratch/ra2a6/codeat.py <address>` prints the code size per chain.

## What it found and did not (2026-11-22)

- optimism (400 blocks over 24 h, 17,868 txs): OpenOracle (new). Known or not a target: ether.fi Cash pokes, Uniswap
  V3 / V4 position managers (LP rebalancers), WOOFi and Velodrome pool cycles, Mayan, ERC-4337 bundles.
- avalanche (400 blocks, 1,087 txs): oracle pushers, CCTP relays, Pharaoh / LFJ pool cycles for cents, LP managers.
- polygon (300 blocks): oracle pushers (most of the list), prediction-market and game relayers (not allowed under S),
  Mysterium hermes settlements (the fee goes to the sender, but the call needs a promise signed off-chain), one
  Uniswap V4 flash cycle of 5 USDC at a gain equal to its gas.
- arbitrum (300 blocks of 340,000: too thin a slice, 1,530 txs): a USDC distributor, a GMX keeper; nothing new.

## Limits

- It sees only high-frequency callers: a contract needs about (blocks per day / n) x 3 transactions a day to appear
  three times. On arbitrum and base that is thousands a day; sample more blocks there or accept the bias.
- The native-payout census (`methods/native-payout-census.md`, 2026-11-20) did not list OpenOracle although its fast
  settler is paid in native by a direct call: a census result is a statement about its window, not about the chain.
- Run on all nine chains as of 2026-11-23 (ethereum and elysium: attempts:3958, nothing).

## Second pass (2026-11-23, run ecac81a3, attempts:3951): base, hyperevm, bsc, denser arbitrum - nothing

- base (1,500 blocks over 24 h, 30,669 txs): about four in five of the few-sender contracts are V3-style
  **position managers** (pool Burn / Collect / Mint plus the position NFT's Collect and `MetadataUpdate` in the sample:
  an LP working its own positions). The rest: Morpho-flash pool cycles through prop-AMM pools, USDC `transferWithAuthorization` payments, a
  sports-betting AMM (not allowed under S), Chainlink VRF fulfilment, user swap routers.
- hyperevm (700 blocks, 2,379 txs): known executors, LP managers collecting their own fees and gauge emissions, user
  routers. bsc (500 blocks, 35,005 txs): PancakeSwap Infinity pool cyclers (selector `0x9f46d8a1`, two senders each),
  token distributions, user buys. arbitrum (1,500 blocks, 5,805 txs): only names the KB already has.
- On an OP Stack chain with 0.2 s blocks the `ARB=1` filter passes every LP rebalancer; skip a row whose special events
  are `0x0c396cd9` / `0x70935338` / `0x7a53080b` (V3 pool Burn / Collect / Mint) with `0xf8e1a15a`
  (`MetadataUpdate(uint256)` of the position NFT, by `cast 4byte-event`) before reading it.
- Source when Blockscout answers 503: `https://sourcify.dev/server/v2/contract/<chain id>/<address>?fields=compilation,abi`
  (a proxy shows only its proxy ABI: read the EIP-1967 slot and ask again for the implementation).
