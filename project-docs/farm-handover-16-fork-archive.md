# 引き継ぎ書 16: phase 15h（fork レーンの古い状態を公開ノードに回さない）2026-11-19

本体は `farm/farm-handover.md`。バンドル `farm/phase15h/`（tar sha256 `34cd4eba063fe0eef8c2aa929e370805db96f080e405243cdf9aa31d4dcbd9ee`）。`regress-15e.py` は 15e の test-15e.py の写し、`regress-15c.py` は 15c の test-15c.py の写し（Project には置いていない。`farm/phase15e/` と同じ中身）。状態: **2026-11-19 14:43 JST に人間が適用済み**。

> **訂正（2026-11-20 01:13 JST）**: 下の「fork レーンの古い状態の読み取りは、予算を超えても Alchemy を使う」は、`is_historical()` が真のときだけ成り立つ。実際の anvil の読み取りでは偽になっていて、予算内は [Alchemy, 公開]（Alchemy が cooldown 中なら公開ノードへ）、予算超過後は公開ノードだけになり、`public: HTTP 403 Archive` が出た（meta ee059752・f5e76c77 の報告、`farm/ops/2026-11-20-0113.md`）。直しは 15i で検討中。

## きっかけ

- builder-claude（c6a6f716、11-19 00:00Z）: 4 日前のブロックに reset した bsc のフォークで `missing trie node` が出たり出なかったりし、同じ呼び出しが数秒後に成功。fork が一度 `no provider available` で落ちた
- meta（0facbcb2）は「fork レーンの bsc の上流に非アーカイブのものがある。外してほしい」と依頼（inbox/human 12:34）
- ブリーフの RPC today に `fork/public: ok 1 failed 1`。fork/alchemy は failed 0

## 原因

- fork レーンに専用の上流はない。並びは Alchemy → そのチェーンの公開ノード（bsc は 15f の binance.org → bnbchain.org。どちらも最近の状態しか持たない）
- relay の cooldown は上流の URL ごとに 1 つで、全レーンが共有する。別のレーンの bsc の呼び出しで Alchemy がタイムアウト（30 秒）かレート制限（10 秒）になると、その間 fork の古い状態の読み取りが公開ノードへ行き `missing trie node`（anvil はこれを再試行しない）。公開ノードも休み中なら `no provider available`
- 同じ仕組みで、Alchemy が休み中は送信（Alchemy のみ）も `no provider available` で失敗していた

## 変更（rpc-relay のテキストパッチ 6 箇所）

| # | 内容 |
|---|---|
| 1 | fork レーンで、公開ノードが持たない古さ（head から 800 ブロックより前）の状態の読み取りは Alchemy だけ |
| 2 | cooldown 中でも、fork の唯一の上流（Alchemy）と送信（eth_sendRawTransaction）は試す |
| 3 | fork レーンでレート制限に当たったら、エラーを JSON-RPC のコード 429（`rate limited, retry: …`）で返す。anvil は 429 を間隔を空けて再試行する（今までは -32000 で呼び出しが失敗） |

- ほかのレーン・メソッドは変えない。research・scout の古い状態は今までどおり Alchemy → 公開ノードなので、Alchemy の休み中は `missing trie node` が出うる（meta 宛てのメモで「再試行、revert と数えない」と伝える）
- fork レーンの古い状態の読み取りは、fork の 1 日の予算（60 万）を超えても Alchemy を使う（15h の前から同じ）（→ 冒頭の訂正を参照）
- relay.json・unit・ほかのプログラムは変えない。meta 宛てメモ `inbox/meta/2026-11-19-phase15h-fork-archive.md`

## install.sh

- 参考値: rpc-relay 15e 版 `89f94742647ba2e998e9a7286e8a80f30c9c32a0eedf08d75eb73f1a55d9bbfd`。適用はテキストパッチ（1 回だけ一致）で決める
- オフラインのテスト 10 件（適用前 5/10。落ちる 5 件が meta の症状の再現）、15e のテスト 5 件と 15c のテスト 7 件を新しい relay で
- relay を再起動 → `/health` → signer・watchdog・feed が active。駄目なら relay を戻す。バックアップ `.rpc-relay.bak-15h`
- 確認: farmfork から relay 経由で bsc の約 20 万ブロック前の WBNB の残高（eth_getBalance、約 20 CU）
- 手元のフィクスチャで作ったパッチ後の sha256 は実物と違う。期待値は install が実物から作った版（表示される）

## 適用時の結果（11-19 14:43 JST）

- 適用前の rpc-relay は 15e 版と一致。テスト 5/10 → 10/10、15e の回帰 5/5、15c の回帰 7/7
- relay・signer・watchdog・feed は active
- 確認: farmfork のレーンは fork。bsc の 20 万ブロック前（134,249,254）の WBNB の残高 1,563,699 BNB を返した（手で送った hex のブロック番号の eth_getBalance。anvil の読み取りの形は確かめていなかった）
- install の一覧では fork@ が 9 本で fork@bsc がなかったが、異常ではなかった。fork@ は relay の再起動に合わせて再起動される（11-17 21:45・11-18 03:49・16:13 UTC も同じ）。fork@bsc は relay がまだ待ち受けていない 05:42:36 UTC に起動して `Connection refused` で終了し、10 秒後の自動再起動（05:42:46）で active に戻った。一覧はその間に表示されていた。relay を再起動するバンドルでは、fork@ の一覧を出す前に 15 秒ほど待つ

| ファイル | 適用前（期待値 = 実物） | 適用後（期待値 = 実物） |
|---|---|---|
| rpc-relay | `89f94742647ba2e998e9a7286e8a80f30c9c32a0eedf08d75eb73f1a55d9bbfd` | `1c5e781b34c9ae725421222d9b1ec070e2332dd33608c5a39917af818271369e` |
