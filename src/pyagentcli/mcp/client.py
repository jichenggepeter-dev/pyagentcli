from __future__ import annotations

import json
import queue
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


DEFAULT_PROTOCOL_VERSION = "2025-11-25"


class MCPError(RuntimeError):
    pass


class MCPTransport(Protocol):
    def start(self) -> None:
        ...

    def write_json(self, payload: dict[str, Any]) -> None:
        ...

    def read_json(self, timeout_seconds: float) -> dict[str, Any]:
        ...

    def close(self) -> None:
        ...


@dataclass(frozen=True)
class MCPToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    annotations: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "MCPToolSpec":
        return cls(
            name=str(payload["name"]),
            description=str(payload.get("description", "")),
            input_schema=dict(payload.get("inputSchema") or {}),
            annotations=dict(payload.get("annotations") or {}),
        )


@dataclass(frozen=True)
class MCPCallResult:
    content: list[dict[str, Any]]
    is_error: bool = False
    structured_content: dict[str, Any] | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "MCPCallResult":
        return cls(
            content=list(payload.get("content") or []),
            is_error=bool(payload.get("isError", False)),
            structured_content=payload.get("structuredContent"),
        )

    def text_content(self) -> str:
        parts: list[str] = []
        for block in self.content:
            if block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            else:
                parts.append(json.dumps(block, ensure_ascii=False, sort_keys=True))
        if self.structured_content is not None:
            parts.append(json.dumps(self.structured_content, ensure_ascii=False, sort_keys=True))
        return "\n".join(part for part in parts if part)


class StdioMCPTransport:
    def __init__(self, command: list[str], *, cwd: Path | None = None) -> None:
        if not command:
            raise ValueError("MCP stdio command cannot be empty.")
        self.command = command
        self.cwd = cwd
        self._process: subprocess.Popen[str] | None = None
        self._messages: queue.Queue[dict[str, Any]] = queue.Queue()
        self._reader_thread: threading.Thread | None = None

    def start(self) -> None:
        if self._process is not None:
            return
        self._process = subprocess.Popen(
            self.command,
            cwd=self.cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        self._reader_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader_thread.start()

    def write_json(self, payload: dict[str, Any]) -> None:
        if self._process is None or self._process.stdin is None:
            raise MCPError("MCP transport is not running.")
        self._process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self._process.stdin.flush()

    def read_json(self, timeout_seconds: float) -> dict[str, Any]:
        try:
            return self._messages.get(timeout=timeout_seconds)
        except queue.Empty as exc:
            raise MCPError(f"Timed out waiting for MCP response after {timeout_seconds:.1f}s.") from exc

    def close(self) -> None:
        if self._process is None:
            return
        self._process.terminate()
        try:
            self._process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            self._process.kill()
        self._process = None

    def _read_stdout(self) -> None:
        if self._process is None or self._process.stdout is None:
            return
        for line in self._process.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                self._messages.put(payload)


class MCPClient:
    def __init__(
        self,
        transport: MCPTransport,
        *,
        client_name: str = "pyagentcli",
        protocol_version: str = DEFAULT_PROTOCOL_VERSION,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.transport = transport
        self.client_name = client_name
        self.protocol_version = protocol_version
        self.timeout_seconds = timeout_seconds
        self._next_id = 1
        self._initialized = False

    def initialize(self) -> dict[str, Any]:
        if self._initialized:
            return {}
        self.transport.start()
        result = self._request(
            "initialize",
            {
                "protocolVersion": self.protocol_version,
                "capabilities": {},
                "clientInfo": {"name": self.client_name, "version": "0.1.0"},
            },
        )
        self.transport.write_json({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self._initialized = True
        return result

    def list_tools(self) -> list[MCPToolSpec]:
        self.initialize()
        result = self._request("tools/list", {})
        return [MCPToolSpec.from_payload(tool) for tool in result.get("tools", [])]

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> MCPCallResult:
        self.initialize()
        result = self._request("tools/call", {"name": name, "arguments": arguments or {}})
        return MCPCallResult.from_payload(result)

    def close(self) -> None:
        self.transport.close()

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        self.transport.write_json(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }
        )
        while True:
            response = self.transport.read_json(self.timeout_seconds)
            if response.get("id") != request_id:
                continue
            if "error" in response:
                error = response["error"]
                message = error.get("message", "Unknown MCP error") if isinstance(error, dict) else str(error)
                raise MCPError(message)
            result = response.get("result", {})
            if not isinstance(result, dict):
                raise MCPError(f"Invalid MCP response for {method}.")
            return result
