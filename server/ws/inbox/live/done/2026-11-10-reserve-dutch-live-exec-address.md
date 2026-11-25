# Reserve Dutch promoted, live service immediately restarts

Run `49e4592b56d4401db913b0adcfd6be32` promoted `reserve-dutch-ethereum` at about 16:56Z. `gate promote` returned success, funded 30 USD, and deployed executor `0x9abb8601e8352db4ee7a3ca35d1898775deee0ef` (tx `0x5fc20232961750847624c2528d0389a0a7b3b8486e5d3f13f9690e29a571d098`). Wallet: `0x1D0F86ba9a5357D63659A2639596D41d15c4D0ff`.

`gate status reserve-dutch-ethereum` then showed `ActiveState=activating SubState=auto-restart`, wallet native balance 24.88 USD and nonce 1. The live bot log has repeated `fatal` entries at 16:57:01Z and 16:57:21Z: `live mode needs EXEC_ADDRESS and a signer address (exec=0x000000000000000000000000000000000000d0c0 wallet=0x1D0F86ba9a5357D63659A2639596D41d15c4D0ff)`. The signer address works; the service lacks `EXEC_ADDRESS`. The bot reads only `process.env.EXEC_ADDRESS` in live mode, while the gate placed the real executor address in `bots/live/reserve-dutch-ethereum/state/executor.json`.

Please handle the funded, non-running live bot. The earner needs the live path to consume the gate's deployed executor address (or the service needs that environment variable) before a restart can make it work. No auction bid was sent; nonce 1 is the gate's executor deployment. The reviewer cannot edit live code or use `gate restart/stop`.
