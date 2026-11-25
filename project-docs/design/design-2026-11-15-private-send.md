# 設計書（案）: 非公開の送信（phase 12b の候補）

2026-11-15 作成。**まだ何も実装していない**。

**人間の判断（11-15 13:21 JST）**: (1) 経路は B（Flashbots Protect）。(2) 非公開の送信は ethereum だけで、ほかのチェーンは今までどおり Alchemy。(3) 非公開にするかは manifest で決め、reviewer が審査する。(4) C（バンドルとビルダーへの支払い）は、いずれ要るとは思うが今は作らない。取れるようになってから考える。

**疎通の確認（11-15 13:21 JST、サーバーから）**: B は `eth_chainId` に `0x1` を返した。A（Alchemy の `eth_sendPrivateTransaction`）は `-32000 Unable to complete request at this time.` を返した。「method がない」でも「tx の形式の誤り」でもなく、使えるとは言えないので、**A は予備にもしない**。

**実装（phase 12b、11-15 13:4x JST に作成。`farm/phase12b/`）で、下の 3・4 から変えた点**:

- **nonce の待ちは作らなかった**。非公開の tx は載るまでノードから見えないので、載る前の 2 本目は同じ nonce になり、1 本目を置き換える。同じ nonce の tx は高々 1 本しか載らないので、安全の上では待ちは要らない。bot は「非公開の送信は、まだ載っていない前の tx を置き換える」と理解して使う
- **gate は変えなかった**。`gate stop` の sweep が古い非公開の tx と同じ nonce になった場合、どちらか 1 本だけが載る。古いほうが先に載ると sweep は載らず、10e の「未完の stop」（終了コード 3、bot は live に残る）になるので、`gate stop` をやり直せば進む
- **期限の引数は、コードでは強制していない**。executor に期限を持たせるのは、プロンプト側の規則として次の段階で足す（それまでエージェントには非公開の送信を使わせない）
- **1 日の送信額の数え方はそのまま**。signer は送るたびに最悪額を `capital_usd` の 1 日の枠に足す。非公開の tx は載らなければ費用がかからないが、枠は減る。capital の小さい bot が非公開で何度も送ると、実際には何も払っていないのに枠を使い切る。使い始めてから実測を見て直す
- signer の設定は足していない。対象のチェーンは gate.json の `private_send_chains`（なければ `["ethereum"]`）

## 1. 何のために作るか

今の farm は、bot の tx を Alchemy の `eth_sendRawTransaction` で公開の mempool に出している。これには 2 つの弱点がある。

- **真似される・先に取られる**: ethereum では次のブロックまで数秒〜12 秒、tx が誰にでも見える。
- **外した tx にもガスを払う**: 先に取られて revert した tx も、ブロックに載ればガスがかかる。

非公開の送信は、tx を公開の mempool に出さず、ブロックを作るビルダーに直接渡す。載らなかった tx は捨てられ、ガスはかからない（revert protection）。

### 期待してはいけないこと（lead 14 の実測、11-15）

11-14 23:02 JST の Morpho の清算では、取り手は優先手数料 0 で、tx の中でビルダーに 4.014 ETH（約 7,570 USD）を払っていた。粗利 約 7,523 USD のほぼ全額にあたる。**皆が見ている清算は「粗利のほぼ全額をビルダーに払う入札」で決まっており、非公開の送信を足しても、勝ったときに手元に残るのはわずか**。

したがって、この仕組みの価値は次の 2 つに限る。

1. 競争の薄い機会（単発の取り残し、他の人が見ていない keeper の報酬など）を、真似されずに取る
2. 外したときの損失を 0 に近づける（次のブロック型の試行の費用が下がる）

## 2. 使える経路（2026-11-15 に調べた範囲）

| 案 | 経路 | 要るもの | 状況 |
|---|---|---|---|
| A | Alchemy の `eth_sendPrivateTransaction` | 追加なし（今のキー） | Alchemy の文書では ethereum mainnet だけの対応。ただし Alchemy の文書のリポジトリに、この method を仕様と手引きから削除する変更が出ており、**今も使えるかは不明**。サーバーから 1 回呼んで確かめる |
| B | Flashbots Protect RPC（`https://rpc.flashbots.net/fast`）に `eth_sendRawTransaction` | 追加なし（アカウントもキーも不要） | 通常の使い方は 2025-11 の変更の影響を受けない。fast は登録済みの全ビルダーに渡す |
| C | Flashbots や各ビルダーへの `eth_sendBundle`（署名つき、対象ブロック指定、ビルダーへの支払いは executor の中で） | 認証用の署名鍵（資金の鍵とは別）、ビルダーの一覧、executor の作り替え | 専業の取り手と同じ土俵。今回は作らない |

- 署名なしの `eth_sendPrivateTransaction`（Flashbots）は 2025-11-17 に廃止され、署名ヘッダ `X-Flashbots-Signature` が要る。B はこの method を使わないので影響しない
- Flashbots は非公開の tx を最大 25 ブロック試す
- ビルダーに渡すということは、そのビルダーを信用するということ（先回りしない、第三者に見せない）。秘匿は絶対ではない
- **対象は ethereum だけ**。ほかのチェーン（Base、Arbitrum、OP などのシーケンサー型、BSC、Polygon）の事情は調べていない

**勧める案: B を主に、A はサーバーで確かめて使えるなら予備**。B は契約も鍵も増えない。「送信は Alchemy のみ」（11-05、6j）は「公開の送信は Alchemy のみ、非公開の送信は Flashbots Protect のみ、どちらも公開 RPC にはフォールバックしない」に改めることになる。

## 3. 変更する場所

変えるのは relay と signer。gate・watchdog・bot@ の unit・鍵は変えない。

### rpc-relay

- `relay.json` に `private_send`（チェーン → URL。ethereum だけ）を足す
- send socket（farmgate 専用の unix socket）で、`route=private` のついた `eth_sendRawTransaction` を `private_send` の URL に送る。その URL がないチェーンでは拒否する。**公開の経路に落とさない**（落とすと、非公開のつもりの tx が公開される）
- 統計は provider `private` として ops.db に残す

### farm-signer

- bot が非公開で送れるのは、manifest に `send_route: private` と書いてあり、reviewer が審査した bot だけ。tx ごとに bot が選ぶ形にはしない（審査した送り方と実際の送り方がずれないように）
- ポリシーの検査（L、送り先、approve、bot あたりの上限）は今のまま。最悪の損失の計算も変えない（載れば今と同じだけガスがかかりうる）
- signer.log の `decision: sent` に `route` を足す。watchdog は今までどおりこの行で nonce を既知とする
- **nonce**: 非公開の tx は Alchemy のノードからは見えないので、載るまで `pending` の nonce が進まない。signer が「非公開で送って、まだ載っても捨てられてもいない nonce」を覚え、同じ nonce の次の tx を、前の tx の期限（下の 4）が切れるまで出さない

### gate

- sweep、配備、cancel は今までどおり公開の経路（Alchemy）。止めるときに確実に載ることを優先する
- `gate stop` は、その bot の非公開の tx の期限が切れるのを待ってから sweep する（待たないと、sweep の後に古い tx が載ることがある）

## 4. 期限の扱い

B では「このブロックまで」を送信側で指定できない（指定は署名つきの method だけ）。代わりに **executor の入口に期限（ブロック番号か時刻）の引数を持たせ、過ぎていたら revert する**。revert する tx は載らないので、期限を過ぎた tx は自然に消える。

- reviewer の審査の項目に足す: 非公開で送る bot の executor は期限の引数を持ち、fork で「期限を過ぎたら revert」を再現する
- 期限は短く（次の 2〜3 ブロック）。signer はこの期限 + 余裕を、上の nonce の待ち時間に使う
- executor を使わない tx（今はない）は非公開で送らせない

## 5. 危険と、その抑え方

| 危険 | 抑え方 |
|---|---|
| 非公開のつもりが公開される | relay は private の経路が失敗しても公開に落とさない。signer もやり直さない |
| 載らないまま気づかない | bot は送信の後、期限まで receipt を見て、載らなければ `private_not_included` をログに出す。ダッシュボードに件数を出す |
| 載るのが遅い（参加しているビルダーのブロックにしか載らない） | 過去 1 週間に Protect 経由で載った割合を、小さな自分宛ての tx で実測してから bot に使う |
| nonce が詰まる | 上の 3 の待ち。最悪でも期限が切れれば次が出せる |
| ビルダーが中身を見る | 受け入れる。対象を executor に焼き込まない規則（decision 2026-11-15-executor-no-baked-targets）と合わせて、事前に見えるものを減らす |
| 外部の経路が止まる | その間、非公開の bot は送れない。公開に切り替えるのは人間が manifest を変えて再審査するときだけ |

守るもの: mempool の監視はしない。他人の tx の前後に入ることはしない（common.md の S）。相手のコントラクトの不備は使わない。X・n・L・bot あたり 400 USD・累計損失 30 USD の停止は変えない。

## 6. 作る順

1. サーバーから A と B の疎通を確かめる（下のコマンド。送金はしない）
2. relay と signer のパッチ、オフラインテスト、バンドル（phase 12b）。文字列照合のパッチと、失敗時に元へ戻す install は今までと同じ形
3. selfping（自分宛て 0 ETH）を非公開で 1 回送り、載るまでのブロック数を見る
4. common.md、earner.md、paper-reviewer.md に `send_route: private` と期限の規則を足す。`private-send` の印がついた lead を見直す

## 7. 決めてほしいこと

1. **経路は B（Flashbots Protect）でよいか**。Alchemy 以外の送り先が 1 つ増える
2. **対象は ethereum だけ**で始めてよいか
3. **非公開にするかどうかは manifest で決め、reviewer が審査する**形でよいか
4. **C（バンドルとビルダーへの支払い）は作らない**でよいか。作らない限り、皆が見ている清算では勝てないが、勝っても残らないことは実測済み

## 疎通の確認（送金はしない。出力にキーは出ない）

```bash
# B: Flashbots Protect が答えるか（chain id 0x1 が返れば可）
curl -s -m 10 -X POST -H 'content-type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' https://rpc.flashbots.net/fast

# A: Alchemy がこの method をまだ受け付けるか（わざと壊れた tx を渡す。
#    「method がない」という答えなら廃止済み、tx の形式の誤りという答えなら生きている）
sudo sh -c 'curl -s -m 10 -X POST -H "content-type: application/json" --data "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_sendPrivateTransaction\",\"params\":[{\"tx\":\"0x00\"}]}" "https://eth-mainnet.g.alchemy.com/v2/$(cat /etc/farm/alchemy.key)"'
```

## 調べた資料（2026-11-15）

- Alchemy: eth_sendPrivateTransaction の説明（ethereum mainnet のみ）https://docs.alchemy.com/reference/eth-sendprivatetransaction
- Alchemy の文書のリポジトリ: private transaction の method を仕様と手引きから削除する変更（pull 720・723 の写し）https://gh.r-mj.com/alchemyplatform/docs/pull/720
- Flashbots: Protect RPC の変更と廃止（2025-11-17）https://collective.flashbots.net/t/changes-and-deprecations-in-flashbots-protect-rpc/5368
- Flashbots: JSON-RPC の説明（eth_sendBundle、eth_sendPrivateTransaction、25 ブロック）https://docs.flashbots.net/flashbots-protect/api/json-rpc
- Flashbots: Protect の始め方（fast、ビルダーへの信頼）https://docs.flashbots.net/flashbots-protect/quick-start
