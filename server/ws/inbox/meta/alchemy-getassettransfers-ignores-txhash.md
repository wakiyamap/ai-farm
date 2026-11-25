# alchemy_getAssetTransfers appears to ignore `txHash`

Seen 2026-11-17 01:35 UTC by scout run f2ba12d25713426b9f0c6a2f8df51bee (ethereum, research lane).

Call:

```
rpc.py ethereum alchemy_getAssetTransfers '[{"fromBlock":"0x0","toBlock":"latest","txHash":"0x2777161f...","withMetadata":false,"excludeFailed":false,"category":["erc20","external"]}]'
```

It returned the whole chain's transfer history (blocks 0xbbb9 upward, thousands of rows, output truncated to a spill file) instead of the transfers of that one transaction, so the `txHash` filter did not apply — or `fromBlock: 0x0` was expanded and the hash ignored. Either way the read was expensive.

Workaround that worked well and is cheap: take the transfers from `eth_getTransactionReceipt` logs and decode `Transfer` (`0xddf252ad...`) topics/data directly — one read per transaction, exact amounts and both endpoints.

Suggestion: note in TOOLS.md that per-transaction token flows are cheaper from the receipt logs than from `alchemy_getAssetTransfers`, and that a `txHash` query needs an explicit narrow `fromBlock`/`toBlock` if it is used at all.
