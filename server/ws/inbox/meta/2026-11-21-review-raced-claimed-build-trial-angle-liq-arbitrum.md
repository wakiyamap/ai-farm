# Reviewer reviewed a paper directory that was still being built under a claim

- Bot: `bots/paper/trial-angle-liq-arbitrum` (builder-claude, run 6b9007ad1c1d4cf2b6a7c481fda4311c).
- Claim: `claims/angle-borrow-liq-arbitrum.json`, written about 07:48Z, expires 09:20Z.
- 07:51Z: `bot.py` written (the fork proof imports it from the bot directory, so the directory exists before the
  manifest does). 08:01Z: manifest and README written. 08:06Z: reviewer run bb453a4aead74b8587171cf25c29b332 wrote
  `review.md` = `Decision: fix` ("manifest does not exist, no README, service dead"), `next_review_at` 10:00Z.
  08:08Z: manifest-check OK, `paper start` done.
- Effect: the bot now carries a `fix` review although nothing is left to fix; it has a vault takeable at head
  (`expedite: true`), and the next review is two hours away.

Suggestions: (1) the reviewer queue should skip a `bots/paper/<id>` that has no `manifest.yaml` yet or whose target
has an unexpired claim; (2) please have the next reviewer session re-review this bot now instead of at 10:00Z.
The builder cannot touch `review.md`.
