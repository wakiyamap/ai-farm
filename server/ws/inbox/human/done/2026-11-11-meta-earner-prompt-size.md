# earner プロンプトのサイズ超過: 対応済み (meta d14035aa, 2026-11-11 10:5xZ)

原因: 前回の meta 実行 (35f952d9, 08:13Z) で TOOLS.md と earner.md に追記した結果、earner の組み立て後プロンプトが 61,377 バイトとなり上限 60,000 を超えました。今日 08:13Z 以降、earner の約 37 セッションが起動直後に失敗しています (no_report)。申し訳ありません。

対応:
- relay / fork / ledger add-source / gate の詳細と日付付きの経緯を、そのまま wiki `infra/relay-reference.md` に移し、TOOLS.md の各行は要点だけに短縮 (24,097 → 17,347 バイト)。
- earner.md から過去事例の逸話を削除 (21,298 → 19,393 バイト)。ルール自体は変えていません。
- 新ツール `tools/prompt-size.py`: role ごとの組み立てサイズを表示し、56,000 を超えると exit 1。role ファイルや TOOLS.md を編集したら毎回実行します (TOOLS.md に記載)。

現在の組み立てサイズ (common + role + TOOLS):
- earner 52,722 (余裕 7,278)
- paper-reviewer 42,483 / live-operator 37,170 / meta 35,968 / researcher 37,008

assemble-prompt の MAX_BYTES は暫定で 64,000 になっていますが、60,000 に戻していただいて問題ありません。

提案 (任意): researcher も TOOLS.md を編集できるため、assemble-prompt が 56,000 を超えた時点で inbox/meta/ に警告を書くようにすると、次の超過を起動失敗の前に検知できます。
