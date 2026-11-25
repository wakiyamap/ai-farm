# 引き継ぎ書 17: phase 15i（fork レーンは Alchemy だけ・上限なし、読み取りの予算、feed、builder の文脈）2026-11-20

本体は `farm/farm-handover.md`。バンドル `farm/phase15i/`（tar sha256 `06892f4ab2afada1c32b9a2b0fab2bd1b9744140dfb6857c531666aa94bb5bd7`）。状態: **2026-11-20 01:51 JST に人間が適用済み**。人間の判断は `farm/ops/2026-11-20-0113.md`・`-0129.md`。

## きっかけ

- 15h の後も fork が `public: HTTP 403 Archive` で失敗（meta ee059752・f5e76c77）。15h の「古い状態は Alchemy だけ」は `is_historical()` が真のときだけで、anvil の読み取りでは偽になっていた。予算内は [Alchemy, 公開]（Alchemy が cooldown 中なら公開へ）、予算超過後は公開だけ
- 人間の判断（11-20）: fork は全部 Alchemy・上限なし。11-24 で締めるので Alchemy の月の枠は使い切ってよい。base の feed のフィルタ上限を上げる
- builder のセッション文脈の古い表示 3 点（meta の builder-queue-stale-entries）

## 変更

| ファイル | 内容 |
|---|---|
| rpc-relay | fork レーンは、メソッド・ブロック・その日の使用量にかかわらず Alchemy だけ（送信の判定の直後で返す）。15h / 15c の fork の分岐は消した。Alchemy が唯一の上流なので、15h の cooldown の例外と 429 の書き換えはすべての fork の読み取りに効く |
| relay.json | `alchemy_daily_cu`: fork 600,000 → 95,200,000（relay は fork に使わない。/health とダッシュボードで「使い切り」に見えないための値）、research 700,000 → 1,500,000、scout 300,000 → 1,200,000 |
| feed.json | `max_log_filters_per_chain` 8 → 16 |
| context/earner | 「修正待ちの paper bot」は review.md の先頭 15 行で最初の decision の行か見出し（`**Decision: fix**`、`decision fix stands`、`## … — fix`）で判定。review.md より新しい bot.py / *.sol / manifest.yaml があれば「再提出済み（reviewer の番）」に分けて表示。「bot のない measured lead」から next_steps が TRIAL BOT PLACED / NOT A BUILD TARGET のものと、paper・live の manifest にある lead（`lead: N`・`lead_id: N`・`leads:N`）を除く |
| context/builder | 「Trial bots live: N / 45」 |

- `is_historical()` が anvil の読み取りで偽になる理由は調べていない（fork では使わなくなった）。research・scout・paper の古い状態の扱いは変えていない
- meta 宛てメモ `inbox/meta/2026-11-20-phase15i-fork-alchemy-budgets.md`: 上の内容、OP Stack の損失上限の答え、`gate promote` の小数、avalanche の scout の答え

## install.sh

- 適用前の 5 ファイルの sha256 を参考値（11-20 01:42 JST に送られた tar の中身）と並べて表示。適用はパッチ（1 回だけ一致）と cfg（今の値が期待どおり）で決める
- オフラインのテスト 16 件（適用前 7/16。fork 5 件・文脈 4 件が落ちる）。15c / 15e / 15h の relay の挙動のうち残すもの（research・scout・watch・live・送信・lane の割り当て）も同じテストで確かめる
- バックアップ `<dir>/.<name>.bak-15i`。rpc-relay を再起動 → /health で research 1.5M・scout 1.2M を確認 → 15 秒待つ（fork@）→ farm-feed を再起動 → relay・signer・watchdog・feed が active。駄目なら全部戻す
- 確認: farmfork から arbitrum の head−400 と head−400,000 の WETH の残高（どちらも以前は公開ノードに行きえた）。builder の文脈の変わった節の先頭を表示

## 適用時の結果（11-20 01:51 JST）

- 適用前の 5 ファイルはすべて参考値と一致。テスト 7/16 → 16/16
- /health で research 1,500,000・scout 1,200,000。relay・signer・watchdog・feed は active。feed は全チェーン再接続
- 確認: farmfork のレーンは fork。arbitrum の head−400（525,672,627）と head−400,000（525,273,027）の WETH の残高を両方返した
- fork@ は 10 本とも active（15 秒待ったので fork@bsc の取りこぼしなし）
- builder の文脈: 修正待ちは gmx-buyback-slow-arbitrum・peapods-arb-arbitrum・silo1-liq-arbitrum の 3 本。再提出済みに bim-harvest-base と peapods-arb-base（どちらも manifest.yaml が review.md より新しい）。試行は 30 / 45
- 残った漏れ: measured lead の一覧に lead 271（folio-bid-base、live）が残る。next_steps が `BOT PLACED`（TRIAL なし）で、manifest に lead の番号もないため。lead 302（sperax、scout が「bot にする価値なし」）も残る。どちらも meta に next_steps の書き方を揃えてもらえば消える（次の直しの候補: 条件を `%BOT PLACED%` に広げる）

| ファイル | 適用前（期待値 = 実物） | 適用後（期待値 = 実物） |
|---|---|---|
| rpc-relay | `1c5e781b34c9ae725421222d9b1ec070e2332dd33608c5a39917af818271369e` | `aeb3fb3c1d4290d1a8a05ab50c58679a60741e9b4d8df56754c150c17e6130e4` |
| context/earner | `0412faf8660d0a56c339ef8ccb06ee2a0c7e4cee6e6a2d9be7d574d36f8f597e` | `fc8c8527fa998c8ec5dc8beb0f7ea5c7828fa9c66ee207ddb676844defa98ebf` |
| context/builder | `7aa638a2752c6fa879071c5553104e9a7d29f89d6e182d550cfd9661b4bd76b5` | `461b290df62865133e8f3e840b3417cd82bc0393c930dd9155fc5ed835c7190c` |
| relay.json | `ba248582d9d64c03c5a9cb04b0d70be598aeec52756bde26365e09016fc9c9b3` | `d7f43dd415b1532d058da5d326a6c4cbb9085c86edc2c6b1948321b779b4336f` |
| feed.json | `915c5cb752381d355e4c2a9875567d3118d0e5f4fb4bff85fa65143babf7248c` | `77a5b58f39788dde552cb3ff9dbae0276c5c4c0f039cb081e00af61265af4ccb` |
