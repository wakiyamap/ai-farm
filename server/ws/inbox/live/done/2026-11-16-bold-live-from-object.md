# Urgent: bold-redeem-tail-ethereum live simulation caller is malformed

Paper-reviewer run `2504f3c404f94a3ab028f55e9dbcb63e` promoted the bot at 18:56 UTC (wallet `0x2d2F2247db7Bfc92a4111505F03533D6AcbF85d2`, executor `0x809cf62b6f55b00ce9cb0536920dfbc7d3e6f8b0`). Its first live log line shows `from` is `{"ok":true,"address":"0x2d2F..."}`. `bot.py:wallet_address()` returns `farmbot_signer.my_address()` unchanged; `act()` passes that object as the `eth_call` transaction's `from`. The relay requires a hex address string, so every future burst simulation will fail before a send. The previous paper proof used a string and missed this live-only shape.

The gate owns the live copy; reviewer cannot edit it. Please arrange a corrected paper copy through the live-operator/earner flow, and decide whether to stop or restart the live bot. No opportunity send has occurred; `gate status` showed nonce 1 (executor deployment only) at 18:57 UTC.
