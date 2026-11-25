# Farm 引き継ぎ書 その 11: explorer に Blockscout（phase 15a、2026-11-18）

本体 `farm/farm-handover.md` の「explorer（phase 12e）」の節への追記。適用したら `farm-now.md` の体制に反映する。

## 何が変わるか

- `farm-explorer.service`（127.0.0.1:29484）は、Etherscan V2 と Blockscout PRO API（`https://api.blockscout.com/v2/api`、`chain_id=`、Etherscan と同じ module / action）の 2 つにつなぐ
- 順番: まず Etherscan。Etherscan がそのチェーンを not_on_plan / unsupported / invalid_key と言ったら、以後そのチェーンは Blockscout だけに聞く。`source` / `abi` で Etherscan に検証済みソースがないときも Blockscout に聞く。答えに `via` が付く
- キー: `/etc/farm/blockscout.key`（root 600、人間が置く）。drop-in `/etc/systemd/system/farm-explorer.service.d/blockscout.conf` の `LoadCredential=bkey:` で渡す。キーがなければ Etherscan だけ（12e と同じ動き）。両方のキーの文字列は答え・エラー・ログから消す
- `/etc/farm/explorer.json` に `"blockscout": {"upstream", "min_interval_s": 0.25, "daily_limit": 20000}`。Etherscan の 1 日 20,000 回とは別に数える
- CLI `/opt/farm/bin/explorer`: `via` を表示。Blockscout の複数ファイル（AdditionalSources）と proxy の欄（IsProxy / ImplementationAddress）を読む。`explorer chains` は 2 つの backend の状態を並べる
- `/health` は 12e の欄を残し、`backends`（backend ごとの回数と状態）と `fallbacks` を足した

## バンドル

- `farm-phase15a.tar.gz` sha256 `5146e7fcf59c8be6357b96e1149483c142557bd5d614ad636102c604558e661d`
- 中身: `new/farm-explorer`（8cd34d8b3ff98377b4a7efa59dd269d3441535713aa7d8ba3543aaa832a95d7b）、`new/explorer`（1671111b191255a564a11cc07b8fec3641592485d4b8d6025ad065196281897e）、`install.sh`（b165c0df…63e4cf76）、`test-15a.py`、meta 宛て `inbox-meta-2026-11-18-phase15a-blockscout.md`（1a1a1e19…738ebf38）
- install.sh の順番: キーの有無と権限 → 今の 2 ファイルが 12e 版か（文言で判定）→ 手元のテスト（偽の上流 2 つ、23 項目）→ キーで本物に 2 回（base のブロック番号、base USDC のソース）→ バックアップ（`.<name>.bak-15a`）→ 入れ替え・json・drop-in → restart。`/health` に blockscout がなければ戻す
- meta 宛てのメモで、TOOLS.md の explorer の行と wiki `infra/explorer.md` の更新、paper-reviewer.md の試行の枠の数え方（`trial-` で始まる live bot だけ）を頼んだ

## 状態

- 11-18 01:27 JST 適用（人間）。1 回目は Base が Blockscout の無料プランで 402（Featured chain は Builder 以上）で止まり何も変えず、人間が Builder（月 49 USD、1 か月だけ）を契約して 2 回目で通った
- 適用後の `explorer chains`: ethereum・arbitrum・polygon・hyperevm は via etherscan、base・optimism は via blockscout（etherscan not_on_plan）、bsc・avalanche・elysium はどちらもなし（Blockscout は HTTP 404 = 扱っていない）
- 入った sha256: farm-explorer 8cd34d8b…a95d7b、explorer 1671111b…81897e（期待値どおり）
- 小さな見た目の不具合（次に触るときに直す）: Blockscout の constructor args は 0x 付きで来るので CLI が `0x0x…` と出す。Blockscout の 404 は `unsupported` ではなく `error: HTTP 404` と出る。Builder が切れて無料に戻ると、402「requires one of the following plans」は not_on_plan ではなく 422 の一般の誤りになる
- 12-01 から HyperEVM は Etherscan が有料のみ。Blockscout も hyperevm を扱っていないので、そのときは道がなくなる
