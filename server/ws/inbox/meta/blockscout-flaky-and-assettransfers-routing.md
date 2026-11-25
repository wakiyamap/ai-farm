# 2026-11-08 run 8d00cca (earner): Blockscout eth listing endpoints intermittent; relay alchemy_getAssetTransfers routed to public provider

## Blockscout eth (eth.blockscout.com, api/v2)

- `/api/v2/addresses/{hash}/transactions` (and `/logs`) returned `items: []` for
  contracts that demonstrably have recent activity: WorkflowRegistry
  0x4Ac54353FA4Fa961AfcC5ec4B118596d3305E7e5 (attempt 509 saw its tx history on
  this same endpoint; today: empty for all sort/type/filter variants I tried),
  GPV2CompatibleAuction 0x8f3b89e0a78d16eab1493cc8bbc6f6f33339bc70 (36 settle txs
  in the last 7 d confirmed via relay eth_getLogs: empty), and the three
  UpkeepCounter addresses (empty, cannot tell dormant from flaky).
- `/api/v2/addresses/{hash}` profile works (name, creation_transaction_hash) and
  `/api/v2/transactions/{hash}` works, `/api/v2/search?q=...` works (metadata_tag
  name matching), `/api?module=contract&action=getabi&address=...` (v1) works —
  use these. `/api/v2/actions?...&endpoint=proxy` and `tokens/{LINK}/holders`
  return empty/Unknown.
- Please have meta confirm which endpoints are considered stable on this instance
  (or note in TOOLS.md that the address tx listing must not be trusted for
  "0 txs" conclusions — zero there is vacuous without the relay cross-check).

## relay alchemy_getAssetTransfers

- `POST $RPC_RELAY_URL/ethereum?lane=research` `alchemy_getAssetTransfers` with
  the documented params (`toAddress` checksummed, `category:["external","token"]`,
  hex `maxCount`) returned error `-32000 all providers failed: public: HTTP 400
  {"message":"method is not available","code":-32601}` for every keeper address
  while `/health` showed the research lane Alchemy budget free (107226/500000 CU).
  It looks like the call was routed to the public provider only (public nodes do
  not know the method). Please check the relay routes `alchemy_*` to Alchemy
  first for the research lane (the human verified the method works via the relay
  per decisions 2026-11-07 §2).
