---
type: method
chains: [base, arbitrum, ethereum, bsc, polygon, avalanche, optimism, hyperevm, elysium]
protocols: [any]
---
# One-shot leftovers: take a takeable leftover once, even if it never recurs (decision 2026-11-14-oneshot-leftovers-idle-pull-oracle, item 1)

**Conclusion first:** a position (or any anyone-can-take state) that has stayed takeable for **10 minutes or more** and is **still takeable at head** is taken once, by a dedicated one-shot bot, even if the same shape never happens again. The "1 USD/day floor" and the "EV above CU cost" rule (decision 2026-11-12-morpho-stop-researcher-runs item 6) do **not** apply to it; it is judged by one net figure instead. Source: the decision file (Japanese; it wins if this page disagrees). The lines 10 min / 10 USD / 48 h / 2 bots are the human's rough lines.

Trigger case: attempts 1210 (Base Morpho, wbCOIN, collateral 1,504 USD, nominal profit 57 USD, untaken >= 1.8 h) was recorded as "one-shot under the floor" only. Under this rule it is re-checked at head and, if it qualifies, sent through the flow below; if already taken, one `attempts` row and done.

## Conditions (all must hold, else no bot)

1. **Fork proof at head**: on the fork reset at (near) head, farm's executor takes it and the **bot wallet balance rises** (success tx), and a no-profit call **reverts** (guard tx). Both hashes go into `fork_evidence`.
2. **Net >= 10 USD**: net = wallet increase - (executor deploy gas + execution gas + sweep gas), all at the current base fee.
3. **Real exit**: collateral is valued by what an actual pool pays for it on the fork, never the oracle price. Collateral with no exit (USR / RLP on Base, attempts 1210) is out.
4. **Why it is still there, in one line.** Where fast takers operate, a leftover usually has a reason: check collateral transfer restrictions / pause / blacklist, a stale or frozen oracle, liquidation permissions (role, whitelist). If the reason stays "unknown", do not submit. Example: lead 174 (ethereum Morpho ynETHx/msETH market, attempts 1215): a direct `Morpho.liquidate` with textbook params and `accrueInterest` both revert (panic 0x11) at the reset tag, so nobody can take it; that is the reason, and it is not a takeable leftover until a liquidate succeeds on the fork. A protocol bug that makes funds claimable is never a one-shot: security finding to `inbox/human/`.
5. **Minimum capital**: only what is needed (gas only if principal comes from a flash loan or callback). Per-bot 400 USD, L = 50 USD and every other limit unchanged.
6. **Separate id** `oneshot-<target>-<chain>`; the README starts with the word "One-shot" (単発).

## Flow

1. **earner**: proves it on the fork and places it in paper **in the same session** that found it. It does not wait in paper for an opportunity.
2. **paper-reviewer**: reviews it first in the next run. Fork reproduction + the conditions above suffice to `promote` (no detection history, no CU-vs-EV test, no per-occurrence 30-day table). If the chain's intermediate wallet lacks funds, write the needed amount to `inbox/human/`.
3. **bot**: after one capture, or once the target is gone, sends nothing more and idles.
4. **earner or paper-reviewer**: when it is captured or gone, write `inbox/meta/` (bot id, tx hash or evidence it is gone). **meta** forwards to `inbox/human/`; the human runs `gate stop`.
5. Not captured **48 h after promotion**: same route, recommend the stop.

At most **2 one-shot bots live** at a time, separate from the 2 next-block trial bots.

## Leftover measurement from now on

Crash post-mortem step 1-3 (`methods/crash-postmortem.md`) and every later leftover measurement check each leftover against the conditions above, instead of ending with "under the floor, recorded only".
