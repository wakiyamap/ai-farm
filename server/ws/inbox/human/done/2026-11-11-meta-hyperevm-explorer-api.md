# HyperEVM エクスプローラ API（lead 129）の転送（meta 718540da, 2026-11-11）

優先度は低い。earner は inbox/human に書けないので、`needs_human:` の lead を meta が転送する。

## 提案

HyperEVM のコントラクト一覧を読むために、キー付き（または X402 支払い）のエクスプローラ API を使うかどうか決めてほしい。meta の推奨は **今は見送り**。

## 背景

- lead 129（hyperevm, 2026-11-10 19:49Z 更新）: api.blockscout.com/hyperevm が「API key または X402 payment」を要求し、hyperblocks / hyperevmscan のキー無しの経路は空を返す。そのため felix-vaults、felix-cdp、hyperlend など 9 プロトコルのコントラクトアドレスを特定できていない。
- ただし同じチェーンで 3 セッション（attempts 836, 841, 842）かけても、呼び出し側に報酬を払う poke は 1 件も見つかっていない。duty poker の報酬は 0（841）、既存の主体のルートは blocked_infra（840）。
- hyperevm の中間ウォレットは HYPE が 0 USD なので、仮に見つかっても promote には入金が先に要る。

## 費用

キーの料金は未確認（earner の記録には価格がない）。

## 期待効果と根拠

不明。上の 3 セッションの結果からは、期待値は低いと見ている。

## 判断材料

承認する場合: キーは workspace に置かず、relay か研究用ツールの側に入れてほしい。そのあと earner が 9 プロトコルのアドレスを特定し、20 分の probe を回す（lead 129 の next_steps）。
見送る場合: 何もしなくてよい。lead 129 は 1inch キーのときと同じ扱いで閉じる（earner.md の規則）。

## 同時に閉じたもの

lead 112（Dexalot OmniVaults、subnet での署名が必要）は、400 USD で 1 日 0.23 USD 程度しか見込めない（earner.md の 1 USD/日 未満の規則に当たる）ので、転送せずに meta が dead_end にした。
