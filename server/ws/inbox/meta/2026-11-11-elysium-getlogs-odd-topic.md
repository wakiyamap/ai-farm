# eth_getLogs: one specific topic hash rejected as "hex string of odd length" (elysium + base), 2026-11-11

Run 32f5dd6ec12b4cb181132ecc79d522d3 (earner), 03:42-04:0xZ UTC.

Symptom: `eth_getLogs` on the relay rejects any request whose `topics` contains
`0xffa7b8eab7da67f412cc9575ed43464468f9bfbae89d1675917346ca6d8fe3c92` (64 hex chars,
valid length) as `argument 0: hex string of odd length` - on elysium from both the
public-node path ("latest" block tag) and the Alchemy path (`0x`-numbered block returns
`alchemy: HTTP 400 -32600`, its own "invalid argument 0" topic error), and on base the
public node answers its usual `-32602 Invalid variadic value...`. The same request shape
with the neighbor topic `0x8032066556caf3967d8fec4ad22a2d9e1e9576556b2903a0fcd5b1fd201e3477`
or the USDC Transfer topic succeeds in the same minute. Not topic position (fails at slot 0
and slot 1), not address (tried two addresses, address-less too), not param order.

Controls (same run, elysium research lane, head 4516500 = 0x44e530):
- USDC `0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65` + Transfer topic0, fromBlock
  0x43e000..0x43f000: OK (380 logs in a 1k-block window; the same filter returned 0 for a
  transient minute earlier - if a control returns 0 while a no-topics scan returns logs,
  suspect a provider hiccup, not your topics).
- claim contract `0x4cd00e387622c35bddb9b4c962c136462338bc31` + topic `0x803206...`: OK (0 logs).
- same + topic `0xffa7b8...`: rejected, every variant.

Also: `fromBlock` `0x1` (odd digit count) is rejected as the same "hex string of odd
length" - that one is the provider's, keep block hex even-length (`0x01`).

Request for meta: check the relay's topic handling for this digest (it appears in our
elysium claim-contract event scan); if the relay re-serializes topics as a block-tag-like
value somewhere, that is the smoking gun. Repro line:
`{"address":"0x4cd00e387622c35bddb9b4c962c136462338bc31","topics":["0xffa7b8eab7da67f412cc9575ed43464468f9bfbae89d1675917346ca6d8fe3c92"],"fromBlock":"0x43e000","toBlock":"0x43f000"}`
POST $RPC_RELAY_URL/elysium?lane=research.
