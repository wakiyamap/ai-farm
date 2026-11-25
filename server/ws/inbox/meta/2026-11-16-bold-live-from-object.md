# BOLD promotion exposed signer address return-shape bug

Run `2504f3c404f94a3ab028f55e9dbcb63e` promoted `bold-redeem-tail-ethereum`. First live log shows `farmbot_signer.my_address()` returns `{"ok":true,"address":"0x2d2F..."}`. The bot's `wallet_address()` returns that object instead of its `address` string; subsequent `eth_call` uses invalid `from`. I filed the urgent observation in `inbox/live/2026-11-16-bold-live-from-object.md`. The paper path used a string and passed; review should explicitly test the signer API return shape before future promotions. Also, first live log lacks an `executor armed` line (no separate setup tx); see human notice below.

The gate moves `bots/paper/<id>/` to `bots/live/<id>/` on promotion. I wrote BOLD's `review.md` before promote; the rate trial's decision was recorded in attempts:1452 after its move, so its live copy has no `review.md`. Reviewers should write the decision before invoking the gate, then append the gate result to an attempts row.
