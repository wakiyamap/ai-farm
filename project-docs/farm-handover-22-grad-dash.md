# 引き継ぎ 22: 卒業（grad）の仕組みとダッシュボード（2026-11-23）

11-23 の変更。前は `farm-handover-21-stellar-read.md`。

## 決めたこと（人間の decision）

- `decisions/human/2026-11-23-s-no-skim-rebase-surplus.md`: uniswap-skim 型（余りの拾い）は S で「いいえ」
- `decisions/human/2026-11-24-graduate-and-builder-focus.md`（15:23 配置、sha256 `760836e0…984f`）
  - 卒業の候補: 試行の bot で live 72 時間以上・promote から +1 USD 以上（gate status）・`send_result: won` 3 回以上。meta が毎回一覧を報告
  - grad は `grad-<対象>-<chain>` で作り直し、通常の審査。capital 150 以下、1 送信の損 3 USD 以下、手数料は粗利の 50% が天井（grad ごとに相手の手数料の割合を測って決める、OP Stack では積まない）、量を増やすなら fork で増える証拠、同時に live は 5 本まで、ethereum は対象外。grad が live になったら試行の方は人間が `gate stop`
  - builder の順番: fix → grad 作り → grad を磨く → scout の measured lead → 無ければ短い報告ですぐ終わる

## 設定の変更

- **builder-claude を 4 時間おきに**（15:3x、人間）: `/etc/systemd/system/farm-builder-claude.timer.d/every-4h.conf`

  ```
  [Timer]
  OnCalendar=
  OnCalendar=*-*-* 00/4:40:00 Asia/Tokyo
  ```

  `hourly.conf`（11-17、毎時 40 分）は削除。最初の回は 16:40 JST。builder-codex（3 時間おき）、scout・paper-reviewer・meta は変えていない

## ダッシュボード: phase 16c（15:36 適用）+ 16d（15:41 適用）

- farm-dash（/opt/farm/bin/farm-dash）の sha256: `ae04cc68…6c046c42`（15l の後）→ 16c `c995b351…1234c9` → **16d `5b2e98961c8e3c4362df009cadf924068e81002f64c16be9a297ad4f4a0a0a12`（今の版）**。退避 `/opt/farm/bin/.farm-dash.bak-16c`（15l の版）、`.farm-dash.bak-16d`（16c の版）。バンドルは `farm/phase16c/`・`farm/phase16d/`
- ページ: 「Live bots」を 3 つに分けた
  - **Grad bots（n of 5）**: `grad-` の live bot。列は今までの live の表 + `hours_live`・`won_of_sends`。paper にいる grad は表の下に review 付きで出す。5 本を超えたら警告
  - **Live bots: trial and one-shot**: それ以外の live bot（同じ列）
  - **Graduation candidates**: 条件をすべて満たす試行の bot（`trial-` で始まり `-ethereum` で終わらないもの）。列は live の時間・promote からの PnL・勝ち/送信・grad の状態（live / in paper / —）。その下に「One condition short」
  - タイル「Grad bots」（n/5、候補の数）
- brief.txt: `in profit` の行の後に `grad bots live: n of 5`、grad ごとの行、`graduation candidates (...): n` と候補の行、`one condition short: ...`
- /data.json に `graduation`（stats・candidates・near・grad_live・grad_paper）
- 数え方
  - promote の時刻: gate.log の bot の一番新しい `op: "promote"` の記録（`ok: false`・`error` 付きは除く）。無ければ bots/live/<id> のディレクトリの時刻。確認済み: op は `promote`、全 live bot の時刻が gate.log から取れる
  - 勝ち / 送信（16d）: `bots/live/<id>/logs/bot.jsonl` の `{"ev": "send_result", "result": "won"|"lost"|"unknown"}` の行（`send_result` キーや `send_result: won` の文字も数える）。promote より前の行は数えない。追記分だけ読む。ファイルに 1 行も無ければ `journalctl -u bot@<id>` だが、farmgate には権限がなく実際は読めない
  - PnL は `live PnL since promotion` と同じ値（wallet − 入れた額）
- 戻し方: 16d だけ戻す `sudo cp -a /opt/farm/bin/.farm-dash.bak-16d /opt/farm/bin/farm-dash && sudo systemctl restart farm-dash`。16c ごと戻すなら `.farm-dash.bak-16c`

## 分かったこと

- live の bot のログは `bots/live/<id>/logs/bot.jsonl`（farmbot:farm、ACL で farmgate も読める）。キーは `ts`（epoch 秒）・`ev`・`result`。勝敗の材料に `send_block`・`winner_block`・`tx_index`・`blocks_after_winner` などがある（bot ごとに少し違う）
- 適用時（15:41）の卒業候補: trial-flatmoney-arbitrum（won 13/13、+1.30）、trial-peapods-arb-arbitrum（5/10、+1.79）
- 勝ちの数と儲けは別物: torex-base 116 勝・openoracle-settle-optimism 90 勝・ethos-redeem-optimism 31 勝（+0.16）。1 回の粗利がガスとほぼ同じ型がある
