> Farm の「今の状態」。新しい会話は最初にこの文書だけを読む。判断のたびに丸ごと置き換える（短く保つ。経緯は書かない）。項は 1 件 1 ファイルで `farm/ops/<YYYY-MM-DD>-<HHMM>.md`（JST）。古い記録は `farm/farm-ops-log.md`、仕組みは `farm/farm-handover.md` と `-2`〜`-24`、たたむ手順は `farm/farm-wind-down.md`。

# Farm の今の状態（2026-11-25 09:50 JST）

## 状態

- **Farm はたたみ終えた**（11-24 16:54 に人間が判断。エージェント停止、paper 閉じ、live 全停止・sweep、出金を実施。サービス停止は 11-25 01:08 に残りを止めて完了）。farm-*・fork@*・rpc-relay*・ledger*・agent@*・bot@*・paper@* は active も enabled も 0（farm-acl-fix.timer と farm-nft も止めた）
- qwen-server は Farm の外（16e で外した）

## 今やっていること: 記録の公開（11-25 人間の判断）

- 記事は note、データは GitHub。伏せるのは秘密鍵、API キー・トークン、サーバー・ネットワーク情報。他者が作ったもの（scratch のソースの写しや clone、同梱の Python パッケージ、他者のドキュメント）は公開しない。アドレスと所見の記述は残す
- 記事の下書き（Claude Docs）: https://claude.ai/artifact/26Bdva5c9YiHGZUthA9tK9 。[要記入]: 最終的に戻った額、全期間の総費用、原典記事とリポジトリの URL
- サーバー側のパック: `~/farm-public-server.tgz` 105 MB、sha256 ce89a61e…eea6（`farm/ops/2026-11-25-0900.md`）。木は `/tmp/farm-public`
- **project-docs**: claude.ai のデータのエクスポートの projects.json から取り出す。人間がエクスポート待ち → `bash ~/tools/add_project_docs.sh <projects.json>` で project-docs・README・tools/ を足して固め直す（`farm/ops/2026-11-25-0950.md`）
- 運用者の名前（ホスト名・GitHub ハンドル・法人名）は `~/tools/identities.tsv` にだけある。**公開しない、Project にも置かない**。sanitize.py は `--identities` で読む
- スクリプトと README は `farm/publish/`

## やり残し

- GitHub で公開する前に、記事とリポジトリのどちらにも本人や法人に繋がる名前が残っていないか確かめる（identities.tsv の名前は置き換え・検出される。それ以外の名前は目で）

## 期日

- 12-18 ごろ: Blockscout Builder の更新（たたむ手順の 6 で解約済みか確かめる）
