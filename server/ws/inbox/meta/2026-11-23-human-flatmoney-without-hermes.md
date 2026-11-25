# grad-flatmoney-arbitrum: Hermes なしで動くか調べてください（人間、2026-11-23 21:4x JST）

meta へ。builder（次に空いている回、builder-claude でも builder-codex でも可）に渡してください。

## 事情

- grad-flatmoney-arbitrum（paper、審査待ち）と trial-flatmoney-arbitrum は、Pyth の価格の更新データを hermes の鍵（Pyth Terminal の Demo、残り約 8 日 = 12-01 ごろまで）で取っています
- Pyth の Free プランは「No Pyth API access」（Terminal で見るだけ）で、bot には使えません。Hermes は 2026-08-26 から API キー必須（hermes.pyth.network も認証つきの新しい backend に転送）、有料は月 500 USD から。flatmoney の利益（promote から +1.3 USD）に見合わないので、**鍵は買いません**
- つまり今のままだと、grad も試行も 12-01 ごろに価格が取れなくなって止まります

## 調べてほしいこと

1. Flat Money v2 の注文の実行（OrderExecutionModule executeOrder など）が、**価格の更新データを渡さずに**（空、または更新料 0 で）、チェーン上の Pyth コントラクトにすでに載っている価格で通るか。通るなら、その価格の新しさの条件（maxAge など）と、注文の実行できる窓の中で条件を満たす価格がどのくらいの頻度でチェーン上にあるか（他の keeper や pusher の更新の間隔を、過去の確定したブロックで数える）
2. 1 が通るなら、その形で grad を作り直したときの勝ち / 送信の見込み（試行の 13 勝を、Hermes なしで取れていたかを fork で数える）
3. 通らない、または取れる数がほぼ 0 なら、grad-flatmoney-arbitrum は `paper archive` で閉じ、理由を attempts に書く。trial-flatmoney-arbitrum は鍵が切れるまでそのまま live（止めるのは人間）

## 使ってよいもの・人間が決めるもの（21:49 人間）

- mempool（未確定の tx）は公開の情報なので、そこに出ている Pyth の更新データ（署名済みの価格）を読んで使うのは S に当たらない。確定済みのブロックのデータやチェーン上の状態ももちろんよい。ただし arbitrum には公開の mempool がない（sequencer の feed は順番が決まった後の tx）ので、使える経路があるかから確かめる
- 他の価格 API（有料・無料）の鍵や経路を探して比べるのはよい。費用・条件・Flat Money の executeOrder に使える形式か（Pyth の更新データが要るのか）を inbox/human に書く。**登録・採用・支払いは人間が決める**

## 参考

- grad-peapods-arb-arbitrum は 08:30Z に paper-reviewer が archive（3 秒未満の速さの競争）。卒業の候補で残っているのは flatmoney だけ。次は trial-ryeth-arb-arbitrum（11-24 03:2xZ に 72 h）
