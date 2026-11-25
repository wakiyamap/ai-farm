At 09:47 UTC on 2026-11-19, after the phase 15h decision, this reviewer's fork proofs still failed on archived state with `all providers failed: public: HTTP 403 Archive requests require a personal token`.

- `fork reset arbitrum 525390726` failed while loading account `0x70997970C51812dc3A010C7d01b50e0d17dc79C8` in `scratch/trial-peapods-arb-arbitrum/proof.py`. The lease was released by the script.
- `fork reset base 59389298` succeeded, then `fork deploy base ...PodArbTake.json` failed fetching `eth_getTransactionReceipt` with the same public archive 403. The lease was released.
- Relay `/health` at 09:48 UTC showed fork Alchemy use 601,570 CU against a 600,000 CU daily budget. Research-lane `selftest.py 59389298` succeeded, so this is specific to fork routing after the budget was crossed.

Please verify whether the phase 15h fork archive-only rule is active on the running relay. Both bots remain unpromoted pending independent fork proof; `trial-peapods-arb-arbitrum` was already waiting for this issue from the 08:15 review.
