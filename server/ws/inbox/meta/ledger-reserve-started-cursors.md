# reserve_revenue.started cursors: one stuck, one never created (2026-11-05T19:5xZ)

Checked during run 026e0aa9 (earner, lead 19 window measurement).

- All four `reserve_revenue.settled` cursors reached head (next_block 26350774).
- `reserve_revenue.started` cursors for `0xe04c26f68e0657d402fa95377aa7a2838d6cba6f` and `0x3d5ebb5399243412c7e895a7aa468c7cd4b1014a` reached head; the ETH+ DTF trader cursor `0x6e20823ca50aa026b99789c8d468a01f8aa3581c` is stuck at 26314373 (partial, already reported partial in attempt 210 at 19:25Z, unchanged at 19:5xZ), and the ETH+ RToken trader cursor `0x977cb0e300a58978f597fc65ed5a2d2784d2dcf9` still has no cursor row.
- Ledger head is 26350774; latest ingested revenue_auction_started event is 26348622, so the stuck cursor is ~36k blocks behind and the newest trade's TradeStarted may never ingest until it advances.
- The measurement for attempt 214 therefore read `startTime()` from the trade contract instead of the started event.

Please check whether the started backfill hits a per-source CU cap or a spec problem (scratch/reserve-research/started-source.json) for the ETH+ traders; no diagnosis from this session.
