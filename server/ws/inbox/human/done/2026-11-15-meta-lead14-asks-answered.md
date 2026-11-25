# lead 14 の追加測定 2 件の回答（meta 転送、2026-11-15）

元の依頼: `inbox/meta/2026-11-15-hyperevm-source-replaced-lead14-asks.md` §2。earner run 949e4ce4 が測定（KB attempts 1244、lead 14 next_steps）。live bot は変更していません。meta の確認・訂正は attempts 1245。

## 1. farm の経路が +16.12 USDC しか出さなかった理由

- 返済額は 397.999731 USDC。制限したのは **bot 側のサイズ定数 `CAPITAL_REPAID_CAP = 398 USDC`**（bot.js:198、capital_usd 400 に合わせたもの）。executor の上限でも、スリッページでも、seize 量でもありません（flash loan は手数料 0、量は呼び出しごとの引数）。
- fork（reset 26413694）で全額返済（171,751.81 USDC）を再現: 0.3% プール 0x99ac8ca7 経由で bot wallet +5,207 USDC、gas 約 0.20 USD（tx 0x591d0d1e…、status 1）。
- 今日 arm したのは 0.05% プール 0x9a772018 で、そこでは全額返済の出口が 34,353 USDC しかなく NO_PROFIT で revert します。**上限定数とプール選択の両方**が効いていました。

## 2. 落札者 tx 0xabb7ad1b…（block 26413695）

- block 内 index 56、type 2、effective priority fee **0**。
- tx 内で **block builder（fee recipient）へ 4.014 ETH を直接送金**。
- earner は USD 換算を約 178.4k USD と書いていますが、これは桁の誤りです（meta 訂正、attempts 1245）。4.014 ETH × 1,886 USD/ETH ≈ **7,570 USD**。落札者の gross 約 7,523 USD の**ほぼ全額**を builder に払っていたことになります。
- 分類: P/B/O/T のいずれでもなし（pull oracle なし、トリガーの BTC/USD AnswerUpdated は親ブロック 26413694）。S は未測定のため taxonomy 上は UNKNOWN、実態は「priority 0 + builder 直接支払い」型です。
- 参考: 同じブロックの farm の pool-init tx 0xdf25a9c7… は index 169、priority 0.001 gwei でした。

## meta の所見（判断は人間側）

- +5,207 USDC は「最初に入った者にとっての価値」であって、farm の EV ではありません。現行の制約（mempool 監視なし、bundle なし、builder 直接送金なし、Alchemy 経由のみ）の下では、gross のほぼ全額を builder に払う相手より前には入れません。
- earner が挙げた変更案（`CAPITAL_REPAID_CAP` を上げる、0.3% プールを arm する）はどちらも live bot の変更です。依頼どおり何も変更していません。実施するかどうかはご判断ください。meta の意見としては、上記の理由で、この機会に限れば上限を上げても約定はまず期待できません。
