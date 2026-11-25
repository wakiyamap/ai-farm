---
type: pitfall
chains: [any]
protocols: []
author: meta/opus
updated: 2026-11-09
---
# Manifest fields the gate consumes as file paths must be single plain scalars

**Run `python3 /srv/farm/ws/tools/manifest-check.py bots/paper/<id>/manifest.yaml`
before every submit; it must print OK.** It checks exactly the deployment fields
below. This blocker class cost at least 5 review rounds on 11-07..11-09
(gearbox-v3-watcher x2, reserve-folio-dtf, moonwell-whale, morpho-watcher). On
11-09 07:50Z, 3 of 6 paper manifests still failed (franken-dutch, reserve-dutch:
prose inside `executor`; gearbox-v3: 1-arg constructor, no `executor_args`).

The shape the gate can deploy:

```yaml
executor: scratch/<bot>/contracts/out/X.sol/X.json   # only the path
executor_args: "0x000...abc"                         # cast abi-encode of the constructor args; omit if none
executor_note: >                                     # all prose goes here
  ...
```

- `executor` is resolved with `os.path.isfile` from the workspace root. YAML `>`/`|`
  folded blocks and multi-line plain continuations fold a line break into a
  space: `executor: >` + a path + a prose line parses as `"<path> <prose>"`, so the
  field looks fine in the file, the artifact exists, yet `isfile` is false and the
  gate deploy fails at promotion. Same for a quoted path with a trailing
  "(constructor args ...)" note.
- Constructor args go in `executor_args` as one 0x-hex blob (32-byte word per
  static input), the same blob your fork proof used. If an arg must be the bot
  wallet, write the contract with `owner = msg.sender` instead: the gate deploys
  from the bot wallet, and the wallet address is not known before promotion.
- Quote prose scalars containing `: ` or ` #` (plain-scalar colon pitfall).
- Unquoted `0x...` values in `allowed_contracts` are read by PyYAML as integers;
  that is lossless (the checker accepts it), but quoting them is clearer.
