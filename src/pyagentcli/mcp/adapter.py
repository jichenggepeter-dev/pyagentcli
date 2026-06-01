from __future__ import annotations

import re
from typing import Any

from pyagentcli.mcp.client import MCPClient, MCPToolSpec
from pyagentcli.tools.base import RiskLevel, ToolContext, ToolResult, function_schema
from pyagentcli.tools.registry import ToolRegistry


class MCPToolAdapter:
    def __init__(self, *, server_name: str, spec: MCPToolSpec, client: MCPClient) -> None:
        self.server_name = _safe_name(server_name)
        self.remote_name = spec.name
        self.name = f"mcp_{self.server_name}_{_safe_name(spec.name)}"
        self.description = spec.description or f"MCP tool {spec.name} from server {server_name}."
        self.risk_level = _classify_risk(spec)
        self._input_schema = spec.input_schema or {"type": "object", "properties": {}}
        self._client = client

    def schema(self) -> dict[str, Any]:
        return function_schema(self.name, self.description, self._input_schema)

    def preview(self, args: dict[str, Any], context: ToolContext) -> str | None:
        return f"Call MCP tool `{self.remote_name}` from server `{self.server_name}`."

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        result = self._client.call_tool(self.remote_name, args)
        if result.is_error:
            return ToolResult.failure(result.text_content() or "MCP tool returned an error.", mcp_tool=self.remote_name)
        return ToolResult.success(result.text_content(), mcp_tool=self.remote_name, mcp_server=self.server_name)


def register_mcp_tools(registry: ToolRegistry, *, server_name: str, client: MCPClient) -> list[str]:
    names: list[str] = []
    for spec in client.list_tools():
        adapter = MCPToolAdapter(server_name=server_name, spec=spec, client=client)
        registry.register(adapter)
        names.append(adapter.name)
    return names


def _classify_risk(spec: MCPToolSpec) -> RiskLevel:
    if spec.annotations.get("destructiveHint") is True:
        return RiskLevel.CRITICAL
    if spec.annotations.get("readOnlyHint") is True:
        return RiskLevel.READ
    if spec.annotations.get("openWorldHint") is True:
        return RiskLevel.NETWORK
    return RiskLevel.NETWORK


def _safe_name(raw: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", raw).strip("_").lower()
    return cleaned or "tool"
