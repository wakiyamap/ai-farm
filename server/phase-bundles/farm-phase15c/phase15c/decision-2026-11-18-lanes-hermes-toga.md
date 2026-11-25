# 読み取りの予算の分け方、Pyth Hermes、Superfluid TOGA（人間の判断 2026-11-18）

meta の報告 `inbox/human/2026-11-17-meta-phase15-lane-budget.md` への答えです。phase 15c で入れました。

## 1. research レーンを分ける（meta の案 (a)＋(b)）

- relay に **fork** と **scout** のレーンを足しました。どちらも、どのレーンを名乗っても relay が接続元の unix ユーザーで決めます（URL の `lane=` では選べません）。
  - **fork**（anvil の fork、ユーザー farmfork）: 1 日 400,000 CU。予算の内は Alchemy を先に使うので、research が尽きても fork の過去ブロックの証明は止まりません。
  - **scout**（Qwen の scout、ユーザー earner）: 1 日 300,000 CU。今までの research と同じく公開ノードが先で、Alchemy は予算の内だけ。
  - **research**（builder・reviewer・meta・ledger-ingest）: 1 日 700,000 CU（1,000,000 から下げた。scout が抜けた分）。
- scout は予算が尽きると公開ノードだけになります。scout.md の「`public:` のエラーや空の対照は `unclear`」はそのまま守ってください。
- 数字は `/etc/farm/relay.json` の `alchemy_daily_cu` で、人間が変えます。
- **Alchemy の課金サイクルの見込み**は `curl -s http://127.0.0.1:8545/health` の `cycle` に出ます（`projected_cu`、`projected_share`、`alert_85`）。meta は `alert_85` が true になったら inbox/human に知らせてください（判断 2026-11-18-trial-slots-20 の 5）。

## 2. Pyth Hermes

- 人間が Pyth の API キーを取りました（**2 週間の試用。12-02 ごろに切れる**）。キーは farm-hermes が持ち、誰にも見せません。
- `https://hermes.pyth.network/<path>`（または `https://pyth.dourolabs.app/hermes/<path>`）の代わりに `http://127.0.0.1:29486/<path>` を呼んでください。読み取りの価格の道だけ（`/v2/updates/price/latest`・`/v2/updates/price/<時刻>`・`/v2/price_feeds`・`/v2/updates/twap`・`/api/latest_price_feeds` など）。ストリーム（`/v2/updates/price/stream`）は通しません。
- これで lead 250（arbitrum の flat_money_v2 executeOrder）と、Pyth の pull 型オラクルの keeper 系を試せます。試用が切れた後に続けるかは、取れた額を見て人間が決めます。キーが切れると 401 が返ります。

## 3. Superfluid TOGA の PIC 席（lead 248）

- **例外は作りません**（meta の推奨どおり）。上限 4 USD/日に対して、L・ホールディング枠・watchdog のすべてに例外が要るためです。lead は `dead_end` にしてください。

## 4. paper-reviewer-claude は 1 日 1 回

- codex 製の bot がないので空振りしていました。前の回が終わってから 24 時間おきにします。builder-codex が bot を出したら、審査が最大 1 日遅れます。急ぐときは `inbox/meta` に書いてください（人間が手で走らせます）。

## meta へ

- TOOLS.md に `hermes` の行を足してください（`relayapi` の行の後ろ）。relay の行に fork / scout のレーンと `/health` の `cycle` を 1 文で。earner.md は上限に近いので、先に縮めてください。
- scout.md と builder.md に、レーンは relay が決めること（`lane=` を変えても変わらない）を 1 文で。
