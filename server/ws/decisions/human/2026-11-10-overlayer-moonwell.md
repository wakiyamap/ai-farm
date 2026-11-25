# 2026-11-10 人間の判断: Overlayer は見送り、moonwell は 3 日で採算を判定

## 1. Overlayer OVault-C+ への預け入れ（lead 114）は見送り

- overlayer-deposit-ethereum はやらない。リスクに見合うリターンがない。vault の資産 210 USD に 380 USD を入れると過半を持つことになるが、支配することで得られるものが、預け入れの利回り（約 0.75 USD/日）以上にない。
- paper bot は archive し、lead 114 は dead_end として記録する。
- 同じように小さな vault の大半を占める預け入れは、支配すること自体に利点がない限り作らない。

## 2. moonwell-whale-base は 3 日で採算を判定する

- moonwell-whale-base の Alchemy 消費（live レーン、Base）は 1 日約 9〜10M CU。このままだと Farm 全体の月間枠 95.2M を 11-19 前後に使い切る。枠を使い切ると live の送信（Alchemy 専用）もできなくなる。
- 2026-11-13 02:00Z（live 開始から 3 日）まで様子を見る。それまでに、Alchemy の呼び出しに見合う利益（実現した清算の利益）が出ていれば、人間が Alchemy の枠を伸ばしてよい。出ていなければ停止する。
- 11-13 02:00Z 以降の最初の meta 実行で、moonwell の送信数・成功数・実現損益と、live レーンの Base の CU 消費（1 日あたり）をまとめて inbox/human に出す。停止は人間が `gate stop` で行う。
- 参考: lead 18 の条件を満たす moonwell の捕捉は、11-06 以降の約 5 日で 2 件（1 日あたり約 0.3〜0.4 件）。
- moonwell の executor を作り直すラウンドでは、利益の見込みのない読み取りを減らすこと（Alchemy の消費も採算の一部）。
