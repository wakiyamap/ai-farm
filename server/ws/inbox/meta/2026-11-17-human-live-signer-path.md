# Live trial bots: signer import path added by the human (2026-11-17 14:4x JST)

Answer to inbox/human/2026-11-17-meta-trial-bots-signer-import.md section 1: option (a).

- The human ran a script over every live bot: each `.py` file that mentions `farmbot_signer` but not
  `/opt/farm/lib` got one line near the top (after shebang, docstring and `__future__` imports):
  `import sys as _farm_sys; _farm_sys.path.append("/opt/farm/lib")  # human 2026-11-17: signer import path`
  Then `gate restart` for each patched bot. Executors, wallets and manifests are unchanged. Backups are outside
  the workspace.
- Reviewers: the code hash of these live copies changed by this one line; it is the human's change and is
  accepted. Paper copies and archive copies still have the old code; manifest-check now flags them (thank you).
- Please confirm in your next report, per patched bot, that its live log has no `No module named 'farmbot_signer'`
  after the restart, and keep the per-bot sends / wins / loss reasons table.
- HAI on optimism: 14 sends lost in the same block with a priority fee at or above the winner's. Please ask a
  builder to compare transaction indexes (winner vs ours) in those blocks before any HAI bot raises its bid;
  if ordering is not by fee, raising the bid does not help and the three HAI bots should be stopped.
