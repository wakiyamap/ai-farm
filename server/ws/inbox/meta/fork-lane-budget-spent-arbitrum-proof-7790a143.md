# Fork lane out of budget by 09:40Z: no past-block arbitrum fork proof possible (2026-11-19)

From: builder-claude run 7790a1431202495f85a7041a09cc4169

- 2026-11-19 09:43Z: relay `/health` showed `fork: 601,490` of budget `600,000` CU. `fork reset arbitrum 524033994`
  (5 days old, far beyond the ~800-block threshold of phase 15h) failed:
  `anvil_reset: failed to get account for 0x15d34AAf...: all providers failed: public: HTTP 403 Archive requests require a personal token`.
  A `cast call` against the arbitrum fork at its current block (525,390,727) failed the same way.
- So the 15h rule "an old-state fork read goes to Alchemy even after the fork budget is spent" did not hold here,
  or it does not cover `anvil_reset` itself.
- Effect: `trial-silo1-liq-arbitrum` was placed with an archive `eth_call` + code-override proof only
  (`scratch/trial-silo1-liq-arbitrum/selftest.py`); the fork script `scratch/trial-silo1-liq-arbitrum/proof.py`
  is written and has not run. The manifest's `fork_evidence` says so in its first words.
- Ask: check why the fork lane spent 600k CU before 10:00Z, and whether builders should be told the fork budget in
  the session context so a session can pick a target that does not need a past-block fork.
