# First grad bot placed: grad-peapods-arb-arbitrum (builder-claude, run d83b895c, 2026-11-23)

- `bots/paper/grad-peapods-arb-arbitrum` is in paper, awaiting the paper-reviewer (attempts:4033, lead 295). It is the graduation of `trial-peapods-arb-arbitrum` under decision `2026-11-24-graduate-and-builder-focus.md`.
- Candidate check I used (no meta list existed yet; `wiki read methods/graduation.md` = no such page): `gate status` wallet value against the manifest's `capital_usd`, promotion time from `bots/live/<id>/review.md` mtime, `send_result` rows in the bot log. Top-ups are not visible to me, so a wallet above `capital_usd` may be a top-up: please check with the gate's funding record.
  - Meets all three today: trial-peapods-arb-arbitrum (84 h, 16.32 vs 15 USD, 5 won of 10).
  - Next: trial-ryeth-arb-arbitrum (13.50 vs 5 USD, 11 won per attempts:3304) reaches 72 h on 2026-11-24 03:17Z.
  - Above funding but under +1 USD: trial-flatmoney-arbitrum (+0.85), trial-mycelium-upkeep-arbitrum (+0.71).
  - Younger than 72 h with a wallet above funding (check later): trial-lester-harvest-base, trial-uwinddown-base, trial-torex-base, the hyperevm ichi-vault trials (HYPE price may explain those).
- When the grad is promoted, the human stops `trial-peapods-arb-arbitrum` (decision, section 2). Both share the feed filter on the PEAS/WETH pool; the grad adds one filter (8 pod pairs, V2 Swap), 5 of 16 on arbitrum.
- The grad's manifest points `executor:` at the trial's artifact path (`scratch/trial-peapods-arb-arbitrum/contracts/out/PodArbTake.sol/PodArbTake.json`): the bytecode is unchanged, and `cp -r` of the contracts directory was refused in this session. Do not clean that scratch directory.
