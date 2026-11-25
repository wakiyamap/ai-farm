# meta 提案 2026-11-06（run e1762e9c）: fork deploy の失敗調査と meta の Bash 権限

## 1. `fork deploy` が一部のアーティファクトで status 0 になる（/opt/farm/bin/fork、ワークスペース外）

- 11-06 だけで earner 3 セッション（de13d8f2, aed4765b, c8bcce4f）が fork 証明を作れず、うち aed4765b は fork 証明なしで fix を提出した。
- 症状: gasUsed が gas 上限に関係なく一定、revert データは空。head でも古いブロックでも再現する（c8bcce4f）。コンストラクタの無い Probe.sol でも失敗し、Dummy.sol は成功。同じものが `forge test --fork-url` では成功。
- 原因は未特定。meta は今回コマンドを一切実行できず、検証できなかった。
- お願い: (a) fork 側の anvil の起動オプション（hardfork / chain 設定。forge は evmVersion cancun でビルドしている）を確認してほしい。(b) `cmd_deploy` が失敗時に gasUsed と `debug_traceTransaction` の最後の opcode を表示するようにしてほしい。再現物: `scratch/aave2-probe/contracts`、`scratch/aave2-probe-bytecode.hex`。まとめ: `inbox/meta/fork-deploy-status0.md`。
- それまでの回避策として、earner.md 3b.2 に「status 0 ならツールをデバッグせず anvil_setCode か forge test --fork-url で証明する」を追記した。

## 2. 今回の meta セッションでは Bash が全面的に拒否された

- 以前の meta セッションでは `kb` / `wiki` は使えて git と python だけが拒否されていた。今回は `kb query`、`wiki write`、`tools/session-report.py`、`date` すら実行できない。
- 影響: KB の行追加、wiki ページの更新、wiki-eval の測定、セッションレポートの追記ができない（追記専用ファイルは Write/Edit では書けない）。今回の変更は測定なしの prompt 編集 1 件だけになった。
- お願い: meta の許可リストに、少なくとも `kb`、`wiki`、`python3 /srv/farm/ws/tools/session-report.py`、`python3 /srv/farm/ws/tools/wiki-eval/run.py`、`git -C /srv/farm/ws/history`、`date` を戻してほしい。

## 3. 参考: モデル名の表記ゆれ

- セッションレポートの model に `qwen3.8-flash-next` と `qwen38-flash-next` が混在している（11-06）。週次のモデル別集計がずれる。harness が model を自動で埋めるか、session-report.py で正規化するかを検討してほしい（meta が python を実行できれば後者は meta でやる）。
