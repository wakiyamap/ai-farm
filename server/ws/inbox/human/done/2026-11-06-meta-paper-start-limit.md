# paper ユニットの起動回数制限（meta 19f8d2c3 → 人間）

## 現象（inbox/meta/paper-unit-start-limit.md, earner run f3ba8324）
- paper bot の systemd ユニットは StartLimitBurst=5 / StartLimitIntervalSec=10min です。earner が1セッション内で修正→再起動を繰り返すと start-limit-hit になり、ユニットが failed のまま残ります。
- このとき `paper start` / `paper restart` は ok と表示しますが、実際には起動しません。非特権ユーザーは `systemctl reset-failed` を実行できないため、10分経つまで復旧できません。

## 提案
- paper-ctl の start / restart の前に `reset-failed <unit>` を実行する（または StartLimitBurst を 20 程度に上げる）。
- `paper start` がユニットの最終状態を確認し、failed なら ok ではなくエラーを返すようにする（誤って「起動した」と判断されるのを防ぐため）。

ワークスペースの外（paper runner）の変更なので、meta では対応できません。
