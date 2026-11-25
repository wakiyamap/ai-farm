# git: use the history repo (human, 2026-11-11)

Your last two sessions reported "git denied". The denied command was `git -C /srv/farm/ws log ...`. /srv/farm/ws itself is not a git repository. Allowed and working: `git -C /srv/farm/ws/history log|show|diff` (per-run snapshots of the workspace) and `git -C /srv/farm/ws/wiki log|show|diff`. You cannot commit; the harness snapshots your changes into history after each run. Please fix the wording in meta.md / TOOLS.md if it points at the workspace root.
