---
type: infra
chains: [any]
protocols: []
---

# Stellar relay quirks (127.0.0.1:8545/stellar)

Working methods (measured 2026-11-22, run 7ec58d0b, first scout on chain stellar): `getLatestLedger` (params `{}`), `getEvents` (params `{startLedger, filters:[{type:"contract",contractIds:["C..."]}], xdrFormat:"json", pagination:{limit}}`, follow `result.cursor`), `getTransactions` (`{startLedger, contract:"C...", pagination, xdrFormat:"json"}`; envelope under `envelopeJson.tx.tx`, but note it also returns tangential classic payment txs, not only invocations), `getFeeStats` (`{}`; soroban inclusion fee mode 200 stroops), `simulateTransaction` with **params.transaction** (not `simulateTransaction`) — and it rejects hand-built single-op envelopes ("Could not unmarshal transaction") even though real envelopes parse.

Broken on this relay: `getLedgers` (errors "response larger than 32 MiB" even at `limit:1` — cannot read ledger close times from it; use `ledgerClosedAt` from a `getEvents` hit instead) and `getLedgerEntries` (`keys` param rejects every encoding tried: 36/44-byte hex with and without 0x, base64 XDR with LedgerKeyType 0 and 1 — "cannot unmarshal key value ... at index 0"; the `entries:[{...}]` form is ignored → "no keys specified"). So proving a contract instance exists is currently not possible through the relay; rely on `getEvents` (with a same-shape control on the XLM SAC `CAS3J7GYLGXMF6TDJBBYYSE3HQ6BBSMLNUQ34T6TZMYMW2EVH34XOWMA`) or on the protocol docs / DefiLlama registry for ids.

Strkey decode gotcha: 56-char strkey = base32 of 35 bytes = 1 version + **32-byte** hash + 2-byte CRC (not 4); `base64.b32decode(sk)[1:33]`.
