# Reply (live-operator run 101782fd, 2026-11-11T09:5xZ)

The 06:21Z auction (block 26389854) sold 0x8c106eedad96553e64287a5a6839c3cc78afa3d0, which is NOT the token the bot handles.
reserve-dutch-ethereum-v2 filters TradeStarted on sell = 0xcd5fe23c85820f7b72d0926fc9b05b43e359b7ee (canonical ether.fi weETH, bot.js:27,504,552) and buy = ETH+;
the executor route (ReserveDutch.sol:74) is hardcoded to that weETH. So active=0 is the intended filter outcome, not a detection failure.
If 0x8c106eed lots recur and pay, that is a new target for an earner (new executor route, via paper), not a live fix.

Also: all 4 live bots crashed together at 09:42:13Z (relay "no provider available", signer wallet=null), external infra blip; restarted once each via gate at ~09:43Z, all heartbeating again.
