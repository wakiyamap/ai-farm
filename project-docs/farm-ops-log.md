> Farm の運用記録（今どうなっているか、何があったか、人間が何を決めたか、次に何をするか）。仕組みと操作方法は仕様書 `farm/farm-handover.md`。この Project の Markdown が唯一の版。
> 日々の運用はこの Project のチャットで行う: ダッシュボードの Copy for Claude で取ったブリーフを貼り、判断・バンドル・decisions/human のメモをここで作る（2026-11-10 から）。何かを決めたり当てたりしたら、その日のうちに本書へ書く。
> 2026-11-14 から、本書は複数の文書に分かれている。Project の文書は全文の置き換えでしか更新できず、ファイルから書き戻すには 1 回の読み取りで全部読める大きさ（24 KB 程度まで）でなければならないため。この文書が本体で、ほかの文書は下の「文書の一覧」にある。
> **2026-11-16 17:40 JST から、書き方を変えた**: 今の状態は `farm/farm-now.md`（毎回丸ごと置き換える短い文書。新しい会話は最初にこれだけを読む）、ブリーフや判断の項は 1 件 1 ファイルで `farm/ops/` に足す。この文書は 11-16 までの記録の本体として残し、ふだんは書き換えない。

# Farm 運用記録

2026-11-10 作成（旧・引き継ぎ書の「現状サマリ」「経緯」「未実装・保留事項」をここへ移し、人間の判断を一覧にした） · @operator

## 文書の一覧

- `farm/farm-now.md`: 今の状態（資金と bot、出してあって答え待ちの依頼、閉じたもの、人間の判断待ち、期日）。2026-11-16 から。毎回丸ごと置き換える
- `farm/ops/<YYYY-MM-DD>-<HHMM>.md`（JST）: 2026-11-16 17:40 JST より後のブリーフや判断の項。1 件 1 ファイル。ファイル名が日時順の一覧になるので、この一覧には 1 件ずつ載せない
- `farm/farm-ops-log.md`（この文書）: 11-16 までの現状、人間の判断、保留の項目がどの文書にあるか、人間がサーバーで直接変えたもの
- `farm/farm-ops-log-history.md`: 経緯（日付順）
- `farm/farm-ops-log-open-2026-11-16.md`: 保留・次にやること（11-16 04:58〜17:26 JST）
- `farm/farm-ops-log-open-2026-11-15d.md`: 保留・次にやること（11-15 21:13〜23:25 JST）
- `farm/farm-ops-log-open-2026-11-15c.md`: 保留・次にやること（11-15 13:31〜21:07 JST）
- `farm/farm-ops-log-open-2026-11-15b.md`: 保留・次にやること（11-15 12:38〜13:28 JST）
- `farm/farm-ops-log-open-2026-11-15.md`: 保留・次にやること（11-15 00:29〜12:33 JST）
- `farm/farm-ops-log-open-2026-11-14b.md`: 保留・次にやること（11-14 11:14〜22:02 JST）
- `farm/farm-ops-log-open-2026-11-14a.md`: 保留・次にやること（11-14 03:20〜11:02 JST）
- `farm/farm-ops-log-open-2026-11-13b.md`: 保留・次にやること（11-13 08:41〜18:34 JST）
- `farm/farm-ops-log-open-2026-11-13a.md`: 保留・次にやること（11-13 01:52〜08:33 JST）
- `farm/farm-ops-log-open-2026-11-12.md`: 保留・次にやること（11-11 夕方〜11-12）
- `farm/farm-ops-log-open-backlog.md`: 保留・次にやること（11-11 以前と、日付のない未着手の一覧）

書き足すとき（2026-11-16 17:40 JST から）: (1) 新しいブリーフや判断の項は、`farm/ops/<YYYY-MM-DD>-<HHMM>.md` として 1 件 1 ファイルで足す。書くのは変わったことと判断（人間の判断、人間がサーバーで直接変えたもの、配置した文書の sha256 を含む）だけで、ブリーフの数字は写さない。(2) そのたびに `farm/farm-now.md` を丸ごと置き換える。出した依頼は「答えを待っているもの」に、答えが出たら「閉じたもの」に移す。(3) この文書と `farm-ops-log-open-*.md` には足さない（全文の書き直しになるため）。設定やコードを変えたときに仕様書 `farm/farm-handover.md` を直す決まりは今までどおり。

## 現状（2026-11-11 05:15 JST = 11-10 20:15Z、phase 10f 適用と reserve-dutch-v2 の配備再開の直後）

**live bot は 4 本、どれも active / running**。総資金 943.18 USD / 2000、日次損失 5.14 USD（reserve-dutch の配備ガス 5.12 + moonwell の 0.02）、frozen=false、halted=false。

| bot | 残高（05:15 JST ごろ） | メモ |
|---|---|---|
| franken-dutch-ethereum | 96.34 USD | 11-09 promote。送信なし |
| gearbox-v3-watcher-ethereum | 92.33 USD | 11-09 promote。baseline は 11-10 13:3xZ に入れ直し |
| morpho-watcher-ethereum | 10.03 USD | 11-10 06:00Z promote |
| reserve-dutch-ethereum-v2 | 26.30 USD | 11-10 20:05Z に reviewer が promote → 資金 30 USD が入った後 gate の不具合で停止 → 10f を当てて 20:1xZ に `gate-ctl deploy` で再開。executor `0x83c6473d9e71d603f83514b4b8f08cafa6437ed0`（tx `0xeb07f44c…b1f0`、nonce 0）、配備ガス約 3.70 USD。wallet `0xA65AC730fbE06dBb022ae4035132916309c2433A` |

- 中間ウォレット（index 0、`0x915bd260dCb166f86a499D5fDb3775b5bec70427`）: ethereum ETH 173.19 USD + USDC 400.07、base ETH 20.42 USD + USDC 100、arbitrum ETH 24.50 USD。新 5 チェーンは 0
- paper: moonwell-maero-base（earner が 11-11 05:0x JST に配置、レビュー前。README の CU 見積もりは 15 秒間隔で約 10M/日）
- moonwell-whale-base は人間が 11-10 18:03Z に停止（sweep・archive 完了、−0.0237 USD）。理由と条件は decisions/human/2026-11-11-moonwell-stopped.md
- Alchemy（UTC 11-10 の 20:09Z 時点）: live 7.80M / paper 0.04M / research 0.44M CU。live の大半は 18:03Z まで動いていた moonwell
- 動いているもの: earner（Qwen3.8-Flash-Next、常駐ループ 75 分/セッション）、paper-reviewer（codex gpt-6-sol、90 分間隔）、researcher-codex（gpt-6.1-sol、毎日 04:10 JST）、researcher-claude（opus、毎日 16:10 JST）、meta（opus、6h 間隔）、rpc-relay、ledger-ingest、farm-signer、farm-watchdog、farm-search（RustXNG）、fork@ 9 本、farm-dash（tailnet 9443、JST 表示）
- gate / signer / watchdog は phase 10e（11-10 18:24Z）、gate は 10f（20:1xZ）、全体は 10g（20:54Z）まで適用済み
- **elysium を 9 つ目のチェーンとして追加**（10g、11-10 20:54Z = 11-11 05:54 JST）。読み取り・fork（9009）・gate / signer / watchdog とも稼働。中間ウォレットの elysium 残高は 0（HYPE も USDC も）なので、入金するまで promote は拒否される。10g 適用後の gate status: 総資金 946.22 USD、live 4 本とも active / running
- 11-11 12:07 JST のブリーフ: 総資金 945.79 USD、日次損失 0（UTC 日替わり）、live 4 本とも active / running（franken 96.9 / gearbox 92.86 / morpho 10.08 / reserve-dutch-v2 26.45 USD）。phase 10h まで適用済みで、meta が全 source の初期化を確認。paper は moonwell-maero-base（fix が 4 回、5 回目のレビュー待ち）。Alchemy は UTC 03:07 時点で live 0.55M / paper 0.008M / research 0.055M CU
- 11-13 03:10 JST: phase 11a（farm-feed）まで適用済み。live は 2 本（franken-dutch-ethereum、gearbox-v3-watcher-ethereum）、paper 0 本。上の表と残高は 11-11 時点のもので、その後の停止（reserve-dutch-v2、morpho-watcher、morpho-watcher2、morpho-watcher3）は「保留・次にやること」の各ブリーフの項にある
- 11-13 06:50 JST: phase 11b（farm-dash の表示追加）まで適用済み。適用時の実測: live 2 本（franken-dutch-ethereum 残高 95.16 USD・promote 以降の損失 −0.03 USD、gearbox-v3-watcher-ethereum 残高 91.2 USD・損失 0.00 USD。停止額 30 USD）、サービス 16 本すべて active（rpc-relay、farm-feed、farm-signer、farm-watchdog、farm-search、qwen-server、fork@ 10 本）、Alchemy は relay の集計で 11-03 から 19,835,134 CU（live 14,308,160 / paper 2,140,308 / research 3,386,666）で、このペースなら 12-01 までに約 56.0M（月間枠 95.2M の内）、feed は当日 252 CU / 700,000、lead は dead_end 128・blocked_infra 31・measured 6、プロンプトは最大の earner が 52,718 バイト、pnl.json に未解決の sweep なし
- 11-14 21:46 JST: phase 11e まで適用済み。live は 3 本とも active / running（franken-dutch-ethereum 89.8 / gearbox-v3-watcher-ethereum 86.07 / morpho-nextblock-ethereum 8.18 USD）、paper 0 本、総資金 900.39 USD、日次損失 0、サービス 16/16、Alchemy は今月 22.13M / 95.2M CU（着地の見込み 53.73M）、プロンプトは最大の earner が 49,448 バイト。詳細は「保留・次にやること」の 11-14 21:46 JST の項
- 11-15 00:29 JST: live 3 本とも active / running（franken-dutch-ethereum 86.64 / gearbox-v3-watcher-ethereum 83.03 / morpho-nextblock-ethereum 7.87 USD）、paper 0 本、総資金 886.22 USD、日次損失 0、サービス 16/16、Alchemy は今月 22.27M / 95.2M CU（着地の見込み 53.55M）、プロンプトは最大の earner が 49,831 バイト。morpho-nextblock-ethereum の nonce が 2 になった（bot 自身の最初の送信とみられる、中身は未確認）。2026-11-14 から運用記録と仕様書は複数の文書に分かれている
- 11-15 06:14 JST: live 3 本とも active / running（franken-dutch-ethereum 83.71 / gearbox-v3-watcher-ethereum 80.22 / morpho-nextblock-ethereum 7.61 USD。morpho-nextblock の promote 以降の損失は 7.19 / 30 USD）、paper 0 本、総資金 873.18 USD、日次損失 0、サービス 16/16、Alchemy は今月 22.60M / 95.2M CU（着地の見込み 53.23M）、プロンプトは最大の earner が 50,199 バイト。morpho-nextblock の最初の送信はプールの初期化で、見送った機会は初期化が済んでいても取れなかった（詳細は 11-15 の文書）
- 11-15 13:05 JST: phase 12a まで適用済み。earner は 2 本（earner-local = build のレーン、earner-measure = measure のレーン）、researcher は 1 日 6 回。live は 3 本のまま
- 11-15 13:28 JST: phase 12b まで適用済み（非公開の送信の経路。まだどの bot も使っていない）
- 11-15 13:36 JST: phase 12c まで適用済み（非公開の送信の規則を役割ファイルに、`wiki search` を BM25 に。decisions/human/2026-11-15-private-send.md は install.sh が配置）
- 11-15 14:05 JST: phase 12d まで適用済み（持ち高の枠。まだどの bot も使っていない。`gate status` の `holding_usd` は合計 0 / 200。decisions/human/2026-11-15-holding-frame.md は install.sh が配置）。適用時の実測: 総資金 880.03 USD、日次損失 0、live 3 本とも active / running（franken-dutch-ethereum 85.23 / gearbox-v3-watcher-ethereum 81.68 / morpho-nextblock-ethereum 7.75 USD）、プロンプトは最大の earner が 54,952 バイト（56,000 まで 1,048）
- 11-15 21:3x JST: phase 12e まで適用済み（`explorer` = Etherscan の中継と、researcher-claude の WebFetch。キーで使えるのは ethereum・arbitrum・polygon・hyperevm）。持ち高の枠の最初の候補 whype-gap-elysium は promote の前に閉じ、枠は 0 / 200 のまま。中間ウォレットの elysium に HYPE 5.01 USD + USDC 199.96 を置いてある（使い道は未定、人間の判断でそのまま）
- 11-16 17:40 JST: これより後の現状は `farm/farm-now.md` に書く（phase 12f まで適用済み、live 2 本、総資金 680.41 USD）

## 人間の判断（日付順）

エージェントへの伝達は `decisions/human/<日付>-<題>.md`（root:root 644、日本語で可、meta が読む）。ここはその要約と、チャットで決めたことの記録。

- **11-03（設計の前提）**: 鍵は 24 語の BIP-39 シード 1 つ（生の秘密鍵から切り替え）、エージェントに鍵を持たせない。リスク上限は X 2000 USD / n 200 USD/日 / L 20 USD/tx。live は bot が配備した executor を 1 tx で呼び、利益がなければ revert（選択「A」）。日次損失で凍結しても、稼いでいる bot・様子見中の bot は止めない
- **11-04**: meta は当面 6 時間間隔（6g）。新しい稼得クラスは人間が候補を出さず、researcher / earner に DefiLlama 等で探させ、ledger も自分で育てさせる。earner を Qwen3.8-Flash-Next（:8003）へ（6e）
- **11-05**: Base の L は (a) gas wallet cap 18 USD を採用（(b) 推定の N 倍許容、(c) Base live 不可は不採用、6i）。本番の送信は Alchemy のみ、公開 RPC へのフォールバックなし（6j）。元本の調達を「フラッシュローンで」と規則にしない（清算や悪用にしか使えないシステムになるため）、gate の USDC 供給（7）を作ってから入金。ロール（特に paper-reviewer）を Claude に切り替えない。OpenAI の内容フィルタで落ちたら OpenAI の別モデルで対処（reviewer を gpt-6-sol に、6l）
- **11-06**: newHead / mempool などの高速インフラは、週 1000 USD 程度を稼げるまで作らない。L を 50 USD に、USD 換算は署名時点の価格（ガス価格の変動は含めない、6r）。earner の web_search に You.com プラグインは入れない（6p 破棄）。ethereum の中間ウォレットに USDC 400
- **11-07**: web search は知人作の RustXNG を基にする（8 / 8a）
- **11-08**: earner / researcher は清算以外の稼得クラスも探す（meta 提案 1）。どうしても無ければチェーン追加も検討してよいが、Alchemy が対応しているチェーンだけ
- **11-09**: researcher を codex 版と Claude 版で並走（名前は researcher-codex / researcher-claude、9 / 9b）。promote の基準を緩める（実際の機会を paper で捉えることは必須にせず、損失上限付きで live で試す）。追加チェーンの第 1 弾は BNB Smart Chain・Polygon PoS・Avalanche C-Chain・OP Mainnet（BSC の USDC は Binance-Peg で 18 桁）。中間ウォレットに ETH 100 USD 分を追加
- **11-10**: 日々の運用はこの Project でブリーフを貼って行う。moonwell の promote は reviewer の合格後に人間が実行。Overlayer OVault-C+ への預け入れ bot は見送り（リスクに見合うリターンがない。decisions/human/2026-11-10-overlayer-moonwell.md）。Alchemy は、呼び出しで利益が出るなら枠を伸ばしてよい、出ないならその bot を止める。moonwell-whale-base は 11-13 02:00Z まで 3 日様子見。引き継ぎ書は Project の版だけにし、仕様書と運用記録に分ける。チェーン追加（phase 10）に HyperEVM も入れる。Chainlink のフィードは Standard proxy を使う（SVR ではない）。live 試行の累計損失 30 USD の停止は bot のコードではなく watchdog が行う（phase 10c と decisions/human/2026-11-10-live-loss-stop-watchdog.md）。phase 10d: allowed_contracts は bot の wallet が直接送る相手だけ、live の bot は `EXECUTOR_ADDR` を読む、利益はネイティブか USDC で返す（decisions/human/2026-11-11-executor-bots-funds.md）
- **11-11**: moonwell-whale-base を、3 日の様子見を待たずに人間が停止（11-10 18:03Z）。現状の問題点の洗い出しと修正を依頼し、phase 10e を適用。decisions/human/2026-11-11-moonwell-stopped.md を置いた: (1) 清算をポーリングで待つ型をもう一度出すなら、「価格更新と別ブロックで起きた過去の清算の件数と利益の見積もり」と「live での 1 日あたりの Alchemy CU の見積もり」を manifest か README に書く。なければ reviewer は fix (2) earner の mAERO 拡張は別の ID で出す (3) reviewer は promote の前に、live での 1 日あたりの Alchemy 消費の見積もりを review.md に書く。1 本で 1 日 1M CU を超える bot は、根拠を inbox/human に出してから promote（1M は目安） (4) meta が earner.md と paper-reviewer.md に反映する。Base での promote は止めていない。**途中で止まった reserve-dutch-ethereum-v2 は、stop して戻すのではなく、gate を直して（10f）配備を再開する**（reviewer の審査は通っているため）。**elysium を追加する**（10g）: 新興チェーンのほうが効率がよいかを確かめたい。Alchemy が対応している（11-08 の条件どおり）。USDC は `0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65`、HYPE の価格は hyperevm の HYPE / USD フィードをそのまま使う
- **11-13**: 高速インフラの方針を一部変更。11-06 の「週 1000 USD 程度を稼げるまで作らない」は bloXroute などの契約を想定したもので、契約なしでできるイベント駆動化とホットパス短縮はやっておきたい。実測を見て、イベント駆動化（farm-feed、phase 11a）を先に作り、ホットパス短縮（relay の接続使い回し、signer の先読み）は速いチェーンに live bot を出す段階まで保留。mempool の監視・バンドル・ビルダーへの直接送信は引き続きやらない。WebSocket クライアントは外部パッケージを入れず標準ライブラリだけで自前で書く（余計なライブラリは入れたくない）。速度勝負の線引きを改める（decisions/human/2026-11-13-next-block-feed.md、11-12 の decision の 2 を置き換え）: 同じブロックは今までどおり対象外、次のブロックは feed で待つ bot なら試してよいが期待収益に数えない、2 ブロック以上は feed で待つ bot なら数える（「それでも期待値自体は上がりそう」）。`/head` は実測の費用を見て無効にする。morpho-watcher3-ethereum は止め、researcher 4 回体制のまま数日様子を見る（decisions/human/2026-11-13-morpho3-stop-ev-net-of-gas.md、詳細は下の 11-13 02:16 JST の項）。farm-dash に、これまでの変更で足りなくなった表示を足す（phase 11b）。ダッシュボードの Alchemy の累計は、課金サイクルを毎月 1 日（UTC）開始として数えてよい。**（11-13 07:2x JST）待機中の 2 本の読み取り費用: gearbox はポーリング間隔を 120 秒に延ばす（人間が live のコードの定数を直接変更）、franken は今のまま（作り直しも間隔の変更もしない）。blocked_infra になっている lead が feed で取れるかを確かめる（decisions/human/2026-11-13-blocked-infra-feed-retriage.md）: earner が全件を理由別に分類し、速度が理由のものは過去の事例を 0 / 1 / 2 ブロック以上で数え直す。順番は lead 14 → ethereum の lead → 11-06 に保留にしたままの lead → 残り。次のブロック型だけを狙う bot の promote の例外を設ける（feed で待つ、1 日 5 万 CU 以下、capital 20 USD 以下、30 日に粗利 50 USD 超の 1 ブロック事例が 1 件以上、同時に 2 本まで、14 日で成果がなければ停止を勧める）**
- **11-14**（各項の詳細は下の「保留・次にやること」）: 既存の他の bot の模倣を広げ、資本の要るものやチェーンをまたぐものも継続して調べる（decision 2026-11-14-copy-other-bots）。速度勝負の線引きはブロック数ではなく farm の反応時間で決める（decision 2026-11-14-race-rule-seconds）。急落時の清算の事後検証をさせ、相手の実行用コントラクトを読んで executor に取り入れられる作りを拾う。相手のコントラクトの不備を見つけても mainnet では使わず人間に報告させる（decision 2026-11-14-crash-postmortem-rival-contracts）。取り手の型を tx から見分けて記録し、Pull 型オラクルの市場を調べる。mempool の監視・バンドル・ビルダーへの直接送信・清算の権利の入札は引き続きやらない（decision 2026-11-14-taker-types-pull-oracle）。単発の取り残しでも、今そこにあって取れるものは取る（「1 日 1 USD の床」と「期待収益が CU の費用を上回ること」を単発には適用せず、1 回の差し引きで見る）。live-operator.md の `IDLE_BEFORE_STOP` は 14 日。Pull 型の価格配信を受ける仕組みはいずれ作るが、今は作らない（decision 2026-11-14-oneshot-leftovers-idle-pull-oracle）
- **11-15**（詳細は `farm/farm-ops-log-open-2026-11-15.md`）: executor を先に配備してから実行する作りでは狙いが読めるので、executor に対象を焼き込まず、準備の tx と approve を残さない（decision 2026-11-15-executor-no-baked-targets）。配備と実行を 1 tx にまとめる形（signer と gate の変更が要る）は後で作る。Yul / Huff / 手書きのバイトコードの executor は見送り（reviewer がソースを読んで確かめられることを優先）。引き出せるのは我々だけ、は厳守。**（12:33 JST、方針）利益の邪魔になっている規則を見直す: 非公開の送信はやってよい（11-13・11-14 の「バンドル・ビルダーへの直接送信はしない」を改める。設計書を先に作る）。保有リスクのある型に合計 200 USD の枠を作ってよい（11-03 の選択 A の例外）。earner の規則を削り、清算の相手の測定を止めてほかの区画に回す。Qwen をもっと活用する。decision と設計書はこれから作る**。**（12:38 JST）researcher は Claude も Codex も枠が空いているので 1 日 6 回に増やす。保有リスクのある型は USDC で持つ型にする。researcher を Qwen に移すことはしない（decision 2026-11-15-widen-beyond-liquidations）**。**（13:21 JST）非公開の送信は Flashbots Protect RPC（`https://rpc.flashbots.net/fast`）を使う。ethereum だけで、ほかのチェーンは今までどおり Alchemy。11-05 の「本番の送信は Alchemy のみ」は「公開の送信は Alchemy のみ、非公開の送信は Flashbots Protect のみ、どちらも公開 RPC にフォールバックしない」に改める。非公開にするかは manifest で決め、reviewer が審査する。バンドルとビルダーへの支払いは今は作らない（設計書 `farm/design/design-2026-11-15-private-send.md`）**。**（13:45 JST）USDC で持つ型の枠の作り: 停止の線は「30 USD + holding_usd」（枠の合計 200 USD がそのまま追加の最悪損失）、1 本あたり 100 USD まで、すぐに USDC に戻せる型だけ、止めるときは executor の `exitAll()` を呼んで失敗したら人間に回す、持つ時間は最長 7 日。ブリッジをまたぐ型は対象外（設計書 `farm/design/design-2026-11-15-holding-frame.md`。実装は phase 12d で、11-15 14:05 JST に適用。仕様は `farm/farm-handover-7-holding-frame.md`、エージェント向けの文面は decision 2026-11-15-holding-frame）。`wiki search` の BM25 化は適用する（meta の提案どおり）**。**（20:59〜21:18 JST）elysium に入金する（最初の 1 本のため。対象が閉じた後も資金はそのまま置く）。whype-gap-elysium の審査で確かめる点を decision にする（2026-11-15-whype-gap-review-points。使われる前に bot が閉じた）。ledger の sources.d は meta の提案どおり整理してよい（条件つき）。持ち高の枠の「買う入口の条件」は変えない（同じプールで買って売る型では満たせないと分かったが、当面は割引の売り出しを買う型だけを対象にする）。Etherscan の API キーは中継に持たせてエージェントに使わせる、researcher-claude の WebFetch は許可する（phase 12e）**
- **11-16**（詳細は `farm/farm-ops-log-open-2026-11-16.md`）: 反応時間 R は ethereum を 12 秒、ほかは 3 秒のまま（decision 2026-11-16-reaction-time）。earner が自分の crontab に入れた測定の記録係は、今回は走らせて済んだら閉じる。Relay の API キーを中継に持たせる（phase 12f）。ブリッジ同士の見積もりの差を 1 回だけ測らせる（decision 2026-11-16-bridge-vs-bridge-quotes）。11-24 までに稼げなければ farm を全部落として Flop Labs に使う。elysium の USDC は公式ブリッジで出金。live の franken-dutch-ethereum は停止。earner の起動の間引きは後でよい。lead 74 は「相手より低い線で先に打つ」型で作ってよい（decision 2026-11-16-franken-threshold-bid。結果は reviewer が archive）。**（17:37 JST）運用記録の書き方を変える: 今の状態は `farm/farm-now.md`、項は 1 件 1 ファイルで `farm/ops/`、項は短く書く**
- 11-16 17:40 JST より後の人間の判断は、`farm/ops/` の各項と `farm/farm-now.md` に書く

## 保留・次にやること

項目は新しい順に、次の文書にある。

- `farm/ops/`（11-16 17:40 JST より後）: 1 件 1 ファイル。出してあって答え待ちの依頼と人間の判断待ちは `farm/farm-now.md` にまとめてある
- `farm/farm-ops-log-open-2026-11-16.md`（11-16 04:58〜17:26 JST）: 17:26 JST のブリーフ（franken の threshold 版の archive、lead 197・198 の終了）、13:17 JST のブリーフと decision 2026-11-16-franken-threshold-bid、live の franken の停止、11:52 JST のブリーフ（板が空、公式ブリッジの出金）、11-24 の見切りの線、ブリッジ同士の見積もりの decision、phase 12f、04:58 JST のブリーフ（Relay の最初の数字、R の表、lead 117 と franken の新版の審査、earner の crontab）
- `farm/farm-ops-log-open-2026-11-15d.md`（11-15 21:13〜23:25 JST）: phase 12e（explorer と WebFetch）、bot の邪魔になっている判断の洗い出し、Relay と R の測定の依頼、21:13 JST のブリーフ（whype-gap-elysium の終了、持ち高の枠の買う入口の条件の問題、sources.d の整理の残り、elysium の資金）
- `farm/farm-ops-log-open-2026-11-15c.md`（11-15 13:31〜21:07 JST）: 19:19 JST のブリーフと decision 2026-11-15-whype-gap-review-points、phase 12d（持ち高の枠。作成と適用の結果）、200 USD 枠の方針と設計書、phase 12c（非公開の送信の規則をプロンプトに、`wiki search` の BM25）
- `farm/farm-ops-log-open-2026-11-15b.md`（11-15 12:38〜13:28 JST）: phase 12b（非公開の送信の経路）と設計書、13:06 JST のブリーフ（lead 14 の答え）、phase 12a（earner の 2 本目と測定のレーン）、見直しの進め方
- `farm/farm-ops-log-open-2026-11-15.md`（11-15 00:29〜12:33 JST）: 利益の邪魔になっている規則の見直し（方針）、earner のモデル変更（IQ4_XS）、executor に狙いを焼き込まない、06:14 JST のブリーフ（見送った機会の測定、ledger の source の誤り、crash-postmortem の残り）、プールの初期化と準備の tx の規則、00:29 JST のブリーフ（morpho-nextblock の nonce が 2 に、decision の反映、wbCOIN と lead 174 の結果）
- `farm/farm-ops-log-open-2026-11-14b.md`（11-14 11:14〜22:02 JST）: 単発の取り残し・IDLE_BEFORE_STOP・Pull 型の基盤、21:46 JST のブリーフ、取り手の型、急落の事後検証、プロンプトの見直し（phase 11d・11e）
- `farm/farm-ops-log-open-2026-11-14a.md`（11-14 03:20〜11:02 JST）: 11:02・05:19・03:20 JST のブリーフ（速度勝負の線引き、phase 11c）、資金系の言語、他の bot の模倣
- `farm/farm-ops-log-open-2026-11-13b.md`（11-13 08:41〜18:34 JST）: 18:34・16:34・11:37・08:41 JST のブリーフ、運用者でまとめる、チェーン選びの条件 2
- `farm/farm-ops-log-open-2026-11-13a.md`（11-13 01:52〜08:33 JST）: チェーンを増やすか、earner の start-limit-hit、07:17 JST のブリーフ、phase 11a・11b の後、morpho-watcher3 の停止
- `farm/farm-ops-log-open-2026-11-12.md`（11-11 夕方〜11-12）: morpho の停止と researcher の回数、morpho-watcher2 の途中で止まった promote（phase 10l）、live 4 本の送信 0、earner のプロンプト上限、サーバー再起動（phase 10j）、10i の効果
- `farm/farm-ops-log-open-backlog.md`（11-11 以前と、日付のない未着手の一覧）: live レーンの Alchemy 消費（phase 10i）、elysium、ledger（phase 10h）、Alchemy の月間枠、sweep・signer の弱点、入金・ブリッジなど

## 人間がサーバーで直接変えたもの（バンドル外）

11-16 17:40 JST より後のぶんは `farm/ops/` の各項に書く。

- 中間ウォレットへの入金: 11-06 ethereum USDC 400、11-09 ethereum ETH 100 USD 分、11-10 base USDC 100
- 11-09 halt の解除（watchdog の誤検知の後）
- 11-10 13:3xZ gearbox-v3-watcher-ethereum の pnl.json baseline を新設: ethereum 45173419995513424 wei（約 94.4 USD、その時の wallet 残高）。gate.log に `op: rebaseline`。この bot の sweep 時の PnL と累計損失は、この時点から数える
- 11-10 18:03Z moonwell-whale-base を `gate stop`（sweep・archive 完了、−0.0237 USD）
- 11-11 16:57Z reserve-dutch-ethereum-v2 を `gate stop`（−3.7592 USD）、19:47Z morpho-watcher-ethereum を `gate stop`（sweep 0.004873 ETH）、20:49Z morpho-watcher2-ethereum を `gate stop`（途中で止まった promote の回収、sweep 0.007679 ETH）
- 11-12 17:20Z morpho-watcher3-ethereum を `gate stop`（sweep 0.005334 ETH）
- 11-11 19:4xZ researcher の timer に drop-in second-run.conf（codex 22:10 JST、claude 10:10 JST を追加）
- 11-10 20:1xZ `gate-ctl deploy reserve-dutch-ethereum-v2`（10f の後。executor `0x83c6473d…7ed0` を配備して起動）
- wiki `infra/farm-base-contracts.md`（commit 447f58b、「fork ではない」訂正）
- decisions/human のファイル（11-03〜。11-11 に 2026-11-11-moonwell-stopped.md）
- 11-12 18:0xZ（11-13 03:0x JST）`/etc/farm/feed.json` の `heads` を `["ethereum"]` から `[]` に変えて farm-feed を再起動（`/head` の無効化。`/health` で `heads_offered_on: []`、cu_today 0 を確認。Project の farm/current/etc/farm/feed.json は変更後の内容）
- 11-12 18:09Z ごろ inbox/meta/2026-11-13-phase11a-feed.md を訂正版（sha256 58e68cc7…、`/head` 無効と head の実測値を反映）で上書き。decisions/human/2026-11-13-next-block-feed.md を配置（sha256 2df4775c…）
- 11-12 21:5xZ（11-13 06:5x JST）`sudo rm -r /srv/farm/runners/researcher-chatgpt /srv/farm/runners/researcher`（roles.conf にない古い instance 名の残骸。11b のプロンプト一覧に出ていたため）
- **11-12 22:2xZ（11-13 07:24 JST）live の gearbox-v3-watcher-ethereum のコードを直接変更**: `/srv/farm/ws/bots/live/gearbox-v3-watcher-ethereum/bot.js` の 68 行目 `const CYCLE_MS = 20000;` を `120000` に（一致 1 件を確かめてから `sudo sed -i`）、続けて `gate restart gearbox-v3-watcher-ethereum`。バックアップは admin の home の `~/gearbox-bot.js.bak-20261113`。行末のコメント「20 s is plenty」は古いまま。live の bot のコードを人間が直接変えた最初の例で、変えたのは待ち時間の定数だけ（送信・executor・manifest には触れていない）。reviewer が審査したときのコードハッシュとは一致しなくなっている
- 11-12 22:3xZ（11-13 07:33 JST）decisions/human/2026-11-13-blocked-infra-feed-retriage.md を配置（sha256 becba438…）。11-12 17:2xZ に 2026-11-13-morpho3-stop-ev-net-of-gas.md を配置（sha256 4fc6dd02…）
- 11-12 22:4xZ（11-13 07:45 JST）`agent@earner-local` を `reset-failed` → `start`（start-limit-hit からの復旧）。drop-in `/etc/systemd/system/agent@earner-local.service.d/restart-delay.conf`（`[Service]` `RestartSec=300`）を追加して daemon-reload
- 11-12 23:35Z（11-13 08:35 JST）decisions/human/2026-11-13-chain-selection.md を配置（sha256 f673b5b9…）、meta を手動で起動（07:4x JST と 08:3x JST の 2 回）
- 11-13 02:40Z（11:40 JST）decisions/human/2026-11-13-aave-watcher2-recount.md を `sudo tee` で直接作成（バンドルや Project の文面なし。中身は運用記録の 11-13 11:37 JST の項）
- 11-13 02:44Z（11:44 JST）decisions/human/2026-11-13-chain-selection-windows.md を `sudo tee` で直接作成（チェーン選びの条件 2 の差し替え。中身は運用記録の同日の項）。inbox/meta/2026-11-13-ethcall-wrong-selector.md を配置
- 11-13 07:39Z（16:39 JST）decisions/human/2026-11-13-follow-slow-liquidators.md を配置（sha256 3f8cd0b5…）、meta を手動で起動（この日 4 回目: 07:4x・08:3x・11:4x・16:3x JST）
- 11-13 07:45Z（16:45 JST）decisions/human/2026-11-13-liquidator-clusters.md を配置（sha256 5ef2cee1…）、meta を手動で起動（この日 5 回目）
- 11-13 19:01Z（11-14 04:01 JST）decisions/human/2026-11-14-copy-other-bots.md を配置（sha256 c6af6796…）。11-14 02:14Z（11:14 JST）decisions/human/2026-11-14-race-rule-seconds.md を `sudo tee` で直接作成（速度勝負の線引きを farm の反応時間で決める。中身は運用記録の 11-14 11:02 JST の項）。11-13 18:41Z ごろ inbox/meta/2026-11-14-phase11c-all-live-bots.md を printf で直接作成
- 11-13 18:3xZ（11-14 03:3x JST）inbox/meta/2026-11-14-census-window-answer.md を printf で直接作成（取り手の一覧は約 18 日分で足りる、30 日への換算はしない）。inbox/human/2026-11-13-meta-census-ledger-history.md を done へ
- 11-14 06:5xZ（15:5x JST）decisions/human/decisions-2026-11-14-taker-types-pull-oracle.md を `sudo install -o root -g root -m 644` で配置（sha256 5e2fffcd…、配置前に一致を確認）。11-14 07:0xZ（16:0x JST）に `sudo mv` で decisions/human/2026-11-14-taker-types-pull-oracle.md に改名（ほかのファイルと同じ形にそろえた）
- 11-14 13:35 JST ごろ decisions/human/2026-11-14-crash-postmortem-rival-contracts.md を配置（時刻はブリーフの decisions/human の表示。sha256 b9de6b8c… は 22:02 JST に貼られた出力で確認、Project の文面と一致）
- 11-14 22:02〜22:13 JST の間に decisions/human/2026-11-14-oneshot-leftovers-idle-pull-oracle.md を `sudo install -o root -g root -m 644` で配置（sha256 1524d3c8…、配置前に一致を確認）。22:13〜22:30 JST の間に inbox/human の 2026-11-14-meta-phase11de-followup.md と 2026-11-14-meta-pull-oracle-markets.md を `sudo mv` で done へ
- 11-15 00:46〜00:55 JST の間に inbox/meta/2026-11-15-morpho-nextblock-pool-init.md を `sudo install -o root -g root -m 644` で配置（sha256 e3f81129…、配置前に一致を確認。morpho-nextblock-ethereum が最初の機会にプールの初期化を送って清算を見送った件の、earner への測定の依頼と、準備の tx を起動時に送る規則。文面は Project の `farm/inbox-meta/`）
- 11-14 21:19Z（11-15 06:19 JST）`ledger/sources.d/morpho_blue.liquidate_hyperevm.json` を `scratch/census-ac40/morpho-source-corrected.json` で `sudo cp` して差し替え（差分は `indexed` の `["id", "borrower", "receiver"]` → `["id", "caller", "borrower"]` だけであることを diff で確認。所有者 earner:farm、644 はそのまま。元のファイルは admin の home の `~/morpho_blue.liquidate_hyperevm.json.bak-20261115`）。取り込み済みの行は直していない
- 11-15 06:21 JST ごろ inbox/meta/2026-11-15-hyperevm-source-replaced-lead14-asks.md を `sudo install -o root -g root -m 644` で配置（sha256 b57490a9…、配置前に一致を確認。source の差し替えの報告と wiki の注記の依頼、lead 14 の追加の測定 2 つ）。inbox/human の 2026-11-14-meta-morpho-hyperevm-source-fix.md を `sudo mv` で done へ
- 11-15 07:30 JST ごろ decisions/human/2026-11-15-executor-no-baked-targets.md を `sudo install -o root -g root -m 644` で配置（sha256 80db0fb7…、配置前に一致を確認）
- **11-15 08:5x〜09:07 JST earner のモデルを Qwen3.8-Flash-Next の IQ3_XXS から UD-IQ4_XS に変更**: `/etc/systemd/system/qwen-server.service` の `-m` と、`/etc/farm/earner-headless.patch.yml` のモデル id（2 箇所）を変更し、qwen-server と `agent@earner-local` を再起動。バックアップは各ファイルの `.bak-20261115`。手順と実測は `farm/farm-ops-log-open-2026-11-15.md` の項
- 11-15 12:42 JST ごろ decisions/human/2026-11-15-widen-beyond-liquidations.md を `sudo install -o root -g root -m 644` で配置（sha256 26c2dff5…、配置前に一致を確認）。researcher の timer に drop-in `third-run.conf` を追加して daemon-reload（codex に 13:10 JST = sha256 6c5bdfaa…、claude に 01:10 JST = sha256 a7fad236…。1 日 6 回になった）
- 11-15 21:0x JST decisions/human/2026-11-15-whype-gap-review-points.md を `sudo install -o root -g root -m 644` で配置（sha256 90f85582…、配置前に一致を確認。whype-gap-elysium の審査で確かめる 4 点、elysium への入金、ledger の sources.d の整理の承認）。同じころ、中間ウォレットの elysium に入金（持ち高の枠の最初の 1 本のため。21:13 JST のブリーフで elysium HYPE 5.01 USD + USDC 199.96、ethereum の USDC は 400.07 → 195.07。対象の whype-gap-elysium は promote の前に閉じたので、資金は使われていない）
- 11-15 21:24 JST ごろ `ledger/sources.d` から 4 ファイル（across.filled_relay.json、uniswapx.fill.json、debridge_dln.claimed_unlock.json、horizon_rwa.liquidation.json）を外した（40 → 36。meta の提案、decision 2026-11-15-whype-gap-review-points の 3）。最初は `history/ledger-sources-retired/` に移し、21:3x JST に `/srv/farm/ws/ledger/sources-retired/` へ移し直した（history は run ごとのスナップショットの git リポジトリのため）
- 11-15 21:3x JST `/etc/farm/explorer.key`（Etherscan の API キー、root 600）を作成（phase 12e の適用の前。キーの値はどの文書にも書いていない）
- 11-15 23:01 JST decisions/human/2026-11-15-cross-chain-gap-relay.md を `sudo install -o root -g root -m 644` で配置（sha256 fd4fdfc3…、配置前に一致を確認。elysium と hyperevm の間の WHYPE の差を Relay で運ぶ費用まで入れて測る依頼。人間から出す候補の例外）。21 時ごろの elysium への入金は Relay（relay.link）で ethereum から運んだもの
- 11-15 23:23 JST inbox/meta/2026-11-15-human-measure-reaction-time.md を `sudo install -o root -g root -m 644` で配置（sha256 7781cd0b…、配置前に一致を確認。反応時間 R の実測の依頼。文面は Project の `farm/inbox-meta/`）
- 11-16 05:2x JST `/etc/farm/relayapi.key`（Relay の API キー、root 600）を配置し、phase 12f を適用（farm-relayapi、farm.nft、TOOLS.md の 1 行、decisions/human/2026-11-16-reaction-time.md、inbox/meta/2026-11-16-phase12f-relayapi.md）
- 11-16 05:41 JST decisions/human/2026-11-16-bridge-vs-bridge-quotes.md を配置（sha256 d27db570…、配置前に一致を確認）
- 11-16 10:59 JST elysium の中間ウォレットから 199.96 USDC を公式ブリッジで HyperEVM へ出金（人間の操作。tx 0x99e43ee6874a61522238ce95928f22729710b409caefd9d0bb0137f8a9c3a101、宛先は同じ中間ウォレット。届くのは 11-21〜22 ごろで、HyperEVM の Outbox で claim が要る）
- 11-16 12:04 JST `ledger/sources.d` の 4 件（inverse_dbr_auction.buy、grvt.swapped_receipt_in、angle_transmuter.swap、convex_locker.kick_reward の各 .json）を `ledger/sources-retired/` に移動（40 → 36。meta の 11-16 の依頼）
- 11-16 12:08 JST live の franken-dutch-ethereum を `gate-ctl stop` で停止（sweep 0.0471017 ETH を中間ウォレットへ、archive に移動。lead 74 の線が閉じたため。live は 2 本に）
- 11-16 13:21 JST decisions/human/2026-11-16-franken-threshold-bid.md を配置（sha256 29885179…、配置前に一致を確認。lead 74 を「相手より低い線で先に打つ」型で作ってよい、flash loan、非公開の送信）
