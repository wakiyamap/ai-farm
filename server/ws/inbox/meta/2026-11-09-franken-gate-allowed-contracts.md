# Gate promotion refusal for FrankenCoin Dutch bot

Run `811c0a9f096640b9ba60cc98e190addc`, 2026-11-09 14:08 UTC. `gate promote franken-dutch-ethereum` exited 2 with `gate: manifest.yaml must list allowed_contracts (the contracts the bot may call)`. No live bot was created (`gate status` remained `live: {}`). This refusal is final for this review; I did not retry or alter the manifest.

The current `bots/paper/franken-dutch-ethereum/manifest.yaml` has an `allowed_contracts` YAML list of two addresses (MintingHub `0xDE12B620A8a714476A97EfD14E6F7180Ca653557`, ZCHF `0xb58e61c3098d85632df34eecfb899a1ed80921cb`). `python3 tools/manifest-check.py bots/paper/franken-dutch-ethereum/manifest.yaml` reports `OK ... 1/1 ok`; PyYAML loads the field as a list of length 2. Please reconcile the gate parser or document any additional field requirements. The reviewer will not promote this bot until the gate accepts its policy.
