# reserve-dutch-ethereum-v2: drought ended, live bot saw no auction

From earner run ee6ebe0b, 2026-11-11T06:4xZ. The ledger reserve_revenue drought since 26348622 has ended: 13 new TradeStarted rows (26379242 x7, 26387995 x5, 26389553, 26389854) and 15 settlements through 26389671, including a weETH-sell auction on 2026-11-11 06:21:35Z (block 26389854, sell token 0x8c106eedad96553e64287a5a6839c3cc78afa3d0 = weETH, trade 0x3e851b5554d05926551e2bdac1bacf4bcc07fa00, its 1800 s Dutch window ran to ~06:51Z).

bots/live/reserve-dutch-ethereum-v2/logs/bot.jsonl shows 1069 heartbeats all with active=0 and zero sends since the live boot (promoted 2026-11-10 17:2xZ), including heartbeats through the 06:21Z start and its window. The bot's own log never registered an active auction, so the live detection path (45 s polls, TradeStarted scan, oracle window) is worth an operator's eye: is the new start class-filtered out (pair/sell-token filter), rejected by the oracle staleness guard, or simply not seen? The live-loss stop is quiet (live_loss_usd 0) so no urgency, but the awaited class is now live on-chain and the bot has had its first post-promotion candidate.

No action required from you if the bot's filter explains it; a one-line note in the bot README or logs naming the filter decision would close this out.
