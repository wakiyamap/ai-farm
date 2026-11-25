> Farm の仕様書の一部（RPC relay と ledger、feed、fork と executor 契約、web search）。1 つ目の文書と一覧は `farm/farm-handover.md`。

# Farm 仕様書（続き）

## RPC relay と ledger

チェーンの読み取りはすべて `rpc-relay`（127.0.0.1:8545、`/<chain>?lane=<lane>`）を通る。Alchemy キーは relay だけが持ち、エージェントには見せない。「いつ読むか」を知らせるのは farm-feed（8546、次の節）で、状態の読み取りは feed を使う bot でも relay を通る。

| 項目 | 内容 |
|---|---|
| レーンと日次 Alchemy CU 予算 | live 1,500,000 / paper 900,000 / research 1,000,000（`/etc/farm/relay.json` の `alchemy_daily_cu`。research は 11-09 に 500k を使い切って引き上げ）。優先度 live > paper > research。**live は予算で絞らない**（読み取りも送信も常に Alchemy 優先。予算は paper / research の Alchemy フォールバックだけを止める）。Alchemy の月間枠は 95.2M。月間枠を守る仕組みはない（尽きると全 bot の送信が止まる。運用記録の保留事項）。11b から、ダッシュボードが今サイクルの累計と着地の見込みを出す（見えるだけで、止める仕組みではない） |
| プロバイダ順 | live: Alchemy → 公開。paper / research: 公開 → Alchemy（予算内のとき）。`debug_*` / `trace_*` / `alchemy_*` / `eth_simulateV1` と過去状態の読み取りは常に Alchemy 優先（6k）。`eth_sendRawTransaction` は Alchemy のみ（6j） |
| 空応答の検証（6y） | 公開ノードの空に見える応答（getCode / eth_call の "0x"、null のレシート）は次のプロバイダ（Alchemy）で確かめてから信じる。Alchemy が空でない値を返したら、その公開ノードを 5 分休ませる。空応答はキャッシュしない。revert 以外の公開ノードのエラーは次のプロバイダへ回す |
| 公開ノード | base: mainnet.base.org, base-rpc.publicnode.com · arbitrum: arb1.arbitrum.io/rpc, arbitrum-one-rpc.publicnode.com · ethereum: ethereum-rpc.publicnode.com, eth.drpc.org · bsc: bsc-dataseed.bnbchain.org（eth_getLogs 不可）· polygon: polygon.drpc.org · avalanche: api.avax.network/ext/bc/C/rpc · optimism: mainnet.optimism.io · hyperevm: rpc.hyperliquid.xyz/evm（10a）。User-Agent ヘッダ付き（無いと 403） |
| 許可メソッド | 読み取り専用。`eth_sendRawTransaction` は `/run/farm-relay/send.sock`（farmgate グループのみ）からのみ |
| キャッシュ | メソッドごとの TTL。"latest" / "pending" / "safe" / "finalized" や block 省略の呼び出しは最大 1 秒（6w） |
| エラー | 上流の HTTP エラーはプロバイダの理由文付きで返す（API キーは消す、6x） |
| 状態 | `GET http://127.0.0.1:8545/health` で当日の CU 消費。ダッシュボードの Alchemy CU today はこれ（farm-feed の分は入らない。feed の分は 11b から別のタイル Feed CU today に出る） |

`ledger-ingest`（15 分ごと、research レーン）は `/etc/farm/ledger-sources.json`（人間所有：aave_v3 / morpho_blue の liquidation など）と `ws/ledger/sources.d/`（エージェントが `ledger add-source` で追加、最大 40）のイベントを `ws/ledger/ledger.db` に取り込む。バックフィル 7 日、実行あたり 20,000 CU 上限、アドレスは初回に `eth_getCode` で検証。エージェントの source は実行あたり 6,000 CU を、毎回開始位置をずらして均等に分ける（1 source あたり最低 600 CU、9e）。同じ (source, チェーン) の emitter は、同じブロックまで進んでいるものをまとめて 1 回の `eth_getLogs`（アドレスのリスト）で読む（10h）。先端に追いついた source の費用は emitter の数によらずチェーンあたり 60 CU/回。遅れている emitter（追加されたばかりでバックフィル中）を先に単独で進め、他に追いついたら同じ呼び出しに合流する。その間、先端にいる emitter は待つ。10h より前は emitter ごとに 1 回ずつ読んでいたため、先端の維持だけで 60 CU × emitter 数がかかり、600 CU の枠では 1 source の 12 個目以降の emitter と 2 つ目以降のチェーンが永久に初期化されなかった。actor が `tx_from` の source（イベントごとにレシートを 1 回読む）は、範囲の途中で予算が尽きたら、保存できなかった最初のブロックで cursor を止める（10h より前は範囲の終わりまで cursor が進み、残りのイベントを落としていた。それ以前に落ちた分は戻らない）。`ledger top` / `ledger query` / `actor_daily` で誰が稼いでいるかを引ける。journal_mode は DELETE（WAL は読み手に -shm の書き込み権が要るため）。

source の event（9d 以降）: 動的型・タプル型・配列を含む完全な正規シグネチャを書く（topic0 はその keccak256）。`indexed` は先頭の indexed パラメータに順に名前を付ける（動的型は topic のハッシュのまま）。`data` は先頭から続く静的な 1 ワード型だけに名前を付け、後ろの動的型は省略する。indexed と非 indexed が交互に並ぶイベントは actor_field を tx_from にする。topic0 が合わないと、ハッシュしたシグネチャと計算値がエラーに出る。

farm 自身の live レーン消費（10i）: live レーンを使うのは bot だけではない。watchdog と `gate-ctl status`（ダッシュボードが呼ぶ）も live レーンで読む。11-11 の実測では live 4 本で 1 日約 4.2M CU、うち bot 自身は約 0.8M で、残りは watchdog（15 秒ごとに bot 1 本あたり残高・nonce・価格・USDC、約 2.1M）と、ページを開いている間 60 秒ごとに走る `gate-ctl status`（全チェーンの残高・USDC・価格、1 回約 900 CU、約 1.3M）だった（内訳は呼び出し回数からの試算）。10i から: watchdog は nonce を毎周（15 秒、鍵の漏洩検知は変えない）、残高・USDC・価格を gate.json の `watchdog_balance_interval_s`（60）ごとに読む。nonce が動いた周、初回、読み取りに失敗した次の周はすぐ読む。価格は 1 周につきフィードごとに 1 回。1 回の間隔で L を超える減少の検知と累計損失 30 USD の停止は、残高を読んだ周に判定するので、bot 自身の tx を伴わない減少（承認済みの相手による USDC の引き出し）の検知は最大 60 秒遅れる（人間の判断 11-11。ネイティブ残高は bot 自身の tx なしには減らない）。キーがなければ従来どおり毎周すべて読む。farm-dash は `gate-ctl status` の結果をページと data.json では 5 分、brief.txt（Copy for Claude）では 60 秒まで使い回す。ページの残高は最大 5 分古い。

## feed（phase 11a、11-13 適用）

bot がポーリングの代わりに、指定したイベントを待つための読み取り専用サービス。高速インフラのうち、契約や追加サーバーなしでできる部分として入れた（人間の判断 11-13）。送信の経路は変わらない。

| 項目 | 内容 |
|---|---|
| プログラム | `/opt/farm/bin/farm-feed`（Python 標準ライブラリのみ。外部パッケージは入れない方針で、WebSocket クライアントは RFC 6455 の必要部分を自前で実装: ハンドシェイクの検証、マスク、分割フレーム、ping / pong、close。TLS の証明書検証は有効） |
| unit | `farm-feed.service`（User=farmrelay。rpc-relay と同じ Alchemy キー `/etc/farm/alchemy.key` を読むため。enable、Restart=always）。止めても bot はポーリングに戻るだけ |
| 上流 | チェーンごとに Alchemy へ WebSocket 1 本（`wss://<relay.json の alchemy サブドメイン>.g.alchemy.com/v2/<キー>`、`eth_subscribe`）。購読が 1 つもないチェーンには接続しない |
| `/logs` | `GET http://127.0.0.1:8546/logs/<chain>?address=<a>[,<a>..]&topic0=<t>[,<t>..][&topic1..3]&after=<cursor>&timeout=<秒>`。`after` なしの初回は購読して cursor を返す。以後は一致する log が来たら返る。`address` と `topic0` は必須。待ちは最大 60 秒、時間切れは `{"timeout":true}` |
| `/head` | `GET /head/<chain>?after=<番号>&timeout=<秒>`（newHeads）。**今は全チェーンで無効**（feed.json の `heads` が `[]`、呼ぶと 400）。適用時の実測で ethereum の head 1 件が 3,855 バイト = 154.2 CU、流し続けると 1 日 約 1.1M CU（月 約 17.6 USD）で、relay から `eth_blockNumber` を読むポーリングより高く、feed 全体の上限も head だけで約 15 時間で使い切るため。11-13 に人間が無効化 |
| `/health` | `GET /health`。チェーンごとの接続状態、購読、フィルタごとの `cu_today`、全体の `cu_today` と上限 |
| 取りこぼしの通知 | 再接続・サービス再起動・バッファ超過（フィルタあたり 2000 件）のときは `{"gap":true,"cursor":<新>}` を返す。bot は relay から状態を読み直して続ける。429 / 503 も同じ扱い。bot は数分おきの確認用ポーリングも残す（wiki `infra/feed.md`） |
| 費用 | Alchemy の購読は 1 バイト 0.04 CU。log 1 件はおよそ 40 CU 以上（実測は `/health` のフィルタごとの `cu_today`）。購読は誰かが待っている間だけで、最後の呼び出しから 180 秒で外す（止まった bot は費用がかからなくなる） |
| 上限（`/etc/farm/feed.json`） | 全体 700,000 CU/UTC 日（超えたらその日は全購読を外して 429）、log フィルタ 1 つ 150,000 CU/日（超えたらそのフィルタだけその日は 429）、チェーンあたり log フィルタ 8 個、フィルタあたりアドレス 20 個、同時に待てる呼び出し 64。変更は feed.json を書き換えて `sudo systemctl restart farm-feed`（再起動で全 cursor が `gap` になる） |
| 死活 | 25 秒ごとに ping フレームと `eth_chainId`。75 秒何も来なければ再接続（1〜30 秒の間隔で再試行）。再接続中の呼び出しは待ち続けて `gap` を受け取り、接続そのものに失敗している間は 503 |
| 鍵の扱い | エラー文・ログ・`/health` からキーを消す（テストあり） |
| 確認 | `curl -s http://127.0.0.1:8546/health`、`journalctl -u farm-feed -n 30`、`sudo -u farmrelay /opt/farm/bin/farm-feed --check <chain>`（head を 1 件受けて大きさと CU を表示。購読が通るかの確認に使える） |
| relay の集計との関係 | ダッシュボードとブリーフの Alchemy CU today と今サイクルの累計（どちらも relay の集計）に feed の分は入らない。feed の分は 8546 の `/health` の `cu_today` で、11b からダッシュボードの Feed CU today のタイルと購読一覧、ブリーフの `feed:` の行に出る。feed は日ごとの CU を保存しないので、月の累計には足せない |

- 適用時の実測（11-12 18:03Z）: オフラインテスト 12 件 ALL PASS。farmrelay から ethereum の head 26400530 を 0.3 秒で受信（3,855 バイト）。9 チェーンを認識、farmbot と earner から 8546 に到達可、サービス経由で head 26400531 を受信。その後 `/head` を無効化
- 未確認: hyperevm と elysium で購読が通るか（install が確かめたのは ethereum だけ）、log 1 件の実際の大きさ、Alchemy が ping フレームに pong を返すか（返さなくても `eth_chainId` の応答で生存を確かめる作り）
- 入れていないもの: relay の接続使い回しと signer の先読み（送信経路の短縮）。11-13 の実測で上流 1 回あたり 74〜145 ms（接続の張り直し込み）、送信経路は Ethereum で約 0.25 秒、改善しても約 0.1 秒で、12 秒ブロックでは入るブロックが変わらないため、速いチェーンに live bot を出す段階まで保留。mempool の監視・バンドル・ビルダーへの直接送信もやらない
- 後日の案: 毎ブロックの通知が要るなら、head だけ無料の公開ノードの WebSocket から取る（読み取りと送信は Alchemy のまま）。未着手

## fork と executor 契約（phase 6）

運用者 の選択「A」: live 実行は必ず、bot がデプロイした executor 契約を 1 トランザクションで呼び、契約は「終了時の残高が開始時より多くなければ revert」。これで L の最悪ケースがガス代に限定される。「担保を受け取って別 tx で売る」はシミュレーション結果に関わらず L 違反。

| 部品 | 内容 |
|---|---|
| fork@base / arbitrum / ethereum / bsc / polygon / avalanche / optimism / hyperevm / ethereum-review | anvil 1.9.0（`/opt/foundry/bin`）を user farmfork で。`--fork-url http://127.0.0.1:8545/<chain>?lane=research --auto-impersonate --no-rate-limit`。ポート 9001 base / 9002 arbitrum / 9003 ethereum / 9004 bsc / 9005 polygon / 9006 avalanche / 9007 optimism / 9008 hyperevm / 9013（reviewer 専用、earner と bot からは nft で到達不可）。chain id は本物と同じ。fork 時点のブロックに固定（`fork reset` で追従） |
| `fork` CLI（エージェント用） | `fork status` / `fork url <chain>` / `fork reset <chain> [block]` / `fork fund <chain> <addr> <eth>` / `fork fund-token <chain> <token> <holder> <to> <amount>`（失敗時は終了コード 2、9h）/ `fork deploy <chain> <artifact> [--args <abi>]`（forge の JSON artifact を読み、コンストラクタ引数の欠落を警告、revert 時は gasUsed と最後の opcode を表示）/ `fork send` / `fork replay <chain> <tx>` / `fork trace` / `fork info <chain>`。lease と世代番号で共有を管理（`scratch/.fork/<chain>.gen`、`.lease.log`）。計測前に reset |
| forge / cast | `scratch/<bot>/contracts` で `forge build`、`forge test --fork-url $(fork url base)`。`cast` で ABI エンコード |
| earner の手順（earner.md 3b） | (1) 勝者の tx を `fork replay` / `fork trace` で理解 (2) executor を Solidity で書く（機会を calldata で受け、repay / seize / sell を atomic に、`minProfit` 引数、利益なしで revert）(3) 既知の機会の直前に `fork reset` して成功を証明、機会がない状態で revert を証明。両方の tx hash と残高差を manifest `fork_evidence` に |
| 同じ run.sh | paper モードは fork に対して executor を `eth_call`、live モードは signer 経由で同じ calldata を送信（`FORK_URL_<CHAIN>` 環境変数、`BOT_MODE`） |

anvil 1.9.0 には `--silent` がない。fork@.service は `StandardOutput=null` で RPC ログを捨て、stderr のみ journal に残す。`--block-time 0` も不要（デフォルトが即時マイニング）。

## web search（phase 8 / 8a）

- `farm-search.service`: RustXNG（知人作の Rust 版 SearXNG、github.com/sahenjp/RustXNG、AGPL-3.0、無改変、キー不要の standard プロファイル）を 127.0.0.1:29483 で。DynamicUser、ディスク状態なし
- `/opt/farm/bin/websearch "<query>"`: 全ロール用の CLI（claude のロールは `Bash(websearch *)`）
- earner（dsh）の web_search: ローカルのプロバイダプラグイン `@farm/dsh-web-search-rustxng` が farm-search を引く。dsh はインストールかプロファイルの依存グラフにあるパッケージしか読まないので、`dsh plugin --profile headless add`（pnpm）で入れる（8a）
