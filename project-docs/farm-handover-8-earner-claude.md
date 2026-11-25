> Farm 仕様書の続き（8 つ目）。本体は `farm/farm-handover.md`。この文書は 2026-11-17 の変更を扱う: phase 13a・13b（earner の役を Claude で回す 3 本目の instance）と、安いチェーンでの live の試行（decision 2026-11-17-cheap-chain-trials）。
> 状態: 13a は 11-17 01:50 JST、13b は 02:11 JST、decision は 02:20 JST ごろに人間が適用・配置済み。**本体の「文書の一覧」「役割とモデル」の表・systemd unit の表・promote の基準には、まだこの文書の内容を足していない。**

# 1. earner-claude（phase 13a・13b）

## 何のためか

人間の判断（2026-11-17）: 役とモデルの割り当てを見直す。最終の形は「Qwen は数を打つ下調べ（scout）、作る仕事は Claude と codex（builder）、審査は作り手と逆のモデル、researcher は builder に吸収」。1 歩目として、earner の規則のまま Claude の earner を 1 本足して測る。

## 構成（実際の値）

| 項目 | 内容 |
|---|---|
| instance | `earner-claude`（roles.conf: `earner-claude  earner  claude  claude-mythos-5-2`） |
| role ファイル | `roles/earner.md`（Qwen の earner と同じ。組み立て後 55,873 bytes） |
| レーン | build（`/opt/farm/context/earner` は名前が `-measure` で終わらなければ build） |
| モデル | Mythos 5.2。`--model` には ID `claude-mythos-5-2` を渡す（`/model` の表示名は使えない）。変えるには 13a の `sudo MODEL=<ID> ./install.sh` を入れ直す |
| 実行ユーザー | harness（researcher-claude・meta と同じ）。nftables の earner 向けの制限はかからない |
| 起動 | `farm-earner-claude.timer`: 毎日 00:40 JST から 3 時間おき、1 日 8 回 |
| 打ち切り | drop-in `agent@earner-claude.service.d/session.conf`: `RuntimeMaxSec=75min`、`SESSION_MAX_MIN=75`、`UMask=0002`。再起動のループなし |
| run-role | `claude_tools()` に `earner)` の枝（13a）、その Bash の一覧を広げた（13b）。dsh の earner はこの一覧を読まない。置換前は `/opt/farm/bin/.run-role.bak-13a`・`.run-role.bak-13b` |

run-role の sha256（どれも適用時に実測が一致）: 12e 後 `594c299e…bbd1c9` → 13a 後 `9a56b50a157f141cc728868a3987cb0e47a889d355e80c1dd97db2007a0b623b` → 13b 後（今）`c355840c1a470b6970ef930250b543b8830ea0ea7d721615c0c07a275791c058`。

バンドル: `farm-phase13a-r2.tar.gz`（sha256 `fb82bcea411d74593d1cb955249dbd012ac3da057b24c1b9d75ca6fc9f40051f`。最初の版は install.sh のモデル名の検査が誤っていて、何も変えずに止まった）、`farm-phase13b.tar.gz`（`9747b647ada733239feffd421b7d9b2de306435ff523e0763fb280bd0562279c`）。

## 許した道具（13b 適用後）

共通の一覧（kb / wiki / ledger / websearch / explorer / curl / fork / gate status / paper の読み取り / scratch の編集）に加えて:

- Bash: `date` `python3` `jq` `node` `npm` `forge` `cast` `ls` `cat` `head` `tail` `grep` `wc` `sleep` `cp` `setfacl` `mkdir` `cd` `sed` `awk` `sort` `uniq` `cut` `tr` `echo` `printf` `find` `diff` `tee`、`paper start|restart|stop`、scratch と bots/paper の下の `chmod +x`・スクリプトの実行、`rm /srv/farm/ws/claims/*`
- Edit: `bots/paper/**`、`claims/**`、`inbox/**`
- 許していない: `gate promote` ほか gate の操作、`paper archive`、WebFetch、`prompts/roles/` の編集、任意の `rm`・`bash`

13b の理由: 最初の回で Bash が 2 回断られた（相対パスの `mkdir -p`、`sed` を含むパイプ）。`B=...; curl $B/...` のような変数の代入で始まるコマンドが通るかは未確認。

注意: `python3` を許しているので、一覧は柵であって境界ではない。境界は OS ユーザー（harness）と gate。harness は `gate promote` を呼べるユーザーなので、「作り手は自分の bot を審査しない」はプロンプト側の規則だけで守られる（researcher-claude も同じ）。

## 最初の回（run 3fa7205c、11-17 01:54〜02:01 JST）

- 6.6 分、67 ターン、定価換算 4.53 USD、outcome `blocked_infra`
- 待ち行列が空でも、KB にない型（GEB 系の報酬つき keeper job）を見つけて 3 つ測った。HAI（optimism）は最初のブロックの取り合い、Open Dollar（arbitrum）と Reflexer RAI（ethereum）は dead_end（attempts 1439〜1441）
- 分かったこと: モデルを替えても、速度勝負を対象外にする規則のままでは同じ所で止まる → 下の 2 の decision
- 枠（Max。01:51 → 02:03 JST）: 5 時間 25 → 40%、週 4 → 5%、Fable 7 → 9%。Mythos は Fable の枠（週の最大 50%）に数えられる。この Project の会話も同じ枠を使う。bot を作る長い回の費用は未測定

## 枠と課金

- 使用クレジットはオンで残り 6.04 USD（11-17 01:51）。`-p` のセッションでは、枠を超えた分が確認なしで引かれる。自動の買い足しの設定は未確認
- researcher-claude・meta・live-operator と同じ枠。枠が尽きると、異常時に live-operator が起きられない

## 分かっている不具合

- ops.db の runs の表は、claude の instance の全部の行で `tokens`・`cost_usd`・`session_id` が空（researcher-claude・meta も。Mythos のせいではない）。record-run（sha256 b5b40937…904f62）の `parse_claude` は見た目は合っていて、原因は未特定。費用は journal から取る: `sudo journalctl -u agent@earner-claude --since today -o cat | grep '"type":"result"' | jq -c '{duration_ms, num_turns, total_cost_usd}'`
- 13a の install.sh は「lane」の行の後に「(no lane line)」も出す（表示だけ）

## 止め方・戻し方

- 止める: `sudo systemctl disable --now farm-earner-claude.timer`（すぐ止めるなら `sudo systemctl stop agent@earner-claude`）
- 戻す: 上に加えて `sudo cp -a /opt/farm/bin/.run-role.bak-13a /opt/farm/bin/run-role`、roles.conf の `earner-claude` の行を消す、`sudo rm -r /etc/systemd/system/agent@earner-claude.service.d /etc/systemd/system/farm-earner-claude.timer`、`sudo systemctl daemon-reload`

# 2. 安いチェーンでの live の試行（decision 2026-11-17-cheap-chain-trials）

プロンプト側の規則で、コード（gate・signer・watchdog）は変えていない。置いたのは `decisions/human/2026-11-17-cheap-chain-trials.md`（sha256 ae20f331…8c182cd6）と `inbox/meta/2026-11-17-human-cheap-chain-trials.md`（add4eef6…84a71011）。11-12 の「スピード勝負はやらない」を、下の「試行の bot」に限って覆す。

| 項目 | 値 |
|---|---|
| チェーン | ethereum 以外 |
| `capital_usd` | 20 以下。それがその bot の損の上限（追加入金なし） |
| `max_loss_per_tx_usd` | 1 以下 |
| 読み取り | 1 日 100,000 CU 以下。feed の `/logs` かタイマー。毎ブロックのポーリングなし |
| 名前 | ID `trial-<対象>-<chain>`、`strategy` の先頭に `trial:` |
| 同時に live | 10 本まで（合計 200 USD）。次のブロック型の 2 本・単発の 2 本とは別枠 |
| 終わり | promote から 7 日、または資金を使い切ったら結果を attempts と inbox/human へ。止めるのは人間 |

- 外すもの（試行の bot だけ）: 共通の指示の原則 2、反応時間の区分、数えられる期待収益、1 日 1 USD の床、期待収益と CU の比較、paper での自然な機会と待ち時間
- 残すもの: X・n・L・S、executor の決まり（1 tx で完結、残高が増えなければ revert）、fork の成功と revert、誰でも呼べることの確認、送る条件のコード、送信ごとのログ。mempool の監視と他人の未確定 tx への割り込みは禁止のまま
- 求める証拠: 過去 7 日にその入口で誰かが受け取った tx が 1 件以上、1 回の粗利が 1 回のガス代より大きい
- reviewer: 次の回で先に審査、review.md に「安いチェーンの試行」、通ればその回で promote
- 最初の 1 本: optimism の HAI の OracleJob（attempts:1439）。人間が 11-17 02:2x JST に中間ウォレットの optimism へ 20 USD 分の ETH を送った

確かめていないこと:

- signer が manifest の `max_loss_per_tx_usd`（1 USD）で拒否するか。signer が強制すると分かっているのは L（50 USD）
- optimism と base は L1 のデータ費が tx の欄で縛れないので、1 回 1 USD はコードでは保証されない。実際の上限は 1 本 20 USD の資金（gas wallet の上限は 18 USD）
- meta が役割ファイルに反映したか。earner が decision を読むのは 3 日間だけなので、11-20 までに要る。`tools/manifest-check.py` の `trial:` の検査も meta に頼んである

# 3. 次の段（まだ作っていない）

1. scout: Qwen の earner 2 本を、スクリプトが列挙した候補を 1 件ずつ測る役に置き換える（役割ファイルは 5 KB 程度）
2. builder-codex を足し、審査は作り手と逆のモデルにする
3. researcher を builder に吸収する
4. record-run の直し
5. Ultra に変えるかは、bot を作る回の費用を測ってから
