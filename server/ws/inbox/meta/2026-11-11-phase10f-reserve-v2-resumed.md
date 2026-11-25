# Phase 10f (2026-11-11): the gate bug behind the partial promotion of reserve-dutch-ethereum-v2 is fixed; the bot was resumed and is running

From the human side, in answer to `inbox/meta/2026-11-10-reserve-v2-gate-partial-promote.md` and
`inbox/live/2026-11-10-reserve-v2-partial-promote-sweep.md`. Nothing here needs a decision.

## What happened

`gate promote reserve-dutch-ethereum-v2` (reviewer, about 20:05Z on 2026-11-10) moved the bot to
`bots/live/`, funded 30 USD and then stopped with `executor artifact unreadable`. Two causes, both on
the gate's side:

1. The manifest's `executor:` pointed into the bot's own paper directory
   (`bots/paper/<id>/contracts/...`). The gate moved that directory to `bots/live/<id>/` first and
   read the artifact afterwards, so the path no longer existed.
2. The bot carried a `state/executor.json` copied from the archived `reserve-dutch-ethereum`, with
   that older bot's executor address. `gate-ctl deploy` took it for "already has an executor".

## What changed in the gate (phase 10f)

- `gate promote` reads the executor artifact and `executor_args` before anything moves. An
  unreadable artifact is now refused before the move and the funding.
- An artifact path under `bots/paper/<id>/` is fine: after the move the gate reads the same file
  under `bots/live/<id>/`. Paths under `scratch/` work as before.
- A `state/executor.json` whose address was not created by this bot's own key is not treated as an
  executor, and the gate removes it before it deploys.

## What was done with the bot

The human chose to resume rather than stop: `gate-ctl deploy reserve-dutch-ethereum-v2` deployed the
executor `0x83c6473d9e71d603f83514b4b8f08cafa6437ed0` and started the service (active/running, about
26.3 USD left after the deployment gas). The code is the copy the reviewer passed; nothing was edited.
**Do not stop or sweep it on the strength of the earlier inbox/live note** - that request is
withdrawn (the human moves the note to `inbox/live/done/`).

## For the role files (meta)

- earner.md: when a stopped live bot is copied back from `bots/archive/` to `bots/paper/`, leave
  `state/executor.json` out. It holds the previous bot's executor address. (The gate now removes a
  stale one, but it should not be there in paper.)
- paper-reviewer.md: if `gate promote` ever ends after funding but before the executor is deployed,
  report it to `inbox/human/` as well - the live-operator is only woken by the watchdog, so a note in
  `inbox/live/` alone is not acted on.
