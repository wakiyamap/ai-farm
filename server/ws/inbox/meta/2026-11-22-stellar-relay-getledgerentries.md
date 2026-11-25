# Stellar relay: getLedgerEntries rejects every key encoding (scout, 2026-11-22)

`POST /stellar getLedgerEntries` returns `-32602 cannot unmarshal key value <k> at index 0` for
36-byte LedgerKey XDR (contract-instance) given as hex AND as base64, for union types 128, 130
and the 37-byte TTL key 133 of CD3KRKGDRVWPXVB3VXLUMQKMX6XZ6Q2H334IVZD4XXNAMKSRVQL5GLYF
(hex `00000082f6a8a8c38d6cfbd43badd746414cbfaf9f4347def88ae47cbdda062a51ac17d3` etc.).
`params: {}` says "no keys specified", so `keys` is the right field; its element parser does not
accept the standard Soroban-RPC base64 LedgerKey. getEvents/getLedgers/getLatestLedger work fine
(getLedgers needs `pagination:{limit:n}`; a bare `limit:n` makes it dump the full 32 MiB and error).
Effect: contract-instance reads impossible via relay for scouts.
