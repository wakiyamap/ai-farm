# 卒業の反映と候補の一覧、avalanche の explorer（meta 0d18f9f3、2026-11-23 10:5xZ）

## 1. decision 2026-11-24-graduate-and-builder-focus の反映（済み）

- builder.md: 対象の順番を decision の 3 に置き換えました（fix → 卒業候補 → live の grad を磨く → scout の measured lead → 無ければ短く終わる）。「自分で新しく探す」と長い census の項は削除。manifest の雛形に grad の上限（capital 150、1 送信 3 USD）を追記。
- paper-reviewer.md: grad の審査の段落を追加（試行の実績で EV 可、上限、手数料の分布表、OP Stack は手数料を積まない、2x/5x の fork、同時 5 本、promote 後は止める試行を inbox/meta へ）。
- meta.md: 毎回候補を報告に書く 1 文。
- wiki `methods/graduation.md` を新規作成（細かい手順）。
- 新ツール `tools/grad-candidates.py`（読み取りのみ）: gate status には「promote からの差し引き」が出ないため、中間ウォレット → bot の実際の送金（native + USDC、追加入金を含む）を alchemy_getAssetTransfers で読み、現在の価格で差し引きを出します（watchdog と同じ基準）。manifest の capital_usd で引くと最大 15% ずれます（flatmoney: capital 基準 +0.85、送金基準 +1.29）。
- プロンプトの大きさ: earner 55892、paper-reviewer 55190、builder 52253（−506）、meta 38431。上限 56000 内。

## 2. 卒業の候補（10:5xZ 時点、65 本の live 試行）

| bot | live 時間 | 差し引き | 勝ち/送信 | 型 |
|---|---|---|---|---|
| trial-peapods-arb-arbitrum | 87 h | +1.79 USD | 5/10 | Peapods pod と pool の価格差（arb）。grad-peapods-arb-arbitrum を builder が 07:49Z に paper へ配置済み（審査待ち） |
| trial-flatmoney-arbitrum | 127 h | +1.29 USD | 13/13 | Flat Money の遅延注文 keeper（報酬は WBTC、ETH に売る）。**注意: Pyth の価格を hermes の鍵で取得しています。鍵の試用は 12-02 頃に終わるため、grad にするなら 12-02 以降の価格の取り方（有料の鍵か無料の経路）が先に必要です** |

もうすぐ条件を満たすもの: trial-ryeth-arb-arbitrum（+8.16、11/11、11-24 03:2xZ に 72 h）、trial-lester-harvest-base（+1.45、19/19、32 h）、trial-angle-liq-arbitrum（+1.69 だが勝ち 1 回、清算型）、trial-ichi-vault-hyperevm（+1.30、2/2）。

grad-peapods が live になったら、decision 2 のとおり trial-peapods-arb-arbitrum の `gate stop` をお願いします（paper-reviewer から改めて連絡が来ます）。

## 3. avalanche の explorer（提案、急ぎません）

`explorer source/abi avalanche` は etherscan not_on_plan → blockscout 404 で常に失敗します（11-23 05:41Z の scout、meta 10:5xZ に再現）。routescan の鍵なし API（`api.routescan.io/v2/network/mainnet/evm/43114/etherscan/api`）は検証済みのソースを返すので、各 agent は curl で回避しています（wiki infra/explorer.md に記載済み）。`/opt/farm/bin/explorer` に avalanche の routescan 経路を足していただければ回避が不要になります。TOOLS.md の誤解を招く記述は直しました（「avalanche: curl routescan, not the tool」）。

その他: 今日の損失 0、frozen ではありません。live で最も古いのは 11-16 なので、14 日送信なしの bot はありません。
