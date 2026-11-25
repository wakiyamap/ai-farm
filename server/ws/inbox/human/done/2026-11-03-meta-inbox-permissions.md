# 提案: inbox/meta のファイル権限（meta から読めない）

- 送信: meta / opus, run e3456e9c73d9468591448366beddf9b5, 2026-11-03
- 種別: インフラ（ホスト権限設定。meta の権限では変更できないため提案します）

## 事象
- `inbox/meta/ledger-query-field-truncation.md` を Read すると EACCES になり、meta から読めません。
- セッション報告によると、earner（`inbox/meta/earner-file-permissions-pitfall.md`）と paper-reviewer（KB の reviewer outcome 不一致、プロセスに関するメモ）も inbox/meta に書いたことになっていますが、これらのファイルは Glob にも出てきません。
- 同じ根本原因と思われる事象が bots/paper にもありました。earner のファイルが 0600 で ACL mask が `---` だったため、paper-reviewer が morpho-watcher-base を読めず、レビューが 1 サイクル無駄になりました（attempts:4、attempts:7）。

## 提案
1. `/srv/farm/ws` の共有ディレクトリ（inbox/*, bots/paper, scratch, claims）に、グループ farm の default ACL（`d:g:farm:rX` と `d:m::rwx`）を設定する。
2. もしくは、各ロールのセッションの umask を 002 か 022 にする。
3. この 2 つが設定されるまでは、上記の inbox/meta のファイルの権限を手動で 0644 に直していただけると助かります。

## 影響
meta が inbox/meta を読めないと、ツールの不具合報告に対応できません。今回は session log の notes から内容を推測しました。
