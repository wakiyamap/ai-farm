# meta 報告: phase 14 の対応と試行 bot の最初の数字（2026-11-16 21:xxZ, run bd67a2a5）

## 1. 試行の bot（decision 2026-11-17-cheap-chain-trials）

live の試行 bot は 2 本（上限 10 本）。gate: 本日の損失 0 USD、capital 731.13 USD。

| bot | live 開始 | 送信 | 勝ち | 差し引き |
|---|---|---|---|---|
| trial-updaterate-hai-optimism | 11-16 18:54Z | 2 | 0 | 約 -0.000001 ETH（2 回とも revert、ガスのみ。1 回あたり約 0.0000004 ETH） |
| trial-aave-arbitrum | 11-16 20:50Z | 0 | 0 | 0（executor の deploy 済み、wallet 14.97 USD） |

- HAI updateRate: 2 回とも相手の **1 ブロック後**（19:04Z 窓: 相手 159628548、自分 159628549。20:04Z 窓: 相手 159630348、自分 159630349）。相手の優先手数料は 0.0975 gwei と 0.0001 gwei、自分は 0.01 gwei。どちらも相手は due と同じ秒のブロックに入っており、自分は due の 1.0〜1.2 秒前に送っても 1 ブロック遅れています。1 回の粗利見込みは約 0.000034 ETH（0.05 HAI）。
- ログの不具合: 2 回目の窓は bot のログで `not_sent_or_no_receipt` と出ていますが、実際は送信済みで status 0（tx 0x86057f68…、ブロック 159630349）。receipt の読み取りで `'NoneType' object is not subscriptable` が出ています。勝ち負けの集計がこのログに頼るので、次に paper に戻すときは直す必要があります（live のコードは触っていません）。
- trial-aave-arbitrum: paper-reviewer-claude が 20:50Z に promote しました（attempts:1471）。ただしその reviewer の session report の行は途中で書いた「wait 1」のままで、`bots/live/trial-aave-arbitrum/review.md` の先頭も古い「wait」の記載です。bots/live は gate 専用で meta も書けないため、可能なら先頭に「2026-11-16 20:50Z promote (cheap-chain trial), see attempts:1471」を足してください。

## 2. signer のアドレス（inbox/meta/2026-11-17-human-bold-live-patch.md 5）

live の 5 本を確認しました。同じ不具合はありません。
- bold-redeem-tail-ethereum `bot.py:98-99`（人間の修正済み）、trial-updaterate-hai-optimism `bot.py:295-296`: dict から `address` を取り出している
- gearbox-v3-watcher-ethereum `bot.js:408-410`、morpho-nextblock-ethereum `bot.js:889-891`: socket の `{"op":"address"}` の返答から `.address` を取っている
- trial-aave-arbitrum `bot.py:133-134`: 取り出している

対応: wiki `pitfalls/signer-my-address-dict.md`、manifest-check に警告（`my_address()` の 3 行以内に `["address"]` / `.get("address")` がなければ警告、合成テストで確認）、paper-reviewer.md に 1 行。

## 3. 各インスタンス（11-16、phase 14 開始後）

- builder-claude: 2 session（4886c647 fix_submitted、31babb54 実行中）。paper に置いた bot 0、fix 2（trial-oraclejob-hai-optimism）。
- builder-codex: 1 session（6af286a0 paper_placed: trial-aave-arbitrum → promote 済み）。
- 閉じた型の繰り返し: まだなし（Aave arbitrum は速度で blocked_infra だった lead 7 で、試行の対象どおり）。no_target はまだ 0 件。
- scout（4 本）: 13 session、scouted 6、no_report 7（全部 19:37Z 前後の最初の組、20 分で打ち切り。うち 1 本は報告なしでも attempts:1459 を残した）。1 本の報告は次の行とつながっていた（下の 4 で修正）。結果: trial 7 件（arbitrum lead 7・9、base lead 197・171・18・170・2）。pays_strangers 6、unpaid 1（lead 197）。protocol / actor 種別の候補はまだ来ていません。
- earner-local / earner-measure / earner-claude: 停止済み。earner の最後の報告は 19:3xZ。

## 4. meta の変更（測定つき）

- `tools/session-report.py`: role `builder`（earner と同じ outcome）と `scout`（scouted / no_candidate / aborted）を追加。`>>` で改行なしに書かれた行（11-16 の 135 行目）があると次の行がつながるため、追記前に改行を補い、coverage は 1 行に 2 つの JSON があっても読むようにしました。coverage の missing 2 → 1（残りは実行中の builder）。
- `tools/manifest-check.py`: `trial:` bot の警告（ethereum、capital_usd > 20、max_loss_per_tx_usd > 1、id の形）。paper の 3 本はすべて警告なし、合成 manifest で 4 つの警告が出ることを確認。
- `paper-reviewer.md`: `other-reviewer` の行は飛ばす 1 行、試行 bot の審査基準（安いチェーンの試行）、live 分岐の `from` を読む 1 行。
- `scout.md`: attempts の outcome は KB が受け付ける `lead_recorded` / `dead_end_recorded` にし、判定は reason の先頭に書く（kb-write は `pays_strangers` を拒否し、/opt にあるので meta は変えられません）。
- `tools/prompt-size.py` に builder と scout を追加。組み立て後（TOOLS.md +115 を含む）: earner 55988、paper-reviewer 50677、builder 49672、scout 37847、meta 37346、live-operator 37943、researcher 40880（すべて 56000 以下）。builder.md 16162 バイト（18 KB 以下）。scout.md 4337 バイト。
- earner.md は変えていません: earner のインスタンスは 3 本とも停止済みで、試行の決まりは builder.md にすでに入っています。earner を戻す場合は先に言ってください。

## 5. 人間に決めてほしいこと

1. **paper-reviewer-claude の Bash 許可**: "don't ask" モードで `python3 /srv/farm/ws/tools/manifest-check.py ...` が拒否されます（審査の必須手順。inbox/meta/2026-11-16-paper-reviewer-claude-bash-denied-7e676a2d.md）。meta の session でも `ls` や `python3 -c` などが拒否されました。runner の許可リストは workspace の外なので、追加をお願いします。
2. **scout の時間**: scout.md は「開始から 25 分で書き始める」ですが、19:37Z の組は 20 分で打ち切られていました（no_report 7 件）。session の長さが今 25 分より長いなら問題ありません。20 分のままなら scout.md の 25 を 12 にします。どちらか教えてください。
3. **kb-write の attempts outcome**: scout の判定語（pays_strangers など）をそのまま入れたいなら `/opt/farm/bin/kb-write` の OUTCOMES に足す必要があります。今の対応（reason の先頭に書く）で足りるなら不要です。
