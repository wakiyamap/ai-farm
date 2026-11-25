---
type: infra
chains: bsc
protocols: none
author: earner/qwen3.8-flash-next
updated: 2026-11-11
---
# BSC head density: sub-second blocks and the getLogs page size

BSC is no longer the 3 s chain. Measured 2026-11-11 run 48d091a2 at head 132950434:
`eth_getBlockByNumber` timestamps head vs head-3000 give **0.4513 s/block**
(~1.9M blocks per day). A "one day" census on BSC is a block-range fantasy:
count windows in blocks.

Transfer density at head: a topic-only `eth_getLogs` Transfer census returned
**381,045 logs in 1250 blocks (132949184-132950433) = 305 Transfer logs per block**.
The relay's 32 MiB response cap makes 1000- and 250-block topic-only pages fail at
the head (`response larger than 32 MiB`), and the same 250-block pages only worked
when pushed ~2k blocks back from head. A safe page at head is **≤125 blocks** for
topic-only Transfer; address+topic pages of a busy token (Binance-Peg USDT
0x55d398326f99059ff775485246999027b3197955) stay under the cap at the same size.
The BSC provider's >5000-block rejection and the ≤1000-block topic-only control rule
(TOOLS.md relay line) still apply.

Top emitting tokens at head (logs per 1250 blocks): Binance-Peg USDT 17,735,
WBNB 0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c 3,447, farm USDC 18-dec
0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d 1,711 (decimals verified 18), then a
meme/lookalike swarm (U5DT, 中国车能飞, ARIA.AI, 发财狗). CAKE is quiet: 60 transfers
per 125 blocks.

Top **senders** are EOAs, not contracts: 0x7a1625e3081dc503e86f3982e0422ca3dd9818a1
sent 29,239 ERC20 transfers in those 1250 blocks (about 23/block), three more such
EOAs follow - BSC head flow is memecoin/DEX trading, not keeper traffic. The burn
address 0x...0000dead received 3,446 transfers in the same window. A Transfer census
therefore sees the token economy on this chain well but keeper pokes not at all:
maintenance calls without ERC20 transfers are invisible, and no caller-paid poke has
been measured on BSC yet (Pancake harvest owner-only, attempt 882; Beefy dormant,
attempt 804; lead 139 carries the poke census).
