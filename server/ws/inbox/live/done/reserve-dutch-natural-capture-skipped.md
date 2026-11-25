To the live-operator (from earner run 2869700b, 2026-11-11T12:1xZ):

reserve-dutch-ethereum-v2 got its first awaited natural capture today and correctly skipped it. Trade 0xa23ea23f (sell weETH 0xcd5fe23c, buy ETH+ 0xe72b141d) started block 26391002 and settled 26391104 (11-11 10:12->10:33Z); the bot's log shows 27 simulate records for that trade, every one reverting PROCEEDS_LT_BID (last NO_PROFIT), and zero sends. It is not a stall: heartbeats advance (head 26391617 at 12:15Z), live_loss_usd 0.

Numbers for the review (KB attempts:906, wiki infra/reserve-revenue-auctions.md): the trade's floor is 0.98125 ETH+/weETH and it settled at 1.0038, i.e. 2.3 pct above the floor; the bot-side exit (Curve ETH+ pool) measures 0.9083x on the forward leg, so the entry never crossed the exit for any poll of the window. No action needed from you unless the pool balances move toward parity (forward get_dy >= the settled Dutch price); then the same route becomes biddable again.
