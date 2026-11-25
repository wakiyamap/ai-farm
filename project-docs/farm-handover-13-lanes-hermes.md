# 引き継ぎ書 13: phase 15c（fork / scout のレーン、/health の課金サイクル、farm-hermes、reviewer-claude 1 日 1 回）と 15d（farm.nft で 29486）2026-11-18

本体は `farm/farm-handover.md`。この文書は 15c・15d の変更だけ。バンドルは `farm/phase15c/`（tar sha256 `159db1f3aff8689f2f2d5b13a7d4e8f4c8806d720283d6a1bd8733986dfacdb5`）と `farm/phase15d/`（tar sha256 `bd38d23040f4d0b235cf62bb16f938548c211406bcab8a20e4665600651d416e`）。状態: **15c は 2026-11-18 06:46 JST、15d は 06:52 JST に人間が適用済み**。

## きっかけ

meta の報告（11-17 21:45Z）: research レーン（1 日 100 万 CU）が毎日 18:45Z ごろ尽き、fork の過去ブロック証明が公開ノードに落ちて builder・reviewer が止まる。大口は scout の bsc・avalanche 走査。人間の判断: (a) fork 用の別予算 ＋ (b) scout の読みを絞る。あわせて Pyth Hermes のキー、TOGA は例外を作らない、課金サイクルの見込みを meta に見せる、paper-reviewer-claude を 1 日 1 回に。

## rpc-relay（7 箇所のテキストパッチ）と relay.json

| レーン | 誰 | 1 日の Alchemy CU | 順 |
|---|---|---|---|
| live | bot | 1,500,000（絞らない） | Alchemy → 公開 |
| paper | paper bot | 900,000 | 公開 → Alchemy |
| research | builder・reviewer・meta・ledger-ingest | **700,000**（1,000,000 から） | 公開 → Alchemy |
| **fork** | anvil（ユーザー farmfork） | **400,000** | **Alchemy → 公開**（予算の内） |
| **scout** | Qwen の scout（ユーザー earner） | **300,000** | 公開 → Alchemy |

- レーンは接続元の unix ユーザーで決める（relay.json `lane_by_user` = `{"farmfork": "fork", "earner": "scout"}`）。`/proc/net/tcp` で相手のソケットの uid を引く（接続ごとに 1 回）。URL の `lane=` は、この 2 ユーザーには効かない。ほかのユーザーが `fork` / `scout` を名乗っても research になる。farmgate の送信ソケット（gate・signer）は変えない
- 過去状態の読み取り（6k、800 ブロックより古い）は今までどおり Alchemy 優先
- `GET /health` に `cycle`（`since`・`ends`・`cu`・`lanes`・`projected_cu`・`projected_share`・`alert_85`）と `lane_by_user`。ops.db の rpc_stats から 2 分キャッシュ。ダッシュボードと同じ計算（feed の分は入らない）
- `GET /lane?lane=<x>`: この接続のユーザーと、使われるレーン
- ダッシュボードのチェーン別の表は live / paper / research だけ。fork・scout は「alchemy CU today」とサイクルの `lanes` に出る
- 数字を変えるときは `/etc/farm/relay.json` を直して `sudo systemctl restart rpc-relay`

## farm-hermes（新しいサービス、127.0.0.1:29486）

- Pyth Hermes に人間の API キーを `Authorization: Bearer` で付けて中継する。12f の farm-relayapi をもとにした標準ライブラリのみの実装、DynamicUser、キーは systemd の credential（`/etc/farm/pyth-hermes.key`、root 600、55 文字）
- upstream `https://pyth.dourolabs.app/hermes`。GET だけ。通す道: `/v2/updates/price`（latest・時刻指定）、`/v2/price_feeds`、`/v2/updates/twap`、`/api/latest_price_feeds`・`latest_vaas`・`get_price_feed`・`get_vaa`。`/v2/updates/price/stream` は拒否（終わらないため）。1 日 30,000 回、間隔 0.05 秒、timeout 10 秒（`/etc/farm/hermes.json`）
- **キーは 2 週間の試用（12-02 ごろに切れる）**。切れると Hermes が 401 を返す
- 届くユーザー: harness・earner・farmbot（earner と farmbot は 15d から）
- キーの置き方（表示されない）: `sudo install -o root -g root -m 600 /dev/stdin /etc/farm/pyth-hermes.key` → 貼り付け → Enter → Ctrl-D
- 1 日 30,000 回は全員で共有。bot が毎ブロック呼ぶ作りだと使い切る

## paper-reviewer-claude

- `/etc/systemd/system/farm-paper-reviewer-claude.timer.d/daily.conf`: `OnUnitInactiveSec=24h`（90 分から）。戻すときはこのファイルを消して daemon-reload。適用後の次の回は 11-19 06:13 JST

## decision とメモ

- `decisions/human/2026-11-18-lanes-hermes-toga.md`（レーン、Hermes、TOGA は例外を作らない、reviewer-claude 1 日 1 回）
- `inbox/meta/2026-11-18-phase15c-lanes-hermes.md`（TOOLS.md に hermes の行、scout.md・builder.md にレーンの 1 文、`alert_85` の見張り、lead 248 を dead_end）。このメモには「farmbot が届かなければ promote 前に人間へ」とあるが、15d で解消済み

## install.sh（15c）

- 適用前: 全ファイルの構文、relay のテキストパッチ（7 箇所すべて 1 回だけ一致）、オフラインのテスト 7 件（適用前の relay は 2/7）
- relay と relay.json を入れて rpc-relay を再起動 → `/health` に `cycle` → earner が scout、farmfork が fork、harness が research になることを `/lane` で確認 → signer・watchdog・feed が active。どれかが駄目なら relay と relay.json を戻す
- Hermes: キーがなければこの部分だけ飛ばす（後で再実行）。ETH/USD の latest で 200 を確認、401/403 なら farm-hermes だけ止める。stream が 403、journal にキーが出ないことも確認
- バックアップ: `/opt/farm/bin/.rpc-relay.bak-15c`、`/etc/farm/relay.json.bak-15c`

## 15c 適用時の結果（06:46 JST）

- テスト: 適用前 2/7 → 適用後 7/7。レーン: earner → scout、farmfork → fork、harness → research。signer・watchdog・feed と fork@ 10 本は active のまま
- サイクル: 30.56M CU（11-03 から）、見込み 57.41M、枠の 60.3%、alert_85 false
- Hermes: ETH/USD の latest が HTTP 200（1,805.73 USD、更新データ 631 バイト）、stream は 403、journal にキーなし。届いたのは harness だけ

| ファイル | 適用前 | 適用後（期待値 = 実物） |
|---|---|---|
| rpc-relay | `0fb9481a019f10870ad56aa6c620c88515228c17b988b7157da6f9165c17fe4c` | `323337d8ffe6a46a7ca759101b1f8c823521332a5f990c2448d075fe9581006c` |
| relay.json | — | `5aa7b48b450de921463c812f7af3039a8ac7c85280ac8a142933d9db9509efab` |
| farm-hermes | （新規） | `5c94100cd2c6db6d32e89978060816b48384505a222cf995c797ccff5c2acc87` |

## 15d: farm.nft で earner と farmbot に 29486

- farm.nft（output チェイン）は earner と farmbot に「このローカルポート以外は reset」の許可リストをかけている。15d の後: earner は 53・8000・8003・8545・8546・9001-9009・29483・29484・29485・29486、farmbot は 53・8545・8546・9001-9009・29486
- テキストパッチ 3 箇所（注釈、earner の行、farmbot の行）。ほかは変えない（9013・29483〜29485 は farmbot から閉じたまま）
- install: sha256 が 12f の版と一致するときだけ適用 → `nft -c` → 置いて `nft -f` → 届くかを確認、駄目なら元に戻す。バックアップ `/etc/farm/farm.nft.bak-15d`
- 新しい中継を足すときは、このリストにも足すこと（15c で抜けていた）

## 15d 適用時の結果（06:52 JST）

- earner・farmbot・harness → 29486 届く。farmbot → 29485・9013 は拒否のまま、8545 は届く

| ファイル | 適用前（期待値 = 実物） | 適用後（期待値 = 実物） |
|---|---|---|
| farm.nft | `acc2c1df146dbf4a16a9743791641c2b64175e56c7d13cef1b5a2d74d3e15310` | `7ed9a8b32324c56f977f945be85e3151459e312b0632c63949e5b29804dff559` |
