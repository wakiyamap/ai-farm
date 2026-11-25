# S の判断のお願い: rebase でプールの reserve を超えた残高を取ってよいか（skim 型）

builder-claude（run 775e819a、2026-11-22 21:50Z）からの転送です。KB: leads:415、actors:374、protocols:2043。数字は builder のもので meta は計測し直していません。

## 質問（はい / いいえ）

rebase するトークンが rebase したあと、プールの帳簿上の reserve を超えて残った残高を、farm が取ってよいか。wiki `methods/skim-excess-sweep.md` が「実際に当たりが出たら建てる前に判断をもらう」としていた問いで、今回が最初の実例（毎日繰り返す）です。

## 実例

- sLGNS（Staked Longinus、Polygon、`0x99a57e6c8558bc6689f894e068733adf83c19725`）は 14,400 block ごとに rebase。
- DODO の sLGNS / USDT プール `0x51542cbb21b98cf261f415ee77e123a9c0baece5` は reserve を帳簿で持つので、rebase のたびに約 1.08 sLGNS が reserve を超えて残り、次に `sellBase(to)` を呼んだ人がそれを受け取る。新しいアドレスからの `eth_call` で 0.160 USDT（block 97784713、何も送っていない）。
- 既に 1 つの非公開アービトラージ executor が毎回 rebase の 3-5 秒後に取っている（tx `0x8cce1f2d041127d31c2cd94018c8bafa0d84b12293669328188a811fc01ba426`）。
- 規模: 0.16 USD × 1 日 3 回 = 約 0.48 USD / 日。このプール単体より、同じ型（DODO / V2 型プールに入った他の rebase トークン、V2 の `skim`）全体への判断として意味があります。

## 両論

- はい: 入口は公開の、DODO の通常の swap（送ってから `sellBase` で残高 − reserve を精算）。バグは使わず、front-run もせず、既存の取り手がいる。時刻は 1 日前から分かる。
- いいえ: その価値はプールの LP の staking 利回りで、DODO も Longinus も呼び出し人への支払いとして用意していない。プールが rebase を計上しないから漏れているだけ。S は「プロトコルが誰にでも払うつもりの仕組み」に限る。

## meta の意見

「いいえ」を勧めます。common.md の S は「意図して誰にでも払う仕組み」に限り、不明なら不可です。LP の利回りが会計の漏れから流れ出るもので、前例の security finding（BSC の LBP pair-harvest、pair の残高超過を `swap()` で持ち出す型）とも形が近い。額も 0.48 USD / 日と小さい。判断が出るまで lead 415 は `blocked_infra`（`needs_human:`）のままです。
