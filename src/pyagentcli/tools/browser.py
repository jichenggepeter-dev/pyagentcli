from __future__ import annotations

import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from pyagentcli.tools.base import RiskLevel, ToolContext, ToolResult, function_schema


LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


@dataclass(frozen=True)
class BrowserCapabilityStatus:
    playwright_installed: bool
    message: str

    def format_text(self) -> str:
        status = "installed" if self.playwright_installed else "missing"
        return (
            "Browser capability status:\n"
            f"- Playwright package: {status}\n"
            f"- {self.message}"
        )


def check_browser_capabilities() -> BrowserCapabilityStatus:
    if find_spec("playwright") is None:
        return BrowserCapabilityStatus(
            playwright_installed=False,
            message='Install optional browser support with `python -m pip install -e ".[browser]"`, then run `python -m playwright install chromium`.',
        )
    return BrowserCapabilityStatus(
        playwright_installed=True,
        message="Playwright Python package is available. If browser launch fails, run `python -m playwright install chromium`.",
    )


class InspectPageTool:
    name = "inspect_page"
    description = "Inspect a local HTML page or localhost URL and return title, URL, and a text snapshot."
    risk_level = RiskLevel.READ

    def schema(self) -> dict[str, Any]:
        return function_schema(
            self.name,
            self.description,
            {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "A file://, workspace-relative path, localhost, 127.0.0.1, or ::1 URL.",
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Maximum number of text snapshot characters. Defaults to 2000.",
                    },
                },
                "required": ["url"],
            },
        )

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        raw_url = args.get("url")
        if not isinstance(raw_url, str) or not raw_url.strip():
            return ToolResult.failure("Missing required non-empty string argument: url")

        max_chars = _coerce_max_chars(args.get("max_chars"))
        prepared = _prepare_local_url(raw_url.strip(), context)
        if isinstance(prepared, ToolResult):
            return prepared

        display_url, html = prepared
        snapshot = _html_snapshot(html, max_chars=max_chars)
        return ToolResult.success(
            f"URL: {display_url}\nTitle: {snapshot.title or '<untitled>'}\n\nText:\n{snapshot.text or '<no text>'}",
            url=display_url,
            title=snapshot.title,
            text_chars=len(snapshot.text),
        )


class BrowserDomSnapshotTool:
    name = "browser_dom_snapshot"
    description = "Return a local page DOM-oriented snapshot with headings, links, controls, and text."
    risk_level = RiskLevel.READ

    def schema(self) -> dict[str, Any]:
        return function_schema(
            self.name,
            self.description,
            {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "A file://, workspace-relative path, localhost, 127.0.0.1, or ::1 URL.",
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Maximum text snapshot characters. Defaults to 2000.",
                    },
                },
                "required": ["url"],
            },
        )

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        raw_url = args.get("url")
        if not isinstance(raw_url, str) or not raw_url.strip():
            return ToolResult.failure("Missing required non-empty string argument: url")

        prepared = _prepare_local_url(raw_url.strip(), context)
        if isinstance(prepared, ToolResult):
            return prepared

        display_url, html = prepared
        snapshot = _html_snapshot(html, max_chars=_coerce_max_chars(args.get("max_chars")))
        content = _format_dom_snapshot(display_url, snapshot)
        return ToolResult.success(
            content,
            url=display_url,
            title=snapshot.title,
            headings=len(snapshot.headings),
            links=len(snapshot.links),
            controls=len(snapshot.controls),
            text_chars=len(snapshot.text),
        )


class BrowserConsoleLogsTool:
    name = "browser_console_logs"
    description = "Collect console logs from a local page with optional Playwright support."
    risk_level = RiskLevel.READ

    def schema(self) -> dict[str, Any]:
        return function_schema(
            self.name,
            self.description,
            {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "A file://, workspace-relative path, localhost, 127.0.0.1, or ::1 URL.",
                    },
                    "wait_ms": {
                        "type": "integer",
                        "description": "Milliseconds to wait after page load. Defaults to 500.",
                    },
                },
                "required": ["url"],
            },
        )

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        raw_url = args.get("url")
        if not isinstance(raw_url, str) or not raw_url.strip():
            return ToolResult.failure("Missing required non-empty string argument: url")

        prepared_url = _prepare_browser_target(raw_url.strip(), context)
        if isinstance(prepared_url, ToolResult):
            return prepared_url
        playwright = _load_playwright()
        if isinstance(playwright, ToolResult):
            return playwright

        wait_ms = _coerce_wait_ms(args.get("wait_ms"))
        sync_playwright, playwright_error = playwright
        logs: list[str] = []
        try:
            with sync_playwright() as manager:
                browser = manager.chromium.launch(headless=True)
                page = browser.new_page()
                page.on("console", lambda message: logs.append(f"{message.type}: {message.text}"))
                page.goto(prepared_url, wait_until="load", timeout=10_000)
                page.wait_for_timeout(wait_ms)
                browser.close()
        except playwright_error as exc:
            return ToolResult.failure(f"Could not collect console logs: {exc}", exception_type=type(exc).__name__)

        content = "\n".join(logs) if logs else "<no console logs>"
        return ToolResult.success(f"URL: {prepared_url}\n\nConsole logs:\n{content}", url=prepared_url, logs=len(logs))


class BrowserScreenshotTool:
    name = "browser_screenshot"
    description = "Capture a screenshot of a local page with optional Playwright support."
    risk_level = RiskLevel.READ

    def schema(self) -> dict[str, Any]:
        return function_schema(
            self.name,
            self.description,
            {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "A file://, workspace-relative path, localhost, 127.0.0.1, or ::1 URL.",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Workspace-relative output path under .pyagent/browser/. Defaults to auto-generated.",
                    },
                },
                "required": ["url"],
            },
        )

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        raw_url = args.get("url")
        if not isinstance(raw_url, str) or not raw_url.strip():
            return ToolResult.failure("Missing required non-empty string argument: url")

        prepared_url = _prepare_browser_target(raw_url.strip(), context)
        if isinstance(prepared_url, ToolResult):
            return prepared_url
        playwright = _load_playwright()
        if isinstance(playwright, ToolResult):
            return playwright

        output_path = _prepare_screenshot_path(args.get("output_path"), context)
        if isinstance(output_path, ToolResult):
            return output_path

        sync_playwright, playwright_error = playwright
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with sync_playwright() as manager:
                browser = manager.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(prepared_url, wait_until="load", timeout=10_000)
                page.screenshot(path=str(output_path), full_page=True)
                browser.close()
        except playwright_error as exc:
            return ToolResult.failure(f"Could not capture screenshot: {exc}", exception_type=type(exc).__name__)

        return ToolResult.success(
            f"URL: {prepared_url}\nScreenshot: {output_path}",
            url=prepared_url,
            screenshot_path=str(output_path),
        )


class _HTMLSnapshot:
    def __init__(
        self,
        title: str,
        text: str,
        headings: list[str],
        links: list[str],
        controls: list[str],
    ) -> None:
        self.title = title
        self.text = text
        self.headings = headings
        self.links = links
        self.controls = controls


class _SnapshotParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.heading_parts: list[str] = []
        self.links: list[str] = []
        self.controls: list[str] = []
        self._in_title = False
        self._heading_tag: str | None = None
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_dict = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._heading_tag = tag
        if tag == "a":
            href = attrs_dict.get("href") or "<no href>"
            self.links.append(href)
        if tag in {"button", "input", "textarea", "select"}:
            label = attrs_dict.get("aria-label") or attrs_dict.get("name") or attrs_dict.get("id") or tag
            self.controls.append(f"{tag}: {label}")
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        if tag == self._heading_tag:
            self._heading_tag = None
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
            return
        if self._skip_depth:
            return
        stripped = data.strip()
        if stripped:
            if self._heading_tag:
                self.heading_parts.append(f"{self._heading_tag}: {stripped}")
            self.text_parts.append(stripped)


def _prepare_local_url(raw_url: str, context: ToolContext) -> tuple[str, str] | ToolResult:
    parsed = urllib.parse.urlparse(raw_url)
    if not parsed.scheme:
        target = context.safety_policy.resolve_workspace_path(raw_url)
        return _read_file_url(target)

    if parsed.scheme == "file":
        path = Path(urllib.request.url2pathname(parsed.path))
        try:
            path.relative_to(context.workspace_root)
        except ValueError as exc:
            return ToolResult.failure(f"File URL escapes workspace: {raw_url}", exception_type=type(exc).__name__)
        return _read_file_url(path)

    if parsed.scheme in {"http", "https"}:
        host = parsed.hostname or ""
        if host not in LOCAL_HOSTS:
            return ToolResult.failure(f"Only local browser URLs are allowed in v0.1: {raw_url}")
        return _read_http_url(raw_url)

    return ToolResult.failure(f"Unsupported URL scheme for inspect_page: {parsed.scheme}")


def _prepare_browser_target(raw_url: str, context: ToolContext) -> str | ToolResult:
    parsed = urllib.parse.urlparse(raw_url)
    if not parsed.scheme:
        path = context.safety_policy.resolve_workspace_path(raw_url)
        if not path.exists() or not path.is_file():
            return ToolResult.failure(f"Page file does not exist: {path}")
        return path.as_uri()

    if parsed.scheme == "file":
        path = Path(urllib.request.url2pathname(parsed.path))
        try:
            path.relative_to(context.workspace_root)
        except ValueError as exc:
            return ToolResult.failure(f"File URL escapes workspace: {raw_url}", exception_type=type(exc).__name__)
        if not path.exists() or not path.is_file():
            return ToolResult.failure(f"Page file does not exist: {path}")
        return path.as_uri()

    if parsed.scheme in {"http", "https"}:
        host = parsed.hostname or ""
        if host not in LOCAL_HOSTS:
            return ToolResult.failure(f"Only local browser URLs are allowed: {raw_url}")
        return raw_url

    return ToolResult.failure(f"Unsupported URL scheme for browser tool: {parsed.scheme}")


def _read_file_url(path: Path) -> tuple[str, str] | ToolResult:
    if not path.exists():
        return ToolResult.failure(f"Page file does not exist: {path}")
    if not path.is_file():
        return ToolResult.failure(f"Page path is not a file: {path}")
    try:
        html = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ToolResult.failure(f"Page file is not valid UTF-8 text: {path}")
    return path.as_uri(), html


def _read_http_url(url: str) -> tuple[str, str] | ToolResult:
    request = urllib.request.Request(url, headers={"User-Agent": "PyAgentCLI/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type and content_type:
                return ToolResult.failure(f"Unsupported content type: {content_type}")
            body = response.read(1_000_000).decode("utf-8", errors="replace")
            final_url = response.geturl()
    except urllib.error.URLError as exc:
        return ToolResult.failure(f"Could not inspect local URL: {exc.reason}")
    return final_url, body


def _html_snapshot(html: str, *, max_chars: int) -> _HTMLSnapshot:
    parser = _SnapshotParser()
    parser.feed(html)
    title = _normalize_text(" ".join(parser.title_parts))
    text = _normalize_text(" ".join(parser.text_parts))
    if len(text) > max_chars:
        text = text[: max_chars - 15].rstrip() + "\n... <truncated>"
    headings = [_normalize_text(value) for value in parser.heading_parts]
    links = [_normalize_text(value) for value in parser.links]
    controls = [_normalize_text(value) for value in parser.controls]
    return _HTMLSnapshot(title=title, text=text, headings=headings, links=links, controls=controls)


def _format_dom_snapshot(url: str, snapshot: _HTMLSnapshot) -> str:
    lines = [f"URL: {url}", f"Title: {snapshot.title or '<untitled>'}", ""]
    lines.append("Headings:")
    lines.extend(f"- {heading}" for heading in (snapshot.headings or ["<none>"]))
    lines.append("")
    lines.append("Links:")
    lines.extend(f"- {link}" for link in (snapshot.links or ["<none>"]))
    lines.append("")
    lines.append("Controls:")
    lines.extend(f"- {control}" for control in (snapshot.controls or ["<none>"]))
    lines.append("")
    lines.append("Text:")
    lines.append(snapshot.text or "<no text>")
    return "\n".join(lines)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _coerce_max_chars(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 2000
    return max(200, min(parsed, 20_000))


def _coerce_wait_ms(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 500
    return max(0, min(parsed, 5_000))


def _prepare_screenshot_path(value: Any, context: ToolContext) -> Path | ToolResult:
    if isinstance(value, str) and value.strip():
        raw_path = value.strip()
    else:
        raw_path = ".pyagent/browser/screenshot.png"
    path = (context.workspace_root / raw_path).resolve()
    try:
        path.relative_to(context.workspace_root)
    except ValueError:
        return ToolResult.failure("Screenshot output_path escapes workspace.")
    browser_dir = context.workspace_root / ".pyagent" / "browser"
    try:
        path.relative_to(browser_dir)
    except ValueError:
        return ToolResult.failure("Screenshot output_path must be under .pyagent/browser/.")
    return path


def _load_playwright():
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        return ToolResult.failure(
            "Playwright is not installed. Install optional browser dependencies to use this tool."
        )
    return sync_playwright, PlaywrightError
