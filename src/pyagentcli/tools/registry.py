from __future__ import annotations

from time import perf_counter
from typing import Any

from pyagentcli.safety.policy import SafetyAction
from pyagentcli.tools.base import Tool, ToolContext, ToolResult


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.schema() for tool in self._tools.values()]

    def execute(self, name: str, args: dict[str, Any], context: ToolContext) -> ToolResult:
        started_at = perf_counter()
        try:
            tool = self.get(name)
        except KeyError as exc:
            return ToolResult.failure(str(exc), unknown_tool=name)
        decision = context.safety_policy.evaluate_tool(tool.name, tool.risk_level, args)
        try:
            preview = _tool_preview(tool, args, context)
        except Exception as exc:  # noqa: BLE001 - preview failures should become observations.
            result = ToolResult.failure(str(exc), exception_type=type(exc).__name__)
            context.audit_logger.record(
                goal=context.goal,
                step=context.step,
                tool_name=tool.name,
                tool_args=args,
                risk_level=tool.risk_level,
                decision="preview failed",
                result=result,
                started_at=started_at,
            )
            return result

        approval = context.approval_handler.request(
            tool_name=tool.name,
            risk_level=tool.risk_level,
            args=args,
            decision=decision,
            preview=preview,
        )

        if not approval.approved:
            result = ToolResult.failure(approval.reason, approval="denied")
        elif decision.action == SafetyAction.DENY:
            result = ToolResult.failure(decision.reason, approval="denied")
        else:
            try:
                result = tool.run(args, context)
            except Exception as exc:  # noqa: BLE001 - tool failures should become observations.
                result = ToolResult.failure(str(exc), exception_type=type(exc).__name__)

        context.audit_logger.record(
            goal=context.goal,
            step=context.step,
            tool_name=tool.name,
            tool_args=args,
            risk_level=tool.risk_level,
            decision=approval.reason,
            result=result,
            started_at=started_at,
        )
        return result


def _tool_preview(tool: Tool, args: dict[str, Any], context: ToolContext) -> str | None:
    preview = getattr(tool, "preview", None)
    if not callable(preview):
        return None
    return preview(args, context)


def default_registry() -> ToolRegistry:
    from pyagentcli.tools.browser import (
        BrowserConsoleLogsTool,
        BrowserDomSnapshotTool,
        BrowserInteractTool,
        BrowserQuerySelectorTool,
        BrowserScreenshotTool,
        InspectPageTool,
    )
    from pyagentcli.tools.filesystem import EditFileTool, ListFilesTool, ReadFileTool, WriteFileTool
    from pyagentcli.tools.search import SearchDependenciesTool, SearchFilesTool, SearchIndexTool, SearchTextTool
    from pyagentcli.tools.shell import RunShellTool

    registry = ToolRegistry()
    registry.register(ListFilesTool())
    registry.register(ReadFileTool())
    registry.register(SearchFilesTool())
    registry.register(SearchTextTool())
    registry.register(SearchIndexTool())
    registry.register(SearchDependenciesTool())
    registry.register(InspectPageTool())
    registry.register(BrowserDomSnapshotTool())
    registry.register(BrowserQuerySelectorTool())
    registry.register(BrowserConsoleLogsTool())
    registry.register(BrowserScreenshotTool())
    registry.register(BrowserInteractTool())
    registry.register(WriteFileTool())
    registry.register(EditFileTool())
    registry.register(RunShellTool())
    return registry
