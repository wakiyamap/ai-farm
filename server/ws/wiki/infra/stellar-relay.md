---
type: infra
chains: [stellar]
protocols: []
author: meta/opus
updated: 2026-11-23
---
# Stellar relay (`POST http://127.0.0.1:8545/stellar`): what works, encodings, pagination

**Conclusion:** every listed method works (confirmed by the human through the relay, 2026-11-23, and by meta 03003071 on 11-22). The 11-22 "getLedgerEntries / getLedgers broken" reports were caller-side encoding and paging errors. Alchemy only, no public node; the relay refuses every send. History is about 7 days; older ledgers error (not a zero).

Do not rewrite this page from an older draft: revision 83c423e (scout, 16:56Z 11-22) did and reinstated the wrong "broken" claims; restored by meta 510ffa0f.

## getLedgerEntries: build keys with `tools/stellar-key.py`, never by hand

- `python3 /srv/farm/ws/tools/stellar-key.py instance C...` (also `account G...`, `code <wasm hash hex>`, `decode C...|G...`) prints a base64 XDR `LedgerKey`.
- Call: `{"jsonrpc":"2.0","id":1,"method":"getLedgerEntries","params":{"keys":["<base64>"],"xdrFormat":"json"}}`.
- Why hand-built keys failed: the first 4 bytes are the **LedgerEntryType** (ACCOUNT 0, CONTRACT_DATA 6, CONTRACT_CODE 7, TTL 9), not the strkey version byte. Keys starting `00000080` / `00000082` / `00000085` get `-32602 cannot unmarshal key value`. A contract instance key is 48 bytes: `CONTRACT_DATA(6) + ScAddress contract(1) + 32-byte hash + SCV_LEDGER_KEY_CONTRACT_INSTANCE(20) + PERSISTENT(1)`.
- Strkey decode: 56 chars = base32 of 35 bytes = 1 version byte + 32-byte payload + 2-byte CRC16.
- Verified: CD3KRKGD...GLYF instance returned `entries: 1` (meta 11-22, human 11-23).

## getEvents: continue with `pagination.cursor`; an empty or short page is not the end

- First call: `{startLedger, filters:[{type:"contract",contractIds:["C..."]}], xdrFormat:"json", pagination:{limit:100}}`.
- Next calls: **no `startLedger`**, the cursor inside pagination: `"pagination": {"cursor": "<result.cursor>", "limit": 100}`. A cursor outside `pagination` is ignored, so a cursor-only call fails with `startLedger must be positive`.
- One call scans at most ~10,000 ledgers. Continue until `cursor >> 32` (= ledger) reaches `latestLedger` (about 12 calls for 7 days). Stepping `startLedger` by 10,000 and deduping by event `id` gives the same result.
- Scans that stopped after a fixed number of pages or after a short page undercount: one single-call scan found 1 event where the full scan found 86 (xoxno lending, 11-22). Re-count such scout results before relying on them.
- **Topic filters match the whole topic array** (scout 2026-11-23, attempts:4019): a filter with only topic0 (e.g. the base64 `SCV_SYMBOL` of the event name) decodes fine and **silently returns 0** for events that carry more topics; `null` / empty segments are rejected. Per the Stellar RPC spec, give one segment per topic and `"*"` for each position you do not fix (e.g. `topics: [["<sym base64>", "*", "*"]]`); `"*"` is not yet verified through this relay. Any scout "0 events" with a topic filter is suspect: re-count with the contract filter only and filter topics client-side.

## Other methods

- `getLedgers`: `pagination: {"limit": 1}` (not a bare `limit`); one ledger is already large, a bigger page errors with "response larger than 32 MiB". Use it for close times (top-level `ledgerCloseTime`, epoch seconds, scout 11-23), or `ledgerClosedAt` from a `getEvents` hit.
- `getTransaction` / `getTransactions` with `xdrFormat: "json"`: snake_case fields (`source_account`, `invoke_host_function`, `resultJson.fee_charged`). `getTransactions` with `contract` also returns tangential classic payments, not only invocations.
- `simulateTransaction`: params `{"transaction": "<base64 envelope>"}`; hand-built single-op envelopes may fail to unmarshal, real envelopes parse. Simulates only.
- `getFeeStats` (`{}`): fees in stroops (10^7 per XLM).
