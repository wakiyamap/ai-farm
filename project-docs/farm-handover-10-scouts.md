> Farm 仕様書の続き（10 個目）。本体は `farm/farm-handover.md`。この文書は phase 14b・14c（Qwen の scout 4 本と候補の待ち行列）を扱う。
> 状態: **14b は 2026-11-17 04:36 JST、14c は 05:2x JST に人間が適用済み**。本体の表にはまだ足していない。**11-22 17:18 JST に TVL の下限を 10 万 → 2.5 万 USD に変更**（下の「変更履歴」）。

# phase 14b・14c: scout と候補の待ち行列

## 何のためか

新しい割り当て（11-17 04:10）の後半。Qwen を「作り手」から「数を打つ下調べ」に移す。scout は自分で対象を選ばない。スクリプトが列挙した候補を 1 件ずつ、決まった手順で測り、数字と判定を残す。良い結果は `measured` の lead になり、builder（14a）が作る。

## 構成（14c 適用後）

| 項目 | 内容 |
|---|---|
| instance | `scout-1` 〜 `scout-4`（roles.conf: `scout-N  scout  dsh  qwen3.8-flash-next`）。実行ユーザー earner、llama-server の 4 枠（`-np 4`）を 1 本 1 枠 |
| 役割ファイル | `roles/scout.md`（14c 版 sha256 `b7accc523f0cd6296b065ba7f45f325c5aa344baae260ed88b038046ec307d0b`、その後 meta が attempts の outcome の書き方を直した（判定は reason の先頭、outcome は `lead_recorded` / `dead_end_recorded`）。組み立て後 37,847 bytes） |
| セッション | **35 分で打ち切り**（14c。`RuntimeMaxSec=35min`、`SESSION_MAX_MIN=35`。14b は 20 分）。scout.md で「開始から 25 分で、途中でも書く」「標本は最大 20 件、合計は 1 つの問い合わせで」。前の回が終わって 1 分後に次（`farm-scout@N.timer`）。`ExecCondition`（Qwen が答える、かつ待ち行列が空でない）を満たさなければ始めない。10 分ごとの暦の発火は保険 |
| 待ち行列 | `/srv/farm/ws/scout/{queue,doing,done}`（harness:farm 2775、farm の既定 ACL）。ファイル名 `<段>-<日数>-<id>.json` で、名前順が作業の順 |
| 候補の取り出し | `/opt/farm/context/scout`（python。14c 版 sha256 `debc1442b561f21150ec76a1e582128ede446826fdcc6742f892337980509994`）: 名前順の先頭を `doing/<id>.json` に rename（原子的）、run_id を書き、候補と種類ごとの手順（標本の形）を出す |
| 閉じる | `/opt/farm/bin/scout-done <id> --verdict <v> --line "..." --kb ...`: `doing` → `done`（判定は pays_strangers / role_gated / no_reward / unpaid / unclear / not_found / aborted） |
| 列挙 | `/opt/farm/bin/scout-enum`（`farm-scout-enum.timer`、起動 10 分後と 2 時間ごと、earner で実行、自分では RPC を呼ばない）。手で回すときは `sudo systemctl start farm-scout-enum.service` |
| ExecCondition | `curl -sf -m 3 http://127.0.0.1:8003/v1/models >/dev/null && ls /srv/farm/ws/scout/queue \| grep -c json >/dev/null`（最初は `grep -q` で、`ls: write error: Broken pipe` が journal に出ていた。11-17 04:4x に人間が sed で直した） |

列挙する候補（段の順）:

1. `trial`: ethereum 以外で `blocked_infra` の lead（試行の候補の確認）
2. `actor`: `ledger top --days 7` の上位 15 アドレス（安いチェーンと ethereum）のうち、KB の `actors` にないもの
3. `protocol`（安いチェーン）/ 4. `protocol`（ethereum）: DefiLlama の `/protocols` のうち、farm のチェーンで **TVL 2.5 万 USD 以上**（`MIN_TVL`。11-22 までは 10 万）、KB の `protocols` にないもの（slug と名前の両方で照合、`-` は `_`）。CEX・Chain・Canonical Bridge は除く。新しく載ったものから
5. 手で足す候補: `5-00000-<id>.json`（`id`・`kind`・`chain`・自由文の `steps`）

- 待ち行列の上限 600、1 回の追加は 250 まで。最初の列挙（11-17 04:36）: trial 21・actor 58・protocol 1,525
- `doing/` に 45 分以上残ったものは待ち行列に戻し、3 回目で `done/` に `aborted`
- DefiLlama のチェーン名の対応: Ethereum / Base / Arbitrum / BSC・Binance / Polygon / Avalanche / OP Mainnet・Optimism / Hyperliquid L1・HyperEVM。elysium は対象外

scout が書くもの: `protocols` 行（kind protocol）、pays_strangers なら `measured` の `leads` 行、`actors` 行（kind actor）、trial は lead の更新（`TRIAL CANDIDATE:`）、毎回 `attempts` 1 行、`scout-done`、セッション報告（outcome は scouted / no_candidate / aborted。meta が session-report.py に role scout を足した）。bot は作らない、fork は使わない、送信しない。

## 実際の動き

- 14b（20 分）: 最初の 8 回のうち 7 回が時間切れで何も書けなかった。清算の lead の数百件を 1 件ずつ手で計算していた
- 14c（35 分、標本）の後: 20:27Z 以降の回は全部 `success`。06:31 JST の時点で done/ 12 件、多くが pays_strangers（base の Aave v3・Morpho・Compound v3・Moonwell・exactly、aave-v4 など）
- 11-22 午後: TVL 10 万以上の候補を使い切り、待ち行列 0。ExecCondition ではじかれて毎分 `no_report`（`exec-condition`）がセッション報告に並んだ（害はない）。ethereum の protocol は名前順に s 付近まで来ていた

## 変更履歴（バンドルを使わない手の変更）

- **11-22 17:18 JST**: `/opt/farm/bin/scout-enum` の `MIN_TVL = 100_000` を `25_000` に（人間が sed で 1 行置き換え）。バックアップ `/opt/farm/bin/scout-enum.bak-tvl25k`。直後に手で列挙して待ち行列 250 件（1 回の上限）。理由: 候補切れ。小さいプロトコルほど相手がいない。戻し方: `sudo cp -p /opt/farm/bin/scout-enum.bak-tvl25k /opt/farm/bin/scout-enum`

## 切り替え

- `agent@earner-local` と `agent@earner-measure` は stop して disable（unit と earner.md は残す）
- builder（14a）は今のまま。scout の `measured` の lead を builder.md の 1 の 5 で取る

## バンドル

- `farm-phase14b.tar.gz` sha256 `9063b9ef6ee045321730b1eaaeb48332734cda96f02162802b68f6517b667769`（install.sh は 74 行目の `ls | head` で止まり、残りは手で行った。この Project の install.sh は直してある）
- `farm-phase14c.tar.gz` sha256 `13223a45f862e7949a2d018899a8b49a7acf15dd6754fdcd4f573ad2fdec5e22`
- meta 宛て `inbox/meta/2026-11-17-phase14b-scouts.md`
- この Project の `farm/phase14b/scout-enum` は 14b の版（`MIN_TVL = 100_000`）のまま。サーバーの版とは違う

## 止め方・戻し方

- 止める: `sudo systemctl disable --now farm-scout@{1,2,3,4}.timer farm-scout-enum.timer`
- 戻す: 上に加えて `sudo systemctl enable --now agent@earner-local agent@earner-measure`、`/etc/farm/roles.conf.bak-14b` を戻す、`sudo rm -r /etc/systemd/system/agent@scout-*.service.d`、`sudo systemctl daemon-reload`
