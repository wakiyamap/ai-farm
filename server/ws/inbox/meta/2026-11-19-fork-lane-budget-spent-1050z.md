# Fork lane archive budget spent by 10:50Z: a ready bot could not be fork-proven (builder-claude, run 05728037)

- 2026-11-19 10:50Z: `fork reset arbitrum 525321630` failed with `all providers failed: public: HTTP 403 ... Archive
  requests require a personal token`. Relay `/health` at that time: `fork` 601,570 of 600,000 CU (research 322,014 of
  700,000). With the fork lane spent, no fork on any chain can reset to a past block for the rest of the UTC day, so no
  builder session can produce a fork proof and no reviewer can re-run one.
- Effect this session: `trial-gmx-buyback-slow-arbitrum` (lead 298, attempts:2486) is fully written and checked through
  the relay (simulation at the capture's parent block: +0.0045 WETH per batch; 12 such batches sat for a week), but it
  is not placed: `proof.py` needs one reset. The draft waits in `scratch/trial-gmx-buyback-slow-arbitrum/`; lead 298's
  `next_steps` lists the three steps left.
- Suggestions: (1) put the fork lane's spend and budget in the builder's session context, so a session knows at the
  start whether a proof is possible and can pick relay-only work otherwise; (2) consider letting fork archive reads fall
  back to the research lane's remaining budget once the fork lane is spent (research had 378k CU left), or raise the
  fork budget on days with many trial builds (several trial bots were fork-proven and re-run by reviewers on
  2026-11-19 before 10:00Z; I did not count the lane's spend per run).
- Also for the session context: "Trial bots live: 30 / 10" shows a stale cap (the limit is 30 since
  `2026-11-18-trial-slots-30.md`).
