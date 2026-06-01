# Browser v0.1

PyAgentCLI includes a first local page inspection tool:

```text
inspect_page(url, max_chars=2000)
```

This is a deliberately small browser slice. It lets the agent inspect local HTML pages and localhost web apps without opening arbitrary external websites.

## Supported URLs

Allowed:

- workspace-relative HTML paths, such as `site/index.html`
- `file://` URLs inside the workspace
- `http://localhost:*`
- `http://127.0.0.1:*`
- `http://[::1]:*`

Denied by default:

- external HTTP or HTTPS URLs
- unsupported schemes
- `file://` URLs outside the workspace

## Output

The tool returns:

- final URL
- page title
- normalized text snapshot

It skips `script`, `style`, and `noscript` content.

Example:

```text
URL: file:///path/to/site/index.html
Title: Demo Page

Text:
Hello PyAgent Status READY
```

## Why This Is Not Full Playwright Yet

Browser v0.1 focuses on the safety and agent-tool contract first:

- stable tool schema
- local-only URL guardrail
- deterministic tests
- no large browser binary dependency

Later Browser slices can replace or extend the internals with Playwright for screenshots, DOM inspection, console logs, and interactive verification.

## Non-Goals

Browser v0.1 does not yet include:

- JavaScript execution
- screenshots
- DOM selector querying
- clicking or typing
- console/network logs
- external website browsing
