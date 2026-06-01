# PyAgentCLI 技术架构设计

## 1. 总体架构

PyAgentCLI 采用分层架构：

```text
CLI / REPL
  -> Agent Loop
    -> LLM Client
    -> Tool Registry
      -> Filesystem Tools
      -> Shell Tools
      -> Search Tools
      -> Browser Tools
      -> MCP Tools
    -> Safety Policy
    -> Memory
    -> RAG Retriever
    -> Audit Log
```

核心思想：Agent Loop 负责“思考与调度”，工具层负责“真实世界动作”，Safety 层负责“是否允许动作”，Memory 与 RAG 负责“让模型拿到正确上下文”。

这个架构参考了 PaiCLI 从最小 ReAct Agent 逐步演进到 Plan、Memory、RAG、Multi-Agent、HITL、MCP 的路线，但实现上采用 Python 生态，并把安全审批和审计提前到 v0.1。

## 2. 建议目录结构

```text
pyagentcli/
  pyproject.toml
  README.md
  .env.example
  src/pyagentcli/
    cli/
      main.py
      repl.py
    agent/
      loop.py
      state.py
      planner.py
      reviewer.py
      prompts.py
    llm/
      base.py
      openai_compatible.py
      model_config.py
    tools/
      base.py
      registry.py
      filesystem.py
      shell.py
      search.py
      browser.py
    memory/
      short_term.py
      long_term.py
      compressor.py
    rag/
      indexer.py
      chunker.py
      embeddings.py
      store.py
      retriever.py
    safety/
      policy.py
      approval.py
      audit_log.py
    mcp/
      client.py
      adapter.py
    skills/
      loader.py
      builtin/
    evals/
      cases.py
      runner.py
      metrics.py
```

## 3. 核心模块

### CLI

职责：

- 解析命令行参数
- 初始化 workspace、配置、模型、工具
- 提供 REPL 和单次任务模式

推荐技术：

- `typer`：命令行框架
- `rich`：终端输出、表格、审批提示
- `python-dotenv`：读取 `.env`

### Agent Loop

职责：

- 维护任务状态
- 构造 prompt / messages
- 调用模型
- 解析 tool calls
- 执行工具
- 将工具结果写回上下文
- 控制最大步数与错误恢复

v0.1 采用纯 ReAct / Tool Calling 循环；v0.2 之后增加 Plan Preview；v0.4 之后再把计划结构升级为 DAG。

建议状态字段：

```python
AgentState:
  user_goal: str
  messages: list[Message]
  tool_results: list[ToolResult]
  step_count: int
  workspace_root: Path
  plan: list[str]
  memory_context: str
  retrieved_context: str
```

### LLM Client

职责：

- 封装 OpenAI-compatible Chat Completions 或 Responses API
- 提供统一接口，不把模型厂商逻辑散落在 Agent Loop
- 支持 function/tool schema

核心接口：

```python
class LLMClient:
    def chat(self, messages, tools=None, tool_choice="auto") -> LLMResponse:
        ...
```

### Tool Registry

职责：

- 注册工具
- 暴露工具 schema 给模型
- 按工具名执行对应函数
- 统一返回结构化结果

工具注册表是 PyAgentCLI 的核心扩展点。所有本地工具、MCP 工具、浏览器工具最终都应转换成同一种 `Tool` 接口，统一走 Safety、Approval 和 Audit。

工具接口：

```python
class Tool:
    name: str
    description: str
    risk_level: RiskLevel

    def schema(self) -> dict:
        ...

    def run(self, args: dict, context: ToolContext) -> ToolResult:
        ...
```

### Safety

职责：

- 工具执行前判断风险
- 检查路径是否在 workspace 内
- 检查命令是否命中黑名单
- 根据策略决定 allow / ask / deny
- 写入审计日志

风险等级：

```text
LOW: 只读，例如 list_files/read_file
MEDIUM: 写文件，例如 write_file
HIGH: 执行命令，例如 run_shell
CRITICAL: 删除、权限、网络、系统级操作
```

### RAG

职责：

- 扫描项目代码
- 建立 chunk
- 存储索引
- 检索与当前任务相关的代码上下文
- 支持显式引用：`@file`、`@folder`、`@symbol`

MVP 可以先实现文本搜索，v0.3 再接 embedding。

### Memory

职责：

- 记录当前任务状态
- 保存项目约定
- 保存用户偏好
- 对长对话进行压缩

推荐分层：

```text
Session Memory: 当前对话临时状态
Project Memory: .pyagent/memory.md
User Memory: 用户全局配置目录
```

### Multi-Agent

职责：

- Planner 负责拆解
- Executor 负责执行
- Reviewer 负责检查

早期不需要真的并发，可以先实现顺序工作流：

```text
User Goal -> Planner -> Executor -> Reviewer -> Final Answer
```

推荐采用权限隔离：Planner 只产出计划，Reviewer 只审查结果，只有 Executor / Worker 可以调用真实工具；但 Executor 的工具调用仍必须经过 Safety Policy。

### MCP

职责：

- 连接外部 MCP server
- 将 MCP tools 转换为 PyAgentCLI Tool
- 复用同一套 Safety 与 Audit 机制

## 4. Agent Loop 流程

```text
1. 用户输入任务
2. CLI 初始化 AgentState
3. RAG 注入相关上下文
4. Memory 注入项目偏好
5. Agent 调用 LLM
6. 如果模型返回普通文本，输出给用户
7. 如果模型返回 tool call：
   1. Tool Registry 找到工具
   2. Safety Policy 评估风险
   3. 如需审批，向用户确认
   4. 执行工具
   5. Audit Log 记录
   6. Tool Result 加回 messages
8. 重复直到完成、失败、超步数或用户中断
```

### ReAct 与 Plan 模式切换

默认使用 ReAct，因为它实现简单、反馈即时，适合大多数短任务。

当用户输入包含明显多步骤线索时，切到 Plan Preview：

- 先、然后、接着、最后
- 同时修改多个文件
- 创建完整项目
- 修复一组测试
- 分阶段完成

Plan Preview 先不执行，只把计划展示给用户或传给 Executor。后续版本再把计划持久化为 DAG。

## 5. 安全设计

### 路径围栏

- 默认只能读写 workspace 内文件
- 禁止写入 `.git`、系统目录、用户 home 根目录等敏感路径
- 支持配置 allowlist

### 命令策略

默认阻止或审批：

- `rm -rf`
- `sudo`
- `chmod -R`
- `chown -R`
- 磁盘格式化相关命令
- fork bomb 类命令
- 未经确认的网络下载执行

### 审批体验

审批提示应展示：

- 工具名
- 参数
- 风险等级
- 为什么需要审批
- 将要影响的路径或命令

## 6. 数据与配置

### 项目本地目录

```text
.pyagent/
  config.toml
  memory.md
  audit.log.jsonl
  index.sqlite
```

### 环境变量

```text
OPENAI_API_KEY=
OPENAI_BASE_URL=
PYAGENT_MODEL=
PYAGENT_WORKSPACE=
```

## 7. 可测试性

### 单元测试

- Tool schema 是否正确
- 路径围栏是否阻止越界路径
- 命令黑名单是否命中
- Tool Registry 是否能注册和执行工具

### 集成测试

- Agent 读取文件并回答
- Agent 写入文件前触发审批
- Agent 执行命令并记录日志
- 工具失败后 Agent 能继续下一步

### Eval

每个 eval case 包括：

- 初始文件树
- 用户任务
- 期望文件变化
- 期望命令调用
- 成功判定函数

## 8. 技术取舍

| 问题 | 方案 | 原因 |
| --- | --- | --- |
| CLI 框架 | Typer | 简洁、类型友好、适合 Python CLI |
| 终端展示 | Rich | 审批、日志、进度展示体验好 |
| LLM 接口 | OpenAI-compatible | 可接 OpenAI、兼容服务和本地网关 |
| RAG 存储 | SQLite 起步 | 简单可靠，便于本地项目使用 |
| Browser | 后置 Playwright | MVP 先聚焦代码 Agent |
| Multi-Agent | 顺序调度起步 | 先验证角色分工价值 |

## 9. PaiCLI 到 PyAgentCLI 的工程映射

| PaiCLI 模块/能力 | PyAgentCLI 设计 |
| --- | --- |
| `Main.java` CLI 入口 | `cli/main.py` + Typer |
| `Agent.java` ReAct 循环 | `agent/loop.py` |
| `GLMClient.java` | `llm/openai_compatible.py`，模型厂商可配置 |
| `ToolRegistry.java` | `tools/registry.py` |
| `read_file/write_file/list_dir/execute_command` | `read_file/write_file/list_files/run_shell` |
| Plan-and-Execute | `agent/planner.py` + `TaskStep` |
| Memory 系统 | `memory/short_term.py` + `memory/long_term.py` + `memory/compressor.py` |
| RAG 代码检索 | `rag/indexer.py` + `rag/store.py` + `rag/retriever.py` |
| 人工审批 | `safety/approval.py` |
| MCP 接入 | `mcp/client.py` + `mcp/adapter.py` |
| DevTools / Browser | `tools/browser.py` |

关键差异：PyAgentCLI 不追求用最少代码复刻教程，而是把每个模块拆成可测试、可替换、可评估的工程组件。
