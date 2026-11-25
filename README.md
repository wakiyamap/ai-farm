# Farm — public records

Farm was an autonomous on-chain earning system: several AI agents found
opportunities, wrote bots, reviewed them on mainnet forks, and promoted them
to live with real funds under hard limits enforced in code. It ran from
2026-11-03 to 2026-11-24 on one Ubuntu host and was shut down because it did
not earn more than it cost. Everything is published here except private keys,
API keys/tokens, host/network identifiers, and third-party code the agents
downloaded while researching.

（日本語）AIエージェントにオンチェーンで稼ぐbotを作らせ、審査させ、本番で動かした
「Farm」の全記録です。2026-11-03〜11-24 の3週間運用し、運用費に届かずたたみました。
秘密鍵・APIキー・ホスト名とIPアドレス、調査中にエージェントが落とした他者のコード以外は
すべて公開しています。

## Layout

| Path | Contents |
| --- | --- |
| `server/ws/wiki/` | Wiki the agents maintained |
| `server/ws/kb/knowledge.db` | Knowledge base (SQLite): leads, attempts, verdicts |
| `server/ws/ledger/ledger.db` | On-chain event ledger (SQLite) |
| `server/var-lib-farm/ops.db` | Agent run records (SQLite): duration, tokens, cost |
| `server/var-lib-farmgate/` | Gate and signer logs, PnL ledger, account index → address map |
| `server/ws/bots/archive/` | Every bot that was built: code, manifest, review, stop PnL |
| `server/ws/scratch/` | The agents' own working notes only (see below) |
| `server/ws/decisions/`, `server/ws/inbox/` | Human decisions and agent ↔ human messages |
| `server/prompts/`, `server/runners/` | Role prompts and the assembled prompts |
| `server/opt-farm/`, `server/etc-farm/`, `server/systemd/`, `server/sudoers.d/` | Code and config: gate, signer, watchdog, relay, feed, fork, dashboard |
| `server/phase-bundles/` | Change bundles, phase 6–16 |
| `project-docs/` | Spec, handovers, ops log, wind-down (the human-side records) |
| `tools/` | The redaction scripts used to produce this repository (host and operator names are read from a private file that is not included) |

## What was redacted or left out

- The BIP-39 seed and anything derived from it (never copied; the derived
  private keys were checked for by exact match and none were found)
- API keys and tokens (Alchemy, Etherscan, Relay, Pyth Hermes, Blockscout, LLM harness credentials)
- Host name, LAN/tailnet addresses, admin user name
- Most of `ws/scratch/`: the agents downloaded verified contract sources, cloned
  protocol repositories and site bundles there while researching. That is other
  people's code, so only the agents' own top-level notes (`*.md`, `*.log`,
  `*.py`, `*.json`, `*.txt` up to 1 MB, minus contract-source dumps) are included.
- The Python packages vendored in `/opt/farm/pylib` (pycryptodome, pydantic and
  others): they are other people's code. `server/opt-farm/pylib-packages.txt`
  lists them with versions so the code can be set up again.

Redacted spots read `<REDACTED>`, `<REDACTED_SECRET>`, `<lan-ip>`, `<tailnet-host>`,
`farm-host`, `admin`. Wallet, bot and executor addresses are kept so every
transaction can be followed on an explorer.

`.git` histories of the workspace snapshots and the wiki are not included (they
predate redaction).

## Querying the databases

```sh
sqlite3 server/ws/kb/knowledge.db '.tables'
sqlite3 server/var-lib-farm/ops.db 'SELECT * FROM sqlite_master'
```

## License

- Software (everything under `server/opt-farm/`, `server/etc-farm/`, `server/systemd/`,
  `server/sudoers.d/`, `server/phase-bundles/`, bot code in `server/ws/bots/`, and
  `tools/`): MIT, see [LICENSE](LICENSE).
- Records and documents (wiki, `project-docs/`, inbox, decisions, reports, logs and
  the SQLite databases): CC BY 4.0, see [LICENSE-docs](LICENSE-docs).
- Third-party components keep their own licenses. `server/opt-farm/lib/rustxng.d/`
  holds the notices of an AGPL-3.0 component whose binary is not included.

No warranty. The bots here traded with real funds; running them can lose money.
