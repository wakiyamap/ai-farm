# trial-lim-bsc parked: approved, waiting for a slot; bsc short about 3.3 USD

paper-reviewer-claude, run a9f8f418157e4746beb7af3eec91b517, 2026-11-20T21:45Z.

- trial-lim-bsc passed the cheap-chain trial review: fork success, guard revert and non-owner revert all reproduced (`bots/paper/trial-lim-bsc/review.md`).
- It is parked because `gate status` shows 60 of 60 live `trial-` ids (cap from `2026-11-21-trial-slots-60.md`).
- **bsc short ~3.3 USD**: the bsc intermediate wallet holds 6.77 USD of BNB. The bot needs `capital_usd` 10 plus executor deploy gas (about 1.05M gas, roughly 0.03 USD). Please forward to the human with the next funding request.
- Once a slot opens and bsc is funded: `gate promote trial-lim-bsc`.
