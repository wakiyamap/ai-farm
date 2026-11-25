# 2026-11-04 セッション報告の欠落と meta の実行権限（inbox/human/2026-11-04-meta-session-logs.md への回答）

phase 6f（2026-11-04 適用）で両方対応した。

## 1. セッション報告

- `logs/sessions/*.jsonl` は追記専用（`chattr +a`）にした。シェルの `>>` と `tools/session-report.py` は動く。ファイル全体を書き直す Write / Edit は失敗し、何も変わらない。common.md の「Session report」にこの旨を明記した。
- harness 側の保証: run の終了時に record-run（root）が、その run_id の行が無ければ `outcome: no_report` の行を追記する。これで「報告が無い run」は欠落ではなく可視の行になる。coverage の計測はこの行を分母に入れてよい（`no_report` は report 無しとして数える）。
- `tools/session-report.py` は採用。TOOLS.md の案内のままでよい。

## 2. meta の実行権限

meta の許可リストに `python3 /srv/farm/ws/tools/*` と `git -C /srv/farm/ws log / show / diff / status` を追加した。コミット系（add / commit / push）は引き続き `wiki write` 経由のみ。全ロール（claude harness）に `python3 tools/session-report.py` を許可した。
