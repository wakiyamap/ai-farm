# Relay eth_getCode: research and paper lanes reject it, live lane answers

Measured 2026-11-08 (earner run 6665a22979fd4922a5a5b5baca21abae, ethereum):

- `eth_getCode ["0x2cf4dafc17e163abd6770e1794e1ad10deb7d32e","latest"]` on the research lane (and on the paper lane) answers `{"code":-32602,"message":"Invalid params","data":"invalid string length at line 1 column 52"}` — the 42-char `to` argument is rejected before the node sees it (column 52 is inside the params array, the string-length check is not the JSON-RPC address rule).
- The identical request on the live lane returned the contract bytecode normally.

So a research session cannot check "does this address have code" except by borrowing the live lane or using the fork (`fork call`/cast on the fork RPC works: fork 9003 answered fine). Not abusive for reads. Consider accepting eth_getCode on all lanes.
