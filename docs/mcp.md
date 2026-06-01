# MCP v0.1

PyAgentCLI includes a minimal Model Context Protocol client layer.

This first slice is intentionally small:

- stdio transport for local MCP servers
- JSON-RPC request/response handling
- `initialize` handshake plus `notifications/initialized`
- `tools/list`
- `tools/call`
- adapter from MCP tool specs into PyAgentCLI `ToolRegistry`
- project-level `pyagent.toml` MCP server config
- automatic MCP tool registration during Agent startup
- risk classification from MCP annotations
- audit and approval reuse through the existing tool execution path

## Risk Classification

MCP tools are not trusted automatically.

PyAgentCLI maps MCP annotations into local risk levels:

| MCP annotation | PyAgentCLI risk |
| --- | --- |
| `readOnlyHint: true` | `READ` |
| `destructiveHint: true` | `CRITICAL` |
| `openWorldHint: true` | `NETWORK` |
| no annotation | `NETWORK` |

In the current policy, `NETWORK` and `CRITICAL` tools are denied by default. This is deliberate: MCP can expose powerful remote capabilities, so v0.1 only allows clearly read-only tools through the normal execution path.

## Programmatic Use

```python
from pathlib import Path

from pyagentcli.mcp import MCPClient, StdioMCPTransport, register_mcp_tools
from pyagentcli.tools.registry import default_registry

transport = StdioMCPTransport(["python", "my_mcp_server.py"], cwd=Path("."))
client = MCPClient(transport)

registry = default_registry()
registered_names = register_mcp_tools(registry, server_name="local", client=client)
```

The registered tool names are prefixed:

```text
mcp_<server_name>_<tool_name>
```

For example, a remote MCP tool named `search_docs` from server `docs` becomes:

```text
mcp_docs_search_docs
```

## Project Config

Add `pyagent.toml` to the workspace root:

```toml
[mcp.servers.docs]
command = ["python", "scripts/docs_mcp_server.py"]
enabled = true
```

When `build_agent()` starts, PyAgentCLI reads this file, starts enabled stdio MCP servers, calls `tools/list`, and registers their tools in the local `ToolRegistry`.

If one MCP server fails to start or list tools, PyAgentCLI skips that server and keeps the built-in local tools available. This keeps one broken extension from disabling the whole coding agent.

## Non-Goals

MCP v0.1 does not yet include:

- HTTP/SSE or streamable HTTP transports
- resources
- prompts
- sampling
- OAuth or credential handling
- advanced long-running server lifecycle management beyond stdio process start/close

These belong in later Phase 2 slices.
