# 09 接入 MCP

这一篇对应 PaiCLI 学习路线里的 MCP 扩展思路，但内容全部落到 PyAgentCLI 当前的 Python 实现。

先给结论：

> MCP 扩展的是工具来源，不扩展工具权限。PyAgentCLI 当前实现了最小 stdio MCP client、tools/list、tools/call、MCP tool adapter 和项目级 `pyagent.toml` 配置，但外部 MCP 工具仍然必须经过本地 ToolRegistry、SafetyPolicy、ApprovalHandler 和 AuditLogger。

这句话很重要。

MCP 不是“接上外部工具就能随便调用”。对 Coding Agent 来说，外部工具越灵活，越需要保守的默认安全策略。

## 这一篇学什么

学完这一篇，你要能讲清楚：

- MCP 解决什么问题。
- MCP 和本地 Tool Registry 的关系。
- PyAgentCLI 当前 MCP v0.1 实现了哪些能力。
- stdio transport 如何工作。
- `initialize`、`tools/list`、`tools/call` 的最小链路。
- MCP tool 如何适配成本地 Tool。
- MCP annotation 如何映射成 RiskLevel。
- 为什么没有 `readOnlyHint` 的 MCP tool 默认是 NETWORK。
- 为什么一个坏 MCP server 不能拖垮内置工具。
- 当前 MCP 的边界和后续增强方向。

## MCP 解决什么问题

MCP 是 Model Context Protocol。

它解决的问题是：

> 外部工具、服务和数据源如何用统一协议接入 Agent。

没有 MCP 时，每接一个外部工具都要写一套 glue code：

```text
GitHub adapter
Notion adapter
Docs adapter
Browser adapter
Database adapter
...
```

有 MCP 后，Agent 可以通过统一协议做：

```text
initialize
tools/list
tools/call
```

但在 PyAgentCLI 里，MCP 只是外部工具入口。

真正执行仍然要进入：

```text
MCP tool
  -> MCPToolAdapter
  -> ToolRegistry
  -> SafetyPolicy
  -> ApprovalHandler
  -> AuditLogger
```

一句面试答案：

> MCP 统一了外部工具协议，但不能绕过本地 Agent Runtime 的安全执行层。

## PyAgentCLI 当前实现了什么

当前 MCP v0.1 已实现：

- stdio transport。
- JSON-RPC request / response。
- `initialize` handshake。
- `notifications/initialized`。
- `tools/list`。
- `tools/call`。
- `MCPToolSpec`。
- `MCPCallResult`。
- `MCPToolAdapter`。
- MCP tool name prefix。
- `pyagent.toml` 项目级 MCP server 配置。
- Agent 启动时自动注册 enabled MCP tools。
- MCP annotations 到 RiskLevel 的映射。
- MCP 工具复用现有 approval / audit。
- 一个 MCP server 失败时跳过，不影响内置工具。

当前还没有落地：

- HTTP/SSE transport。
- streamable HTTP。
- MCP resources。
- MCP prompts。
- MCP sampling。
- OAuth。
- credential 管理。
- 长生命周期 server 管理。
- server health check UI。
- per-server permission config。

所以最准确的表达是：

> PyAgentCLI 已实现最小 MCP stdio 工具接入链路，并把 MCP 工具纳入本地工具注册、安全审批和审计体系。

## 最小配置例子

在 workspace 根目录写：

```toml
[mcp.servers.docs]
command = ["python", "scripts/docs_mcp_server.py"]
enabled = true
```

当 `build_agent()` 启动时：

```text
load_config()
  -> load_project_mcp_servers()
  -> default_registry()
  -> register_configured_mcp_tools()
  -> MCPClient(StdioMCPTransport(...))
  -> tools/list
  -> registry.register(MCPToolAdapter)
```

如果 MCP server 提供工具：

```text
search_docs
```

注册到 PyAgentCLI 后名字会变成：

```text
mcp_docs_search_docs
```

命名格式：

```text
mcp_<server_name>_<tool_name>
```

这样可以避免和内置工具重名。

## MCP Client 怎么工作

源码：

```text
src/pyagentcli/mcp/client.py
```

核心类：

```text
StdioMCPTransport
MCPClient
MCPToolSpec
MCPCallResult
```

stdio transport 做什么：

- 启动子进程。
- stdin 写 JSON-RPC。
- stdout 读 JSON-RPC。
- reader thread 把消息放进 queue。
- close 时 terminate / kill。

MCPClient 做什么：

```text
initialize()
  -> transport.start()
  -> request initialize
  -> send notifications/initialized

list_tools()
  -> initialize()
  -> request tools/list
  -> parse MCPToolSpec

call_tool(name, arguments)
  -> initialize()
  -> request tools/call
  -> parse MCPCallResult
```

如果返回 error：

```text
raise MCPError(message)
```

如果超时：

```text
Timed out waiting for MCP response
```

## MCP Tool Adapter 怎么工作

源码：

```text
src/pyagentcli/mcp/adapter.py
```

`MCPToolAdapter` 把远程 MCP tool 变成本地 Tool。

它有：

- `name`
- `description`
- `risk_level`
- `schema()`
- `preview()`
- `run()`

`schema()`：

```text
使用 MCP inputSchema
```

`preview()`：

```text
Call MCP tool `remote_name` from server `server_name`.
```

`run()`：

```text
client.call_tool(remote_name, args)
```

如果 MCP 返回 `isError`：

```text
ToolResult.failure(...)
```

否则：

```text
ToolResult.success(result.text_content())
```

这意味着 MCP 工具一旦进入 registry，就和内置工具走同一条安全执行链路。

## 风险映射

MCP 工具不能自动信任。

PyAgentCLI 当前映射：

| MCP annotation | PyAgentCLI risk |
| --- | --- |
| `readOnlyHint: true` | `READ` |
| `destructiveHint: true` | `CRITICAL` |
| `openWorldHint: true` | `NETWORK` |
| no annotation | `NETWORK` |

当前 policy：

```text
READ -> allow
NETWORK -> deny
CRITICAL -> deny
```

所以：

- 明确 read-only 的 MCP 工具可以走正常 READ path。
- 没有 annotation 的 MCP 工具默认 NETWORK。
- destructive MCP 工具默认 CRITICAL。

这是保守设计。

一句面试答案：

> 外部工具如果没有清楚声明只读，就不能默认当成安全工具。

## MCP 和本地 Tool 的区别

本地 Tool：

- Python 类实现。
- 项目内置。
- schema 可控。
- risk level 可控。
- run 逻辑可审查。

MCP Tool：

- 外部 server 提供。
- 通过 JSON-RPC 调用。
- schema 来自远端。
- metadata 可能不完整。
- server 行为可能不透明。

所以 MCP 工具需要更保守。

PyAgentCLI 的策略是：

```text
MCP 负责扩展工具来源
ToolRegistry 负责统一执行入口
SafetyPolicy 负责权限边界
AuditLogger 负责可追踪性
```

## 自动注册和失败隔离

源码：

```text
register_configured_mcp_tools()
```

逻辑：

```text
for server in servers:
  if not enabled:
    continue
  client = MCPClient(StdioMCPTransport(command))
  try:
    register_mcp_tools(...)
  except:
    client.close()
    record error
```

测试里确认：

> 一个 bad MCP server 不会让内置 `list_files` 等工具消失。

这是工程上很重要的设计。

如果一个外部扩展坏了，不能拖垮整个 Coding Agent。

## MCP Call Result 怎么变成文本

MCP 返回 content blocks：

```json
{
  "content": [
    {"type": "text", "text": "hello"}
  ],
  "isError": false
}
```

PyAgentCLI 会把 text blocks 拼成：

```text
hello
```

如果是非 text block，会转成 JSON 字符串。

如果有 structuredContent，也会追加 JSON。

当前这是一个简单实现。

后续可以增强：

- image content。
- resource references。
- structured result rendering。
- binary artifact handling。

## 和安全篇的关系

第 06 篇讲过：

```text
Tool Call -> SafetyPolicy -> ApprovalHandler -> Tool.run -> AuditLogger
```

MCP 接入后仍然是：

```text
MCPToolAdapter.run()
```

只是 `Tool.run()` 的具体实现变成：

```text
client.call_tool(remote_name, args)
```

安全层不变。

这就是 MCP 的正确接法：

> 接入协议，但不绕过权限。

## 源码阅读路线

建议按这个顺序看：

1. `docs/mcp.md`
   - 先看 MCP v0.1 能力和 non-goals。
2. `src/pyagentcli/mcp/client.py`
   - 看 stdio transport、JSON-RPC、initialize、tools/list、tools/call。
3. `src/pyagentcli/mcp/adapter.py`
   - 看 MCPToolAdapter、risk classification、register_mcp_tools。
4. `src/pyagentcli/config.py`
   - 看 `MCPServerConfig` 和 `load_project_mcp_servers()`。
5. `src/pyagentcli/cli/main.py`
   - 看 `build_agent()` 如何自动注册 configured MCP tools。
6. `tests/test_mcp.py`
   - 看 fake transport、read-only MCP tool、non-read denied、bad server ignored。
7. `tests/test_config.py`
   - 看 `pyagent.toml` server config parsing。

## 我们协作时真实遇到的坑

### 1. MCP 不能写成“工具权限全开”

我们在文档里反复强调：

```text
MCP extends tools, but does not bypass local safety policy.
```

这是因为 MCP 的工具来源更开放。

如果默认允许所有 MCP 工具，风险比内置工具更高。

### 2. readOnlyHint 很关键

MCP tool 如果声明：

```text
readOnlyHint: true
```

PyAgentCLI 才把它当 READ。

没有 annotation 时默认 NETWORK。

这避免了“看起来像查询，实际可能发邮件/写数据库”的情况。

### 3. 一个坏 server 不能拖垮 Agent

测试里专门写了：

```text
missing_server.py
```

Agent 仍然要保留内置工具。

这说明扩展系统要 failure-isolated。

### 4. MCP 命名要避免冲突

远端工具叫：

```text
echo
```

本地注册成：

```text
mcp_docs_echo
```

否则不同 server 之间、或和内置工具之间，很容易重名。

### 5. MCP preview 不能假装已经执行

preview 只说明：

```text
Call MCP tool ...
```

不能在 preview 阶段调用远端工具。

这和 Tool/HITL 的原则一致：预览不能产生副作用。

## 你自己开发时大概率会遇到的坑

### 1. 把 MCP server 当可信代码

MCP server 可能来自第三方。

它的工具 schema、description、annotations 都可能不完整或不可信。

所以默认策略应该保守。

### 2. 不做风险映射

如果 MCP tools 全部注册成 READ，会非常危险。

最低限度要区分：

```text
readOnlyHint -> READ
destructiveHint -> CRITICAL
openWorldHint/no annotation -> NETWORK
```

### 3. server 启动失败导致 Agent 启动失败

外部 server 很容易因为路径、依赖、权限失败。

正确做法：

```text
skip bad server
keep local tools
record error
```

### 4. 不给 MCP tool 加 server prefix

多个 server 都可能有：

```text
search
read
query
echo
```

没有 prefix 会冲突。

### 5. MCP preview 阶段调用远端

preview 应该只是展示即将调用什么。

不能为了生成 preview 去 call remote tool。

### 6. 忘记关闭 stdio process

stdio MCP server 是子进程。

如果失败后不 close，可能留下僵尸进程或资源泄漏。

PyAgentCLI 在注册失败时会 `client.close()`。

### 7. 超时处理缺失

远端 server 可能不响应。

MCPClient 设置 timeout，避免 Agent 永远等待。

### 8. 把 resources/prompts/sampling 说成已实现

当前只实现 tools。

不要把 MCP 完整协议能力写成当前项目事实。

### 9. 不经过 AuditLogger

MCP 工具也必须写 audit log。

否则外部调用不可追踪。

### 10. 直接把 credentials 写进 pyagent.toml

当前 config 只支持 command。

后续如果需要 credentials，也应该通过环境变量或安全 secret store，而不是明文写入项目配置。

## 简历上怎么写

保守可信版：

> 为 PyAgentCLI 实现最小 MCP stdio client，支持 initialize、tools/list、tools/call 和项目级 `pyagent.toml` server 配置，并通过 MCPToolAdapter 将外部工具注册进本地 ToolRegistry，复用风险分级、人工审批和 JSONL 审计。

更技术版：

> 设计 MCP 工具接入层：`StdioMCPTransport` 管理本地 server 子进程与 JSON-RPC 消息，`MCPClient` 完成 handshake 和工具调用，`MCPToolAdapter` 将 MCP `inputSchema` 转换为本地 function schema，并根据 `readOnlyHint / destructiveHint / openWorldHint` 映射 READ / CRITICAL / NETWORK 风险；失败 server 被隔离，避免影响内置工具。

不要这么写：

> 实现完整 MCP 协议、OAuth、resources、prompts 和远程工具生态。

除非后续真的实现这些能力。

## 面试官会怎么追问

### Q1：MCP 解决什么问题？

一句话答案：

> MCP 让外部工具用统一协议接入 Agent。

展开回答：

- 不需要每个工具写完全不同 adapter。
- 通过 initialize、tools/list、tools/call 发现和调用工具。
- PyAgentCLI 把 MCP tool 适配成本地 Tool。

### Q2：MCP 会不会绕过本地安全策略？

一句话答案：

> 不会。MCP tool 注册后仍然走 ToolRegistry、SafetyPolicy、ApprovalHandler 和 AuditLogger。

展开回答：

- MCPToolAdapter 是本地 Tool。
- risk level 来自 annotations 映射。
- NETWORK / CRITICAL 默认拒绝。
- audit log 仍然记录调用。

### Q3：为什么没有 annotation 的 MCP tool 默认 NETWORK？

一句话答案：

> 因为外部工具行为不透明，没有明确只读声明就不能当成 READ。

展开回答：

- 可能发网络请求。
- 可能写远端数据。
- 可能触发外部副作用。
- 保守默认更安全。

### Q4：stdio MCP transport 怎么工作？

一句话答案：

> 启动本地子进程，通过 stdin/stdout 发送 JSON-RPC 消息。

展开回答：

- Popen 启动 command。
- stdin 写 JSON。
- stdout reader thread 读 JSON。
- queue 按 id 等待响应。
- close 终止进程。

### Q5：坏 MCP server 怎么办？

一句话答案：

> 跳过这个 server，保留内置工具。

展开回答：

- 注册时 try/except。
- 失败时 close client。
- 记录 error。
- 不让一个扩展拖垮整个 Agent。

### Q6：MCP 和 Skill 有什么区别？

一句话答案：

> MCP 是可执行工具协议，Skill 是 prompt guidance。

展开回答：

- MCP tool 会执行远端调用。
- Skill 不执行工具。
- MCP 必须走安全策略。
- Skill 不能授予权限。

### Q7：你们现在实现完整 MCP 了吗？

一句话答案：

> 没有。当前是最小 stdio tools slice。

展开回答：

- 已实现 stdio、initialize、tools/list、tools/call。
- 未实现 resources、prompts、sampling、HTTP/SSE、OAuth。
- 当前重点是把工具接入本地安全执行层。

## 标准回答思路

如果面试官让你整体讲 MCP，可以按这个顺序：

1. 先讲 MCP 解决外部工具统一接入。
2. 讲 PyAgentCLI 当前只做 stdio tools slice。
3. 讲 client：initialize、tools/list、tools/call。
4. 讲 adapter：MCP inputSchema -> local function schema。
5. 讲风险映射：readOnlyHint / destructiveHint / openWorldHint。
6. 讲安全：仍走 ToolRegistry、approval、audit。
7. 讲失败隔离：bad server 不影响内置工具。
8. 讲边界：未实现 resources/prompts/OAuth。

一版完整回答：

> PyAgentCLI 里 MCP 的作用是把外部工具用统一协议接进本地 Agent，但它不会绕过本地安全执行层。当前我实现的是最小 stdio tools slice：`StdioMCPTransport` 启动本地 MCP server 子进程，通过 stdin/stdout 发送 JSON-RPC；`MCPClient` 完成 initialize、notifications/initialized、tools/list 和 tools/call；`MCPToolAdapter` 把 MCP tool 的 inputSchema 转成本地 function schema，并注册到 ToolRegistry，名字用 `mcp_<server>_<tool>` 避免冲突。风险上，readOnlyHint 映射 READ，destructiveHint 映射 CRITICAL，openWorldHint 或没有 annotation 都映射 NETWORK；v0.1 里 NETWORK/CRITICAL 默认拒绝。这样 MCP 扩展了工具来源，但执行仍经过 SafetyPolicy、ApprovalHandler 和 AuditLogger。当前还没做 resources、prompts、sampling、HTTP/SSE 和 OAuth。

## 还能继续怎么增强

下一阶段可以增强：

- HTTP/SSE transport。
- streamable HTTP。
- MCP resources。
- MCP prompts。
- OAuth。
- credential handling。
- per-server permission config。
- server health check。
- MCP tool allowlist。
- MCP audit summary。
- long-running server lifecycle。
- MCP eval fixtures。

更工程化的方向：

- MCP server stderr capture。
- MCP registration diagnostics command。
- per-tool risk override。
- tool annotation validation。
- structured content renderer。
- resource reference handling。

## 这一篇之后做什么

下一篇进入：

> Prompt 分层和 Skill System

MCP 扩展的是可执行工具来源；Skill 扩展的是可复用 prompt guidance。两者必须分清：Tool 能执行，Skill 不能绕过权限。
