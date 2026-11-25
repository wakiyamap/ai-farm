# 試行の枠が 75/75 で埋まり、審査済みの trial-kdiem-redeem-base が待っています（meta 72f560af、2026-11-21 22:4x UTC）

1. `gate status` で `trial-` で始まる live の bot は 75 本、枠（`2026-11-22-trial-slots-75.md`）いっぱいです。HyperEVM の 2 本（behype、hbhype）と trial-dfm-pegkeeper-arbitrum は資金が入って live になりました。
2. trial-kdiem-redeem-base（清算以外、審査で fork の成功と revert を再現済み）は、20:35 UTC に Base の資金不足で promote が断られました。今は Base の中間 wallet に 40.83 USD あるので、資金ではなく枠で待っています（attempts:3497）。
3. live の試行のうち、おおよそ 35 本は清算型です（aave / aave2 / aave4、euler、moonwell、morpho、venus、kinza、silo1-liq、metronome-liq、felix-liq など。名前から数えた概数です）。`2026-11-22-no-liquidation-trials-oneshot-no-cap.md` では 11-24 まで置くことになっています。
4. 判断していただきたいこと（どちらか）: (a) 送信が 0 回の清算型の試行を 1 本止めて kdiem に枠を回す、(b) 11-24 の締めまでこのまま待つ。どちらでも、meta は試行の bot を止めません。
5. 単発の bot は枠の外なので、この件では待ちません。
