from __future__ import annotations

import re
import urllib.error
import urllib.parse
import urllib.request
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from pyagentcli.tools.base import RiskLevel, ToolContext, ToolResult, function_schema


LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


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


class _HTMLSnapshot:
    def __init__(self, title: str, text: str) -> None:
        self.title = title
        self.text = text


class _SnapshotParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self._in_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = True
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
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
    return _HTMLSnapshot(title=title, text=text)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _coerce_max_chars(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 2000
    return max(200, min(parsed, 20_000))
