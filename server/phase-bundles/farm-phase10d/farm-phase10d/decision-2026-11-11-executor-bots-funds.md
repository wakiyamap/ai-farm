# executor を使う bot の allowed_contracts・executor アドレス・利益の返し方（人間の判断 2026-11-11）

phase 10d（11-11）から次のとおりにする。11-10 の reserve-dutch-ethereum の promote と停止（executor アドレスの環境変数の取り違えで再起動ループ、配備ガス約 5.1 USD の損失）を受けたもの。

1. **allowed_contracts は、bot の wallet が自分で tx を送る相手だけを書く。**
   - executor を通して動く bot は空でよい（`allowed_contracts: []`）。gate が executor を配備し、signer はそのアドレスを state/executor.json から自動で許可する。gate も 10d から、executor があれば空を受け付ける。
   - executor が中で呼ぶプロトコル（トークン、ルーター、オラクルなど）や、fork 上で配備したときの executor のアドレスは書かない。書くと bot の wallet がそこへ直接送れるようになり、「1 tx で executor を通す」という L の前提が崩れる。
   - reserve-dutch-ethereum-v2 の今の 8 件はこれに当たる。空にしてから再審査すること。
2. **live の bot は executor のアドレスを環境変数 `EXECUTOR_ADDR`（なければ state/executor.json）から読む。**
   - meta: tools/manifest-check.py で、executor を持つ bot の bot.js がどちらかを読んでいることを確かめるようにすること（paper では executor アドレスを使わないので、今回は審査で見えなかった）。
3. **利益はネイティブか USDC で bot の wallet に返す。**
   - X、停止時の sweep、watchdog の累計損失は、ネイティブと gate.json の USDC しか数えない。ETH+・WETH・LP トークンなどで返した利益は、停止しても回収されず、累計損失では損失として扱われる。
   - reserve-dutch-ethereum-v2 は ETH+ を wallet に返す作りなので、executor の中で ETH（WETH を unwrap）か USDC に替えて返すように直してから再審査すること。
4. meta: paper-reviewer.md と earner.md に 1〜3 を反映すること。
