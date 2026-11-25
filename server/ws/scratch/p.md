# Page Not Found

The URL `v/woofi-dev-docs` does not exist. This page may have been moved, renamed, or deleted.

## Suggested Pages

You may be looking for one of the following:
- [How to swap tokens on WOOFi](https://learn.woo.org/user-guides/woofi-swap.md)
- [Earn vaults](https://learn.woo.org/woofi/earn-vaults.md)
- [Crosschain swaps](https://learn.woo.org/woofi/crosschain-swaps.md)
- [Perpetual futures](https://learn.woo.org/woofi/perpetual-futures.md)
- [WOOFi: All assets are coming onchain](https://learn.woo.org/woofi-all-assets-are-coming-onchain.md)

## How to find the correct page

If the exact page cannot be found, you can still retrieve the information using the documentation query interface.

### Option 1 — Ask a question (recommended)

Perform an HTTP GET request on the following URL with the `ask` and `goal` query parameters:

```
GET https://learn.woo.org/user-guides/woofi-swap.md?ask=<question>&goal=<user_goal>
```

`ask` is the immediate question: it should be specific, self-contained, and written in natural language.
`goal` is what the user is ultimately trying to achieve, the reason they need the answer. Sharing it helps GitBook give you a better, more relevant answer. A goal is most helpful when it describes the outcome the user wants rather than restating the question. For example, with `ask=how do I create an API token`, a goal like `automate deployments from our CI pipeline` lets GitBook tailor the answer to that use case.

The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

### Option 2 — Browse the documentation index

Full index: https://learn.woo.org/sitemap.md

Use this to discover valid page paths or navigate the documentation structure.

### Option 3 — Retrieve the full documentation corpus

Full export: https://learn.woo.org/llms-full.txt

Use this to access all content at once and perform your own parsing or retrieval. It will be more expensive.

## Tips for requesting documentation

Prefer `.md` URLs for structured content, append `.md` to URLs (e.g., `/user-guides/woofi-swap.md`).

You may also use `Accept: text/markdown` header for content negotiation.
