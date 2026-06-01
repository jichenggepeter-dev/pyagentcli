from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

from pyagentcli.tools.base import RiskLevel, ToolContext, ToolResult, function_schema


class ListFilesTool:
    name = "list_files"
    description = "List files and directories under a workspace-relative directory."
    risk_level = RiskLevel.READ

    def schema(self) -> dict[str, Any]:
        return function_schema(
            self.name,
            self.description,
            {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Workspace-relative directory path. Defaults to current directory.",
                    }
                },
            },
        )

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        raw_path = str(args.get("path") or ".")
        target = context.safety_policy.resolve_workspace_path(raw_path)
        if not target.exists():
            return ToolResult.failure(f"Directory does not exist: {raw_path}")
        if not target.is_dir():
            return ToolResult.failure(f"Path is not a directory: {raw_path}")

        entries = []
        for child in sorted(target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
            if child.name in {".git", ".pyagent", ".pytest_cache", "__pycache__", ".venv", "node_modules"}:
                continue
            suffix = "/" if child.is_dir() else ""
            relative = child.relative_to(context.workspace_root)
            entries.append(f"{relative}{suffix}")
        return ToolResult.success("\n".join(entries) or "<empty directory>", path=raw_path)


class ReadFileTool:
    name = "read_file"
    description = "Read a UTF-8 text file from the workspace."
    risk_level = RiskLevel.READ

    def schema(self) -> dict[str, Any]:
        return function_schema(
            self.name,
            self.description,
            {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Workspace-relative file path to read.",
                    }
                },
                "required": ["path"],
            },
        )

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        raw_path = str(args.get("path") or "")
        if not raw_path:
            return ToolResult.failure("Missing required argument: path")
        target = context.safety_policy.resolve_workspace_path(raw_path)
        if not target.exists():
            return ToolResult.failure(f"File does not exist: {raw_path}")
        if not target.is_file():
            return ToolResult.failure(f"Path is not a file: {raw_path}")
        try:
            content = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return ToolResult.failure(f"File is not valid UTF-8 text: {raw_path}")
        return ToolResult.success(content, path=raw_path, bytes=len(content.encode("utf-8")))


class WriteFileTool:
    name = "write_file"
    description = "Write full UTF-8 content to a workspace-relative file."
    risk_level = RiskLevel.WRITE

    def schema(self) -> dict[str, Any]:
        return function_schema(
            self.name,
            self.description,
            {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Workspace-relative file path to write.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full file content to write.",
                    },
                },
                "required": ["path", "content"],
            },
        )

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        raw_path = str(args.get("path") or "")
        content = args.get("content")
        if not raw_path:
            return ToolResult.failure("Missing required argument: path")
        if not isinstance(content, str):
            return ToolResult.failure("Missing required string argument: content")

        target = context.safety_policy.resolve_workspace_path(raw_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return ToolResult.success(
            f"Wrote {len(content.encode('utf-8'))} bytes to {raw_path}",
            path=raw_path,
            bytes=len(content.encode("utf-8")),
        )

    def preview(self, args: dict[str, Any], context: ToolContext) -> str | None:
        raw_path = str(args.get("path") or "")
        content = args.get("content")
        if not raw_path or not isinstance(content, str):
            return None

        target = context.safety_policy.resolve_workspace_path(raw_path)
        if target.exists() and target.is_file():
            try:
                old_content = target.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                old_content = ""
        else:
            old_content = ""

        old_lines = old_content.splitlines(keepends=True)
        new_lines = content.splitlines(keepends=True)
        if old_lines == new_lines:
            return f"No content changes for {raw_path}."

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{raw_path}",
            tofile=f"b/{raw_path}",
            lineterm="",
        )
        preview = "\n".join(diff)
        if len(preview) > 4000:
            return preview[:4000] + "\n... <diff truncated>"
        return preview


class EditFileTool:
    name = "edit_file"
    description = "Replace one unique text span in an existing UTF-8 file."
    risk_level = RiskLevel.WRITE

    def schema(self) -> dict[str, Any]:
        return function_schema(
            self.name,
            self.description,
            {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Workspace-relative file path to edit.",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "Exact text to replace. It must appear exactly once.",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "Replacement text.",
                    },
                },
                "required": ["path", "old_text", "new_text"],
            },
        )

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        prepared = self._prepare_edit(args, context)
        if isinstance(prepared, ToolResult):
            return prepared

        raw_path, target, old_content, new_content, old_text = prepared
        target.write_text(new_content, encoding="utf-8")
        return ToolResult.success(
            f"Edited {raw_path}; replaced {len(old_text)} characters.",
            path=raw_path,
            bytes=len(new_content.encode("utf-8")),
        )

    def preview(self, args: dict[str, Any], context: ToolContext) -> str | None:
        prepared = self._prepare_edit(args, context)
        if isinstance(prepared, ToolResult):
            raise ValueError(prepared.error or "Invalid edit_file arguments.")

        raw_path, _target, old_content, new_content, _old_text = prepared
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{raw_path}",
            tofile=f"b/{raw_path}",
            lineterm="",
        )
        preview = "\n".join(diff)
        if len(preview) > 4000:
            return preview[:4000] + "\n... <diff truncated>"
        return preview

    def _prepare_edit(
        self,
        args: dict[str, Any],
        context: ToolContext,
    ) -> tuple[str, Path, str, str, str] | ToolResult:
        raw_path = str(args.get("path") or "")
        old_text = args.get("old_text")
        new_text = args.get("new_text")
        if not raw_path:
            return ToolResult.failure("Missing required argument: path")
        if not isinstance(old_text, str) or old_text == "":
            return ToolResult.failure("Missing required non-empty string argument: old_text")
        if not isinstance(new_text, str):
            return ToolResult.failure("Missing required string argument: new_text")

        target = context.safety_policy.resolve_workspace_path(raw_path)
        if not target.exists():
            return ToolResult.failure(f"File does not exist: {raw_path}")
        if not target.is_file():
            return ToolResult.failure(f"Path is not a file: {raw_path}")

        try:
            old_content = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return ToolResult.failure(f"File is not valid UTF-8 text: {raw_path}")

        match_count = old_content.count(old_text)
        if match_count == 0:
            return ToolResult.failure("old_text was not found in the target file.")
        if match_count > 1:
            return ToolResult.failure(
                f"old_text matched {match_count} times. Refusing ambiguous edit."
            )

        new_content = old_content.replace(old_text, new_text, 1)
        return raw_path, target, old_content, new_content, old_text


def ensure_text_path(path: Path) -> Path:
    return path
