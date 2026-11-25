> Farm の仕様書（どう作られていて、どう動き、どう操作するか）。日々の状態・経緯・人間の判断・保留事項は運用記録 `farm/farm-ops-log.md` に分けた（2026-11-10）。
> この Project の Markdown が唯一の版（2026-11-10 から）。旧 Claude Doc https://claude.ai/artifact/99qma2NfcN63zxvTwWTaKu は更新を止めた（図だけはそちらを参照）。
> 設定やコードを変えたら、本書（仕様が変わる部分）と運用記録（何をいつ当てたか）の両方を更新する。
> 2026-11-14 から、本書は複数の文書に分かれている（11-15 から 7 つ）。Project の文書は全文の置き換えでしか更新できず、ファイルから書き戻すには 1 回の読み取りで全部読める大きさ（24 KB 程度まで。英数字の多い文書はもう少し大きくてもよい）でなければならないため。この文書が 1 つ目で、続きは下の「文書の一覧」にある。

# Farm 仕様書

2026-11-03 作成 / 2026-11-17 更新（researcher の timer を 1 日 8 回に。phase 12f、decision 2026-11-15-executor-no-baked-targets・2026-11-15-widen-beyond-liquidations・2026-11-15-holding-frame まで反映） · @operator

farm-host 上で動く自律オンチェーン稼得システム「Farm」の仕様。2026-11-16 時点で phase 12f まで全て適用済み（9h も適用済みを 11-10 に確認）。チェーンは base / arbitrum / ethereum / bsc / polygon / avalanche / optimism / hyperevm / elysium の 9 つ（bsc〜hyperevm の 5 つは 11-10 に 10a（読み取り側）・10b（資金側）で、elysium は 11-11 に 10g で追加）。本書の各所にある「8 チェーン」という記述は 10b 時点のもので、elysium の分は「elysium（phase 10g）」の節にまとめてある。前提となる設計判断はすべて 運用者 が決めたもので、本書はそれを実装どおりに記録する。判断の一覧と理由は運用記録の「人間の判断」にある。

## 文書の一覧

- `farm/farm-handover.md`（この文書）: 役割とモデル、全体像、資金とリスク上限（promote の基準）、サーバー構成、鍵管理と署名、bot のライフサイクル
- `farm/farm-handover-2-relay-feed-fork.md`: RPC relay と ledger、feed、fork と executor 契約、web search
- `farm/farm-handover-3-chains-dash-commands.md`: チェーン追加、elysium、ダッシュボード、日常運用コマンド集
- `farm/farm-handover-4-pitfalls-a.md`: 既知の落とし穴と対処（前半）
- `farm/farm-handover-5-pitfalls-b.md`: 既知の落とし穴と対処（後半）
- `farm/farm-handover-6-phases.md`: フェーズ履歴とバンドル
- `farm/farm-handover-7-holding-frame.md`: 持ち高の枠（phase 12d）。`holding_usd` のある bot の上限、gate の promote / stop（`exitAll()`）、watchdog の線、コマンド、確かめていないこと

探す先の方針（decision 2026-11-15-widen-beyond-liquidations。プロンプト側の規則）: 清算の相手の測定（取り手の一覧、急落の事後検証、取り手の型、blocked_infra の見直し）は打ち切り。清算は禁じないが、探すことにセッションを使わない。探す先は清算以外で、候補は人間から出さない。人間が作る予定だったもの: 非公開の送信の経路（公開 mempool が理由で閉じた lead は `next_steps` に `private-send`）、USDC で持つ型のための合計 200 USD の枠。非公開の送信の経路は 12b で入り、エージェント向けの規則は 12c で入った（下の「鍵管理と署名」）。200 USD の枠は 12d で入った（`farm/farm-handover-7-holding-frame.md`。この文書では、該当する箇所に「12d」と書いて要点だけを足してある）。

## 役割とモデル

5 役（instance は 7 つ。earner は 12a から 2 本）は互いに直接会話せず、ワークスペースのファイル（KB・wiki・inbox・セッション報告）だけで連携する。`/etc/farm/roles.conf` が instance → role → harness → model の対応表。

| instance | role | モデル / harness | 起動 | 実行ユーザー | 権限の要点 |
|---|---|---|---|---|---|
| earner-local | earner（稼ぎ手） | Qwen3.8-Flash-Next ローカル（llama-server :8003）/ dsh headless | `agent@earner-local` 常駐ループ、75 分でセッション打ち切り→5 分後に次（drop-in `restart-delay.conf` の `RestartSec=300`、11-13 から。それまでは 15 秒） | earner | bots/paper・claims・KB・wiki・scratch に書く。fork / forge / ledger / relay 読み取り。web_search（RustXNG）。鍵なし |
| earner-measure | earner（同じ役。測定のレーン、12a） | 同上 | `agent@earner-measure` 常駐ループ（75 分、次の起動まで 5 分） | earner | earner-local と同じ。違いはレーンだけ: `/opt/farm/context/earner` が instance 名（`-measure` で終わる）から `measure` と決め、セッションの文脈に出す。measure は古い順に unmeasured の lead の「測定の依頼」をそのまま実行して結果を書き、bot は作らない（単発の取り残しを除く）。build（earner-local）は bot のない measured の lead を先に取る |
| paper-reviewer | paper 監視 | ChatGPT gpt-6-sol / `codex exec` | timer: 前回終了から 90 分 | harness | `review.md` 書き込み、`paper archive`、`gate promote` |
| researcher-codex | 研究役 | ChatGPT gpt-6.1-sol / `codex exec` | timer: 毎日 04:10・13:10・19:10・22:10 JST（11-12 から 2 回、11-15 から 3 回、11-17 から 4 回） | harness | TOOLS.md 更新、`ledger add-source`、inbox/human への提案 |
| researcher-claude | 研究役（同じ role ファイル） | Claude Opus / `claude -p` | timer: 毎日 01:10・07:10・10:10・16:10 JST（11-12 から 2 回、11-15 から 3 回、11-17 から 4 回） | harness | 同上。Bash は kb / ledger / websearch / date / python3 / jq など、Edit は tools/ と inbox/ と prompts/roles/TOOLS.md（9k）。12e から WebFetch（claude の役のうち researcher だけ） |
| meta | メタ役 | Claude Opus / `claude -p` | timer: 前回終了から 6 時間 | harness | roles/*.md と TOOLS.md の改訂、reports/、inbox/human への提案（日本語）。python3 / git / date 可 |
| live-operator | live 運用監視 | Claude Opus / `claude -p` | watchdog が異常時に起こす（常駐なし） | harness | `gate` 全操作（stop / restart / fund / sweep）。差し戻し用に bots/archive → bots/paper の `cp`、bots/paper での `mkdir -p`、inbox/live のメモの `mv`（10d） |

- 共通: `/opt/farm/bin/run-role <instance>` が `assemble-prompt` で `common.md` + `roles/<role>.md` + `TOOLS.md` + 動的コンテキスト（`/opt/farm/context/`、セッション時計、未完 bot の引き継ぎ）を組み立て、harness 別に起動し、終了後に `record-run` が `/var/lib/farm/ops.db` へ記録する
- harness ごとの固定オプション: dsh は `DSH_PERMISSION_MODE=danger-full-access`（bwrap が sudo を壊すため。境界は OS ユーザー・nftables・unit）。Qwen の空ターン終了は最大 3 回再試行（6o）。claude は `--permission-mode dontAsk --allowedTools "Bash(kb *),..."` と `/etc/farm/claude-settings.json`。codex は `--skip-git-repo-check --sandbox danger-full-access`
- プロンプトの書き方: 固定部分を先頭（キャッシュ）、動的コンテキストは末尾。「記録してから作る」「1 コマンド 1 呼び出し」「下書きは scratch/」「チェーンは本物の mainnet」を明記（過去の失敗から）
- モデルの方針: reviewer などを Claude に切り替える案は採らない（この種の解析では Claude の拒否のほうが強い）。OpenAI の内容フィルタで落ちたら、OpenAI の別モデルへの切り替えで対処する
- paper-reviewer のレビュー待ち判定（`/opt/farm/context/paper-reviewer`）: review.md がない=NEW、review.md より新しいファイルがある=CHANGED、`next_review_at` を過ぎた=YES、manifest の `expedite: true`=EXPEDITE。それ以外はレビューしない
- live-operator は watchdog が起こしたときしか動かない。inbox/live にメモを置いても、それだけでは誰も処理しない（live bot が inactive でも「failed」でなければ watchdog は起こさない）
- live-operator.md の「Wake reasons」にある「検知なしが `IDLE_BEFORE_STOP` 続き、待っていたイベントもなくなった」の値は 14 日（decision 2026-11-14-oneshot-leftovers-idle-pull-oracle の 2）。ただし **watchdog にこの条件の実装はない**: watchdog が live-operator を起こすのは、signer / gate の記録にない nonce、1 回の読み取りの間の L を超える減少、promote 以降の損失 30 USD 超、日次損失の上限、bot@ の failed だけ（12d から、`holding_usd` のある bot は 2 つの線がそれぞれ `holding_usd` だけ上がる）。当面は meta が、検知も送信も 14 日ない live bot の停止を inbox/human に勧める（止めるのは人間）
- earner の起動の間引き（meta の提案、11-16）は採らない（11-17、人間。earner はローカルのモデルで費用がほぼかからず、間引いても稼ぎは増えない）。代わりに researcher を 1 日 8 回にした

## 全体像

（図: Farm 全体像 · エージェント / ワークスペース / 読み取り系 / 資金系 / mainnet — 旧 Claude Doc 参照）

エージェントはワークスペースのファイルと relay の読み取りだけで仕事をし、送信は farmgate 配下の signer が relay の farmgate 専用 unix socket（`/run/farm-relay/send.sock`）から行う。bot は paper 時は fork に対して検証し、live 時は同じ `run.sh` が signer に executor 呼び出しを依頼する。

## 資金とリスク上限

上限はすべてコード（gate / signer / watchdog）が強制する。エージェントのプロンプトにも同じ値を書いてあるが、プロンプトは説明であって境界ではない。値は `/etc/farm/gate.json`。

| 記号 | 値 | 意味 | どこで強制 |
|---|---|---|---|
| X | 2000 USD | リスクにさらす総資金（中間ウォレット + 全 live bot 残高、全チェーンのガストークンと USDC を含む）。全損は許容、超過は不可 | gate（promote / fund 時に残高合計を確認） |
| n | 200 USD / UTC 日 | 日次実現損失。超えたら**新規 promote を凍結**し live-operator を起こす。**稼いでいる bot や様子見中の bot は止めない**（運用者 の指示） | gate（promote 拒否）、watchdog（起床） |
| L | 50 USD / tx（11-06 に 20 から変更） | 1 トランザクションの最悪損失。executor 契約が利益なしで revert する前提で、最悪ケース = value + ガス（maxFeePerGas × gasLimit）。USD 換算は署名時点の Chainlink 価格（ガス価格の変動までは含めない） | signer |
| OP Stack の gas wallet cap | base 18 USD / optimism 18 USD（10b） | OP Stack の L1 データ費は gasLimit で上限が決まらないため、Base と OP Mainnet の bot のネイティブ ETH 残高を 18 USD 相当に制限。promote の資金事前確認も上限後の額で判定する（9i） | gate（fund 時）、signer（超過時に拒否） |
| 1 tx のガス上限 | 3,000,000（hyperevm は 2,000,000） | HyperEVM の small block は 2M gas。それを超える tx は big block にしか入らず、big block は送信元が HyperCore で `evmUserModify` を送って選ぶ必要がある（farm の鍵はしない）。値は farmchains.py の `max_tx_gas` | signer（bot の tx）、gate（executor 配備。hyperevm は promote の資金移動前に見積もって拒否、10b） |
| bot あたり | 400 USD | manifest の `capital_usd` 上限、日次送信合計の上限。`gate fund` の追加入金も、いまの wallet 残高（ネイティブ + USDC）+ 追加額がこれを超えるなら拒否（10e。それまでは promote 時と 1 回の fund 額しか見ておらず、fund を繰り返せば超えられた） | gate、signer |
| live の累計損失停止 | 30 USD（gate.json `max_live_loss_usd`）。12d から、`holding_usd` のある bot は 30 + `holding_usd` | promote 以降の損失 = pnl.json の baseline（gate が送ったネイティブと USDC。後の `gate fund` や sweep 時のガス補充を含む）− いまの bot wallet の残高（現在の Chainlink 価格）。超えたら `gate stop` して live-operator を起こす。executor の配備ガスも損失に入る。wallet の外（executor など）に置いた価値は損失扱い（12d の枠の bot は、`holding_usd` までを「別の資産になっている」と見て線を上げる。持ち高の時価は見ない）。あるチェーンが読めない周回と、baseline のない bot は判定しない（後者は journal に 1 度だけ）。11-10 の 10c までは bot 自身のコードの責任で、reviewer がクラッシュ耐性まで審査していた。10e から: `gate stop` が終わらなかった（bot がまだ bots/live にある）場合は 10 分ごとにやり直し、1 回目と以後 6 回ごとに live-operator を起こす。live から消えた ID は忘れるので、同じ ID で再 promote された bot も判定される（それまでは watchdog を再起動するまで対象外だった） | watchdog（10c、10e、12d） |
| 持ち高の枠（12d） | 合計 200 USD / 1 本 100 USD（gate.json `max_holding_usd_total` / `max_holding_usd_per_bot`） | manifest に `holding_usd` と書いた bot だけが、USDC で別の資産を買って executor に持ち、後の tx で売り戻せる（「残高が増えなければ revert」の例外）。枠の合計がそのまま追加の最悪損失。`holding_usd` ≤ `principal_usdc`、`holding_max_hours` ≤ 168、executor に引数なしの `exitAll()`。詳細は `farm/farm-handover-7-holding-frame.md` | gate（promote）、watchdog（線を上げる） |
| 送り先 | manifest の `allowed_contracts` + 中間ウォレット + 自 bot の executor | それ以外の to は署名拒否 | signer |
| approve | 許可コントラクトへの有限額のみ | 無限 approve は拒否。`increaseAllowance(address,uint256)` も同じ規則（10e。USDC にはこの関数があり、それまでは相手も額も確かめずに通っていた） | signer |

- 実現 PnL は sweep（bot 停止時に残高を中間ウォレットへ戻す）時点で `/var/lib/farmgate` の台帳に記録。baseline（promote 時の資金）は sweep 成功時にのみ消費される（二重 sweep で +5.0 USD が出た不具合の対策）
- baseline の保存（10e）: promote と `gate fund` は送金 1 本ごとに pnl.json を保存する。それまでは全チェーンの送金が終わってから 1 度だけで、2 チェーン目の送金で失敗すると、資金は入ったのに baseline のない live bot ができた（累計損失停止が判定できず、sweep でも PnL が出ない）
- sweep の記帳（10e）: `sweep()` は途中で例外が出ても、そこまでの記帳を pnl.json に保存する（それまでは後のチェーンの RPC 失敗で先のチェーンの記帳が消え、次の sweep が空の wallet を「principal gone」と読んで元本全額を損失計上しえた）。送信の呼び出しが失敗した送金（relay のエラーやタイムアウト。実際には届いていることがある）は、nonce と額を pnl.json の `sweep_unsure` に覚え、gate.log の `sweep_failed` にも nonce を付ける。次の sweep で wallet が空で、bot の nonce がその値より進んでいれば「届いていた」と見て、そのとき wallet にあった額が戻ったものとして記帳する（nonce が進んでいなければ従来どおり）。例外は RuntimeError 以外（ソケットのタイムアウトなど）も捕まえる。`poll_receipt` は読み取りの失敗では待ちを打ち切らない
- 空になったガス wallet（10e）: ネイティブ残高が送金手数料に満たない（何も送れない）チェーンでも、baseline があればその差を実現損失として記帳し、baseline を消費する。それまでは「swept 0」で終わり、ガスを使い切った bot の損失が台帳に残らなかった（日次損失 n にも入らなかった）
- L2 の sweep は L1 データ費分を予約（手数料 1.2 倍 + 21000 × maxFee を余分に残す）
- USDC 元本（phase 7）: manifest の `principal_usdc`、`gate fund --usdc`、sweep で USDC も戻す。X / PnL / watchdog / signer が USDC を含めて計算する。USDC の桁数はチェーンごと（farmchains.py の `usdc_dec`、BSC の Binance-Peg USDC は 18 桁、他は 6 桁。10b で gate / signer / watchdog の全箇所を一般化）。signer が「USDC トークン」と見なすのは、その bot のチェーンの USDC アドレスだけ（10b まではどのチェーンの USDC アドレスも許していた）
- USDC の sweep（9i）: 送金直後に nonce 付きで `sweep_usdc_sent` を gate.log に書き（watchdog が既知の nonce として扱う）、レシートを最大 180 秒待つ。返らなければ `pnl.json` の `usdc_in_flight` に残し、次の sweep がレシートから確定する（空のウォレットを「principal gone」と読んで元本全額を損失計上しないため）。revert は失敗扱いで baseline を残す
- promote の資金: ネイティブは `(capital_usd − principal_usdc) / チェーン数` を送るが、上限のあるチェーンでは上限まで。事前確認は実際に送る額 + 0.001 ETH を中間ウォレットに求める（9i 以前は上限前の額を求めていた）。10b で加えたチェーンでは、予備は 0.001 ネイティブと「送金 tx（ネイティブ 21,000 + USDC 90,000 gas）× maxFee × 2」の大きい方（0.001 POL では 1 回分のガスにも足りないため）。gate の手数料は、新しいチェーンではノードの `eth_maxPriorityFeePerGas` を下限にする（Polygon は優先手数料の最低額を強制する）

### promote の基準（11-09 に緩めた）

すべて満たせば promote してよい。

1. 仕組みの再現: reviewer が fork 上で成功（利益）と、ガードによる revert（元本が戻る）の両方を自分で再現した
2. 配備できる: `tools/manifest-check.py` が PASS
3. 損失の上限: 1 tx の最悪損失が L 以下で、コードで保証されている
4. 検知の妥当性: paper のログで、待っているイベントを正しく監視していることが確認できる。**実際の機会を paper で利益の出る形で捉えたことは、もう必須ではない**
5. live 試行の損切り: 累計損失 30 USD で止まる。11-10 から watchdog が強制するので、これで満たされたものとする（decisions/human/2026-11-10-live-loss-stop-watchdog.md）。reviewer は bot 側の損失記録のクラッシュ耐性で fix にしない。bot 側の自己停止はあってよいが必須ではない

最初の promote では、gas 用のネイティブ資産を最小限だけ渡す。USDC 元本は、元本のガードを reviewer が fork で再現した場合だけ渡す。gate が資金不足で拒否したら、reviewer は必要額を inbox/human に出す。送信がないだけでは demote しない。2 週間後（11-23 ごろ）に meta が、この基準を続けるか締め直すかを提案する。

持ち高の枠の bot（12d、decision 2026-11-15-holding-frame。プロンプト側の規則）: 基準 1・3・5 を読み替える。買う tx の成功と値段が合わないときの revert、`exitAll()` を買った直後と時間を進めた後の両方で呼んで USDC が戻ること、出口のプールの厚みが持ち高の 10 倍以上、README に最悪の損失、期待収益は 1 往復ごと。詳細は `farm/farm-handover-7-holding-frame.md` の「プロンプト」。

11-11 の decision（2026-11-11-moonwell-stopped）で加えた運用上の条件: reviewer は promote の前に live での 1 日あたりの Alchemy 消費の見積もりを review.md に書く。1 本で 1 日 1M CU を超える bot は根拠を inbox/human に出してから promote する。清算をポーリングで待つ型は、ポーリングで取れる根拠と CU 見積もりを manifest か README に書く。これはプロンプト側の規則で、コードは強制していない。

速度勝負の線引き（decision 2026-11-14-race-rule-seconds。11-13 の next-block-feed のブロック数による線引きを改めたもの。プロンプト側の規則）: ブロック数ではなく farm の反応時間で決める（Base は 11-05 から 0.2 秒/ブロックで、2 ブロックが 0.4 秒にしかならないため）。T = 取れる状態になったブロックの時刻、R = そのチェーンでの farm の反応時間（実測するまで全チェーン 3 秒。earner が測って wiki `infra/reaction-time.md` に記録）、L = 時刻が T + R 以上の最初のブロック。相手が L より前に取っていれば対象外（`blocked_infra`）、L か L から R 秒未満なら feed で待つ bot は試してよいが期待収益に数えない、L から R 秒以上後なら数えてよい。R = 3 秒なら ethereum では以前と同じ結果（同じブロックは対象外、次のブロックは試行のみ、2 ブロック以上は数える）、Base では 3 秒未満が対象外、3〜6 秒が試行のみ、6 秒超が数える。ポーリングで待つ bot は今までどおり（ポーリング間隔 + 取り込みまでの時間より短い事例は数えない）。期待収益は事例ごとに「粗利 − ガス代」で数える（decision 2026-11-13-morpho3-stop-ev-net-of-gas）。

期待収益と費用（decision 2026-11-12-morpho-stop-researcher-runs の 6、2026-11-13-morpho3-stop-ev-net-of-gas の 2・3。プロンプト側の規則）: README に事例ごとの粗利・ガス代・差し引きを書き、reviewer は README の合計を使わずに自分で計算し直す。1 日の CU は 100 万 CU ≒ 0.53 USD で値付けし、期待収益がそれ以下の bot は promote しない。lead を `dead_end` か `blocked_infra` で閉じるとき、その lead から作った live bot があれば、earner が停止の勧めを inbox/meta に書き、meta が inbox/human に回す（止めるのは人間）。

次のブロック型の試行（decision 2026-11-13-blocked-infra-feed-retriage の 3。上の「期待収益が CU の費用以下なら promote しない」の例外）: 次のブロックで取られる事例だけを狙う bot は数えられる期待収益が 0 になるので、次をすべて満たすものに限り promote してよい。feed の `/logs` で待つ（確認用のポーリングは 5 分以上の間隔）、1 日の CU の合計が 50,000 以下、`capital_usd` が 20 以下、過去 30 日に 1 ブロックで取られた粗利 50 USD 超の事例が 1 件以上、同時に live に置くのは 2 本まで。それ以外の審査は通常どおり。live で 14 日たっても送信が 0 件か、送信がすべて revert なら、停止の勧めを inbox/meta → inbox/human に出す。同じ decision で、`blocked_infra` の lead を feed で見直す作業（理由別の分類、速度が理由のものは過去の事例を 0 / 1 / 2 ブロック以上で数え直す）を earner に割り当てた。

単発の取り残し（decision 2026-11-14-oneshot-leftovers-idle-pull-oracle の 1。上の「期待収益が CU の費用以下なら promote しない」と、役割ファイルの「1 日 1 USD の床」の例外。プロンプト側の規則）: 清算できる状態（または同じように誰でも取れる状態）のまま 10 分以上残り、今の head でも残っているものは、同じ形が繰り返さなくても、1 回の差し引きで見て取りに行く。条件は次のすべて。head の fork で bot の wallet が増える成功の tx と、利益なしの revert。差し引き（wallet の増分 − executor の配備・実行・sweep のガス、今の base fee）が 10 USD 以上。担保の出口は実際のプールで換えた額で数える（オラクルの価格で数えない。出口のないものは対象外）。なぜ残っているかを 1 行で書ける（担保トークンの送金の制限・停止・ブラックリスト、止まっているオラクル、清算の権限を確かめる。分からなければ出さない）。capital は必要な最小限で、bot あたり 400 USD・L 50 USD などの上限はそのまま。ID は `oneshot-<対象>-<chain>`、README の先頭に「単発」。流れ: earner は見つけたセッションのうちに fork で実証して paper に置き（paper で機会を待たない）、reviewer は次の回で先に審査する。bot は 1 回取れるか対象が消えたら送信をやめ、earner か reviewer が inbox/meta に書き、meta が inbox/human に回して人間が `gate stop` する。promote から 48 時間で取れていなければ、同じ流れで停止を勧める。同時に live に置く単発の bot は 2 本まで（次のブロック型の 2 本とは別枠）。数字の線（10 分、10 USD、48 時間、2 本）は目安。

executor の準備の tx（inbox/meta 2026-11-15-morpho-nextblock-pool-init、meta が 11-15 05:15 JST に役割ファイルへ反映。プロンプト側の規則）: 配備の後に要る準備や owner の tx（売却先のプールの許可、approve、設定など）は、live の起動時に全部送り、済んだら `executor armed` を含む 1 行をログに出す。機会が来た時まで準備を残す bot は reviewer が fix にする。reviewer は promote の後、executor のアドレスの確認と一緒にこの行を確かめる。`tools/manifest-check.py` は、executor の ABI に準備用らしい関数があるのにコードに `executor armed` がないと警告する（警告で、拒否ではない。gate は確かめない）。きっかけ: morpho-nextblock-ethereum は、コンストラクタが許可するプールが 1 つだけで、残りは機会が来た時に `setPoolAllowed` を送ってその機会を飛ばす作りだった（11-14 23:02 JST の最初の送信）。この「機会の時に初期化する」ブロックは Morpho / Moonwell 系の bot にコピーされて広がっていた（archive の 29 本中 9 本）。

executor に狙いを焼き込まない（decision 2026-11-15-executor-no-baked-targets。プロンプト側の規則で、上の「executor の準備の tx」を改める。新しく出す bot と fix で戻った bot から適用し、11-15 時点の live 3 本は変えない）: 対象（市場の ID、借り手、トークン、売却先のプール、換金の経路）はコンストラクタの引数・storage・定数に入れず、実行の tx の引数で渡す。コンストラクタの引数は owner（`{bot}`）だけが基本で、プロトコル本体のアドレスは定数でよい。コールバックの呼び出し元は、許可リストを storage に持たず、owner が呼んだ入口で一時的に記録して照合し、tx の終わりに消す。配備の後に owner の tx が要る executor は作らない（どうしても要る場合だけ、起動時に送って `executor armed` を出し、README に理由を書く）。approve は実行の tx の中で使う額だけ出して 0 に戻し、tx の終わりに executor に残高を残さない（reviewer が fork の成功の tx の後で確かめる。12d の枠の bot は、持ち高だけは executor に残してよい）。単発の bot は live の起動の直後に最初の tx を送る。executor は Solidity で書き（Yul・Huff・手書きのバイトコードは出さない）、ソースを公開の場に出さない。配備と実行を 1 tx にまとめる形は signer（宛先のない tx を拒否する）と gate の変更が要り、人間が後で作る。それまで bot は作成 tx を送らない。
、2026-11-14-oneshot-leftovers-idle-pull-oracle の 3）: 区分は C（farm にない仕組みが要る）のままで、価格配信を受ける仕組みはいずれ作るが、今は作らない。作る時期は人間が決める。

## サーバー構成

ホストは farm-host（Ubuntu、LAN <lan-ip>、tailnet `<tailnet-host>`）。管理は `admin`（sudo 可）、エージェント・サービスは専用 OS ユーザー。境界は「OS ユーザー + nftables + systemd unit + sudoers」で、harness サンドボックスは使わない。

| OS ユーザー | 何を動かすか | 持つもの / 持たないもの |
|---|---|---|
| harness | codex / claude のエージェント（`agent@paper-reviewer` など）。node は nvm（`/etc/farm/farm.env` の HARNESS_PATH） | sudo なし。`kb-write` / `wiki-write` / `paper-ctl` / `gate` は sudoers で検証付きラッパーだけ許可 |
| earner | `agent@earner-local`（dsh。`/opt/farm/dsh` は root 所有） | prompt.md と headless patch は BindReadOnlyPaths で `~/.dsh/` に読み専用マウント。自分の指示を書き換えられない |
| farmbot | `paper@` / `bot@`（group farm、bot@ は SupplementaryGroups=farmbot） | 鍵なし。live 時は signer ソケットだけ |
| farmgate | farm-signer、gate-ctl、farm-watchdog、farm-dash | `/var/lib/farmgate/mnemonic`（0400）、accounts.json、台帳、gate.log（farmgate 以外は sudo で読む）。gate-root への sudo（bot ディレクトリの移動と所有権のみ） |
| farmrelay | rpc-relay、farm-feed（11a） | Alchemy キー（`/etc/farm/relay.json`）。send socket は farmgate グループのみ |
| farmfork | fork@base / arbitrum / ethereum / bsc / polygon / avalanche / optimism / hyperevm / ethereum-review（anvil） | relay の research レーンだけを見る |
| （DynamicUser） | farm-search（RustXNG） | ディスク状態なし |

| パス | 内容 |
|---|---|
| `/srv/farm/ws` | ワークスペース（kb/knowledge.db、wiki/、bots/{paper,live,archive}、claims/、scratch/、inbox/{human,meta,live}（回答済みは各 `done/`）、decisions/human/、logs/sessions/、reports/、ledger/ledger.db、tools/、history/）。inbox / scratch / logs / claims / bots/paper は group farm の default ACL |
| `/srv/farm/prompts` | `common.md`（root 所有、人間のみ）、`roles/*.md` + `TOOLS.md`（harness 所有、meta が改訂可） |
| `/srv/farm/runners/<instance>/prompt.md` | `assemble-prompt` が生成した完成プロンプト |
| `/opt/farm/bin` | run-role, assemble-prompt, record-run, kb, kb-write, wiki, wiki-write, rpc-relay, farm-feed（11a）, ledger, ledger-ingest, paper, paper-ctl, gate, gate-ctl, gate-root, farm-signer, farm-watchdog, farm-dash, farm-acl-fix, fork, websearch, bot-run（11c）, farm-explorer と explorer（12e）, farm-relayapi（12f）。各 phase の install が置換前のファイルを `.<name>.bak-<phase>` で残す |
| `/opt/farm/lib` | farmchains.py（10b。8 チェーンの chain id・Chainlink のネイティブ/USD Standard フィード・受け付ける description・USDC の桁数・価格の妥当範囲・1 tx のガス上限。gate-ctl / farm-signer / farm-watchdog が読む唯一の表）、farmkeys.py（BIP-39/44、EIP-1559 署名、ABI エンコード）、farmbot_signer.py（bot 側クライアント）、bip39-english.txt、rustxng（バイナリ）と rustxng.d/（LICENSE・NOTICE・SOURCE、AGPL-3.0 無改変） |
| `/opt/farm/dsh-plugins/` | dsh-web-search-rustxng（earner の web_search プロバイダ。headless プロファイルに `dsh plugin add` で導入） |
| `/opt/farm/context/` | 動的コンテキスト生成スクリプト（earner: 未完 bot、timeout したセッション；paper-reviewer: レビュー待ち） |
| `/opt/foundry/bin` | anvil / forge / cast（root 所有。`/usr/local/bin/forge`, `cast` はシンボリックリンク） |
| `/etc/farm` | roles.conf, farm.env, gate.json, relay.json, feed.json（11a）, ledger.json, ledger-sources.json, fork*.env, farm.nft, claude-settings.json, earner-headless.patch.yml, explorer.json と explorer.key（12e。key は Etherscan の API キーで root 600）, relayapi.json と relayapi.key（12f。key は Relay の API キーで root 600）。**エージェントは読んではいけない** |
| `/var/lib/farm/ops.db` | セッション実行記録（record-run）。journal_mode=DELETE |
| `/var/lib/farmgate` | mnemonic, accounts.json, 台帳（pnl.json：realized_usd / baseline / baseline_usdc / usdc_in_flight / sweep_unsure（10e））、gate.log、signer.log、halt フラグ |
| `/run/farm-relay/send.sock` | relay の送信専用 unix socket（farmgate グループのみ） |

| systemd unit | 役目 | 起動 |
|---|---|---|
| `agent@.service` | run-role でエージェント 1 セッション（RuntimeMaxSec 2h。earner は drop-in で 75 分、Restart=always、qwen-server 待ち、次の起動まで 5 分（`restart-delay.conf`、11-13）） | earner-local と earner-measure（12a。drop-in は `agent@earner-measure.service.d/`、プロンプトの読み専用マウントは unit ごと）: enable で常駐。他: timer |
| `farm-paper-reviewer.timer` / `farm-meta.timer` / `farm-researcher-codex.timer` / `farm-researcher-claude.timer` | 前回終了から 90 分 / 6 時間 / 毎日 04:10・13:10・19:10・22:10 JST / 毎日 01:10・07:10・10:10・16:10 JST。2 回目は drop-in `farm-researcher-{codex,claude}.timer.d/second-run.conf`（`OnCalendar=` は足し算。decision 2026-11-12-morpho-stop-researcher-runs）、3 回目は同じ場所の `third-run.conf`（11-15、decision 2026-11-15-widen-beyond-liquidations）、4 回目は同じ場所の `fourth-run.conf`（11-17、人間の判断。meta への知らせは inbox/meta/2026-11-17-human-researcher-8-runs.md）。researcher は合わせて 1 日 8 回、3 時間おき。`systemctl list-timers` の表示は UTC | — |
| `rpc-relay.service` | 127.0.0.1:8545 | RuntimeDirectory=farm-relay |
| `farm-feed.service` | 127.0.0.1:8546。Alchemy の WebSocket 購読を bot に渡す（11a）。rpc-relay・signer・bot とは独立 | enable、Restart=always |
| `ledger-ingest.timer` | 15 分ごと | — |
| `farm-search.service` | RustXNG、127.0.0.1:29483 | enable |
| `farm-explorer.service`（12e） | 127.0.0.1:29484。Etherscan V2 API への読み取り専用の中継で、API キーを持つ（下の「explorer」） | enable、DynamicUser、Restart=always |
| `paper@` / `bot@` | paper / live bot（enable 済みで再起動後も復帰、6o）。`bot@` の ExecStart は 11c から `/opt/farm/bin/bot-run`（executor のアドレスを環境に入れてから `run.sh`） | paper-ctl / gate からのみ |
| `farm-signer` / `farm-watchdog` | 鍵と監視（watchdog は drop-in で NoNewPrivileges=no、9g。manifest の chains は gate と同じ規則で読む、9i。1 チェーンの読み取り失敗で他を飛ばさない、10b。累計損失 30 USD で停止、10c。終わらなかった停止の再試行、manifest を読めないディレクトリを飛ばして続ける、signer / gate が失敗と記録した nonce も既知とする、10e。`holding_usd` のある bot の線を上げる、gate の `exit_*` の nonce を既知とする、12d） | enable |
| `fork@base` / `fork@arbitrum` / `fork@ethereum` / `fork@bsc` / `fork@polygon` / `fork@avalanche` / `fork@optimism` / `fork@hyperevm` / `fork@ethereum-review` | anvil fork（9001–9008、reviewer 専用 9013） | enable。MemoryMax=6G、stdout は捨てる |
| `farm-dash.service` | 127.0.0.1:8090 → tailscale serve で 9443 | SupplementaryGroups=farm farmrelay |
| `farm-acl-fix.timer` | ACL の補修 | — |
| `farm-nft.service` | nftables（`/etc/farm/farm.nft`） | — |

ネットワーク: earner と farmbot のローカル向け TCP は 53 / 8545 / 8546 / 9001–9009 のみ（10a で 9003 → 9008、10g で 9009、11a で 8546 = farm-feed）。earner は加えて 8003（Qwen サーバー）と 29483（farm-search）と 29484（farm-explorer、12e）と 29485（farm-relayapi、12f）。9013 は reviewer（harness）だけ。それ以外のローカルポートは reject。外向けは自由（web 検索・DefiLlama 用）。

explorer（phase 12e、11-15 適用）: エージェントが、分かっているアドレスの検証済みソース・ABI・配備の tx・取引履歴を Etherscan から取るための道具。`/opt/farm/bin/explorer`（CLI）が `farm-explorer.service`（127.0.0.1:29484）を呼び、サービスが Etherscan V2 API（`https://api.etherscan.io/v2/api`）に API キーをつけて問い合わせる。

- キーは `/etc/farm/explorer.key`（root 600、人間が置く）。サービスは systemd の credential として受け取り、エージェントからは読めない。応答とエラーからはキーの文字列を消す
- 通すのは 6 つの操作だけ（`source` = getsourcecode、`abi` = getabi、`creation` = getcontractcreation、`txs` = txlist、`internal` = txlistinternal、`tokentx`）。呼び出し側が渡した module / action / apikey などは上流に渡らない。アドレスは 0x + 40 桁だけ、件数は 200 まで
- **名前からアドレスを引く検索はない**（Etherscan の API にない）。名前 → アドレスは、今までどおり docs・リポジトリ・DefiLlama の adapter・オンチェーンの getter で確かめる
- 設定は `/etc/farm/explorer.json`（チェーン名 → chain id、呼び出しの間隔 0.4 秒、1 日 20,000 回の上限。秘密なし）。`source` / `abi` / `creation` の答えは 1 日キャッシュする
- 使えるチェーンはキーの契約で決まる。**11-15 の適用時: ethereum・arbitrum・polygon・hyperevm が ok、base・bsc・optimism・avalanche が not_on_plan、elysium は unsupported（Etherscan が扱っていない）**。`explorer chains` が 1 チェーン 1 回の呼び出しで確かめて表示する（ok / not_on_plan / unsupported。6 時間たてば確かめ直す）。Etherscan の無料の枠は 2025-11 から BSC・Base・OP Mainnet・Avalanche が対象外で、HyperEVM は 2026-12-01 から有料のみ（人間、11-15）。対象外のチェーンでは「not on this API key's plan」と返すので、そのチェーンのエクスプローラーや Routescan を今までどおり直接使う
- nftables: earner は 29484 に届く。farmbot（bot）は届かない
- claude の役は `Bash(explorer *)` を許可（run-role の `common`）。codex と dsh は制限なし
- farm-dash のサービスの数（16）には入っていない

relayapi（phase 12f、11-16 適用）: Relay（relay.link）の API を、人間の API キーをつけて呼ぶための中継。`farm-relayapi.service`（127.0.0.1:29485、DynamicUser、Restart=always）。エージェントは `https://api.relay.link/<path>` の代わりに `http://127.0.0.1:29485/<path>` を呼び、サービスが `x-api-key` をつけて `https://api.relay.link` に渡す。

- キーは `/etc/farm/relayapi.key`（root 600、人間が置く）。systemd の credential で渡し、エージェントからは読めない。応答・エラー・ログからキーの文字列は消す。チャットや文書には書かない。
- 通すのはデータの口だけ: GET `/chains` `/requests` `/intents/status` `/currencies` `/config` `/price`、POST `/quote` `/price` `/currencies`（`/quote/v2` のような下位のパスを含む）。ほか（`/execute` など）はサービスが 403 で断り、Relay には送らない。tx を送る力はない。
- 設定は `/etc/farm/relayapi.json`（通すパス、間隔 0.2 秒、1 日 50,000 回の上限。秘密なし）。`GET /health` で当日の回数。
- farm.nft: earner は 29485 に届く。farmbot（bot）は届かない。run-role は変えていない（`Bash(curl *)` は既にある）。
- TOOLS.md に `relayapi` の行（`explorer` の行の後）。
- 目的: decision 2026-11-15-cross-chain-gap-relay の 7（見積もりと実際の費用のずれ）。`/requests/v3` がキーなしでは使えなかった（lead 191）。
- 適用時の確認（11-16）: 実際のキーで `/chains` と `/requests/v3?limit=1` が 200、`/execute/swap` は 403、キーは journal に出ていない、earner は届き farmbot は refused。エージェントが実際に使った結果はまだ見ていない
- farm-dash のサービスの数（16）には入っていない

## 鍵管理と署名

鍵は 24 語の BIP-39 シード 1 つだけ（`/var/lib/farmgate/mnemonic`、farmgate のみ 0400）。Rabby / MetaMask / ハードウェアウォレットに同じ 24 語を入れれば、このコードなしで全アドレスが復元できる（運用者 の要求で生の秘密鍵から切り替え）。シードはオフラインに控え済み、Rabby からは削除済み。

| 項目 | 内容 |
|---|---|
| 導出パス | `m/44'/60'/0'/0/<i>`。index 0 = 中間ウォレット（入金先、sweep の戻り先）。bot は promote 時に 1, 2, 3… を順に割当（`/var/lib/farmgate/accounts.json`、`gate accounts`） |
| 実装 | `/opt/farm/lib/farmkeys.py`（純 Python + coincurve：ニーモニック→seed→BIP-32→EIP-1559 署名、`selector` / `encode_call` で ABI エンコード） |
| 署名経路 | live bot → `$SIGNER_SOCK`（unix socket）→ farm-signer が peer credentials + cgroup で `bot@<id>` を特定 → ポリシー検査 → 署名 → relay の send socket で live レーン送信（Alchemy のみ）。送信の呼び出しが失敗したら、どの例外でも（ソケットのタイムアウトを含む）nonce 付きで `decision: broadcast_failed` を signer.log に残す（10e。それまでは RuntimeError だけで、タイムアウトでは記録が残らなかった） |
| 非公開の送信（12b、11-15） | ethereum だけ。live の manifest に `send_route: private` と書いた bot の tx を、signer が relay の send socket に `?route=private` をつけて渡し、relay が `relay.json` の `private_send`（`https://rpc.flashbots.net/fast` = Flashbots Protect RPC）に送る。**失敗しても Alchemy や公開ノードには落とさない**（非公開のつもりの tx を公開しないため）。対象のチェーンは gate.json `private_send_chains`（なければ `["ethereum"]`）で、それ以外のチェーンは `send_route: private` の bot でも Alchemy に送る。検査（L、送り先、approve、1 日の枠）は公開と同じ。signer.log の `sent` / `broadcast_failed` と bot への返事に `route`（`public` / `private`）が入る。非公開の tx は載るまでノードから見えないので、載る前に同じ bot がもう 1 本送ると同じ nonce になり、前の tx を置き換える（載るのは高々 1 本）。gate の配備・sweep・cancel は公開のまま。`gate stop` の sweep が古い非公開の tx と同じ nonce になり、古いほうが先に載った場合は「未完の stop」になるので、`gate stop` をやり直す。送るたびに最悪額が 1 日の枠に足される点は公開と同じ（載らなければ費用はかからないが枠は減る）。11-05 の「送信は Alchemy のみ」は「公開の送信は Alchemy のみ、非公開の送信は Flashbots Protect のみ」になった。設計は `farm/design/design-2026-11-15-private-send.md`。**エージェント向けの規則は 12c（11-15）で役割ファイルに入れた**（プロンプト側の規則で、コードは強制しない）: executor の入口に期限のブロック番号を持たせて過ぎたら revert（2〜3 ブロック先、fork で再現）、送信後は期限まで receipt を見て載らなければ `private_not_included` をログに出す、executor から `block.coinbase` に払わない、README に非公開にする理由を 1 行、reviewer はこれらを確かめてから promote（decision 2026-11-15-private-send）。**実際の tx が非公開で載ること、載るまでのブロック数、revert する tx が載らないことは未確認**（最初に使う bot の最初の送信で確かめ、結果は inbox/human に回る） |
| bot 側 API | `/opt/farm/lib/farmbot_signer.py`: `my_address()`, `send(chain, to, value, data, gas, max_fee_per_gas)`, `limits()` |
| 価格換算 | 各チェーンのネイティブトークンの Chainlink Standard フィード（ETH / BNB / POL / AVAX / HYPE、8 桁。SVR ではない）。表は `/opt/farm/lib/farmchains.py`（10b、それまでは 3 プログラムが ethereum / base / arbitrum を個別にハードコード）。signer 起動時に全チェーンで `decimals()==8` と `description()`（チェーンごとに受け付ける文字列。Polygon は "MATIC / USD" も可）を検証し、元の 3 チェーンで失敗すれば起動拒否、10b で加えたチェーンで失敗すればそのチェーンだけ署名を止める（signer.log に `chain_disabled`、signer を再起動すれば再検証）。価格は gate / signer / watchdog のどれもチェーンごとの妥当範囲で確かめ、外れたら使わない |
| executor のコード | gate-ctl `executor_code()`（10b で `deploy_executor` から分離）: artifact の creation code + `executor_args`。`check_deploy_gas()` が hyperevm で配備の見積もり × 1.2 が 2M gas を超える promote を、資金を動かす前に拒否。`deploy_executor` も送信前に同じ上限を見る。10f から: promote は artifact と `executor_args` を、bot を live に移す前に必ず読む（読めなければ移動と送金の前に拒否。それまでは移動と送金の後に読んでいた）。manifest のパスが `bots/paper/<id>/…`（bot 自身のディレクトリ内）なら、移動後は `bots/live/<id>/…` の同じファイルを読む |
| executor デプロイ | gate-ctl `deploy_executor`: bot 自身の鍵で forge artifact + manifest の `executor_args` をデプロイ（`{bot}` は bot のアドレスを 32 バイトにパディングして差し込む）。送信直後に gate.log へ `deploy_executor_sent`（nonce 付き）を記録し、レシートを待って status 0x1 でなければ promote を中止。アドレス = keccak(rlp([sender, nonce]))。signer が許可先に自動追加。10f から: 配備の前に `state/executor.json` を確かめ、その bot の鍵と記録の nonce から導いたアドレスと一致しないファイル（archive からコピーされた他の bot のものなど）は消す（gate.log に `stale_executor_state_removed`）。消せなければ配備の前に止まる。`gate-ctl deploy` の「すでに executor がある」も、ファイルの有無ではなくこの一致で判定する |
| gate が bot の鍵で送る tx | 配備・sweep・sweep_usdc・cancel は必ず nonce 付きで gate.log に記録する（人間側の開発ルール）。sweep の nonce は署名前に読んだ値（9i）、USDC は送信直後に `sweep_usdc_sent`。送信の呼び出しが失敗した sweep / cancel も、nonce 付きで `sweep_failed` / `cancel_failed` を残す（10e）。watchdog は signer の記録（`sent` と、10e から `broadcast_failed`）か gate.log の記録（sweep / sweep_usdc / sweep_usdc_sent / cancel / deploy_executor_sent / deploy_executor と、10e から nonce 付きの sweep_failed / cancel_failed、12d から exit_sent / exit / exit_failed）に無い nonce の前進を「鍵の漏洩の可能性」として halt する。失敗と記録された送信を既知に含めるのは、relay がエラーやタイムアウトを返しても tx が実際には届いていることがあり、そのたびに全 bot を halt・sweep するのを避けるため。12d から、`holding_usd` のある bot の stop では executor の `exitAll()` も bot の鍵で送る（送信の直後に `exit_sent`） |
| 1 本だけ鍵を出す | `sudo -u farmgate /opt/farm/bin/gate-ctl export-key intermediate`（管理ユーザーからのみ） |
| バックアップ | `sudo cat /var/lib/farmgate/mnemonic` を紙に。チャットやリポジトリには絶対に貼らない |

エージェントに秘密鍵を持たせない理由: 当初「live 運用監視が自分の bot を止められるか」が不安点だったが、bot を systemd サービスとして gate が起動・停止する形にしたことで、誰でも（人間も watchdog も）`gate stop` で止められる。鍵を持つプロセスは farm-signer と gate-ctl だけ。`gate stop --all` は 1 本の停止が例外で失敗しても残りを止め続け、`stop_failed` を gate.log に残す（9i）。

## bot のライフサイクル

（図: bot のライフサイクル · 6 段階と watchdog — 旧 Claude Doc 参照）

各段階の条件:

| 段階 | 誰が | 条件・ルール |
|---|---|---|
| paper 作成 | earner | `claims/` でターゲットをロック。先に KB `attempts`（`lead_recorded`）と `scratch/report-<run>.json` を書く。最後に `paper_placed`。manifest 必須: id, chains, strategy, capital_usd, allowed_contracts, max_loss_per_tx_usd, max_loss_guarantee, executor, executor_args, fork_evidence |
| paper 実行 | paper-ctl（farmbot） | `paper start <id>` で `paper@<id>` を起動（reset-failed してから起動し、3 秒後に実状態を確認）。bot は自分のセッションから nohup / & で起動してはいけない |
| レビュー | paper-reviewer | executor の Solidity を読み、`fork_evidence` の成功・revert を fork（ethereum は専用の 9013）で自分で再現。EOA がプロトコルを直接呼ぶ bot は常に fix。コードハッシュをスナップショット（reviewer 自身が実装） |
| promote | gate（reviewer が呼ぶ。人間も可） | executor の配備ガスを全チェーンで見積もり、1 tx の上限を超えるか見積もれなければ拒否（10l。それまでは hyperevm だけ）。n 凍結中は拒否。X 超過は拒否。`capital_usd` ≤ 400。manifest に `executor:` があるのに、bot のコードのどこも `EXECUTOR_ADDR` と `executor.json` に触れていなければ拒否（10e）。executor の artifact と引数が読めなければ拒否（10f）。中間ウォレットに実際に送る額があるかを確認（9i）。`holding_usd` のある manifest は、1 本 100・live の合計 200・`principal_usdc` 以下・ABI の `exitAll()`・`holding_max_hours` 168 以下を満たさなければ拒否（12d）。ここまでは何も動かさない。その後 `gate-root` が `bots/paper/<id>` → `bots/live/<id>` に移動（以後読み専用）し、資金を送り（送金ごとに baseline を保存、10e）、**レシートを待ってから** executor を配備（9f）してサービスを起動。途中で止まった promote は `gate-ctl deploy <id>` で再開 |
| live | bot@ + signer | 送信はすべて signer がポリシー検査。拒否は最終回答（回避禁止）。累積損失 30 USD で watchdog が `gate stop`（10c。`holding_usd` のある bot は 30 + `holding_usd`、12d） |
| stop / sweep | gate（live-operator、人間、watchdog） | `gate stop <id>` → `bot@<id>` 停止 → 残高を中間ウォレットへ sweep → PnL 記録 → `bots/archive/<id>/ARCHIVE.md`。**sweep が未完なら archive しない**（10e）: サービスは止まるが bot は bots/live に残り、X にも数えられ watchdog も見続ける。gate は「the sweep is incomplete」と出して終了コード 3、gate.log に `stop_incomplete`。`gate stop <id>` をやり直すと続きから進み、全部戻れば archive する。`gate sweep <id>` も未完なら終了コード 3。あるチェーンの nonce が読めなくても、他のチェーンの cancel と sweep は進める。**`holding_usd` のある bot は、sweep の前に executor の `exitAll()` を呼ぶ**（12d）: 失敗したら何も sweep せず、「its holdings are NOT back」と出して終了コード 3、bot は live に残る。その先は人間が決める（live-operator は stop をやり直さず inbox/human に書く）。失敗した tx が 3 本たまると `gate-ctl stop <id> --exit-again` を待つ |

manifest の書き方（9e 以降）:

- `executor`: forge artifact のパス 1 つだけ（ワークスペースからの相対パス）。scratch/ 以下でも、bot 自身のディレクトリ内（`bots/paper/<id>/contracts/out/…`）でもよい（後者は 10f から。promote で bot が live に移っても gate が追う）。説明は `executor_note` に書く
- `executor_args`: ABI エンコード済みの 16 進数。コンストラクタに bot 自身のアドレス（owner など）を渡すワードは `{bot}` と書く（固定アドレスを書くと live で呼べない executor ができる）。msg.sender を owner にする作りなら不要
- `allowed_contracts` / `chains`: ブロック形式、インライン形式、マッピングのリストのどれでもよい。行末のコメントは無視される。ブロック内のアドレスはすべて許可対象（コメント内と別キーのアドレスは対象外）。gate・signer・watchdog が同じ規則で読む（watchdog は 9i から）
- `allowed_contracts` に書くのは、bot の wallet が自分で tx を送る相手だけ。executor を通して動く bot は空でよい（`allowed_contracts: []`。gate が配備した executor を signer が state/executor.json から自動で許可する。gate は 10d から executor があれば空を受け付け、executor がなければ 1 件以上を求める）。executor が中で呼ぶプロトコルや fork 上の executor アドレスを書くと、bot の wallet がそこへ直接送れてしまう（decisions/human/2026-11-11-executor-bots-funds.md）
- live の bot は executor のアドレスを環境変数 `EXECUTOR_ADDR`（なければ `state/executor.json`）から読む。**この環境変数を実際に渡すようになったのは 11c（11-14）から**: `bot@` は drop-in `bot@.service.d/executor-env.conf` により `/opt/farm/bin/bot-run /srv/farm/ws/bots/live/<id>` で起動し、bot-run が `state/executor.json` を読んで `EXECUTOR_ADDR_<CHAIN>`（チェーンごと）と `EXECUTOR_ADDR`（全チェーンで同じアドレスのとき）を設定してから `run.sh` に切り替わる。ファイルがなければ何も設定せずに `run.sh` を起動する。環境に元からあった値よりファイルを優先する（signer が許可するのはファイルのアドレス）。それまでは unit が `BOT_MODE` `BOT_ID` `RPC_*` `SIGNER_SOCK` しか渡しておらず、`process.env.EXECUTOR_ADDR || '<fork のアドレス>'` と書いた bot は fork のアドレスで live を走っていた（下の落とし穴の表）。paper では使わないので審査で見えない（11-10 の reserve-dutch は `EXEC_ADDRESS` を読んで再起動ループ）。10e から gate が promote 時に確かめる: bot のディレクトリのコード（`.md` `.yaml` `.yml` `.json` `.sol` `.log` `.txt` `.lock` `.toml` と node_modules / logs / state / .git 以下を除く、2 MB 以下のファイル）のどれかに `EXECUTOR_ADDR` か `executor.json` という文字列がなければ、資金を動かす前に拒否する。manifest-check も同じ確認をする（meta が 11-11 に反映）
- `send_route`（12b）: `private` と書くと、ethereum での送信が非公開の経路になる。書かないか `public` なら今までどおり。それ以外の値は signer が送信のたびに拒否する。gate と manifest-check はこのキーを見ない（11-15 時点）
- `holding_usd` / `holding_max_hours`（12d）: 持ち高の枠を使う bot だけが書く。`holding_usd` は別の資産で持ってよい上限（USD、100 以下、`principal_usdc` 以下）、`holding_max_hours` は持つ時間の上限（168 以下）。書かない・0・空欄なら今までどおり。gate と watchdog が読む。manifest-check はまだ見ない（meta に依頼済み）
- archive した live bot を paper に戻すとき、`state/executor.json` は一緒にコピーしない（前の bot の鍵で配備した executor のアドレスが入っている）。コピーされていても 10f から gate が配備の前に消すが、paper の時点で無いのが正しい
- 資金として数えるのはネイティブと gate.json の USDC だけ（X、停止時の sweep、watchdog の累計損失）。executor は利益をそのどちらかで bot の wallet に返す。他のトークン（ETH+、WETH、LP など）で返した分は sweep で戻らず、累計損失では損失扱い。12d の枠の bot だけは、`holding_usd` までを executor に別の資産で持ってよい（X には数えられず、`gate stop` の `exitAll()` で USDC に戻してから sweep する）

全ループは `selfping`（自分宛て 0 ETH 送金）で promote → fund → signer ポリシー拒否 → stop → sweep まで実資金で確認済み。実際の bot の promote は 11-09 が最初（経緯は運用記録）。USDC を持つ bot の sweep は、実資金ではまだ一度も通っていない（9i・10e のオフラインテストのみ）。10e の sweep / stop の変更（未完時に archive しない、`sweep_unsure`、空の wallet の記帳）も、実資金では未確認。10f の `gate-ctl deploy` による再開は 11-10 に reserve-dutch-ethereum-v2 で実資金で通った。12d の持ち高の枠（promote の検査、stop の `exitAll()`、watchdog の線）も、実資金では未確認（オフラインテスト 37 件のみ。最初の 1 本は `holding_usd` 20 程度で通す）。
