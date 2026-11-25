> Farm 仕様書の続き（21 個目）。本体は `farm/farm-handover.md`。この文書は phase 16a（Stellar の読み取りだけ）と 16b（scout の使い方の直し）を扱う。
> 状態: **16a は 2026-11-22 21:09 JST に人間が適用済み**（3 回目。1・2 回目は止まって戻した）。**16b は 11-23 06:38 に人間が適用済み**（sha256 3 つとも一致）。下調べは `farm/research/stellar-desk-research-2026-11-22.md`。

# phase 16a: Stellar を読み取りだけで足す

## 何のためか

人間「面白そうだから今から作れる？」（11-22 20:49）。EVM 以外で相手の少ない場所を探す。まず読み取りだけで「誰でも呼べて払われる入口」があるかを scout に数えさせる。**署名・送信・executor・gate は作らない**（払われている証拠が出てから）。

## 変更

| ファイル | 内容 |
|---|---|
| `/opt/farm/bin/rpc-relay` | relay.json の `nonevm_chains` を読み、`chains` に混ぜてルーティング。非 EVM のチェーンは **Stellar RPC の読み取りの method だけ**（getHealth, getNetwork, getVersionInfo, getLatestLedger, getFeeStats, getLedgers, getLedgerEntries, getTransaction, getTransactions, getEvents, simulateTransaction）、**チェーンに書いた lanes だけ**（research・scout・paper）。それ以外（sendTransaction、eth_* 全部、live / fork / watch レーン、send socket からの呼び出し）は -32601 で拒否し、上流を呼ばない。**空の params（relay の既定の `[]`）は上流に送らない**（Stellar RPC は配列を拒む）。CU は `STELLAR_CU`（推定。getEvents 60 など）。`/health` の `chains` は EVM だけのまま、`nonevm_chains` を足した |
| `/etc/farm/relay.json` | `"nonevm_chains": {"stellar": {"alchemy": "stellar-mainnet", "public": [], "kind": "stellar", "lanes": ["research","scout","paper"]}}`。公開ノードはまだ入れない（保持期間がまちまちで getEvents の結果がずれるため）。Alchemy の予算が尽きたレーンでは Stellar は読めない |
| `/opt/farm/bin/scout-enum` | DefiLlama の `Stellar` → chain `stellar`。待ち行列の段は 2（ほかの protocol より先、actor と同じ段） |
| `/opt/farm/context/scout` | chain が stellar の protocol 候補に Stellar の手順（strkey、require_auth、getEvents で 7 日、stroops、KB が chain stellar を拒んだら any）。16b で getLedgerEntries と getEvents の部分を直した |
| `roles/scout.md` | 「Stellar (16a, read only)」の節: relay への curl だけを例外として許す（rpc.py・explorer・cast は使えない）、params はオブジェクト、7 日 ≒ 120,000 ledger、0 には対照が要る。組み立て後の scout のプロンプト 42,023 bytes（11-23 06:23 には 42,216: meta が改訂した可能性） |
| 待ち行列 | 人が書いた候補 2 件を先頭（段 1）に: `stellar-blend-interest-auction`（Blend V2 の interest auction、清算ではない）、`stellar-bim-harvest`（Base で live の BIM の harvest と同じ入口が Stellar にあるか） |

変えないもの: gate、farm-signer、farm-watchdog、farm-feed、farmchains.py、fork@、鍵。

## 適用の結果（21:09）

- Alchemy 直接: latest ledger 65,612,659。テスト 26/26
- relay を再起動、relay 経由で stellar getLatestLedger 65,612,663、base eth_blockNumber 60,794,948、stellar sendTransaction は -32601 で拒否、/health は EVM 9 チェーン + nonevm `['stellar']`、fork@ の failed 0
- sha256（期待 = 実物）: rpc-relay `d3241a0787429489aa65f3b649d8d354a5cf1d8a4dca346b41127c1fb8274c68`、scout-enum `a8371c7030b8a84948f661c717f2470d971a2d166df1173b0919acf57c7d6d51`、context/scout `fca5c78fe6acae7f79fd31c6bb7642b2e36e607659ad5b14318bcc65ffd31778`（16b で変わった）、scout.md `38246bee5d6c501571909aeb9aa182a9baefb3fb1df388fdc51dabbada8188d1`
- 待ち行列の Stellar の候補 24 件（人の 2 件 + DefiLlama の 22 件）

## バンドル

- `farm-phase16a.tgz` 修正版 2 sha256 `400502dd1242045bf81d65b123fe852b11cb531d35edaba841d26f9a9721038f`（Project の `farm/phase16a/`。候補 2 件の json は tgz の中だけ）。前の版（`e8231926…`、`02bd3b0a…`）は使わない
- 受け取ったサーバーのファイル（11-22 20:51）: rpc-relay `aeb3fb3c…6130e4`、scout-enum `92adcd93…e8ea487`（11-22 17:18 の TVL 2.5 万の版）、context/scout `debc1442…85d1`（14c）、scout.md `99da9804…dfbc84b9`
- install.sh（修正版 2）: (1) 4 ファイルの sha256 (2) Alchemy のキー（`/etc/farm/alchemy.key`、stdin で curl に渡し表示しない）で Stellar の getLatestLedger。JSON は stdin で解析 (3) 元の版は `.bak-16a` があればそこから写しにとり、sha256 を確かめてパッチ、テスト (4) relay.json と rpc-relay だけを入れ替えて再起動・確認、失敗なら 5 ファイル全部を `.bak-16a` に戻す (5) relay が stellar を返してから scout の 3 ファイル、プロンプト、候補、scout-enum

### 適用の経緯

- **1 回目（21:03）**: install.sh の判定の不具合で止まった（何も変えていない）。答えを `python3 -c ... "$resp"` の引数で渡しており、ledger の XDR 込みの答えが引数 1 つの上限（128 KiB）を超えた。→ JSON を stdin で渡す
- **2 回目（21:06）**: relay 経由の stellar getLatestLedger が `-32602 cannot unmarshal array into ... GetLatestLedgerRequest`。relay は params のない要求に `[]` を補って上流に送っていた。rpc-relay と relay.json は自動で戻ったが、scout の 3 ファイルは新しい版のまま残った。→ relay で空の params を送らない、install は relay 先・失敗なら全部戻す
- **3 回目（21:09）**: 成功

# phase 16b: scout の Stellar の使い方を直す（11-23、適用済み）

## きっかけ

scout が inbox/meta に 2 件書いた: (1) getLedgerEntries がどの key でも `cannot unmarshal key value` (2) getEvents の cursor でのページ送りが同じ events を返す、cursor だけだと `startLedger must be positive`。

## 人間がサーバーで確かめた結果（06:32、`/tmp/relay-check.sh`）

- **relay は正しい**。正しく組んだ contract instance の LedgerKey（CD3KRKGD…GLYF）で `entries: 1`（lastModifiedLedgerSeq 63,585,030）
- scout の key は型の部分が誤り（`00000082` = 130 という型を付けていた。ハッシュ `f6a8a8c3…` は正しい）
- getEvents は 2 ページ目以降 `startLedger` を付けず `pagination.cursor` に入れれば続く（エラーなし、cursor が進む）。scout は cursor を外側に置いていた
- **1 回の getEvents は最大約 10,000 ledger しか見ない**: page 1 の cursor の ledger（cursor >> 32）は 65,609,408（startLedger 65,599,409 から 10,000）、page 2 は 65,619,407（latest）。events が 0 でも cursor は進む。空・短いページは終わりではない

## 変更（06:38 適用、sha256 は期待 = 実物）

| ファイル | 内容 |
|---|---|
| `/srv/farm/ws/tools/stellar-key.py`（新規、harness:farm 755） | SDK なしで base64 の LedgerKey を作る: `instance C...`（CONTRACT_DATA(6) + ScAddress contract(1) + hash + SCV_LEDGER_KEY_CONTRACT_INSTANCE(20) + PERSISTENT(1)、48 バイト）、`account G...`、`code <wasm hash>`、`decode`（strkey の base32・版のバイト・CRC16-XMODEM を確かめる）。sha256 `e5077eb70aea6fd1d499344d3436106d2f6b535c0c6da3590d8a7e2ff1573a89` |
| `/opt/farm/context/scout` | `fix-ctx-16b.py`（sha256 `3a08c29da660348d2c4ce8dc1298481f65b225dc7be9c950e65b59b17ff17d05`）で 2 か所を置き換え: getLedgerEntries の key は stellar-key.py で作る、getEvents は 2 回目から startLedger なしで `pagination.cursor`、空ページで止めず cursor の ledger が latestLedger に届くまで（7 日で約 12 回）、getLedgers は pagination.limit 1。パッチ後 `914a786ad09d266a2be3e6da321221280bf39aa53e347ea2576e49e1aec48733`。バックアップ `/opt/farm/context/.scout.bak-16b` |
| `roles/scout.md` | 人間は直さない（11-23 06:23 にプロンプトの大きさが 16a 直後から増えており、meta が改訂した可能性がある）。inbox/meta `2026-11-23-human-stellar-relay-usage.md`（sha256 `d93024e2b1ad4829e2fb289c6483762da0dc5d3a04ada81a4dd17a8240c79ddf`）で meta に 1〜3 の追記と wiki `infra/stellar-relay` を頼んだ |

Project の写し: `farm/phase16b/`（stellar-key.py、fix-ctx-16b.py）、`farm/inbox-meta/inbox-meta-2026-11-23-human-stellar-relay-usage.md`

## 戻し方（16b）

`/opt/farm/context/.scout.bak-16b` を戻す、`/srv/farm/ws/tools/stellar-key.py` を消す。

## 分かっていること・注意

- relay.json にキーはない。キーは `/etc/farm/alchemy.key`
- Stellar RPC は params に配列を受け付けない（オブジェクトか、なし）
- getLatestLedger・getLedgers の答えは大きい（ledger の XDR 込み）。getLedgers は `pagination.limit`（素の `limit` だと 32 MiB を超えてエラー）
- getEvents: 1 回で最大約 10,000 ledger。cursor は `pagination` の中、startLedger と一緒に使わない。cursor の数値 >> 32 がその ledger
- getTransaction の `xdrFormat:"json"` は snake_case
- Alchemy の Stellar の CU の表はこちらで確かめていない。STELLAR_CU は推定で、ダッシュボードとの突き合わせは人間。11-23 06:23 の brief の chain 別の表は stellar「research 40 CU / ok 1,552」（scout レーンは表に出ない）、平均 1,238 ms
- scout は Qwen。XDR / ScVal の読み取りは `xdrFormat: json` に頼る。うまく読めなければ verdict は unclear になる
- 10 ページで打ち切った 16a 直後の scout の Stellar の結果は、件数が少なく出ている可能性がある（例: protocol-stellar-xoxno-lending の最初の「1 件」は分割すると 86 件）
- 次の段（払われた証拠が出たら）: ed25519・XDR の署名、Soroban（Rust/WASM）の executor の雛形、simulateTransaction での成功と revert の証明、gate の残高と sweep、trustline と base reserve

## 戻し方（16a）

`.rpc-relay.bak-16a`・`.scout-enum.bak-16a`（/opt/farm/bin）、`.scout.bak-16a`（/opt/farm/context）、`.scout.md.bak-16a`（roles）、`/etc/farm/relay.json.bak-16a` を戻して `systemctl restart rpc-relay`、scout のプロンプトを組み立て直す。待ち行列の stellar の候補は消してよい。
