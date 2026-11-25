> Farm の運用記録の一部（保留・次にやること、11-11 以前と、日付のない未着手の一覧）。本体と文書の一覧は `farm/farm-ops-log.md`。項目は新しい順。

# Farm 運用記録: 保留・次にやること（11-11 以前と、日付のない未着手の一覧）

- [ ] inbox/human（meta、11-11 17:17 JST）: (1) elysium の fork が reset 直後に `Excess blob gas not set.` で eth_call を拒否（1 tx 採掘すると直る。回避策は TOOLS.md に記載済み）→ fork CLI で reset 後に 1 ブロック採掘する案 (2) polygon の公開ノードが 2 つのヘッドを交互に返し、getLogs が空を返した時間帯があった → 公開ノードの入れ替えを検討
- [x] moonwell-maero-base は paper から消えた（11-11 18:46 JST のブリーフで paper 0 本）
- [ ] **live レーンの Alchemy 消費が moonwell 停止後も多い**（11-11 12:07 JST のブリーフ: UTC 0 時から 3.1 時間で live 551,250 CU = 約 4.2M/日のペース、30 日で約 127M。月間枠は 95.2M）。11-11 12:13 JST に rpc_stats で内訳を確認: 残っているプロセスはない（farmbot のプロセスは live 4 + paper 1 のみ）。UTC 0 時から約 3.2 時間で ethereum の live が 461,060 CU（19,106 回）、bot のいない 8 チェーンの live が各約 13,900 CU（elysium 8,878）。呼び出し回数からの試算では、主因は bot ではなく farm 自身: watchdog（15 秒ごとに bot 1 本あたり残高・nonce・価格・USDC の 4 回 = 約 92 CU、4 本で約 2.1M CU/日）と、全チェーンの残高を読む gate status の定期実行（約 60 秒ごと、全体で約 1.3M CU/日）。bot 自身の読み取りは残りの約 0.8M/日。月の累計は 11-11 時点で 15.3M / 95.2M、今のペースだと月末にほぼ枠いっぱい。gate status の呼び出し元は farm-dash（ページを開いている間 60 秒ごと）と確認。人間の判断（11-11）: watchdog の残高確認は 60 秒ごとでよい（清算の計算に使っているものではないため）。**phase 10i を 11-11 04:48Z（13:48 JST）に適用**（パッチ 11 箇所一致、適用前 7 件 FAIL → ALL PASS、10e・10g の回帰も PASS。1 回目は再起動後の待ちの間に SSH が切れて確認前に中断し、04:49Z の再実行で watchdog / dash の稼働と HTTP 200 を確認。journal にエラーなし。切断の原因は不明）。適用直前の当日 live は 795,160 CU（ethereum 673,746、他の 8 チェーン各約 16,200）。効果の確認は未了: watchdog は nonce 毎周・残高と USDC と価格は 60 秒ごと（nonce が動けばすぐ）、farm-dash の gate status はページ 5 分・brief.txt 60 秒のキャッシュ。試算では watchdog 約 2.1M → 約 0.76M、dash 約 1.3M → 約 0.26M CU/日。適用後 1 時間ほどで rpc_stats の live を見て効果を確認
- [ ] moonwell-maero-base: earner 自身の測定で「ポーリングで取れて 1 USD 以上残る捕捉は 0/8」、唯一取れる 1 件は市場の現金不足で実行不能。meta が 11-11 に入れた規則では「測定して 0 なら demote / blocked_infra」。CU 見積もりは 180 秒間隔で約 0.83M/日。次のレビュー（11-11 12:53 JST）の判定を確認
- [ ] inbox/human の HyperEVM エクスプローラ API（lead 129、meta の推奨は見送り）への回答
- [ ] inbox/live に処理済みの古いメモが 4 件残っている（reserve-dutch-ethereum の 2 件、morpho の promote 通知、compound のメモ）。done へ移す
- [ ] 11-11 11:08 JST の meta が「git denied」と報告（変更はディスクには書けている）。→ 原因は権限ではなく、meta が `git -C /srv/farm/ws log` を実行していたこと（許可は `/srv/farm/ws/history` と `/srv/farm/ws/wiki` だけ。ワークスペース直下は git 管理ではない）。inbox/meta にメモで伝える
- [ ] **inbox/live/2026-11-10-reserve-v2-partial-promote-sweep.md を done へ**（reviewer の「stop と sweep を」という依頼。再開したので不要になった。放置すると、次に起きた live-operator が依頼どおり止めるおそれがある）: `sudo mv /srv/farm/ws/inbox/live/2026-11-10-reserve-v2-partial-promote-sweep.md /srv/farm/ws/inbox/live/done/`
- [ ] meta / reviewer に 10f と再開を伝える（inbox/meta の不具合報告 2026-11-10-reserve-v2-gate-partial-promote.md への回答）。伝える中身: gate は artifact を移動の前に読むようになった、bot のディレクトリ内の artifact でもよい、古い state/executor.json は gate が消す、reserve-dutch-ethereum-v2 は人間が `gate-ctl deploy` で再開して稼働中
- [ ] reserve-dutch-ethereum-v2 の最初の送信と損益。累計損失停止の baseline は 30 USD（配備ガス 3.70 USD はすでに損失側に入っている）
- [ ] **elysium の中間ウォレットへの入金**（HYPE、必要なら USDC）。今は 0。HyperEVM から HYPE をブリッジして `gate intermediate` のアドレスへ。bot が出てきてから必要額だけ入れるか、先に少額を入れておくかは人間の判断。ブリッジの経路は一次情報（Kinetiq の公式）で確かめる
- [ ] elysium で earner / researcher が何を見つけるか（次のブリーフ）。毎ブロック読む作りは CU が約 100 倍になるので、README の CU 見積もりを確認。meta が inbox/meta/2026-11-11-phase10g-elysium.md を TOOLS.md と役割ファイルに反映したか
- [ ] elysium で Alchemy の `debug_*` / `trace_*` が使えるかは未確認（testnet では非対応だった）。`fork trace` / `fork replay` が弱ければ meta か earner が報告してくるはず
- [ ] 10g の Nitro 向けガス見積もり（promote / fund / sweep）は実資金でまだ通っていない。elysium か arbitrum の最初の promote が実地確認になる
- [ ] **moonwell-maero-base の CU 見積もりが約 10M/日**（止めた moonwell-whale-base と同じ）。decision の 3 では 1M を超える bot は inbox/human に根拠を出してから promote。reviewer がそこで止めるか、次のレビューで確認。条件 1 の測定は「26 件中 12 件が前ブロック末で清算可能」
- [x] （11-11 11:08 JST の meta が 10h 後を測定: 32 の source/チェーンの組すべてが初期化済み、beefy ethereum 9→20・arbitrum 0→20、folio 11→20。inbox/human の報告は done へ移す。先端まで届いたかは未確認）**ledger の emitter 初期化が途中で止まっている**（inbox/human/2026-11-10-meta-ledger-emitter-init-stall.md、meta の不具合報告）。beefy.charged_fees は ethereum の先頭 9 件、reserve_folio.auction_opened は先頭 11 件だけ cursor があり、残り（beefy の arbitrum 20 件を含む）は 25 時間以上なし。その間この 2 ソースの「イベント 0 件」は証拠にならない。→ 11-11 に原因を特定し **phase 10h を適用（11-10 21:17Z ごろ）**。残る確認: 適用後 2〜3 回の実行の journal（`journalctl -u ledger-ingest -n 6 --no-pager`）で errors が増えていないこと（アドレスのリストを渡す eth_getLogs は relay 経由の実 RPC では未確認）、meta の次の測定で initialized = configured。原因は特定のアドレスの失敗ではなく、emitter ごとに 1 回ずつ eth_getLogs（60 CU）を呼ぶ作りで、先端の維持だけで 600 CU の枠を使い切ること（10 個で 600 CU。11 個目は 1 回/実行、12 個目以降と 2 つ目のチェーンは永久に初期化されない）。手元の再現でも 11 個で止まる。10h は同じブロックにいる emitter を 1 回の呼び出しにまとめる。適用後、初期化は数回の実行で終わり、先端までは ethereum が数時間、arbitrum（7 日分で約 240 回）がほぼ 1 日の見込み。適用したら install の出力を貼り、meta の次の測定（tools/ledger-source-coverage.py）で initialized = configured を確認。inbox/human の報告は done へ
- [ ] 10h で見つかった別件: actor が `tx_from` の source は、予算切れのとき範囲の残りのイベントを落としていた（10h で修正）。10h より前に落ちた分は戻らない。どの agent source が tx_from かは未確認。必要なら該当 source の cursor を巻き戻す（人間の作業）
- [x] meta が inbox/meta/2026-11-11-phase10e-gate-watchdog.md を役割ファイルに反映したか → 11-11 05:04 JST の meta が earner / paper-reviewer / live-operator.md と TOOLS.md に反映（stop の終了コード 3 = sweep 未完を含む）
- [x] meta が 2026-11-11-executor-bots-funds を役割ファイルと manifest-check に反映したか → 同じ meta 実行で反映。manifest-check は 10e の gate と同じ確認（EXECUTOR_ADDR / executor.json）をし、executor bot の空の allowed_contracts を受け付ける
- [ ] meta が 2026-11-11-moonwell-stopped の 1〜3 を earner.md / paper-reviewer.md に反映したか（earner は 2 に従って別 ID で出した。3 の「review.md に CU 見積もり」は次のレビューで確認）
- [x] reserve-dutch-ethereum-v2: allowed_contracts を空に、利益を ETH で返すよう直って再審査 → 合格、11-10 20:05Z promote（10f で再開）
- [x] moonwell の停止・採算判定・meta への伝達（11-10 18:03Z 停止、decision 11-11）
- [x] phase 10c / 10e / 10f の適用、gearbox の baseline 入れ直し、チェーン追加 10a・10b
- [ ] meta が TOOLS.md / ロールファイルを 8 チェーンに合わせたか（inbox/meta に 10a・10b のメモを置いた）
- [ ] 新チェーンの中間ウォレットへの入金（今は 5 チェーンとも 0）。bot が出てきてから、チェーンごとに必要額だけ。earner は HyperEVM の初 promote に HYPE の入金が要ると書いている
- [ ] **Alchemy の月間枠を守る仕組みがない**（10e の監査で確認、未実装）。live レーンは予算で絞らず、送信は Alchemy のみなので、月間枠 95.2M が尽きると全 bot の送信が止まる。11-11 の decision で reviewer が promote 前に CU を見積もる運用にしたが、コードの歯止めはない。案: relay が月の累計（ops.db の rpc_stats に日別の CU がある）を見て、残りが少なくなったら live の読み取りだけ公開ノード優先に切り替える。作るなら Alchemy の課金サイクルの開始日が要る（11-13 に人間が「毎月 1 日開始として扱ってよい」と回答）。人間の判断待ち。11b からは、ダッシュボードが今サイクルの累計と着地の見込みを出し、着地が枠を超えるペースになると「要確認」に出る（見えるだけで、止める仕組みではない）
- [ ] native の sweep はレシートを待たない（10e でも据え置き。待つと stop --all が bot ごとに遅くなる）。送信が受け付けられた後に落とされた場合、記帳済みなのに資金が bot wallet に残る。stop 後に `gate accounts` のアドレスの残高を見れば分かる
- [ ] signer は state/executor.json のアドレスを確かめずに許可先へ足す（10f で gate は古いファイルを配備前に消すようになったが、signer 側の確認はない）。promote と配備の間はサービスが動いていないので実害は出にくい
- [ ] 10e の stop / sweep の変更（未完なら archive しない、空の wallet の記帳、`sweep_unsure`）は実資金でまだ通っていない。次に bot を止めるときが最初の確認
- [ ] earner への前提共有（任意）: SVR を使うプロトコル（Base・Arbitrum・BNB Chain は Atlas オークション）では、オラクル更新がきっかけの清算はオークションで売られる。ポーリング型の清算 bot が取れるのは、それ以外の型が中心
- [ ] USDC 2000 の残りの入金（現在は ethereum に 400、base に 100。元本を使う bot の promote が見えた時点で）
- [ ] ERC-20 approve の明示的な取り消し（stop 時）
- [ ] Relay Protocol でのチェーン間ブリッジ（資金のチェーン間移動）
- [ ] paper 開始時のコードハッシュ記録を paper-ctl 側に（現在は reviewer が自前でスナップショット）
- [ ] 1inch API キーは渡していない（reserve-folio-dtf は見積り経路がないので対象外）
- [x] 高速インフラのうちイベント駆動化は phase 11a（farm-feed）で導入（11-13）。mempool の監視・バンドル・ビルダーへの直接送信は引き続きやらない。送信経路の短縮は上の項のとおり保留（11-06 の「newHead / mempool は週 1000 USD 程度を稼げるまで作らない」を 11-13 に改めたもの）
