# meta 800d2363（2026-11-15 14:40Z）: franken の -6 秒の件、Relay と反応時間の測定依頼を載せたこと

## 1. live の franken-dutch-ethereum: 起こす時刻を 6 秒早める案（判断は不要、知らせのみ）

- earner（run ac75a922、attempts:1308、inbox/meta/2026-11-15-franken-minus6s-proof-ready.md）が fork で確かめました: 締め切りの 6 秒前の入札は通り、払う額は liqPrice の 0.007% ほど（1.79 ZCHF で 0.430 WBTC）。数えられる回は 10 件中 1 件 → 2 件（attempts:1300 の分類）。締め切り前 6 秒の間に他人が入札した例は 12 件中 0 件。
- ただし **live の executor（DutchBidder）は「払う額が 0 でなければ revert」** なので、そのままでは使えません。executor の条件を「払う額 ≤ 上限」に変えて、作り直す（paper に新版を置き、paper-reviewer の審査を通して、次の stop / promote の回で入れ替える）必要があります。
- 今の live の bot を止める理由にはなりません（損失 0、動作は正常）。入れ替えるかは、paper-reviewer が新版を見て決めます。止めて入れ替える段になったら、そのときに改めて書きます。

## 2. 測定の依頼を 2 件、earner の measure のレーンに載せました

- **lead 191（elysium）**: Relay で elysium ↔ hyperevm を 1 周したときの差し引き（decision 2026-11-15-cross-chain-gap-relay の 2）。tx は送らず見積もりだけ。`GET https://api.relay.link/chains` はこのホストから鍵なしで通りました（HTTP 200）。elysium の通貨は HYPE（ネイティブ）と USDC だけで、**WHYPE は載っていません**（hyperevm には WHYPE あり）。依頼文には「API キーを求められたら止めて知らせる」「最低受取額で数える」を入れてあります。
- **lead 192（any）**: 反応時間 R の測定（inbox/meta の人間の依頼どおり、検知 p90 + 送信から取り込みまでの中央値、tx は送らない）。Relay の後に回すと書いてあります。
- 順番の都合: 測定の列は「更新が古い順」なので、測ることの残っていない lead 14（11-04 から unmeasured のまま、問いは attempts:1244/1245 で答え済み）を measured にしました。今の列は 191 → 192 の順です。

## 3. phase 12e

- `explorer` の行は TOOLS.md に入っていました。短くして wiki `infra/explorer.md` を作りました（今日の `explorer chains`: ethereum / arbitrum / polygon / hyperevm が使える、base / optimism / avalanche / bsc は plan 外、elysium は非対応）。
- researcher-claude で WebFetch が使えたかは、次の claude の回（16:10Z）の後に報告します。paper-reviewer が読めなかった source を読めるようになったかも、次の審査の後に書きます（その後まだ審査の回はありません）。
