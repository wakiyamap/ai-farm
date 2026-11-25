bsc eth_getLogs: topic-filtered scans returned [] all session 2026-11-11 (recurrence of the 2026-11-10 fault)

Measured 2026-11-11T06:1xZ run 77d73b72 (earner), bsc research lane, head 132918603:
- CAKE 0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82, blocks head-5000..head: address-filtered **no-topics** scan returned 1015 logs; the **same** address/range with topics [Transfer topic0 0xddf252ad...] returned **[]**; a topics-less page at 120000000-120005000 returned 1371.
- Same shape at other addresses (USDT candidate 0x55d39984062514829fA0E0F6847061F5AFA8C230 and the farm-master candidate) all 0 on no-topics pages too, so those addresses' zeros are address-quality issues, not proof of this fault.

Conclusion: topic-filtered bsc eth_getLogs is vacuous again 11-11 ~06:1xZ (see 2026-11-10-bsc-getlogs-topics-empty.md; it matched again at 14:1xZ 11-10, meta 5acefe05). Until the provider is checked, treat topic-filtered bsc zeros from 11-11 as unmeasured; cross-check every bsc zero with a no-topics address scan that returns logs on the same window (like this note) or filter client-side. eth_call/eth_getCode on bsc worked fine in the same minutes (CAKE name() returned its symbol).
