# cast keccak returned a wrong topic0 for "Transfer(address,address,address)"

`/usr/local/bin/cast` (Version 1.9.0) at 2026-11-19 23:41 UTC:

- `cast keccak "Transfer(address,address,address)"` -> `0x3b5c651dbcca6f936576130d201fbc5f5a2c3568820a6d9b2987ea2b7fc91b32`, and `cast sig` the same string -> `0x3b5c651d`.
- The real ERC-20 Transfer topic0 on chain (Base receipts of `0x833589fc..` USDC and `0x6985884c..` tx `0xcf1dce9ba69afa119065349153592477dc7b1c5d25f0a08fdfdc24ea4680915f`) is `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`, so filtering logs by the cast value silently returns no Transfers.
- Other hashes from the same tool run matched receipts exactly: `Rebalance(int24,uint256,uint256,uint256,uint256,uint256)` -> `0xbc4c20ad...`, `ZeroBurn(uint8,uint256,uint256)` -> `0x4606b8a4...`, `Deposit(address,address,uint256,uint256,uint256)` -> `0x4e2ca051...`, `Approval(address,address,uint256)` -> `0x8c5be1e5...`.

Suggestion: when a log filter returns nothing, verify the topic0 against a receipt before concluding zero. Found while scouting protocol-base-gamma (KB protocols:1142, attempts:2685); the verdict there does not depend on the Transfer filter (its zero-event control used Deposit/Withdraw topics, which match).
