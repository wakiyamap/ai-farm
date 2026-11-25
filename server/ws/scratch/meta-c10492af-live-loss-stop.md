---
type: pitfall
chains: [any]
protocols: []
---
# The 30 USD live-loss stop: every invariant the reviewer checks, in one list

**Conclusion:** promote criterion 5 (`decisions/human/2026-11-09-promote-criteria.md`)
cost 7 `review_fix` verdicts on 2026-11-09 (attempts 677, 689, 698, 710, 711, 720,
721) across gearbox-v3, moonwell-whale, morpho-watcher and reserve-dutch, because
each fix closed one bypass and the next review found another. Check **all ten**
below before you submit; each one was a real blocker.

The stop is correct only if: *no signer send can happen while realized live loss
could already be >= 30 USD, or while any confirmed receipt is not yet counted.*

1. **Every send is gated.** Run the stop check immediately before *every*
   signer call: executor sends, approvals, pool/market initialisation
   (`setPoolAllowed`), retries. A one-off init send before the check is a bypass
   (attempt 721).
2. **Pending receipts block sends.** While a confirmed receipt is not yet
   valued and added to the total, do not send (attempts 720, 721).
3. **Value only at a fresh price from this cycle.** Settle a receipt only in a
   cycle whose ETH/USD read succeeded *this cycle*; never at a cached, stale,
   startup or zero price. Guarding only `price <= 0` is not enough (attempts
   698, 710, 711). Order: read price, then settle, then stop check, then send.
4. **Never drop a receipt.** A receipt leaves `pending` only when it has been
   added to the total. Missing price, failed decode or a missing field keeps it
   pending (attempt 677).
5. **Count every fee component.** Ethereum: `gasUsed x effectiveGasPrice` plus
   any principal loss. Base (OP Stack): add `l1Fee` and the operator fee too. A
   component the receipt omits is counted at a stated upper bound justified
   against the gas cap, never as zero (attempts 689, 720).
6. **Units.** Check the divisor with a unit test on one real receipt (reserve-dutch
   divided by 1e12 instead of 1e24, a 1e6-fold error; attempt 695).
7. **Persist before the next send.** Write the total and pending list to
   `state/` (atomic write: temp file + rename) before any further send; if the
   write fails, do not send (attempt 698).
8. **Stop is sticky across restarts.** When the total reaches 30 USD write
   `state/STOPPED.json` with the reason, exactly once, from the cycle-level
   check (not only inside the send branch), and refuse to send at startup if it
   exists (attempts 677, 683, 700).
9. **Restart reload.** On start, load total, pending receipts and the stop
   flag before the first send; a missing or unreadable state file in live mode
   fails closed.
10. **Prove it.** Ship a small offline test under `scratch/<bot>/` that drives
    the extracted settle/stop functions through: fresh price, failed price,
    missing fee field, crossing 30 USD, restart with `STOPPED.json`. Cite it in
    the attempts row (e.g. `scratch/mw-whale-fix/settle-proof.js`).

If your bot shares this code with sibling bots, apply the fix to all of them in
the same session (`pitfalls/copy-reviewed-fix-to-all-bots.md`). The general
review checklist is `pitfalls/paper-review-blockers.md`.
