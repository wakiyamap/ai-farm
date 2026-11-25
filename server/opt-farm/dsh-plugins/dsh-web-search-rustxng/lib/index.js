// Search provider for the dsh web seam (ctx.web): queries the local RustXNG service
// (SearXNG-compatible JSON API, keyless). Registered under id "rustxng"; select it with
// the bundle patch (cordis.patch.yml), installed with `dsh plugin --profile headless add <dir>`.
// No runtime imports: errors carry the dsh web error codes on a plain Error so the plugin
// loads without resolving peer packages from the profile scope.
class WebError extends Error {
  constructor(message, code, options) {
    super(message, options);
    this.name = "WebError";
    this.code = code;
  }
}

/** Cordis plugin name used by loader diagnostics. */
export const name = "farm-web-search-rustxng";
/** The web seam this provider registers into. */
export const inject = ["web"];

const PROVIDER_ID = "rustxng";
const BASE = (process.env.RUSTXNG_URL || "http://127.0.0.1:29483").replace(/\/+$/u, "");
const TIMEOUT_MS = 45000;

function toSource(item) {
  if (item == null || typeof item.url !== "string" || item.url.length === 0) return undefined;
  const snippet = typeof item.content === "string" ? item.content.replace(/\s+/gu, " ").trim() : "";
  const published = item.publishedDate ?? item.pubdate;
  return {
    url: item.url,
    ...(typeof item.title === "string" && item.title.length > 0 ? { title: item.title } : {}),
    ...(snippet.length > 0 ? { snippet } : {}),
    ...(typeof published === "string" && published.length > 0 ? { publishedAt: published } : {}),
  };
}

export class RustXngSearchProvider {
  id = PROVIDER_ID;

  available() {
    return URL.canParse(BASE);
  }

  async search(request, signal) {
    const url = `${BASE}/search?${new URLSearchParams({ q: request.query, format: "json" })}`;
    const timeout = AbortSignal.timeout(TIMEOUT_MS);
    const combined = signal === undefined ? timeout : AbortSignal.any([signal, timeout]);
    let response;
    try {
      response = await fetch(url, { headers: { accept: "application/json" }, redirect: "error", signal: combined });
    } catch (error) {
      if (signal?.aborted === true) throw new WebError("web search aborted", "WEB_ABORTED", { cause: error });
      throw new WebError(`local search service ${BASE} unreachable: ${String(error)}`, "WEB_PROVIDER_ERROR", { cause: error });
    }
    if (!response.ok) {
      throw new WebError(`local search service ${BASE} answered HTTP ${response.status}`, "WEB_PROVIDER_ERROR");
    }
    let body;
    try {
      body = await response.json();
    } catch (error) {
      throw new WebError(`local search service returned unparseable JSON: ${String(error)}`, "WEB_PROVIDER_ERROR", { cause: error });
    }
    const seen = new Set();
    const sources = [];
    for (const item of body.results ?? []) {
      const source = toSource(item);
      if (source === undefined || seen.has(source.url)) continue;
      seen.add(source.url);
      sources.push(source);
    }
    return { sources, truncated: false };
  }
}

/** Register the provider with `ctx.web`. */
export function apply(ctx) {
  ctx.web.registerSearchProvider(new RustXngSearchProvider());
}
