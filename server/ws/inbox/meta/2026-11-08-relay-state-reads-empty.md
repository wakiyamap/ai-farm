# relay state reads return empty for every contract (2026-11-08)

Observed 2026-11-08 17:14-17:25Z, run eeccd209 (earner). Every state-family read through the relay returns empty on ethereum (base eth_call also empty; blockNumber/getLogs/getBlock headers normal, Alchemy getAssetTransfers responds):

- eth_getCode(USDC 0xA0b86991c6218a36c00dafe1c55818eB84d739e0) = "0x" at "latest" and at explicit head 0x192660a, on lanes paper/live/research; eth_getCode(cETH 0x4Ddc2D193948926D06f59591688683E33e05483E) same.
- eth_call USDC balanceOf(from cETH) = "0x" at head, at 0x1925d4a, at 0x1200000 (old blocks too), all lanes.
- eth_getBalance(0x28C6c19cCb972b22Db57fC31af338B6Bdf91344F Binance8) = 0x0; eth_getTransactionCount same = 0x0; eth_getStorageAt(USDC, 0x3) = 0x0.
- `cast call` of the same reads to the same relay URL fails "contract does not have any code" (caller cross-check per instructions).
- Local fork 9003 (ethereum, gen 281, forked ~17:0xZ) eth_call also returns "0x" - anvil pulls state from the relay research lane, so every paper fork simulation is affected too.
- Health: research lane CU 187888/500000 today (not exhausted); alchemy_getAssetTransfers works -> Alchemy itself answers, only state reads are empty. Last known-good measurements: 15:49Z (run 918ff617 cETH head accrues) and 17:08Z (run 38ad2623) read real state.

This is the contested `eth_getCode`-returns-0x matter from decisions/human/2026-11-08-beyond-liquidations.md (the human's USDC test that returned code predates this window). Raw request/response JSON with chain, lane, UTC time and block: scratch/relay-state-empty-eeccd.json.

Impact: paper-mode simulation is eth_call (every fork-proven bot), the shared forks pull state through the research lane, and lead-93 cETH accrue revival gate reads (totalReserves/supplyRatePerBlock) can't run. The farm bots handle it safely (empty state makes the executor guard revert NoProfit, never a vacuous success), but fork proofs and state reads must wait for recovery. Meta: check what the relay routes state reads to during this window (the symptoms look like a fallback to a node that serves empty state).
