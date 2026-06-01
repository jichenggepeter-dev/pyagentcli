from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from pyagentcli.mcp.adapter import MCPToolAdapter, register_mcp_tools
from pyagentcli.cli.main import build_agent
from pyagentcli.mcp.client import MCPClient, MCPToolSpec
from pyagentcli.safety.approval import ApprovalResult
from pyagentcli.safety.audit_log import AuditLogger
from pyagentcli.safety.policy import SafetyDecision, SafetyPolicy
from pyagentcli.tools.base import RiskLevel, ToolContext
from pyagentcli.tools.registry import ToolRegistry


class FakeTransport:
    def __init__(self) -> None:
        self.started = False
        self.writes: list[dict[str, Any]] = []
        self.responses: list[dict[str, Any]] = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "fake", "version": "1.0.0"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {
                    "tools": [
                        {
                            "name": "echo",
                            "description": "Echo text.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"text": {"type": "string"}},
                                "required": ["text"],
                            },
                            "annotations": {"readOnlyHint": True},
                        }
                    ]
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 3,
                "result": {"content": [{"type": "text", "text": "hello"}], "isError": False},
            },
        ]

    def start(self) -> None:
        self.started = True

    def write_json(self, payload: dict[str, Any]) -> None:
        self.writes.append(payload)

    def read_json(self, timeout_seconds: float) -> dict[str, Any]:
        return self.responses.pop(0)

    def close(self) -> None:
        self.started = False


class ApproveAll:
    def request(
        self,
        *,
        tool_name: str,
        risk_level: RiskLevel,
        args: dict,
        decision: SafetyDecision,
        preview: str | None = None,
    ) -> ApprovalResult:
        return ApprovalResult(True, "approved in test")


class DenyAll:
    def request(
        self,
        *,
        tool_name: str,
        risk_level: RiskLevel,
        args: dict,
        decision: SafetyDecision,
        preview: str | None = None,
    ) -> ApprovalResult:
        return ApprovalResult(False, "denied in test")


def make_context(tmp_path: Path, approval) -> ToolContext:
    return ToolContext(
        workspace_root=tmp_path,
        safety_policy=SafetyPolicy(tmp_path),
        approval_handler=approval,
        audit_logger=AuditLogger(tmp_path),
        goal="mcp test",
        step=1,
    )


def test_mcp_client_initializes_lists_and_calls_tools() -> None:
    transport = FakeTransport()
    client = MCPClient(transport)

    tools = client.list_tools()
    result = client.call_tool("echo", {"text": "hello"})

    assert transport.started is True
    assert tools[0].name == "echo"
    assert tools[0].annotations["readOnlyHint"] is True
    assert result.text_content() == "hello"
    assert transport.writes[0]["method"] == "initialize"
    assert transport.writes[1]["method"] == "notifications/initialized"
    assert transport.writes[2]["method"] == "tools/list"
    assert transport.writes[3]["method"] == "tools/call"


def test_mcp_read_only_tool_registers_and_executes_through_registry(tmp_path: Path) -> None:
    client = MCPClient(FakeTransport())
    registry = ToolRegistry()

    names = register_mcp_tools(registry, server_name="Fake Server", client=client)
    result = registry.execute(names[0], {"text": "hello"}, make_context(tmp_path, ApproveAll()))

    assert names == ["mcp_fake_server_echo"]
    assert result.ok
    assert result.content == "hello"
    assert result.metadata["mcp_tool"] == "echo"


def test_mcp_non_read_tool_is_denied_by_default_policy(tmp_path: Path) -> None:
    spec = MCPToolSpec(
        name="send_email",
        description="Send email.",
        input_schema={"type": "object", "properties": {}},
        annotations={},
    )
    adapter = MCPToolAdapter(server_name="mail", spec=spec, client=MCPClient(FakeTransport()))
    registry = ToolRegistry()
    registry.register(adapter)

    result = registry.execute("mcp_mail_send_email", {}, make_context(tmp_path, ApproveAll()))

    assert adapter.risk_level == RiskLevel.NETWORK
    assert not result.ok
    assert "disabled" in (result.error or "")


def test_build_agent_registers_configured_mcp_tools(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    server = tmp_path / "fake_mcp_server.py"
    server.write_text(
        """
import json
import sys

for line in sys.stdin:
    request = json.loads(line)
    method = request.get("method")
    if method == "notifications/initialized":
        continue
    if method == "initialize":
        result = {
            "protocolVersion": "2025-11-25",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "fake", "version": "1.0.0"},
        }
    elif method == "tools/list":
        result = {
            "tools": [
                {
                    "name": "echo",
                    "description": "Echo text.",
                    "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}},
                    "annotations": {"readOnlyHint": True},
                }
            ]
        }
    else:
        result = {"content": [{"type": "text", "text": "ok"}], "isError": False}
    print(json.dumps({"jsonrpc": "2.0", "id": request.get("id"), "result": result}), flush=True)
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "pyagent.toml").write_text(
        f"""
[mcp.servers.docs]
command = [{sys.executable!r}, "fake_mcp_server.py"]
enabled = true
""".strip(),
        encoding="utf-8",
    )

    agent = build_agent(workspace=str(tmp_path), interactive=False)
    tool_names = [schema["function"]["name"] for schema in agent.tools.schemas()]

    assert "mcp_docs_echo" in tool_names


def test_build_agent_ignores_failed_mcp_server(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    (tmp_path / "pyagent.toml").write_text(
        """
[mcp.servers.bad]
command = ["python", "missing_server.py"]
enabled = true
""".strip(),
        encoding="utf-8",
    )

    agent = build_agent(workspace=str(tmp_path), interactive=False)
    tool_names = [schema["function"]["name"] for schema in agent.tools.schemas()]

    assert "list_files" in tool_names
    assert all(not name.startswith("mcp_bad_") for name in tool_names)
