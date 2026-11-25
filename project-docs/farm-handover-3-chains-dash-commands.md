> Farm の仕様書の一部（チェーン追加、elysium、ダッシュボード、日常運用コマンド集）。1 つ目の文書と一覧は `farm/farm-handover.md`。

# Farm 仕様書（続き）

## チェーン追加（phase 10、10a・10b 適用済み、11-10）

- 条件: Alchemy が対応しているチェーンだけ（11-08）
- 第 1 弾（11-09 決定）: BNB Smart Chain、Polygon PoS（ガストークン POL、旧 MATIC）、Avalanche C-Chain、OP Mainnet。11-10 に HyperEVM（ガストークン HYPE）も追加。Alchemy の HyperEVM は RPC / Debug / Websockets に対応、Trace API は非対応（`fork trace` 系が弱くなる）
- ネイティブ/USD フィードは Chainlink の **Standard** proxy を使う（SVR proxy ではない）。SVR は清算の OEV を回収する非公開の送信経路で、経路が詰まると Standard に戻るまで遅れうる。gate / signer はガス代の USD 換算に使うだけなので Standard が適切
- USDC（Circle 公式 / Binance）: Avalanche `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E`、Polygon `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`、OP `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85`、BSC は Binance-Peg で **18 桁** `0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d`
- 必要な作業: gate / signer / watchdog をチェーンごとのネイティブ/USD フィードと USDC の桁数に一般化（起動時にオンチェーンで検証）、relay の公開ノード、ledger と kb のチェーン一覧、fork@（9004 以降）、OP の gas wallet cap（Base と同じ理由）
- アドレス（11-10 に人間が data.chain.link / Circle から写したもの。phase 10 の install.sh がオンチェーンで `decimals()` と `description()`（USDC は `decimals()` と `symbol()`）を確かめるまで未検証。Polygon は名前を決め打ちしない）:

| チェーン | ネイティブ/USD（Chainlink Standard proxy） | USDC |
|---|---|---|
| Avalanche C-Chain | AVAX/USD `0x0A77230d17318075983913bC2145DB16C7366156` | `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` |
| BNB Smart Chain | BNB/USD `0x0567F2323251f0Aab15c8dFb1967E4e8A7D42aeE` | Binance-Peg（18 桁）`0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d` |
| Polygon PoS | POL（MATIC）/USD `0xAB594600376Ec9fD91F8e885dADF0CE036862dE0` | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` |
| HyperEVM | HYPE/USD `0xa5a72eF19F82A579431186402425593a559ed352` | `0xb88339CB7199b77E23DB6E890353E22632Ba630f` |
| OP Mainnet | ETH/USD `0x13e3Ee699D1909E989722E753853AE30b17e08c5` | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` |

- 接続先（11-10 に各チェーンの公式ドキュメントと Alchemy の公式ページで確認。HyperEVM の Alchemy サブドメインだけは install で `eth_chainId` = 999 を確かめる）:

| farm のチェーン名 | chain id | Alchemy サブドメイン | 公開 RPC（公式） | 注意 |
|---|---|---|---|---|
| bsc | 56 | bnb-mainnet | https://bsc-dataseed.bnbchain.org | 公開ノードは eth_getLogs 不可（relay が Alchemy に回す） |
| polygon | 137 | polygon-mainnet | https://polygon.drpc.org | 旧 polygon-rpc.com は廃止。Alchemy は Trace API 非対応 |
| avalanche | 43114 | avax-mainnet | https://api.avax.network/ext/bc/C/rpc | 公開ノードはレート制限が厳しい |
| optimism | 10 | opt-mainnet | https://mainnet.optimism.io | OP Stack: Base と同じく L1 データ費 → gas wallet cap |
| hyperevm | 999 | hyperliquid-mainnet | https://rpc.hyperliquid.xyz/evm | Alchemy は Trace API 非対応、公開ノードは WebSocket なし |

- 進め方: 10a（読み取り側: relay・fork・nft・ledger / kb のチェーン一覧・common.md）→ 10b（資金側: gate・signer・watchdog の一般化、OP の gas wallet cap）。10b までは gate が新チェーンの manifest を「chains がない」と拒否する（安全側）
- 10a の中身（11-10 12:41Z ごろ適用、farm/phase10a/）: `cfg-10a.py preflight` が変更前に全公開 RPC と Alchemy に直接 `eth_chainId` を投げる（Alchemy の失敗・chain id 不一致で何も変えずに停止。Alchemy アプリで新ネットワークが有効になっていないと 403 / not enabled）→ `/etc/farm/chains`・`relay.json`（既存エントリは触らない、所有者とモード維持）・`fork-<chain>.env` → relay 再起動（Requires= で既存の fork@ も再起動し状態が消える。世代番号は据え置き）→ `verify`（relay 経由で chain id、Chainlink フィードの decimals 8・description・価格、USDC の decimals・symbol。食い違いは CHECK と表示し 10b の前に解決）→ `ledger`（relay 経由で 20,000 ブロックのタイムスタンプ差からブロック時間を実測、blocks_per_call = 約 2 時間分を 1,000〜10,000 に丸め）。パッチ: fork の PORTS に bsc 9004 / polygon 9005 / avalanche 9006 / optimism 9007 / hyperevm 9008、farm.nft の 9001-9003 → 9001-9008（9013 は閉じたまま）、ledger-ingest は source が使うチェーンの head だけを読み、読めないチェーンはその回だけ飛ばす（runs.note に記録）、common.md に 8 チェーンと新チェーンの注意（gate はまだ promote 不可、BSC の USDC は 18 桁、Polygon / HyperEVM は trace_* なし、公開 BNB ノードは eth_getLogs 不可、OP は OP Stack）。meta 宛てに TOOLS.md / ロールファイル更新のメモを inbox/meta に置く。fork@ は 1 本あたり MemoryMax 6G（5 本追加で最大 30G、空き 103G）
- 10a 適用時の実測（11-10）: エンドポイント 10 本すべて chain id 一致。フィードと USDC は全チェーンで想定どおり（decimals 8、BNB / USD・**MATIC / USD**（Polygon の description は旧名のまま）・AVAX / USD・ETH / USD・HYPE / USD、USDC は BSC 18 桁・他 6 桁、symbol はすべて "USDC"）。ブロック時間と blocks_per_call: bsc 0.45 s / 10,000、polygon 1.5 s / 4,800、avalanche 0.981 s / 7,300、optimism 2.0 s / 3,600、hyperevm 0.984 s / 7,300。fork は 5 本とも起動（anvil 1.9.0、hardfork は OP が Karst、他は Bpo1）、earner と farmbot から到達可
- 10b の中身（11-10 12:57Z 適用、farm/phase10b/）: `farmchains.py` を `/opt/farm/lib` に置き、gate-ctl / farm-signer / farm-watchdog の定数をそこからの import に置き換え。gate: USDC 額をチェーンごとの桁数で（promote・fund・sweep・送金中の確定・X）、ネイティブ価格の妥当性、新チェーンの手数料と送金用の予備、hyperevm の配備ガスの事前確認（資金移動前）。signer: チェーンごとのフィード検証（新チェーンの失敗はそのチェーンだけ停止）、価格範囲、USDC の桁数、ガス上限、USDC トークンはその bot のチェーンのものだけ。watchdog: USDC の桁数、1 チェーンの読み取り失敗で他のチェーンと bot の監視を飛ばさない（失敗と回復を 1 度ずつ journal に）。gate.json: chains に 5 つ、usdc に 5 つ、gas_wallet_cap_usd に optimism 18。common.md: 新チェーンも promote 可（中間ウォレットに資金があれば）、OP Mainnet も cap 対象、HyperEVM は 1 tx 2M gas。install は先に relay 経由で farmchains の全項目を 8 チェーンで照合し、10b のテスト 14 件と 9i / 9j / 9k のテストを 10b 版に流してから入れ替え、signer / watchdog が戻らなければ自動で元に戻す作り
- 10b 適用時（11-10）: 8 チェーンとも farmchains と一致（USDC は ethereum `0xA0b8…eB48`、base `0x8335…2913`、arbitrum `0xaf88…5831` が gate.json の既存値で 6 桁）。テスト全件 PASS、`chain_disabled` なし、signer / watchdog 稼働。gate status に 8 チェーン分の中間ウォレットが並ぶ（新 5 チェーンは残高 0）
- 新チェーンでの promote: 中間ウォレットに、そのチェーンのネイティブ（と、manifest に principal_usdc があれば USDC）が要る。今は 0 なので、promote は「intermediate wallet on <chain> has less than …」で拒否される。入金するかは bot ごとに人間が決める（reviewer が inbox/human に必要額を出す）

## elysium（phase 10g、11-11 適用）

新興チェーンのほうが効率がよいかを確かめるために追加した 9 つ目のチェーン（人間の判断 11-11）。

| 項目 | 内容 |
|---|---|
| 何か | Kinetiq の Arbitrum Orbit（Nitro）チェーン。HyperEVM（chain id 999）に決済する L2。mainnet は 2026-11-09 開始。Vulcan Forged の Elysium（chain id 1338 / 1339）とは別物 |
| farm 名 / chain id | `elysium` / 99901 |
| ガストークン | HYPE（HyperEVM から 1:1 でブリッジ） |
| 接続先 | Alchemy サブドメイン `elysium-mainnet`（ダッシュボードで Elysium Mainnet を有効化済み）、公開 RPC https://rpc.elysium.kinetiq.xyz（Kinetiq のドメイン）。エクスプローラは elysium.kinetiq.xyz/explorer |
| USDC | `0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65`（人間が提示。install がオンチェーンで 6 桁・symbol "USDC" を確認） |
| 価格 | チェーン上に Chainlink フィードがないので、hyperevm の HYPE / USD Standard フィード `0xa5a72eF19F82A579431186402425593a559ed352` で換算する（人間の判断 11-11）。farmchains.py の `feed_chain`。gate・signer・watchdog はフィードを「フィードのあるチェーン」で読む。hyperevm が読めない間は elysium を換算できず、signer は起動時の検証に失敗すると hyperevm と elysium の両方の署名を止める（再起動で再検証） |
| ガス | Nitro は親チェーンへの投稿コストをガスに上乗せするので、単純な送金でも 21,000 を超えることがあり、固定の 21,000 は「intrinsic gas too low」で拒否されうる。farmchains.py の `nitro`（arbitrum と elysium）が付いたチェーンでは、gate が自分の送金（promote / fund / sweep / cancel）のガスを `eth_estimateGas` × 1.3 で決める。USDC 送金は見積もり × 1.3 を 300,000 で頭打ち。見積もれない（空の wallet など）ときは予算値（ネイティブ 100,000 / USDC 300,000）を使う。sweep は予約したガスと署名するガスを同じ値にする。それまで gate は 21,000 / 90,000 固定で、arbitrum でも資金移動が失敗しうる状態だった（arbitrum に bot を出したことがなく表に出ていなかった） |
| L とガス上限 | 親チェーンの費用はガスに含まれるので、最悪ケースは gasLimit × maxFee で決まる（Arbitrum One と同じ扱い。gas wallet cap は不要）。1 tx のガス上限は 3,000,000 |
| fork | `fork@elysium`、ポート 9009（anvil 1.9.0、hardfork Bpo1 で起動を確認） |
| ledger | ブロック時間 0.114 秒（install で実測）、blocks_per_call 10,000 = 1 回の getLogs でチェーン約 19 分ぶん。7 日のバックフィルは 531 回の呼び出しになるので、新しい source の cursor が先端に届くまで日数がかかる。それまでの「イベント 0 件」は証拠にならない |
| エージェントへの注意（common.md） | ブロックが 100〜200 ms なので、毎ブロック読む bot は Ethereum の約 100 倍の呼び出しになる（11-11 の moonwell の decision の CU 見積もりが効く）。ガス上限は定数ではなく必ず `eth_estimateGas` から。Alchemy は `debug_*` / `trace_*` を出さないかもしれない（testnet では非対応だった）。コントラクトのアドレスはプロトコルの公式ドキュメントかエクスプローラからだけ。数日前にできたトークンやプールは明日無いかもしれない |
| promote | 中間ウォレットの elysium 残高は 0。HyperEVM から HYPE をブリッジして入れるまで、promote は資金不足で拒否される |

- install の順序（farm/phase10g/）: パッチ照合 → 公開 RPC と Alchemy に直接 `eth_chainId`（99901 でなければ何も変えずに停止）→ オフラインテスト（10g の 8 件と 10e・10f の回帰）→ 読み取り側の設定（chains・relay.json・fork-elysium.env）→ relay 再起動（fork@ も再起動し状態が消える）→ relay 経由の verify（chain id、USDC、フィード。合わなければ資金側に触らず停止）→ ledger.json → farmchains.py・gate-ctl・farm-signer・farm-watchdog・gate.json → signer / watchdog 再起動（戻らなければ自動で元に戻す）→ fork CLI・nft・common.md → fork@elysium → プロンプト再生成 → meta 宛てメモ
- Alchemy のサブドメインは環境変数 `FARM_ELYSIUM_ALCHEMY` で変えられる。入れるのは `elysium-mainnet` の部分だけで、URL 全体ではない（既定値がそれなので、通常は指定不要）
- 適用時の実測（11-10 20:54Z）: 公開 RPC・Alchemy とも chain id 99901。USDC は 6 桁・"USDC"。HYPE 72.23 USD。単純な送金の見積もりは 21,000 gas（この時点では上乗せなし。gate は見積もり × 1.3 を使うので、上乗せが出ても通る）、ガス価格 0.5001 gwei、送金 1 本 約 0.00076 USD。fork は block 4288189 で起動。テストは適用前 8 件 FAIL → ALL PASS、回帰も ALL PASS。`chain_disabled` なし

## ダッシュボード（farm-dash、phase 5 / 6d / 10i / 11b）

`/opt/farm/bin/farm-dash`（farmgate、127.0.0.1:8090、tailscale serve で 9443）。読み取り専用で、何も変更できない。`/` がページ（30 秒更新、JST 表示）、`/data.json` が同じデータ、`/brief.txt` が Copy for Claude で取るブリーフ。`gate-ctl status` の結果はページと data.json で 5 分、brief.txt で 60 秒まで使い回す（10i）。

11b（11-13）で、phase 7〜11a で増えたもののうち出ていなかったものを足した。ページ・data.json・brief.txt に共通:

| 表示 | 中身と読み取り元 |
|---|---|
| タイル Alchemy CU this cycle | ops.db の rpc_stats（relay の集計）を課金サイクルの初日から合計。月間枠 95.2M に対する現在値、このペースでの着地の見込み、0.53 USD/1M での金額。レーン別の内訳も出る。farm-feed の分は入らない。Alchemy 側の請求の数字ではない |
| タイル Feed CU today | 8546 の `/health`。当日の CU、上限、購読の数。予算切れなら赤 |
| タイル Services | rpc-relay / farm-feed / farm-signer / farm-watchdog / farm-search / qwen-server と fork@ 全部の active 数。存在しない unit は数えない |
| 「要確認」のバッジ（brief では `## Needs a look`） | active でないサービス、running でない live bot（途中で止まった promote、未完の stop）、累計損失が停止額の 3 分の 2 以上の bot、baseline のない bot、pnl.json の `usdc_in_flight` / `sweep_unsure`、feed の停止・予算切れ・フィルタの打ち切り、プロンプト 56,000 バイト超、Alchemy の着地が月間枠超え |
| Live bots の表の 3 列 | promote 以降の損失（pnl.json の baseline を現在価格で換算 − wallet の残高。watchdog が 30 USD で止める数字と同じ定義。残高は最大 5 分古いので概算）、当日の実現損益（pnl.json の realized_usd）、nonce |
| Intermediate wallet | 中間ウォレットのチェーン別残高（9 チェーン、ネイティブの USD 換算と USDC）。brief では残高のあるチェーンと 0 のチェーンを 1 行で |
| Gate log | gate.log の最新 12 件、新しい順。sweep の PnL、失敗の理由、nonce、実行者（`by/role`。人間が `sudo -u harness gate …` で実行したものは `harness/?`）。`deploy_executor_sent` と `sweep_usdc_sent` は省く |
| Alchemy today, by chain | 当日の Alchemy 消費をチェーン別・レーン別に、成功・失敗の回数と平均応答時間つきで |
| Feed (8546) | チェーンごとの接続状態と、購読ごとの状態・待っている呼び出しの数・当日の CU |
| Prompt sizes | `/srv/farm/runners/<instance>/prompt.md` の大きさ（56,000 でメモ、60,000 で起動不可）。7 日以上更新のないものは出さない |
| decisions/human、KB leads by status | decisions/human の最新 6 件（ファイル名と時刻）、lead の status 別件数 |

- 費用: 通常のページ表示で Alchemy CU は増えない。損失の換算に使うネイティブ/USD 価格だけ、relay の research レーン（公開ノード優先）で読む。live bot のいるチェーンごとに 5 分に 1 回まで
- 定数（farm-dash の中）: `ALCHEMY_MONTHLY_CU = 95_200_000`、`ALCHEMY_CYCLE_DAY = 1`（課金サイクルの開始日。UTC の毎月 1 日として数える、人間の判断 11-13）、`USD_PER_M_CU = 0.53`、`LOSS_WARN = 2/3`。Farm は 11-03 開始なので、11 月の累計は 11-03 からで、着地の見込みもその日からのペースで計算する
- 読めない情報源があっても、11b で足した欄はその欄だけ空やエラー表示になり、ページは出続ける。それ以前からの欄は別（既知の落とし穴の brief.txt の行）
- 適用時の実測（11-12 21:50Z ごろ）: Alchemy 19,835,134 CU（live 14,308,160 / paper 2,140,308 / research 3,386,666）で着地の見込み 約 56.0M、feed 252 CU、サービス 16 本すべて active、live 2 本の損失 −0.03 / 0.00 USD、lead は dead_end 128・blocked_infra 31・measured 6。farmgate から runners・gate.json・8546 はどれも読めた
- Alchemy 側との突き合わせ（11-13）: relay の集計 19,835,134 CU（06:50 JST）に対し、Alchemy のダッシュボードは 19,889,563 CU（07:15 JST）。差は 0.27% で、間の 25 分の消費を引くとさらに小さい。タイルの数字は Alchemy 側の累計の目安として使える。Alchemy 側の集計も月初からだった

## 日常運用コマンド集

すべて `admin` で ssh して実行。Windows 側は PowerShell なしの cmd.exe で `scp` / `ssh`。日々の判断は、ダッシュボードの Copy for Claude で取ったブリーフをこの Project のチャットに貼って行う（11-10 から）。

| やりたいこと | コマンド |
|---|---|
| 全体を見る | ブラウザで `https://<tailnet-host>:9443`（JST 表示、30 秒更新）。Copy for Claude / `/brief.txt` でブリーフを取る。何が出るかは「ダッシュボード」の節 |
| 資金・live bot の状態 | `sudo -u harness /opt/farm/bin/gate status` / `gate status <id>` / `gate accounts` / `gate intermediate` |
| gate の記録を読む | `sudo grep <bot id> /var/lib/farmgate/gate.log \| tail -n 20`（farmgate 所有なので sudo が要る） |
| paper bot | `sudo -u harness /opt/farm/bin/paper list` / `paper status <id>` / `paper logs <id>` / `paper archive <id> --reason "<1 行の理由>"`（`paper help` で一覧） |
| 人間が promote する | reviewer の合格判定から bot.js が変わっていないことを `sudo sha256sum /srv/farm/ws/bots/paper/<id>/bot.js` で確かめてから `sudo -u harness /opt/farm/bin/gate promote <id>` |
| bot を止める（sweep 込み） | `sudo -u harness /opt/farm/bin/gate stop <id>` / 全部: `gate stop --all`。「the sweep is incomplete」（終了コード 3）で終わったら、サービスは止まっているが資金がまだ戻りきっていない。bot は live のまま残るので、原因（gate.log の `sweep_failed`、relay の状態）を見てから同じコマンドをやり直す（10e） |
| 途中で止まった promote を再開 | `sudo -u farmgate /opt/farm/bin/gate-ctl deploy <id>`（executor の配備と bot@ の起動）。live に移って資金が入り、executor が未配備の bot が対象。他の bot の古い `state/executor.json` が残っていても gate が配備の前に消す（10f）。「stale state/executor.json … cannot be removed」で止まったら、表示されたファイルを `sudo rm` してからやり直す（配備の前なのでガスは使っていない） |
| watchdog の halt を解除 | 原因を確認してから `sudo rm /var/lib/farmgate/halt`（9g のインストールは halt を消さない） |
| エージェントの実行履歴 | `sudo sqlite3 /var/lib/farm/ops.db "SELECT role, started_at, service_result, tokens FROM runs ORDER BY started_at DESC LIMIT 20"` |
| セッション報告（UTC 日付名） | `tail -n 20 /srv/farm/ws/logs/sessions/$(date -u +%F).jsonl` |
| エージェントのログ | `journalctl -u agent@earner-local -n 100` / `-u agent@paper-reviewer` / `-u agent@meta` / `-u agent@researcher-codex` / `-u agent@researcher-claude` |
| エージェントを今すぐ 1 回走らせる | `sudo systemctl start agent@paper-reviewer.service`（meta / researcher-codex / researcher-claude も同様） |
| earner を止める / 再開 | `sudo systemctl stop agent@earner-local` / `start`（止めても paper@ は動き続ける） |
| earner のモデル（gguf）を替える | (1) `sudo systemctl stop agent@earner-local` (2) `/etc/systemd/system/qwen-server.service` の `-m` を新しい gguf（分割なら 1 本目）に変えて `sudo systemctl daemon-reload && sudo systemctl restart qwen-server`、`journalctl -u qwen-server -f` で listening を待つ (3) `curl -s http://127.0.0.1:8003/v1/models` の `id`（`--alias` がないので gguf のフルパス）を確かめ、`/etc/farm/earner-headless.patch.yml` の旧 id 2 箇所（`models` の `id:` と `agent-default-model` の `model:`）を `sudo sed -i "s#<旧 id>#<新 id>#g"` で置き換える。`n_ctx_slot` が変わったら `contextWindow` も直す (4) `sudo systemctl reset-failed agent@earner-local && sudo systemctl start agent@earner-local`。6e の install.sh は再実行しない（同梱の古い farm.nft と earner.conf で上書きする）。11-15 09:00 JST から gguf は `~/models/qwen38-flash-next-abl/unsloth-UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf`（それまでは同じ場所の `swift-IQ3_XXS/`。ファイルは残してある）。ほかのオプションは `-ngl 99 -c 1048576 --cache-type-k q8_0 --cache-type-v q8_0 -fa on --jinja -np 4 --no-reasoning-preserve`（1 スロット 262,144）。変更前の unit と patch は同じディレクトリの `*.bak-20261115` |
| プロンプトを更新したら | `/opt/farm/bin/assemble-prompt <instance>`（install.sh が全 instance 分を実行する） |
| meta の提案を読む / 返信 | `ls /srv/farm/ws/inbox/human/` → 回答を `sudo install -o root -g root -m 644 ~/decisions-<日付>-<題>.md /srv/farm/ws/decisions/human/<日付>-<題>.md`（`decisions-` 接頭辞を外す。日本語で可。次回 meta 実行で読まれる）→ 回答済みの項目は `sudo mv` で `inbox/human/done/` へ |
| relay の CU 消費 | `curl -s http://127.0.0.1:8545/health` |
| relay の上流の所要時間（当日、live） | `sudo sqlite3 -readonly /var/lib/farm/ops.db "SELECT chain, provider, ok, latency_ms/ok AS avg_ms FROM rpc_stats WHERE day=date('now') AND lane='live' AND ok>0 ORDER BY ok DESC;"` |
| relay の予算変更 | `sudo python3 -c 'import json; p="/etc/farm/relay.json"; c=json.load(open(p)); c["alchemy_daily_cu"]["research"]=1000000; json.dump(c,open(p,"w"),indent=2)' && sudo systemctl restart rpc-relay` |
| feed の状態と CU 消費 | `curl -s http://127.0.0.1:8546/health` / `journalctl -u farm-feed -n 30` |
| feed の設定変更（上限、`/head` の対象） | `sudo python3 -c 'import json; p="/etc/farm/feed.json"; c=json.load(open(p)); c["heads"]=[]; json.dump(c,open(p,"w"),indent=2)' && sudo systemctl restart farm-feed`（キーを変えて使う。再起動で全 cursor が `gap` になり、bot は読み直す） |
| fork の状態 | `sudo -u earner /opt/farm/bin/fork status` / `journalctl -u fork@base -n 30`。止まっていたら `sudo systemctl restart fork@<chain>` |
| web search の確認 | `/opt/farm/bin/websearch "test"` / `systemctl status farm-search` |
| サービス一覧 | `systemctl status rpc-relay farm-feed farm-signer farm-watchdog farm-dash farm-search 'fork@*' --no-pager` / `systemctl list-timers 'farm-*' 'ledger-*'` |
| KB / wiki を直接読む | `sudo -u harness /opt/farm/bin/kb query "SELECT ..."` / `wiki search "<q>"` / `wiki read <path>`。人間が直すときは `wiki write` でコミット |
| バンドルを当てる | `cd ~ && sha256sum farm-phaseN.tar.gz && tar xzf farm-phaseN.tar.gz && sudo ./farm-phaseN/install.sh`（再実行可。期待 sha256 はコードブロックの外に書く） |
| サーバーを再起動する（apt upgrade 後など） | 前: live bot の状況を確認（bot@ は enable 済みで自動復帰する）。NVIDIA が上がったら `dkms status` で新版が今のカーネルに installed、`modinfo -F license nvidia` が `Dual MIT/GPL`（Blackwell は open 必須）。後: `nvidia-smi` → `curl :8003/v1/models`（数分）→ earner は qwen-server を待って起動する（6o）→ `scratch/.fork/<chain>.gen` を +1（fork の状態は消える）。meta / reviewer のタイマーは OnBootSec で前倒しになる |

セキュリティ上の約束: Alchemy キーとニーモニックはチャットに貼らない。エージェントに `/etc/farm`、`/var/lib/farmgate`、他ユーザーの home、認証情報ファイルを読ませない。バンドルは必ず sha256 を照合してから展開。コントラクトのアドレスは一次情報（公式ドキュメント、Etherscan）からだけ書く。
