# 引き継ぎ書 19: phase 15k（bot が稼いだ USDC を sweep で利益として数える）2026-11-21

本体は `farm/farm-handover.md`。バンドル `farm/phase15k/`（tar sha256 `ed2029f00b0b88e737432071c1e5d4934e2ab75bf2b51d004a49def109824dd6`）。状態: **2026-11-21 08:20 JST に人間が適用済み**（1 回目の 08:18 は下の理由で止まり、何も変わらなかった）。

## きっかけ

- oneshot-bundles-rebalance-ethereum（ETH だけで 30 USD を入れた one-shot）が 34.61 USDC を稼ぎ、11-21 07:41 JST に人間が `gate-ctl stop` した。お金は中間 wallet に戻ったが、ダッシュボードでは sweep が −3.73 USD、Today's loss が 4.7 になった
- 原因: gate の sweep は USDC の損益を `baseline_usdc`（gate が入れた USDC の元本）に対してしか付けない。USDC の元本がない bot の USDC は `sweep_usdc` の `usd: null` になり、native の側（使ったガスで減った ETH）だけが損益として `realized_usd` に入った。1 日の損失上限の判定もこれを損として数えていた。`settle_usdc_in_flight` にも同じ穴（元本のない bot だと KeyError も）

## 変更

| ファイル | 内容 |
|---|---|
| gate-ctl（2 箇所） | gate が native で入れた bot（`baseline` にある）で、そのチェーンの USDC の元本がなければ、USDC の元本を 0 とみなす。戻した USDC は全部利益。sweep と settle_usdc_in_flight の両方。gate が一度も入れていない wallet（`baseline` にない）は今までどおり付けない |
| farm-dash（3 箇所） | 「Swept PnL」の合計と 14 日のグラフが、`sweep` に加えて `sweep_usdc`・`sweep_usdc_inflight`・`sweep_usdc_fix` の損益も足す |
| fix-15k.py（1 回だけ） | gate.log に `sweep_usdc_fix`（+34.6142 USD）を 1 行足す。pnl.json の日がまだ 2026-11-20（UTC、09:00 JST まで）なら `realized_usd[oneshot-bundles-rebalance-ethereum]` を −3.7294 → +30.8848 に直す。日が変わった後は gate.log の行だけ。再実行しても二重にならない |

- チェーンには何も送らない。gate-ctl は呼ばれるたびに読み込まれるので再起動は要らない。farm-dash は再起動

## install.sh

- gate-ctl（参考値 = 11-21 07:51 JST に送られた実物）と farm-dash（15j 版）の sha256 を並べて表示。適用はパッチで決める
- オフラインのテスト 7 件（適用前 4/7）。gate-ctl はチェーンの呼び出しを全部偽物にして sweep を通す。fix-15k.py は同じ UTC 日・日が変わった後・再実行
- fix-15k.py の check を表示してから入れる。バックアップ `.gate-ctl.bak-15k`・`.farm-dash.bak-15k`。`gate-ctl status` が通ることを確かめ、fix-15k.py を farmgate で実行、farm-dash を再起動して brief の数字を表示。駄目なら 2 つを戻す
- **落とし穴**: install.sh は fix-15k.py を farmgate で実行するので、展開した場所が farmgate から読めないと `Permission denied` で止まる（ホームの `~/p15k` は読めなかった）。/tmp に展開して実行した。次のバンドルからは、farmgate で動かすスクリプトを読める一時ディレクトリに写してから実行する

## 適用時の結果（11-21 08:20 JST、/tmp/p15k から）

- 適用前の 2 ファイルは参考値と一致。テスト 4/7 → 7/7。`gate-ctl status` は通った
- fix-15k.py: gate.log に `sweep_usdc_fix`（+34.6142）、pnl.json の `realized_usd[oneshot-bundles-rebalance-ethereum]` −3.7294 → +30.8848（UTC の日はまだ 11-20）
- brief: daily loss 0.97（morpho-eth-base の分だけ）、`swept today +29.9126 · swept all time +8.4555`（直す前は −26.16）

| ファイル | 適用前（期待値 = 実物） | 適用後（期待値 = 実物） |
|---|---|---|
| gate-ctl | `b8fded9fd31c403aad5209af9e3bf0b9d562dc98a90ea72cac43e7b88f11e7d8` | `4b32c23d18c6bfd02e4eefb0b1baadeb20a12b5cd7ed6e7c84d35144c0d285b6` |
| farm-dash | `b366e5e42a2b8daa3f81549cded0506006d3b406485fafbe000b39a47fab85fe` | `cc050e4fe3baf12b160c370581fe463d4194f3bcc266f1bcc5edf12ff9ae4bb7` |
