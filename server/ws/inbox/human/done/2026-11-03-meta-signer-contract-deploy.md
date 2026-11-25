# 質問・提案: signer でコントラクトをデプロイできるか

- 送信: meta / opus, run 74b33cae3f674f75973c6391641ba1a3, 2026-11-03
- 種別: インフラ（signer の仕様。meta からは確認も変更もできません）

## 背景
- 2026-11-03 の paper review は 6 件すべて `fix` でした。そのうち 5 件で、最初のブロッカーは「tx が成功した場合の損失上限がコードで強制されていない」ことです（KB attempts 2,3,4,10,11,12）。
- 根本的な解決は、清算・担保売却・「残高が開始時を下回れば revert」を 1 tx で行う executor コントラクトです。wiki `pitfalls/paper-review-blockers.md` でもこれを推奨しています。
- ところが `/opt/farm/lib/farmbot_signer.py` の `send()` は `to` を必須にしているため、コントラクト作成 tx（`to` なし）は送れないように見えます。

## 質問
1. signer は contract creation をサポートしていますか？
2. していない場合、どちらを認めていただけますか？
   - (a) 公開の CREATE2 deployer（`0x4e59b44847b379578588920ca78fbf26c0b4956c`、通常の call）を `allowed_contracts` に入れてデプロイする方法
   - (b) signer に `op: "deploy"` を追加する（L と X のチェックは gas のみで十分です）

## 影響
- どちらも認められない場合、bot は「元本＋全手数料 ≤ 20 USD をコードで強制する」小額ルートしか取れません。収益は小さくなりますが、清算 bot はそのルートで進められます。
- 回答は `decisions/human/` にお願いします。それまで earner には小額ルートを進めるよう KB leads:4 に書いてあります。
