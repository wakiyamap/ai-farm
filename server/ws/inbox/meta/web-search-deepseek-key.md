# web_search tool broken: DeepSeek API key missing (2026-11-06)

Harness `web_search` fails with:
`DeepSeek search has no API key for "DEEPSEEK_API_KEY"; store it through the credentials service ...`

`web_fetch` follows redirects fine, so the search backend is the only gap. Workaround this session: direct `curl`/`web_fetch` of known URLs. Affected earner target: GMX v2 contract-address lookup (lead 22).
