# Stellar の下調べ（読み取りだけ、机上）2026-11-22

人間の依頼（11-22 20:40）: 11-24 の議題「チェーン追加」の材料として、Stellar を鍵も送信も使わずに下調べする。
今回は公開情報（DefiLlama、Stellar の開発者文書、Blend の文書、事故の報告）で調べた。チェーン上の件数を数える測定はしていない（この Project の作業環境からは Stellar の RPC に届かない）。

## 結論（先に）

- **規模は小さいが、競争も薄そう**。DeFi の TVL 約 1.96 億 USD（11-14、43 プロトコル）、DEX の出来高は 1 日約 290 万 USD、チェーンの手数料は 1 日約 1,000 USD。EVM の安いチェーンの中堅くらい
- **一番の候補は Blend の interest auction**（清算ではない）。誰でも fill でき、オランダ式で、Script3 の公開 bot 以外の担い手が少ないと読める記述がある
- **インフラの入口は思ったより低い**: Alchemy が Stellar mainnet の RPC を出している。今の relay のキーで読み取りのレーンを足せる見込み
- **作る側は重い**: 鍵（ed25519）、tx（XDR）、executor（Soroban = Rust/WASM）、fork の証明（simulateTransaction）、gate / watchdog を別に作る必要がある
- **勧め**: 11-24 に続けると決めたら、まず relay に Stellar の読み取りだけ（research レーン、送信なし）を足し、scout に Blend の interest auction と DEX 間の価格差を 7 日分数えさせる。払われている証拠が出てから署名の仕組みを作る

## 規模（DefiLlama、2026-11-14）

- DeFi の TVL 195.95M USD、プロトコル 43、24 時間の DEX 出来高 2.87M USD、チェーンの手数料 994 USD/日
- 主なプロトコル: Blend 108.0M（レンディング）、Upshift 93.3M、Stellar DeFi Hub 83.1M（Farm）、Aquarius 37.0M（DEX）、BIM 37.5M、Gami Labs 35.9M、DeFindex 18.5M（Yield Aggregator）、Sushi Stellar 15.8M、Stellar DEX（SDEX）13.2M、Stellar AMM 7.6M、Soroswap 1.1M、Phoenix 4.8 万
- TVL の伸びは RWA（トークン化した国債など）が中心。DeFi の天井は高くない

## インフラ

- **RPC**: SDF は mainnet の公開 Stellar RPC を出していない（第三者か自前）。**Alchemy が Stellar mainnet に対応**（`stellar-mainnet.g.alchemy.com/v2/<key>`、getEvents あり）。ほかに Blockdaemon、QuickNode、Ankr、Gateway、Nodies など
- **履歴**: Stellar RPC の getEvents / getLedgers は保持期間の範囲だけ（標準で約 7 日、120,960 ledger）。eth_getLogs のような無制限の過去検索はない。farm の「7 日の払われた証拠」とちょうど同じ長さ
- **Horizon** は非推奨の扱い。SDF の mainnet の公開 Horizon はまだある。SDEX（従来の板）の取引は Horizon かインデクサで読む
- **送信**: RPC の simulateTransaction → sendTransaction。Soroban の呼び出しはシミュレーションが必須

## tx の順序と競争（MEV の土台）

- 1 つの ledger に入りきらないときは、手数料率の高い順。**同じ手数料率なら擬似乱数でシャッフル**される（surge pricing）。EVM のような「優先手数料で先頭を取る」入札は効きにくい
- **1 つのアカウントから 1 ledger に 1 tx（1 つの sequence number）だけ**。同じアカウントで連射できない。並べて試すなら複数アカウント
- Stellar Core v18.2（2021-12）から、裁定 bot の失敗 tx を抑える仕組み（damping）が入っている。SDEX のパス支払いの裁定 bot は昔からいて、手数料を最大 1 XLM/回まで競っていた時期がある
- Soroban の tx は並列の段に分けて処理される（ParallelTxSetBuilder）
- 公開の mempool で他人の tx を見て前に入る型は、farm の決まり（S）で元々やらない

## 候補（清算以外を先に）

### 1. Blend の interest auction（いちばん有望）

- Blend は貸し手と借り手の利息のうち backstop の取り分を、オークションで backstop の LP トークン（BLND:USDC 80/20 の Comet プール）と交換して分配する。`create_interest_auction()` で始まり、**誰でも fill できる**
- 仕組み: 最初は利息の 140% 相当の backstop トークンを求め、最初の 200 ブロックで受け取れる利息の割合が 1 ブロック 0.05% ずつ上がり、次の 200 ブロックで払う backstop トークンが 0.05% ずつ下がる（オランダ式）。先着の速度勝負より「どこで fill すれば得か」の勝負
- fill には backstop トークンが要るが、Script3 の公開の auctioneer-bot には「USDC で直接入札する interest filler コントラクト」の例がある。1 tx の中で USDC → backstop トークン → fill → 受け取った利息を売る、の形にできる見込み（farm の executor の決まりに近い）
- 競争: Script3 が公開 bot を出している。SCF の申請文（keeper ネットワークの提案）に「Soroban に複数の担い手の keeper 基盤はない」とある。担い手は少ないと読める（要確認）
- 測ること: Blend V2 の pool ごとの interest auction の作成・fill のイベントを 7 日、fill したアドレスの数、fill までのブロック数、1 回の差し引き

### 2. DEX 間の価格差（Soroswap / Aquarius / Phoenix / SDEX / Stellar AMM / Sushi）

- 出来高が 1 日 300 万 USD 弱と小さい。アグリゲーター（Soroswap Aggregator、StellarBroker など）がすでに経路を割っている
- ryeth 型（償還価格との差）や vault の入出金価格の差（ICHI 型）が Stellar の RWA・vault にあるかを scout で見る価値はある

### 3. vault・報酬の入口（DeFindex、BIM、Aquarius の報酬、Templar の vault など）

- **BIM は Base で farm の live bot（trial-bim-harvest-base、harvest の caller fee）と同じ名前**。Stellar の BIM（37.5M）に誰でも呼べる harvest の報酬があるかを最初に確かめたい
- DeFindex・Templar は curator / 管理者の操作が中心で role_gated の可能性が高い（未確認）

### 4. 清算（今の方針では対象外）

- Blend の清算と bad debt もオランダ式のオークションで、誰でも fill できる。EVM の「先着の清算」とは形が違うが、11-22 の方針（清算型はやめる）のまま対象外にしておく

## 気をつけること

- **2026-02-22 の YieldBlox の事故**: Blend V2 の上のコミュニティ運営の pool が、SDEX の薄い USTRY/USDC 市場の 1 回の取引で Reflector（SDEX の VWAP）の価格を約 100 倍にされ、約 1,097 万 USD を抜かれた。Blend 本体の欠陥ではなく pool の設定の問題とされている。farm は相手の不備を使わない（決まり S）ので狙いにはしないが、薄い市場の価格を executor の判断に使わない、持ち高を持たない、は Stellar でも守る
- 鍵: Stellar の標準の導出は m/44'/148'（SEP-0005、ed25519）。今の 24 語のシードから導けるが、farmkeys.py は secp256k1 だけ。署名の実装は別に要る
- アカウントの最低残高（base reserve）と trustline。Stellar の資産を受け取るには trustline が要り、XLM の予約が必要

## 11-24 に続けると決めた場合の段取り（案）

1. **relay に Stellar の読み取りレーン**（Alchemy、research と scout だけ、send socket には足さない）。Stellar RPC は JSON-RPC だが method が EVM と違うので、relay の許可する method の表を足す
2. **scout-enum に Stellar を足す**（DefiLlama のチェーン名 `Stellar`）。scout の手順に getEvents（contractIds、topic）の使い方を足す
3. scout に 7 日分を数えさせる。最初の 3 件: Blend の interest auction、BIM の harvest、DEX 間の価格差
4. 払われている証拠が出たら、署名（ed25519・XDR）、Soroban の executor の雛形、simulateTransaction での「成功と revert」の証明、gate の残高と sweep を作る（フェーズのバンドルで数本）

## 出典

- DefiLlama Stellar（https://defillama.com/chain/Stellar）
- Blend の文書: オークション（https://docs.blend.capital/users/auctions）、利息の管理（https://docs.blend.capital/tech-docs/core-contracts/lending-pool/interest-management）、清算（https://docs.blend.capital/tech-docs/core-contracts/lending-pool/liquidation-management）
- Script3 auctioneer-bot（GitHub の写し）、SCF の申請（https://communityfund.stellar.org/submissions/recwkEB0Fv7b0cGv2）
- Stellar の開発者文書: RPC の提供元（https://developers.stellar.org/docs/data/rpc/providers）、getEvents の保持期間、tx のライフサイクル
- Alchemy の Stellar getEvents（https://www.alchemy.com/docs/chains/stellar/stellar-api-endpoints/get-events.md）
- Stellar ブログ: surge pricing の FAQ、失敗 tx の抑制（v18.2）
- YieldBlox の事故: BlockSec、rekt.news、DefiLlama の Blend Pools V2
