> Farm の仕様書の一部（既知の落とし穴と対処（前半））。1 つ目の文書と一覧は `farm/farm-handover.md`。

# Farm 仕様書（続き）

## 既知の落とし穴と対処

これまでに踏んだ不具合。すべて恒久対策済みだが、同じ形の問題が再発したときの当たりをつけるために残す。

| 症状 | 原因 | 対策 |
|---|---|---|
| earner が sudo できず kb/wiki に書けない | dsh の bwrap サンドボックス（no_new_privs、nobody 所有の /etc） | `DSH_PERMISSION_MODE=danger-full-access`。境界は OS ユーザー + nft + unit |
| claude が `kb ...; echo` を拒否 | allowedTools はコマンド連結を許さない | プロンプトに「1 呼び出し 1 コマンド」、下書きは scratch/ |
| ledger / dashboard が readonly database | SQLite WAL は読み手も -shm に書く | journal_mode=DELETE。farm-dash に ReadWritePaths と farmrelay グループ |
| 公開 RPC が 403 | User-Agent なしを拒否するノード | relay が UA を付与。死んだエンドポイントは外した |
| gate の送信を relay が拒否 | 送信は HTTP では許さない設計 | farmgate 専用 unix socket。RuntimeDirectory 共有でソケットが消えたため `/run/farm-relay` を専用化 |
| bot@ が signer ソケットで PermissionError | グループ不足 | bot@.service に SupplementaryGroups=farmbot |
| sweep が insufficient funds | 手数料見積もり不足、L2 の L1 データ費 | 手数料 1.2 倍 + L2 は 21000 × maxFee を予約 |
| PnL が +5.0 USD の幽霊利益 | 二重 sweep で baseline が二度消費 | baseline は sweep 成功時のみ消費 |
| Arbitrum USDC アドレスが間違い | 記憶から書いた | Circle 公式で訂正（gate.json）。Chainlink feed は signer 起動時に検証 |
| earner が「チェーンは farm の fork」と思い込む（61 箇所） | プロンプトに無いことを推測 | common.md に「本物の mainnet」を明記。wiki は人間が訂正（infra/farm-base-contracts.md） |
| debug_traceTransaction が失敗 | 公開ノードは提供しない | trace/debug 系は Alchemy 優先（Pay As You Go で利用可） |
| earner がタイムアウトして何も残らない | 75 分を超えてビルド中に打ち切り | セッション時計をコンテキストに、「記録してから作る」、未完 bot を次セッションに引き継ぐ |
| reviewer / meta が bot や inbox を読めない | umask で 0600 | default ACL（group farm）を bots/paper, inbox, scratch, logs, claims に。farm-acl-fix.timer で補修 |
| install.sh のライブラリ検査が失敗 | `python -I` は PYTHONPATH を無視 | 明示的に sys.path を挿入 |
| phase 6 が `anvil lacks --silent` で停止 | anvil 1.9 でフラグ廃止 | unit から除去、StandardOutput=null |
| 6a を当てたのに UTC 表示のまま | phase 6 の install.sh も farm-dash を入れ替える（6a → 6 の順で上書き） | 6a を再実行。手元の phase 6 バンドルは JST 版を同梱済み |
| バンドルに無関係なファイルが混入（phase 2b） | 作業ディレクトリの混入 | 除去して再ハッシュ。展開前の sha256 照合を習慣に |
| paper-reviewer / researcher（codex）が数十分動いた後に exit 1。ログ末尾に「approved for Daybreak Blue … not authenticated with one of your authorized hardware keys」 | gpt-6.1-sol は Daybreak Blue 経由で、2026-09 からハードウェアキー必須。harness の codex トークンが、キーなしでサインインしたブラウザセッション由来だった | `sudo -u harness -i` → `codex logout` → `codex login --device-auth`。ブラウザはプライベートウィンドウで最初からサインインし、USB キーのプロンプトで実際にキーに触れる（パスワードマネージャーのパスキー提案は Cancel）。復旧確認は agent@paper-reviewer を手動 start |
| paper-reviewer を claude harness で動かすと review.md / セッション報告を書けない | run-role の claude_tools に paper-reviewer の分岐がなかった | phase 6b で分岐を追加。roles.conf を claude/opus に切り替えれば代替として使える（1 回 10〜15 分・約 4.5 USD） |
| fork replay / send / deploy が 'NoneType' object has no attribute 'get' で落ちる | 送信直後のレシートを 1 回だけ読んでいた | phase 6b で receipt() が最大 30 秒ポーリング |
| paper-reviewer がセキュリティ所見を inbox/human に書けない | パス表の inbox/human に paper-reviewer が無かった | phase 6b の common.md で security findings only で許可 |
| earner が 15 秒おきに exit-code で即死し、start-limit-hit で起動できなくなる | ローカル LLM サーバーが落ちている（GPU の取り合いなど）。StartLimitBurst=20/1h | サーバーを直してから `systemctl reset-failed agent@earner-local` → start。6o で qwen-server 待ちに |
| セッション報告が消える（18 run 中 2 行） | dsh の Write が jsonl を追記ではなく上書き | 6f: chattr +a、harness が no_report 行を保証、meta の tools/session-report.py |
| `git -C /srv/farm/ws log` が not a git repository | git 管理は wiki/ だけ | 6k: ws/history に run ごとのスナップショット commit。git config --system safe.directory |
| paper-reviewer（codex gpt-6.1-sol）が executor の検証中に「flagged for possible cybersecurity risk」で exit 1 | OpenAI 側の内容フィルタ（認証ではない） | 6l: reviewer のモデルを gpt-6-sol に。Claude への切替は不採用 |
| `fork deploy` が status 0 で失敗する（11-06） | コンストラクタ引数を付けずに creation code を配備していた | 6u: 引数の欠落を検出して警告、`--args` で渡せる |
| paper start が「failed ... result running」と誤報 | `systemctl show --value` の出力を位置で読んでいたが、順序は systemctl 側で決まる | 6y: key=value で読む |
| `eth_getBlockByNumber("latest")` が数分古い | latest も TTL 600 秒でキャッシュしていた | 6w: 動くタグは最大 1 秒 |
| 公開ノードが getCode / eth_call に "0x" を返し、存在するコントラクトが無いように見える | 公開ノードの不完全な応答。共有キャッシュで live レーンにも届きうる | 6y: 空応答は Alchemy で確かめてからにし、キャッシュしない |
| 「コントラクトのはずのアドレス」が `0x`（11-08） | earner（と人間側の Claude）が記憶からアドレスを書いた。Etherscan で EOA だった | relay の不具合ではない。アドレスは一次情報からだけ書く |
| phase 8 の install.sh が何も出さずに終わる | `ldd \| head` が SIGPIPE を起こし、pipefail で即終了 | `getconf GNU_LIBC_VERSION` を使い、ERR trap で失敗行を表示（以後のバンドルの標準） |
| earner の web_search が「configured web provider "rustxng" is not registered」 | dsh はインストールかプロファイルの依存グラフにあるパッケージしか読まない。node が PATH に無く npm の shebang も失敗 | 8a: dsh バンドルにして `dsh plugin --profile headless add`（pnpm）、install.sh で `export PATH="$NODE_DIR:$PATH"` |
| gate が franken-dutch を「allowed_contracts がない」と拒否 | `- 0x…` で始まる行しか読んでいなかった。signer も行末コメント付きのアドレスを読めなかった | 9e: どの YAML のリスト形式でも読む |
| コンストラクタ引数のある executor が promote で配備できない | gate が `executor_args` を無視していた | 9e: executor_args を付けて配備、`{bot}` を差し込む、レシートを確認 |
| promote で「insufficient funds ... have 0」、資金だけ入って executor のない live bot | gas の送金がブロックに入る前に配備していた | 9f: 送金のレシートを待つ。`gate-ctl deploy <id>` で再開 |
| watchdog が「鍵の漏洩の可能性」で全体を halt し sweep（誤検知） | gate が bot の鍵で送った配備 tx を、signer の記録に見つけられなかった | 9g: gate が配備・sweep を nonce 付きで gate.log に記録し、watchdog がそれを既知とする |
| watchdog の緊急停止で「archive failed: no new privileges」 | farm-watchdog.service の NoNewPrivileges が sudo を止めていた | 9g: drop-in で NoNewPrivileges=no |
| `fork fund-token` が失敗しても終了コード 0 | FAILED を表示するだけだった | 9h: 終了コード 2 |
| Base bot の promote が「intermediate wallet on base has less than 120.00 USD + gas」（11-10、moonwell） | 事前確認が gas wallet cap 前の額（capital_usd 全額）を求めていた。実際の送金は 18 USD まで | 9i: 事前確認も上限後の額。拒否文に上限の注記 |
| USDC を持つ bot の sweep / stop が TypeError で途中停止（潜在、実害なし） | 9f が promote 用の `wait_receipt(chain, h, what)` を追加し、sweep が使う 2 引数版を上書きしていた。USDC 送金は出るが PnL・archive なし、nonce は watchdog に未知。再 stop で元本全額を「principal gone」と損失計上しうる | 9i: `poll_receipt` に改名、ステータス確認、`sweep_usdc_sent`、送金中レコード。9g 版を再現するオフラインテストを install.sh に同梱 |
| `gate stop --all` が 1 本の例外で残りを止めない | SystemExit しか捕まえていなかった | 9i: 例外を `stop_failed` として記録し続行 |
| watchdog がブロック形式の `chains:` の bot を監視しない（潜在。11-10 時点の live 2 本はインライン形式で監視されていた） | watchdog だけ 1 行のインライン形式しか読んでいなかった（9e で gate / signer は直したが漏れ） | 9i: gate と同じ manifest 規則で読む。読めない bot は一度だけ journal に「NOT monitored」 |
| promote が資金送付の後に「executor artifact unreadable: … '/srv/farm/ws/"scratch/…json"'」で停止（11-10、moonwell） | gate が `executor:` のパスを引用符ごと読んでいた（`executor_args` は外していた）。manifest-check は引用符付きでも PASS | 9j: 引用符と行末コメントを外して読む。止まった bot は `gate-ctl deploy <id>` で再開 |
| promote が資金送付の前に `ValueError: could not convert string to float: " 16 # Fixed ..."` で終了（11-10、morpho） | gate が `capital_usd` / `max_loss_per_tx_usd` を行末コメントごと float にしていた（`principal_usdc` だけ外していた）。signer は共通の manifest 規則で読むので無事 | 9k: `manifest_number()` で 3 つとも行末コメントと引用符を外す。数値でなければ資金移動前にメッセージ付きで拒否 |
| researcher-claude の TOOLS.md 編集が拒否される（11-10） | run-role の claude 権限に TOOLS.md の Edit がなかった（common.md では書ける表になっている） | 9k: `Edit(//srv/farm/prompts/roles/TOOLS.md)` だけを追加 |
| promote 直後に live bot が「live mode needs EXEC_ADDRESS」で再起動ループ（11-10、reserve-dutch-ethereum。配備ガス約 5.1 USD の損失） | bot.js が executor のアドレスを `EXEC_ADDRESS` で読んでいた。gate が渡すのは `EXECUTOR_ADDR`（と state/executor.json）と当時は書いていたが、実際に渡っていたのは state/executor.json だけで、環境変数は 11c（11-14）まで誰も設定していなかった。paper では使わないので審査で見えなかった | watchdog → live-operator が約 7 分で stop・sweep。bot は `EXECUTOR_ADDR` を読むよう直して -v2 で再審査。10d の decision で規則にし、10e で gate が promote 時に確かめて拒否（manifest-check も同じ確認） |
| live の bot が起動ログに fork 上の executor のアドレスを出し、機会が来ても送らない（11-14、morpho-nextblock-ethereum。reviewer が inbox/live に報告。gearbox-v3-watcher-ethereum も同じ書き方で、promote 以来同じ状態だった。franken-dutch-ethereum は環境変数だけを読み、なければ live では送らない作りで、startup の `exec` が空のまま待機していた。11c より前の live 3 本すべてが該当） | bot は `process.env.EXECUTOR_ADDR \|\| '<fork のアドレス>'`。10e の gate の確認は文字列の有無だけで通る。ところが `bot@.service` は `EXECUTOR_ADDR` を渡していなかった（`/proc/<pid>/environ` で確認）。fork のアドレス宛ては signer が拒否するので損失は出ないが、送信もできない | 11c: `bot@` を bot-run 経由で起動し、`state/executor.json` から `EXECUTOR_ADDR` を渡す。配備済みの executor をそのまま使うので再配備は不要。確認は `sudo cat /proc/$(systemctl show -p MainPID --value bot@<id>)/environ \| tr '\0' '\n' \| grep EXECUTOR`。11-14 より前の「live で送信 0」は、この書き方の bot については機会がなかった証拠にならない |
| live-operator が差し戻しのとき「shell cp / mv denied」（11-10） | run-role の live-operator に cp / mv がなかった（common.md では差し戻しのコピーを書ける表） | 10d: archive → paper の cp、paper の mkdir -p、inbox/live の mv だけを許可 |
| `gate status` / `gate promote` / `gate fund` が、ある 1 チェーンの読み取り失敗（relay の上流障害など）で失敗する | 設計どおり（10b 以降）: X は全チェーンの中間ウォレットと live bot の残高の合計なので、1 チェーンでも読めないと計算できず、安全側に止まる。stop / sweep は X を使わないので影響なし | `curl -s http://127.0.0.1:8545/health` と `journalctl -u rpc-relay` で上流を確認。直るまで待つ。長引くチェーンは gate.json の chains から外すことも可（その場合そのチェーンの中間ウォレット残高は X に入らないので、残高 0 のときだけ） |
| watchdog の journal に「no baseline in pnl.json; the live-loss stop cannot judge it」（10c 以降） | pnl.json にその bot の baseline がない。11-09 の誤検知 halt の sweep で baseline が消費された後、資金を入れ直さずに live に戻した gearbox-v3-watcher-ethereum がこれ | 今の wallet 残高を baseline として入れる（以後の損失はそこから数える）。11-10 に gearbox で使ったコマンドは運用記録の「人間がサーバーで直接変えたもの」。11b からダッシュボードの「要確認」にも出る |
| 10a の install で /srv/farm/runners/researcher-chatgpt と researcher の prompt.md だけ更新されない | roles.conf にない古い instance 名（9b で researcher-codex に改名）の残骸。実行されないので害はない | 11-13 に人間が `sudo rm -r /srv/farm/runners/researcher-chatgpt /srv/farm/runners/researcher` で削除済み（11b のプロンプト一覧に出ていたため）。同じ形の残骸がまたできたら、agent@ の unit や timer がそれを指していないことを確かめてから消す |
