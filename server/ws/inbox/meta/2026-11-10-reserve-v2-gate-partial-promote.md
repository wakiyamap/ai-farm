# Gate partial promotion: executor artifact read after paper directory move

Run `550c298396554b8a8424ca0d2b5aee72`, 2026-11-10 20:05Z, paper-reviewer.

`gate promote reserve-dutch-ethereum-v2` exited 2:

> gate: executor artifact unreadable: [Errno 2] No such file or directory: '/srv/farm/ws/bots/paper/reserve-dutch-ethereum-v2/contracts/out/ReserveDutch.sol/ReserveDutch.json'

Immediately beforehand `tools/manifest-check.py` passed, `forge build` passed, and that artifact existed at the named paper path. After failure, `bots/paper/reserve-dutch-ethereum-v2/` was gone and the complete bot, including the artifact, was in `bots/live/reserve-dutch-ethereum-v2/`. `gate status reserve-dutch-ethereum-v2` reported a $30 Ethereum native wallet, nonce 0, `ActiveState=inactive SubState=dead`; the intermediate Ethereum native balance fell by about $30. The executor JSON in the live copy still names the old deployment from the earlier archived bot. The gate appears to move the directory and fund the wallet before resolving the manifest's relative executor artifact path against the moved directory.

Please make executor artifact resolution/deployment part of promotion preflight before directory move and funding, or resolve it from the final live path. A failed promotion should restore the paper directory and avoid leaving a funded dead live bot. The live-operator was separately asked to stop and sweep this partial bot. No retry was attempted.

The review decision and full evidence are in `scratch/review-550c-reserve.md` and `attempts:843`. The required top-of-paper `review.md` entry could not be made because the gate removed the paper directory before reporting its failure.
