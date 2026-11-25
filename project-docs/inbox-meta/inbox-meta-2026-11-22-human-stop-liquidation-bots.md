# 清算型の bot 33 本を人間が止めました（2026-11-22 07:5x JST）

`2026-11-22-no-liquidation-trials-oneshot-no-cap.md` の「live にある清算型の試行は 11-24 まで置く」を、次のとおり改めます。

- 理由: 大きい清算はビルダーへの入札で決まり、farm の送り方では取れません。残る小口で 1000 USD 単位が取れないなら置いておく意味がない、と人間が判断しました
- **止めたもの（33 本）**: 清算型で、promote から利益が出ていないもの。trial-aave-arbitrum、trial-aave-avalanche、trial-aave-bsc、trial-aave-optimism、trial-aave-polygon、trial-aave2-avalanche、trial-aave2-polygon、trial-aave4-avalanche、trial-aave4-base、trial-benqi-avalanche、trial-dolomite-arbitrum、trial-euler-base、trial-euler-bsc、trial-exactly-optimism、trial-felix-liq-hyperevm、trial-fluid-arbitrum、trial-fluid-polygon、trial-flux-bsc、trial-hyperlend-hyperevm、trial-hypurrfi-hyperevm、trial-kinza-bsc、trial-llamalend-arbitrum、trial-moonwell-base、trial-morpho-arbitrum、trial-morpho-cbbtc-base、trial-morpho-khype-hyperevm、trial-morpho-whype-hyperevm、trial-revert-lend-arbitrum、trial-silo1-liq-arbitrum、trial-venus-bsc、trial-peapods-base（LVF の清算の後追い）、gearbox-v3-watcher-ethereum、morpho-nextblock-ethereum
- **残したもの**: 清算型でも promote から利益が出ている 5 本（trial-angle-liq-arbitrum、trial-metronome-liq-base、trial-aave4-optimism、trial-xlend-base、trial-moonwell-optimism）。相手がいない場所と読んで 11-24 まで置きます。cv3-buy の 3 本は清算ではなく準備金の買い取りなので残します

## お願い（meta）

1. gate.log の sweep を確かめ、`stop` が未完（終了コード 3）の bot があれば inbox/human に名前を書いてください
2. 止めた bot のディレクトリは archive のままにし、paper に戻して再審査しないでください。11-24 の締めまで再 promote はしません
3. 空いた試行の枠は、審査済みで待っている清算以外の bot（trial-kdiem-redeem-base、再審査が通れば trial-swave-arb-polygon）から通常どおり promote してください
4. builder.md・paper-reviewer.md の「live の清算型は 11-24 まで置く」は「利益が出ている清算型だけ 11-24 まで置く（人間が 11-22 に残りを止めた）」に直してください
5. 止めた 33 本の送信の数・勝ち数・差し引きを、11-24 の判断の材料として 1 つの表にして inbox/human に出してください（急ぎません）
