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


class BrowserQuerySelectorTool:
    name = "browser_query_selector"
    description = "Query simple tag, #id, or .class selectors on a local page and return matching text."
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
                    "selector": {
                        "type": "string",
                        "description": "A simple selector: tag, #id, or .class. Complex CSS selectors are not supported yet.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum matches to return. Defaults to 20.",
                    },
                },
                "required": ["url", "selector"],
            },
        )

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        raw_url = args.get("url")
        if not isinstance(raw_url, str) or not raw_url.strip():
            return ToolResult.failure("Missing required non-empty string argument: url")
        selector = args.get("selector")
        if not isinstance(selector, str) or not selector.strip():
            return ToolResult.failure("Missing required non-empty string argument: selector")

        parsed_selector = _parse_simple_selector(selector.strip())
        if isinstance(parsed_selector, ToolResult):
            return parsed_selector

        prepared = _prepare_local_url(raw_url.strip(), context)
        if isinstance(prepared, ToolResult):
            return prepared

        display_url, html = prepared
        max_results = _coerce_max_results(args.get("max_results"))
        matches = _query_html(html, parsed_selector, max_results=max_results)
        lines = [f"URL: {display_url}", f"Selector: {selector.strip()}", f"Matches: {len(matches)}", ""]
        if not matches:
            lines.append("<no matches>")
        else:
            for index, match in enumerate(matches, start=1):
                lines.append(f"{index}. {match.format_text()}")
        return ToolResult.success(
            "\n".join(lines),
            url=display_url,
            selector=selector.strip(),
            matches=len(matches),
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


class BrowserNetworkLogsTool:
    name = "browser_network_logs"
    description = "Collect request and response summaries from a local page with optional Playwright support."
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
                    "max_entries": {
                        "type": "integer",
                        "description": "Maximum request/response entries to return. Defaults to 50.",
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
        max_entries = _coerce_max_entries(args.get("max_entries"))
        sync_playwright, playwright_error = playwright
        entries: dict[str, _NetworkLogEntry] = {}
        ordered_keys: list[str] = []

        def remember_request(request: Any) -> None:
            if len(ordered_keys) >= max_entries:
                return
            key = id(request)
            text_key = str(key)
            ordered_keys.append(text_key)
            entries[text_key] = _NetworkLogEntry(
                method=request.method,
                url=request.url,
                resource_type=request.resource_type,
            )

        def remember_response(response: Any) -> None:
            text_key = str(id(response.request))
            entry = entries.get(text_key)
            if entry is not None:
                entries[text_key] = _NetworkLogEntry(
                    method=entry.method,
                    url=entry.url,
                    resource_type=entry.resource_type,
                    status=response.status,
                    failure=entry.failure,
                )

        def remember_failure(request: Any) -> None:
            text_key = str(id(request))
            entry = entries.get(text_key)
            if entry is not None:
                failure = request.failure
                entries[text_key] = _NetworkLogEntry(
                    method=entry.method,
                    url=entry.url,
                    resource_type=entry.resource_type,
                    status=entry.status,
                    failure=failure or "failed",
                )

        try:
            with sync_playwright() as manager:
                browser = manager.chromium.launch(headless=True)
                page = browser.new_page()
                page.on("request", remember_request)
                page.on("response", remember_response)
                page.on("requestfailed", remember_failure)
                page.goto(prepared_url, wait_until="load", timeout=10_000)
                page.wait_for_timeout(wait_ms)
                browser.close()
        except playwright_error as exc:
            return ToolResult.failure(f"Could not collect network logs: {exc}", exception_type=type(exc).__name__)

        collected = [entries[key] for key in ordered_keys if key in entries]
        lines = [f"URL: {prepared_url}", f"Network entries: {len(collected)}", ""]
        if not collected:
            lines.append("<no network entries>")
        else:
            lines.extend(f"{index}. {entry.format_text()}" for index, entry in enumerate(collected, start=1))
        return ToolResult.success(
            "\n".join(lines),
            url=prepared_url,
            entries=len(collected),
        )


class BrowserAssertTool:
    name = "browser_assert"
    description = "Assert expected text, selector presence, and page status for a local page or localhost URL."
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
                    "expected_text": {
                        "type": "string",
                        "description": "Text expected to appear in the rendered page body.",
                    },
                    "selector": {
                        "type": "string",
                        "description": "Selector expected to exist. Static fallback supports tag, #id, or .class; Playwright supports CSS selectors.",
                    },
                    "expected_status": {
                        "type": "integer",
                        "description": "Expected main page status. File URLs are treated as 200 when the file exists.",
                    },
                    "wait_ms": {
                        "type": "integer",
                        "description": "Milliseconds to wait after page load when Playwright is available. Defaults to 500.",
                    },
                },
                "required": ["url"],
            },
        )

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        raw_url = args.get("url")
        if not isinstance(raw_url, str) or not raw_url.strip():
            return ToolResult.failure("Missing required non-empty string argument: url")
        assertion = _parse_browser_assertion(args)
        if isinstance(assertion, ToolResult):
            return assertion
        if not assertion.has_checks:
            return ToolResult.failure("browser_assert requires at least one of expected_text, selector, or expected_status.")

        prepared_url = _prepare_browser_target(raw_url.strip(), context)
        if isinstance(prepared_url, ToolResult):
            return prepared_url

        playwright = _load_playwright()
        if not isinstance(playwright, ToolResult):
            return _run_playwright_assertion(prepared_url, assertion, playwright)
        return _run_static_assertion(raw_url.strip(), context, assertion, playwright.error or "")


class BrowserInteractTool:
    name = "browser_interact"
    description = "Run approved click, type, or wait actions on a local page and return the resulting text snapshot."
    risk_level = RiskLevel.EXECUTE

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
                    "actions": {
                        "type": "array",
                        "description": "Ordered local browser actions. Supported types: click, type, fill, wait.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "selector": {"type": "string"},
                                "text": {"type": "string"},
                                "wait_ms": {"type": "integer"},
                            },
                            "required": ["type"],
                        },
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Maximum final text snapshot characters. Defaults to 2000.",
                    },
                },
                "required": ["url", "actions"],
            },
        )

    def preview(self, args: dict[str, Any], context: ToolContext) -> str | None:
        actions = args.get("actions") if isinstance(args.get("actions"), list) else []
        lines = ["Browser interaction preview:"]
        lines.append(f"- URL: {args.get('url')}")
        lines.append(f"- Actions: {len(actions)}")
        for index, action in enumerate(actions[:10], start=1):
            if isinstance(action, dict):
                action_type = str(action.get("type") or "")
                selector = str(action.get("selector") or "")
                lines.append(f"  {index}. {action_type} {selector}".rstrip())
        return "\n".join(lines)

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        raw_url = args.get("url")
        if not isinstance(raw_url, str) or not raw_url.strip():
            return ToolResult.failure("Missing required non-empty string argument: url")
        raw_actions = args.get("actions")
        if not isinstance(raw_actions, list) or not raw_actions:
            return ToolResult.failure("Missing required non-empty array argument: actions")

        prepared_url = _prepare_browser_target(raw_url.strip(), context)
        if isinstance(prepared_url, ToolResult):
            return prepared_url
        actions = _parse_browser_actions(raw_actions)
        if isinstance(actions, ToolResult):
            return actions
        playwright = _load_playwright()
        if isinstance(playwright, ToolResult):
            return playwright

        sync_playwright, playwright_error = playwright
        max_chars = _coerce_max_chars(args.get("max_chars"))
        try:
            with sync_playwright() as manager:
                browser = manager.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(prepared_url, wait_until="load", timeout=10_000)
                for action in actions:
                    _apply_browser_action(page, action)
                title = page.title()
                text = _normalize_text(page.locator("body").inner_text(timeout=5_000))
                if len(text) > max_chars:
                    text = text[: max_chars - 15].rstrip() + "\n... <truncated>"
                browser.close()
        except playwright_error as exc:
            return ToolResult.failure(f"Could not run browser interaction: {exc}", exception_type=type(exc).__name__)

        return ToolResult.success(
            f"URL: {prepared_url}\nTitle: {title or '<untitled>'}\nActions: {len(actions)}\n\nText:\n{text or '<no text>'}",
            url=prepared_url,
            title=title,
            actions=len(actions),
            text_chars=len(text),
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


@dataclass(frozen=True)
class _SimpleSelector:
    kind: str
    value: str


@dataclass(frozen=True)
class _ElementMatch:
    tag: str
    element_id: str | None
    classes: tuple[str, ...]
    text: str

    def format_text(self) -> str:
        identity = self.tag
        if self.element_id:
            identity += f"#{self.element_id}"
        if self.classes:
            identity += "." + ".".join(self.classes)
        return f"{identity}: {self.text or '<no text>'}"


@dataclass(frozen=True)
class _BrowserAction:
    type: str
    selector: str | None = None
    text: str | None = None
    wait_ms: int = 0


@dataclass(frozen=True)
class _BrowserAssertion:
    expected_text: str | None
    selector: str | None
    expected_status: int | None
    wait_ms: int

    @property
    def has_checks(self) -> bool:
        return self.expected_text is not None or self.selector is not None or self.expected_status is not None


@dataclass(frozen=True)
class _NetworkLogEntry:
    method: str
    url: str
    resource_type: str
    status: int | None = None
    failure: str | None = None

    def format_text(self) -> str:
        status = self.status if self.status is not None else "<pending>"
        failure = self.failure or "<none>"
        return (
            f"{self.method} {self.url} "
            f"status={status} resource={self.resource_type} failure={failure}"
        )


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


class _QueryParser(HTMLParser):
    def __init__(self, selector: _SimpleSelector) -> None:
        super().__init__(convert_charrefs=True)
        self.selector = selector
        self.matches: list[_ElementMatch] = []
        self._stack: list[dict[str, Any]] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        attrs_dict = dict(attrs)
        frame = {
            "tag": tag,
            "id": attrs_dict.get("id"),
            "classes": tuple((attrs_dict.get("class") or "").split()),
            "text": [],
            "matched": self._matches(tag, attrs_dict),
        }
        self._stack.append(frame)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if not self._stack:
            return
        frame = self._stack.pop()
        text = _normalize_text(" ".join(frame["text"]))
        if frame["matched"]:
            self.matches.append(
                _ElementMatch(
                    tag=str(frame["tag"]),
                    element_id=frame["id"],
                    classes=frame["classes"],
                    text=text,
                )
            )
        if self._stack and text:
            self._stack[-1]["text"].append(text)
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth or not self._stack:
            return
        stripped = data.strip()
        if stripped:
            self._stack[-1]["text"].append(stripped)

    def _matches(self, tag: str, attrs: dict[str, str | None]) -> bool:
        if self.selector.kind == "tag":
            return tag == self.selector.value
        if self.selector.kind == "id":
            return attrs.get("id") == self.selector.value
        if self.selector.kind == "class":
            return self.selector.value in (attrs.get("class") or "").split()
        return False


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


def _local_http_status(url: str) -> int | None:
    request = urllib.request.Request(url, headers={"User-Agent": "PyAgentCLI/0.1"}, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except urllib.error.URLError:
        return None


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


def _parse_simple_selector(selector: str) -> _SimpleSelector | ToolResult:
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", selector):
        return _SimpleSelector(kind="tag", value=selector.lower())
    if re.fullmatch(r"#[A-Za-z_][A-Za-z0-9_-]*", selector):
        return _SimpleSelector(kind="id", value=selector[1:])
    if re.fullmatch(r"\.[A-Za-z_][A-Za-z0-9_-]*", selector):
        return _SimpleSelector(kind="class", value=selector[1:])
    return ToolResult.failure("Only simple tag, #id, or .class selectors are supported.")


def _query_html(html: str, selector: _SimpleSelector, *, max_results: int) -> list[_ElementMatch]:
    parser = _QueryParser(selector)
    parser.feed(html)
    return parser.matches[:max_results]


def _parse_browser_actions(raw_actions: list[Any]) -> list[_BrowserAction] | ToolResult:
    if len(raw_actions) > 20:
        return ToolResult.failure("browser_interact supports at most 20 actions per call.")

    actions: list[_BrowserAction] = []
    for index, raw_action in enumerate(raw_actions, start=1):
        if not isinstance(raw_action, dict):
            return ToolResult.failure(f"Action {index} must be an object.")
        action_type = str(raw_action.get("type") or "").strip().lower()
        if action_type not in {"click", "type", "fill", "wait"}:
            return ToolResult.failure(f"Action {index} has unsupported type: {action_type or '<missing>'}")
        if action_type in {"click", "type", "fill"}:
            selector = raw_action.get("selector")
            if not isinstance(selector, str) or not selector.strip():
                return ToolResult.failure(f"Action {index} requires a non-empty selector.")
            text = raw_action.get("text")
            if action_type in {"type", "fill"} and not isinstance(text, str):
                return ToolResult.failure(f"Action {index} requires string text.")
            actions.append(
                _BrowserAction(
                    type=action_type,
                    selector=selector.strip(),
                    text=text if isinstance(text, str) else None,
                )
            )
            continue
        actions.append(_BrowserAction(type="wait", wait_ms=_coerce_wait_ms(raw_action.get("wait_ms"))))
    return actions


def _parse_browser_assertion(args: dict[str, Any]) -> _BrowserAssertion | ToolResult:
    expected_text = args.get("expected_text")
    if expected_text is not None and not isinstance(expected_text, str):
        return ToolResult.failure("expected_text must be a string when provided.")
    selector = args.get("selector")
    if selector is not None and (not isinstance(selector, str) or not selector.strip()):
        return ToolResult.failure("selector must be a non-empty string when provided.")
    expected_status = args.get("expected_status")
    parsed_status: int | None = None
    if expected_status is not None:
        try:
            parsed_status = int(expected_status)
        except (TypeError, ValueError):
            return ToolResult.failure("expected_status must be an integer when provided.")
        if parsed_status < 100 or parsed_status > 599:
            return ToolResult.failure("expected_status must be between 100 and 599.")
    return _BrowserAssertion(
        expected_text=expected_text if isinstance(expected_text, str) else None,
        selector=selector.strip() if isinstance(selector, str) else None,
        expected_status=parsed_status,
        wait_ms=_coerce_wait_ms(args.get("wait_ms")),
    )


def _run_playwright_assertion(
    prepared_url: str,
    assertion: _BrowserAssertion,
    playwright,
) -> ToolResult:
    sync_playwright, playwright_error = playwright
    failures: list[str] = []
    checks: list[str] = []
    try:
        with sync_playwright() as manager:
            browser = manager.chromium.launch(headless=True)
            page = browser.new_page()
            response = page.goto(prepared_url, wait_until="load", timeout=10_000)
            page.wait_for_timeout(assertion.wait_ms)
            status = response.status if response is not None else (200 if prepared_url.startswith("file:") else None)
            text = _normalize_text(page.locator("body").inner_text(timeout=5_000))
            if assertion.expected_status is not None:
                if status == assertion.expected_status:
                    checks.append(f"status == {assertion.expected_status}")
                else:
                    failures.append(f"status was {status}, expected {assertion.expected_status}")
            if assertion.expected_text is not None:
                if assertion.expected_text in text:
                    checks.append(f"text contains {assertion.expected_text!r}")
                else:
                    failures.append(f"text did not contain {assertion.expected_text!r}")
            if assertion.selector is not None:
                count = page.locator(assertion.selector).count()
                if count > 0:
                    checks.append(f"selector {assertion.selector!r} exists ({count} match(es))")
                else:
                    failures.append(f"selector {assertion.selector!r} did not match")
            browser.close()
    except playwright_error as exc:
        return ToolResult.failure(f"Could not run browser assertion: {exc}", exception_type=type(exc).__name__)

    return _format_assertion_result(
        url=prepared_url,
        mode="playwright",
        failures=failures,
        checks=checks,
    )


def _run_static_assertion(
    raw_url: str,
    context: ToolContext,
    assertion: _BrowserAssertion,
    playwright_error: str,
) -> ToolResult:
    prepared = _prepare_local_url(raw_url, context)
    if isinstance(prepared, ToolResult):
        return prepared

    display_url, html = prepared
    failures: list[str] = []
    checks: list[str] = []
    parsed = urllib.parse.urlparse(display_url)
    status = 200 if parsed.scheme == "file" else _local_http_status(display_url)
    snapshot = _html_snapshot(html, max_chars=20_000)

    if assertion.expected_status is not None:
        if status == assertion.expected_status:
            checks.append(f"status == {assertion.expected_status}")
        else:
            failures.append(f"status was {status}, expected {assertion.expected_status}")
    if assertion.expected_text is not None:
        if assertion.expected_text in snapshot.text:
            checks.append(f"text contains {assertion.expected_text!r}")
        else:
            failures.append(f"text did not contain {assertion.expected_text!r}")
    if assertion.selector is not None:
        parsed_selector = _parse_simple_selector(assertion.selector)
        if isinstance(parsed_selector, ToolResult):
            failures.append(
                f"selector {assertion.selector!r} requires Playwright or a simple tag, #id, or .class selector"
            )
        else:
            matches = _query_html(html, parsed_selector, max_results=1)
            if matches:
                checks.append(f"selector {assertion.selector!r} exists ({len(matches)} match(es))")
            else:
                failures.append(f"selector {assertion.selector!r} did not match")

    return _format_assertion_result(
        url=display_url,
        mode=f"static fallback; Playwright unavailable ({playwright_error})",
        failures=failures,
        checks=checks,
    )


def _format_assertion_result(*, url: str, mode: str, failures: list[str], checks: list[str]) -> ToolResult:
    passed = not failures
    lines = [f"URL: {url}", f"Mode: {mode}", f"Assertion: {'pass' if passed else 'fail'}", ""]
    lines.append("Passed checks:")
    lines.extend(f"- {check}" for check in (checks or ["<none>"]))
    lines.append("")
    lines.append("Failures:")
    lines.extend(f"- {failure}" for failure in (failures or ["<none>"]))
    metadata = {
        "url": url,
        "mode": mode,
        "passed": passed,
        "passed_checks": len(checks),
        "failures": len(failures),
    }
    if passed:
        return ToolResult.success("\n".join(lines), **metadata)
    return ToolResult.failure("\n".join(lines), **metadata)


def _apply_browser_action(page: Any, action: _BrowserAction) -> None:
    if action.type == "click" and action.selector is not None:
        page.click(action.selector, timeout=5_000)
    elif action.type in {"type", "fill"} and action.selector is not None:
        page.fill(action.selector, action.text or "", timeout=5_000)
    elif action.type == "wait":
        page.wait_for_timeout(action.wait_ms)
    else:
        raise ValueError(f"Unsupported browser action: {action.type}")


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


def _coerce_max_results(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 20
    return max(1, min(parsed, 100))


def _coerce_max_entries(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 50
    return max(1, min(parsed, 200))


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
