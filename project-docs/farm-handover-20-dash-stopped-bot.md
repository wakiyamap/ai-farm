# 引き継ぎ 20: 止めた直後の「no baseline」警告を消す（phase 15l、2026-11-21 21:55 JST 適用）

## 症状

`gate-ctl stop` で bot を止めるたびに、ダッシュボードと brief に `▲ <bot>: no baseline in pnl.json, the live-loss stop cannot judge it` が出ていた（11-21 21:45 人間の指摘。fli-arb-polygon・cv3-buy-polygon を止めた後）。

## 原因

farm-dash は `gate-ctl status`（約 900 CU）を最大 5 分キャッシュし、pnl.json は毎回読み直す。`gate stop` は sweep の時点で pnl.json からその bot の baseline を消す。そのため最大 5 分、古い status にまだ live として残る bot に baseline がなく、`live_loss()` が「no baseline」と出していた。watchdog の同名の警告は `bots/live/<bot>` があるときだけ出すので関係ない。

## 変更（farm-dash だけ、テキストパッチ 2 か所）

1. `gate_status()`: gate.log の (mtime, size) をキャッシュと一緒に覚え、変わっていたらキャッシュを捨てて取り直す。gate.log には promote・fund・deploy・sweep・stop が 1 行ずつ足され、`gate-ctl status` は書かない。止めた bot・新しく上がった bot が次の更新ですぐ反映される。gate の出来事 1 回につき status 1 回分（約 900 CU）増える（1 日数十回）
2. `live_loss()`: baseline がなく `bots/live/<bot>` もない bot は飛ばす（止めた直後）。live なのに baseline がない bot は今までどおり警告する

gate-ctl・pnl.json・watchdog・bot には触れない。

## 適用（11-21 21:55 JST）

- 人間が `~/p15l/phase15l` から `sudo ./install.sh`。テスト 6/6、farm-dash は farmgate で動き `/srv/farm/ws/bots/live` を見られる。brief に「no baseline」の行なし
- farm-dash の sha256: 前 `cc050e4f…4bb7`（15k の後）→ 後 `ae04cc68f4fd22853f43d7885e630131d6f619d9c385cf56e1f48049db046c42`（期待値 = 実物）
- ダウンロードした tgz の名前は `Phase15l.tgz`（先頭が大文字）になっていた。中のディレクトリは `phase15l`

## ファイル

- バンドル: `farm/phase15l/`（patch-15l.py、test-15l.py、install.sh）。tgz の sha256 `1a1444f5bf9a2e1158df28d4c5a4596f837b71a0e8411a3f9221ffc0fa03766d`
- 戻し方: `cp -a /opt/farm/bin/.farm-dash.bak-15l /opt/farm/bin/farm-dash && systemctl restart farm-dash`
