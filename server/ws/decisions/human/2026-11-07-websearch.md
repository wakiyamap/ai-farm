# 2026-11-07 Web 検索が使えるようになった（phase 8）

- ローカルのメタ検索サービス（RustXNG。SearXNG 互換で、API キーは不要）を `farm-search.service` として 127.0.0.1:29483 で動かし始めた。
- **earner（dsh）**: `web_search` ツールの検索先を、DeepSeek から上のローカルサービスに切り替えた（プロバイダ `rustxng`）。web_search は今まで鍵のエラーで使えなかったが、次のセッションからそのまま使える。2026-11-07 infra-requests §1 の「web_search を呼ばない」は撤回する。
- **全ロール共通**: `websearch <query> [-n N] [--time day|week|month|year] [--json]` で、番号付きの結果（タイトル、URL、要約）が得られる。claude で動くロールも `Bash(websearch *)` で実行できる。
- **検索エンジンの範囲**: 利用規約で自動アクセスが認められている検索エンジンだけを使う。GitHub、Stack Overflow、Hacker News、arXiv、Wikipedia、npm、crates.io などで、一般 Web の検索は弱い（mwmbl、wiby）。
  - `!gh <語>` で GitHub だけを検索できる。コントラクトアドレスやデプロイ一覧を探すときに有効。`!so`、`!hn`、`!arx`、`!wp` も同様。
  - 結果が少ないときは語を変えるか、DefiLlama の adapter リポジトリ、docs、エクスプローラを web_fetch で直接読むこと。
- 検索エンジンが CAPTCHA や 429 を返しても、回避（UA の偽装やプロキシなど）はしない。1 セッションでの大量の連続検索も避けること。
- meta: TOOLS.md の web の行をこの内容に更新し、web_search の鍵エラーに関する古いメモ（inbox/meta、wiki）を片付けること。次回の meta で、earner の web_search の成功・失敗の件数を数えること。
