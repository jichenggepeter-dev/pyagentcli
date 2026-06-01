from __future__ import annotations

from pathlib import Path
from typing import Any

from pyagentcli.rag.indexer import IGNORED_DIRS, IGNORED_SUFFIXES, CodeIndexer
from pyagentcli.tools.base import RiskLevel, ToolContext, ToolResult, function_schema


class SearchTextTool:
    name = "search_text"
    description = "Search UTF-8 text files in the workspace for a literal query."
    risk_level = RiskLevel.READ

    def schema(self) -> dict[str, Any]:
        return function_schema(
            self.name,
            self.description,
            {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Literal text to search for.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Workspace-relative directory or file to search. Defaults to current directory.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of matches to return. Defaults to 20.",
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Whether matching should be case-sensitive. Defaults to false.",
                    },
                },
                "required": ["query"],
            },
        )

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        query = args.get("query")
        if not isinstance(query, str) or not query:
            return ToolResult.failure("Missing required non-empty string argument: query")

        raw_path = str(args.get("path") or ".")
        target = context.safety_policy.resolve_workspace_path(raw_path)
        if not target.exists():
            return ToolResult.failure(f"Path does not exist: {raw_path}")

        max_results = _coerce_max_results(args.get("max_results"))
        case_sensitive = bool(args.get("case_sensitive", False))
        needle = query if case_sensitive else query.lower()

        files = [target] if target.is_file() else _iter_files(target)
        matches: list[str] = []
        scanned_files = 0

        for file_path in files:
            if len(matches) >= max_results:
                break
            scanned_files += 1
            try:
                lines = file_path.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError):
                continue

            for line_number, line in enumerate(lines, start=1):
                haystack = line if case_sensitive else line.lower()
                if needle not in haystack:
                    continue
                relative = file_path.relative_to(context.workspace_root)
                snippet = line.strip()
                if len(snippet) > 240:
                    snippet = snippet[:237] + "..."
                matches.append(f"{relative}:{line_number}: {snippet}")
                if len(matches) >= max_results:
                    break

        if not matches:
            return ToolResult.success(
                f"No matches for {query!r}.",
                query=query,
                path=raw_path,
                scanned_files=scanned_files,
                matches=0,
            )

        return ToolResult.success(
            "\n".join(matches),
            query=query,
            path=raw_path,
            scanned_files=scanned_files,
            matches=len(matches),
        )


class SearchFilesTool:
    name = "search_files"
    description = "Search workspace file paths by filename or relative path."
    risk_level = RiskLevel.READ

    def schema(self) -> dict[str, Any]:
        return function_schema(
            self.name,
            self.description,
            {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Literal text to match against file names or relative paths.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Workspace-relative directory or file to search. Defaults to current directory.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of file paths to return. Defaults to 20.",
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Whether matching should be case-sensitive. Defaults to false.",
                    },
                },
                "required": ["query"],
            },
        )

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        query = args.get("query")
        if not isinstance(query, str) or not query:
            return ToolResult.failure("Missing required non-empty string argument: query")

        raw_path = str(args.get("path") or ".")
        target = context.safety_policy.resolve_workspace_path(raw_path)
        if not target.exists():
            return ToolResult.failure(f"Path does not exist: {raw_path}")

        max_results = _coerce_max_results(args.get("max_results"))
        case_sensitive = bool(args.get("case_sensitive", False))
        needle = query if case_sensitive else query.lower()

        files = [target] if target.is_file() else _iter_files(target)
        matches: list[str] = []
        scanned_files = 0

        for file_path in files:
            if len(matches) >= max_results:
                break
            scanned_files += 1
            relative = file_path.relative_to(context.workspace_root)
            relative_text = str(relative)
            basename = file_path.name
            haystacks = [relative_text, basename] if case_sensitive else [relative_text.lower(), basename.lower()]
            if any(needle in haystack for haystack in haystacks):
                matches.append(relative_text)

        if not matches:
            return ToolResult.success(
                f"No file path matches for {query!r}.",
                query=query,
                path=raw_path,
                scanned_files=scanned_files,
                matches=0,
            )

        return ToolResult.success(
            "\n".join(matches),
            query=query,
            path=raw_path,
            scanned_files=scanned_files,
            matches=len(matches),
        )


class SearchIndexTool:
    name = "search_index"
    description = "Search the local SQLite FTS workspace index. Run pyagent --index first to build it."
    risk_level = RiskLevel.READ

    def schema(self) -> dict[str, Any]:
        return function_schema(
            self.name,
            self.description,
            {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text to search for in the indexed workspace.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of indexed matches to return. Defaults to 20.",
                    },
                },
                "required": ["query"],
            },
        )

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        query = args.get("query")
        if not isinstance(query, str) or not query:
            return ToolResult.failure("Missing required non-empty string argument: query")

        try:
            result = CodeIndexer(context.workspace_root).search(
                query,
                max_results=_coerce_max_results(args.get("max_results")),
            )
        except FileNotFoundError:
            return ToolResult.failure("Index not found. Run `pyagent --index` for this workspace first.")

        return ToolResult.success(
            result.format_text(),
            query=query,
            matches=len(result.hits),
            index=str(result.database_path),
            stale_paths=result.stale_paths,
        )


def _iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in IGNORED_SUFFIXES:
            continue
        yield path


def _coerce_max_results(value: Any) -> int:
    try:
        return max(1, min(int(value), 100))
    except (TypeError, ValueError):
        return 20
