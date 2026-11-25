# A ninth chain: elysium (phase 10g, human, 2026-11-11)

From the human side. The human wants to find out whether a brand-new chain is a more efficient
place to earn than the established ones. Nothing here needs a decision; please carry it into
TOOLS.md and the role files at your next run. common.md already has the short version.

## What it is

- Farm name `elysium` (relay path, `fork`, `kb`, ledger `chain`). Chain id **99901**.
- Kinetiq's Arbitrum Orbit (Nitro) chain that settles to HyperEVM. Mainnet opened on 2026-11-09.
- Gas token **HYPE**, bridged 1:1 from HyperEVM. Blocks every 100-200 ms.
- USDC: `0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65` (6 decimals; given by the human, checked on
  chain by the install).
- Explorer: elysium.kinetiq.xyz/explorer. Public RPC: https://rpc.elysium.kinetiq.xyz (the relay
  uses it; agents go through the relay as always).
- Not the older "Elysium" of Vulcan Forged (chain ids 1338 / 1339).

## What works

Reads, the ledger, the KB, `fork` (port 9009) and the money path: the gate can fund and promote
there, the signer signs, the watchdog watches. The intermediate wallet on elysium is empty until the
human bridges HYPE there, so a promotion is refused for lack of funds until then; the reviewer puts
the amount a bot needs in `inbox/human/` as on the other new chains.

## What is different (please make sure the earner and the reviewer see these)

1. **Price**: there is no Chainlink feed on elysium. The farm prices HYPE with HyperEVM's HYPE / USD
   feed. If HyperEVM is unreadable, elysium cannot be priced and the signer refuses there.
2. **Gas limits**: Nitro charges the cost of posting to the parent chain as gas. A plain transfer
   needs about 21,140 gas, not 21,000, and a constant gas limit copied from another chain can fail
   with "intrinsic gas too low". Every gas limit in a bot comes from `eth_estimateGas` with headroom.
   The signer's rule is unchanged: gas x maxFeePerGas x HYPE price must stay within L.
3. **Polling cost**: at 100-200 ms per block, a bot that reads every block makes about 100 times the
   calls it would on Ethereum. Decision 2026-11-11-moonwell-stopped applies in full: the README says
   what the bot costs per day in Alchemy CU, and a bot above about 1M CU a day needs the human first.
   Poll on a timer that the opportunity justifies.
4. **Tooling**: Alchemy may not serve `debug_*` / `trace_*` on elysium (it did not on the testnet).
   `fork trace` and `fork replay` may be weaker there; say so in the lead rather than guessing.
5. **Everything is days old**: tokens, pools and launchpads appeared this week. Addresses come only
   from a protocol's own docs or the chain's explorer, never from memory or an aggregator alone.
   Measure liquidity and who else is taking the same opportunity before counting on it; a pool can
   be empty tomorrow. An executor must return profit as HYPE or the USDC above (10d rule).
6. **Ledger**: `blocks_per_call` covers only minutes of chain per call here, so a 7-day backfill of a
   new source takes many runs. A zero event count on elysium is evidence only once the source's
   cursor has reached the head (`tools/ledger-source-coverage.py`).

## What the human would like to learn

Whether opportunities on a chain this new are less contested than on Ethereum or Base: who the
incumbents are, how many there are, and what a farm-sized bot could take per day after gas. A
measured "nothing here yet" is a useful answer too.
