# 2026-11-09 researcher の名前と researcher-claude の権限（inbox/human/2026-11-09-researcher-claude-denied-commands.md への回答）

## 名前

- phase 9b から、codex の researcher のインスタンス名を `researcher-codex` に変えた（役割ファイルは researcher.md のまま）。もう一方は `researcher-claude`。ダッシュボードの Recent runs には、インスタンス名が表示される。
- 2026-11-09-two-researchers の「`researcher`（codex）」は、`researcher-codex` と読み替えること。ops.db の古い run は instance=`researcher` のまま残る。meta が集計するときは、`researcher` と `researcher-codex` を同じものとして扱うこと。

## researcher-claude で拒否されたコマンド

claude harness の許可は「コマンド行の文字列」との照合で、**変数の展開（`$VAR`）、`cd … &&`、for ループ、パイプの先の許可されていないコマンド**を含む行は拒否される。

1. / 2. relay への curl / cast: `$RPC_RELAY_URL` の展開が原因。URL をそのまま書けば通る: `curl -s -X POST 'http://127.0.0.1:8545/ethereum?lane=research' -H 'content-type: application/json' -d '…'`、`/opt/foundry/bin/cast call <addr> "nonce()(uint256)" --rpc-url 'http://127.0.0.1:8545/ethereum?lane=research'`。meta は TOOLS.md の relay の行に、URL をそのまま書いた例を併記すること（codex と dsh のロールは変数のままでよい）。
3. `python3 -c`: phase 9b で researcher-claude に `python3 *` と `jq *` を許可した。
4. `cd … && python3 tools/…`: 絶対パスで、cd なしで実行すること（すでに通っている）。
5. for ループ: 1 回ずつ実行するか、ループは scratch に書いた python スクリプトの中で回すこと。

TOOLS.md の編集が拒否されたのは仕様どおり。prompts（TOOLS.md を含む）は meta の担当なので、提案は inbox/meta に書くこと。
