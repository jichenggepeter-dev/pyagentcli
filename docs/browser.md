# Browser v0.2

PyAgentCLI includes a first local page inspection tool:

```text
inspect_page(url, max_chars=2000)
browser_dom_snapshot(url, max_chars=2000)
browser_console_logs(url, wait_ms=500)
browser_screenshot(url, output_path=".pyagent/browser/screenshot.png")
```

This is a deliberately local-first browser slice. It lets the agent inspect local HTML pages and localhost web apps without opening arbitrary external websites.

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

`inspect_page` returns:

- final URL
- page title
- normalized text snapshot

It skips `script`, `style`, and `noscript` content.

`browser_dom_snapshot` returns a more UI-oriented static snapshot:

- final URL
- page title
- headings
- links
- controls
- normalized text snapshot

`browser_console_logs` and `browser_screenshot` are optional Playwright-backed tools. If Playwright is not installed, they return a clear failure explaining that optional browser dependencies are missing.

Example:

```text
URL: file:///path/to/site/index.html
Title: Demo Page

Text:
Hello PyAgent Status READY
```

## Optional Playwright Support

Browser v0.2 keeps Playwright optional:

- no browser dependency is required for the core CLI
- DOM snapshots work without Playwright for static local HTML
- console logs and screenshots require Playwright when available
- screenshot output is restricted to `.pyagent/browser/`

Install and browser binary setup are intentionally not automatic in this slice.

## Non-Goals

Browser v0.2 does not yet include:

- clicking or typing
- network logs
- external website browsing
