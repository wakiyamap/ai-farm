---
type: pitfall
chains: [any]
protocols: []
---
# The 30 USD live-loss stop: now enforced by the watchdog (checklist below is optional)

**Status (meta 5acefe05, 2026-11-10):** since phase 10c the **watchdog** stops any
live bot whose loss since promotion (gate funding, top-ups included, minus the bot
wallet's current value at Chainlink prices) passes 30 USD
(`decisions/human/2026-11-10-live-loss-stop-watchdog.md`). Promote criterion 5 is
satisfied by that. The decision says:

- a bot's own loss-record crash tolerance (corrupt `state.json`, crash between send
  and log, ambiguous signer reply) is **not** a reason to `fix`;
- a bot-side self-stop is welcome but optional, and a simple one is enough;
- what still matters: profit and principal must end in the **bot's wallet**. Value
  left in an executor or vault counts as loss to the watchdog (an executor with no
  withdrawal path back = `fix`).

The eleven invariants below came from 11 fix verdicts on 2026-11-09/10 (attempts
677-721, 791, 797, 800 on gearbox-v3, moonwell-whale, morpho-watcher,
reserve-dutch). Keep them as a **reference for an optional self-stop**, not as a
promotion gate. Don't spend earner or reviewer sessions on them.

## Reference: invariants of a crash-proof self-stop (optional)

The stop is correct only if: *no signer send can happen while realized live loss
could already be >= 30 USD, or while any confirmed receipt is not yet counted.*

1. **Every send is gated.** Run the stop check immediately before *every*
   signer call: executor sends, approvals, pool/market initialisation
   (`setPoolAllowed`), retries. A one-off init send before the check is a bypass
   (attempt 721).
2. **Pending receipts block sends.** While a confirmed receipt is not yet
   valued and added to the total, do not send (attempts 720, 721). An accepted
   signer reply must carry a valid 32-byte txHash: `ok:true` without one is
   neither a success nor a final rejection — the signer may already have
   broadcast it, so halt sending durably (an append-only halt marker that
   survives a lost state file) until the transaction can be reconciled
   (review b03b0e15).
3. **Value only at a fresh price from this cycle.** Settle a receipt only in a
   cycle whose ETH/USD read succeeded *this cycle*; never at a cached, stale,
   startup or zero price. Guarding only `price <= 0` is not enough (attempts
   698, 710, 711). Order: read price, then settle, then stop check, then send.
4. **Never drop a receipt.** A receipt leaves `pending` only when it has been
   added to the total. Missing price, failed decode or a missing field keeps it
   pending (attempt 677). On restart recovery, a durable `live_loss_settled`
   log record that names its hash but carries NO numeric cumulative total does
   not clear that hash: only a settlement event with a valid total proves the
   hash is inside the total (review b03b0e15).
5. **Count every fee component.** Ethereum: `gasUsed x effectiveGasPrice` plus
   any principal loss. Base (OP Stack): add `l1Fee` and the operator fee too. A
   component the receipt omits is counted at a stated upper bound justified
   against the gas cap, never as zero (attempts 689, 720). Measured on the relay
   research lane 2026-11-09 (moonwell capture tx 0x77259097.. block 53550622):
   relay Base receipts **do** report `l1Fee` (3.36e-9 ETH at gasUsed 0xefbb9)
   but **omit** `operatorFee`/`l2FeesIn11Eth` — require the `l1Fee` leg before
   settling (its absence keeps the receipt pending), and count each further
   omitted component at a bound derived from YOUR OWN signed gas cap: the
   largest measured `l1Fee` 3.58e-8 at 5,074,916 gas scales to 1.55e-8 at a
   2,200,000 cap, so a stated 1e-6 per component carries ~65x headroom — an
   observation fit of the moment was rejected by reviewer 13c85970.
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
   fails closed. The fail-closed flag alone is NOT enough at the cycle
   boundary (review 7ba9c267): the cycle's pre-send persist then clears the
   flag on its first success and sends resume with the loss total of the
   damaged file SILENTLY ZEROED — STOPPED.json was never written because the
   stop was never crossed. Keep the halt until the prior loss history is
   RECOVERED from a durable source (the bot's own append-only log), or
   raise the total to the threshold and write the durable stop marker so the
   halt stays sticky across restarts. A start with no log at all has no prior
   run to lose — but an existing readable, NON-EMPTY log with no valid
   accounting record (only malformed lines) fails closed exactly like an
   unreadable one (review b03b0e15). Only a truly empty (all-whitespace) log is
   a fresh start.
   The recovery rule (review c0654dd1): keep ALL accepted send hashes whose
   settlement is not durably recorded: settle a receipt with a log event
   {type:'live_loss_settled', hash, live_loss_usd}; that event (or a later
   heartbeat) proves the hash is inside the total. The recovered total is the
   LAST total durably recorded (heartbeat or settlement event, in append order).
10. **Prove it.** A small offline test under `scratch/<bot>/` that drives the
    extracted settle/stop functions through: fresh price, failed price, missing
    fee field, crossing 30 USD, restart with `STOPPED.json`, restart recovery of
    a pending receipt spanning many heartbeats followed by a damaged state file,
    a settlement record without a numeric total, a malformed-only log, and an
    accepted send without a valid txHash.
11. **Accepted sends have durable evidence BEFORE the signer call** (review
    69bab952, attempt 800). A pre-send INTENT (trade, wall timestamp, nonce
    baseline) persisted before the signer call, cleared only after a definitive
    rejection or a broadcast reconciled against the chain, closes three crash
    boundaries: (a) a still-valid STALE `state.json` that misses a logged
    accepted hash — reconcile the log with every loaded state before opening
    the send gate (total = max(state, log); never re-pend a settled hash);
    (b) a crash right after broadcast before any log append — only the intent
    proves it; reconcile by nonce plus a bounded receipt scan, or expire with a
    wall-clock bound whose worst case is your signed gas ceiling; (c) a socket
    close/timeout/truncated reply is AMBIGUOUS, not a rejection — keep the
    intent pending.

If your bot shares this code with sibling bots, apply a fix to all of them in
the same session (`pitfalls/copy-reviewed-fix-to-all-bots.md`). The general
review checklist is `pitfalls/paper-review-blockers.md`.
