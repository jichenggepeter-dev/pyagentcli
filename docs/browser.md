# Browser v0.2

PyAgentCLI includes a first local page inspection tool:

```text
inspect_page(url, max_chars=2000)
browser_dom_snapshot(url, max_chars=2000)
browser_query_selector(url, selector, max_results=20)
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

`browser_query_selector` supports simple read-only lookup for:

- tag selectors such as `main`
- id selectors such as `#app`
- class selectors such as `.status`

Complex CSS selectors are intentionally rejected in this static parser slice.

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

Check local browser capability status:

```bash
pyagent --check-browser
```

Install optional browser support:

```bash
python -m pip install -e ".[browser]"
python -m playwright install chromium
```

Install and browser binary setup are intentionally explicit, not automatic.

Optional success-path verification:

```bash
.venv/bin/python -m pytest tests/test_browser_playwright_optional.py
```

Those tests are skipped when the Playwright Python package is missing. If the package is installed but Chromium has not been installed yet, they also skip with a browser-binary message.

## Non-Goals

Browser v0.2 does not yet include:

- clicking or typing
- network logs
- complex CSS selector support
- external website browsing
