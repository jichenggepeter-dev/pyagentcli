# PyAgentCLI v0.1 实现蓝图

## 1. v0.1 的最小工程形态

v0.1 只做一件事：跑通本地 AI Coding Agent 的最小闭环。

```text
pyagent "帮我总结这个项目"
  -> CLI 接收任务
  -> Agent Loop 构造 messages + tools
  -> LLM 返回文本或 tool_calls
  -> Tool Registry 执行工具
  -> Safety/Approval 拦截高风险动作
  -> Audit Log 记录
  -> 工具结果回填给 LLM
  -> 输出最终回答
```

这条链路对应 PaiCLI 第一期的主干：CLI、Agent、LLM Client、Tool Registry。但 PyAgentCLI 从 v0.1 开始就加上 Safety 和 Audit。

## 2. 推荐 Python 包结构

```text
src/pyagentcli/
  __init__.py
  cli/
    __init__.py
    main.py
    repl.py
  agent/
    __init__.py
    loop.py
    state.py
    prompts.py
  llm/
    __init__.py
    base.py
    openai_compatible.py
    model_config.py
  tools/
    __init__.py
    base.py
    registry.py
    filesystem.py
    shell.py
  safety/
    __init__.py
    policy.py
    approval.py
    audit_log.py
  config.py
```

v0.1 暂时不创建空的 RAG、Memory、MCP、Skills 目录，避免“架子很大但不可运行”。README 里说明后续路线即可。

## 3. 核心数据结构

### Message

```python
class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
```

用途：统一 LLM 对话历史，支持普通回复和工具调用。

### ToolCall

```python
class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]
```

用途：把不同模型返回的工具调用格式统一成内部格式。

### ToolResult

```python
class ToolResult(BaseModel):
    ok: bool
    content: str
    error: str | None = None
    metadata: dict[str, Any] = {}
```

用途：所有工具都返回同一种结果，方便 Agent Loop 回填。

### ToolContext

```python
class ToolContext(BaseModel):
    workspace_root: Path
    audit_logger: AuditLogger
    approval_handler: ApprovalHandler
    safety_policy: SafetyPolicy
```

用途：工具执行时拿到 workspace、安全策略、审批器和日志。

### AgentState

```python
class AgentState(BaseModel):
    user_goal: str
    messages: list[Message]
    step_count: int = 0
    max_steps: int = 10
    workspace_root: Path
```

用途：控制循环步数和上下文。

## 4. Tool 接口

```python
class Tool(Protocol):
    name: str
    description: str
    risk_level: RiskLevel

    def schema(self) -> dict[str, Any]:
        ...

    def run(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        ...
```

v0.1 推荐工具：

| 工具 | 风险 | 是否审批 | 说明 |
| --- | --- | --- | --- |
| `list_files` | READ | 否 | 列出目录 |
| `read_file` | READ | 否 | 读取文本文件 |
| `write_file` | WRITE | 是 | 写入文件 |
| `run_shell` | EXECUTE | 是 | 执行命令 |

## 5. 工具 Schema 设计

### list_files

```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Workspace-relative directory path. Defaults to current directory."
    }
  }
}
```

### read_file

```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Workspace-relative file path to read."
    }
  },
  "required": ["path"]
}
```

### write_file

```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Workspace-relative file path to write."
    },
    "content": {
      "type": "string",
      "description": "Full file content to write."
    }
  },
  "required": ["path", "content"]
}
```

### run_shell

```json
{
  "type": "object",
  "properties": {
    "command": {
      "type": "string",
      "description": "Shell command to run in the workspace."
    },
    "timeout_seconds": {
      "type": "integer",
      "description": "Command timeout in seconds. Defaults to 30."
    }
  },
  "required": ["command"]
}
```

## 6. Agent Loop 伪代码

```python
def run(goal: str) -> str:
    state = AgentState(
        user_goal=goal,
        messages=[
            Message.system(SYSTEM_PROMPT),
            Message.user(goal),
        ],
        workspace_root=config.workspace_root,
    )

    while state.step_count < state.max_steps:
        state.step_count += 1
        response = llm.chat(
            messages=state.messages,
            tools=tool_registry.schemas(),
        )

        state.messages.append(response.assistant_message)

        if not response.tool_calls:
            return response.content

        for call in response.tool_calls:
            tool = tool_registry.get(call.name)
            result = tool_registry.execute(call, tool_context)
            state.messages.append(
                Message.tool(
                    tool_call_id=call.id,
                    content=result.content if result.ok else result.error,
                )
            )

    return "任务达到最大步数，已停止。"
```

v0.1 先串行执行 tool calls。后续再支持只读工具并行。

## 7. Safety 策略

### 路径解析

```text
用户传入 path
  -> workspace_root / path
  -> resolve()
  -> 检查是否仍在 workspace_root 内
  -> 检查是否命中 denylist
```

默认 denylist：

- `.git`
- `.pyagent/audit.log.jsonl` 直接覆盖
- `.env`
- `node_modules`
- `.venv`
- 系统绝对路径

说明：v0.1 可以允许读取 `.env.example`，但默认拒绝读取 `.env`。

### 命令策略

默认拒绝：

- `rm -rf`
- `sudo`
- `chmod -R`
- `chown -R`
- `mkfs`
- `dd if=`
- `:(){`
- `curl ... | sh`
- `wget ... | sh`

默认审批：

- 所有 `run_shell`
- 所有 `write_file`

默认允许：

- `list_files`
- `read_file`

## 8. Approval 交互

审批提示用 Rich 展示：

```text
Tool approval required

Tool: run_shell
Risk: EXECUTE
Command: pytest
Workspace: /path/to/project

Approve? [y/N]
```

用户拒绝后，工具返回：

```json
{
  "ok": false,
  "error": "User denied approval for run_shell.",
  "metadata": {"approval": "denied"}
}
```

这个结果要回填给模型，让 Agent 可以解释或改用低风险方案。

## 9. Audit Log

文件位置：

```text
.pyagent/audit.log.jsonl
```

单条记录：

```json
{
  "timestamp": "2026-05-31T16:00:00Z",
  "goal": "fix failing tests",
  "step": 3,
  "tool_name": "run_shell",
  "tool_args": {"command": "pytest"},
  "risk_level": "EXECUTE",
  "decision": "approved",
  "ok": true,
  "error": null,
  "duration_ms": 1234
}
```

审计日志要避免保存敏感完整内容。`write_file` 的 `content` 可以只记录长度、hash、目标路径。

## 10. System Prompt v0.1

```text
You are PyAgentCLI, a local AI coding agent running inside the user's workspace.

You can inspect and modify files only through tools.
Use tools when you need real workspace information.
Do not guess file contents.
Prefer small, reversible changes.
Explain failures clearly.

Available tools:
- list_files: list workspace files
- read_file: read a text file
- write_file: write a full file
- run_shell: run a shell command in the workspace

Safety rules:
- Never request destructive commands unless the user explicitly asks.
- Ask for tool use through tool calls only.
- If a tool fails, use the error message to choose the next step.
- Stop when the task is complete.
```

实际实现时，工具列表由 schema 注入，prompt 只保留行为规则。

## 11. v0.1 Demo Case

### Demo 1：总结项目

用户：

```text
帮我看看这个项目是做什么的
```

期望：

- Agent 调用 `list_files`
- Agent 读取 README 或 pyproject
- Agent 输出项目摘要

### Demo 2：写文件

用户：

```text
帮我创建 notes/hello.md，内容是 hello pyagent
```

期望：

- Agent 调用 `write_file`
- CLI 出现审批
- 用户同意后写入
- Audit log 记录

### Demo 3：运行测试

用户：

```text
帮我运行测试
```

期望：

- Agent 先检查项目文件
- Agent 推断测试命令
- 调用 `run_shell`
- CLI 出现审批
- 输出测试结果摘要

## 12. v0.1 完成后立刻能讲的项目亮点

- 我没有直接用 LangChain，而是手写 Agent Loop，能解释每一步模型、工具、观察结果如何流转。
- 工具不是硬编码散落在 Agent 里，而是通过 Tool Registry 统一注册和暴露 schema。
- 文件和命令工具从第一版就接入路径围栏、风险分级、人工审批和审计日志。
- 工具失败不会让程序崩溃，而是作为 observation 回填给模型，让 Agent 尝试恢复。
- 后续可以自然扩展到 Plan、RAG、Memory、MCP 和 Multi-Agent。

