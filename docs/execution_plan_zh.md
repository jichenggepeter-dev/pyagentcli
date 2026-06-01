# PyAgentCLI 分阶段执行文档

这份文档用于保证 PyAgentCLI 后续开发链路通畅。它把“大板块”拆成“小板块”，每个小板块都包含目标、输入、输出、改动范围、测试方式和完成标准。

## 总体原则

PyAgentCLI 的开发不按“想到哪里写到哪里”推进，而按下面的闭环推进：

```text
需求切片
  -> 架构边界
  -> 数据/接口契约
  -> 测试用例
  -> 最小实现
  -> 文档同步
  -> 全量验证
  -> GitHub 提交
```

每个小板块都必须回答六个问题：

- 这次解决什么用户问题？
- 输入是什么？
- 输出是什么？
- 允许改哪些文件？
- 怎么证明它真的工作？
- 做完后下一个模块如何接上？

## 当前状态

已完成：

- Phase 1：本地 AI Coding Agent CLI 核心闭环
- Phase 2.1：MCP v0.1 客户端和工具适配器

当前推荐继续：

- Phase 3.2d：Advanced RAG Import Graph

## Roadmap 总览

| 大阶段 | 目标 | 状态 |
| --- | --- | --- |
| Phase 0 | 产品需求、架构设计、路线拆解 | 已完成 |
| Phase 1 | Agent Loop、工具、安全、RAG Lite、Memory、Reviewer、Eval | 已完成 |
| Phase 2 | MCP、Browser、真实扩展能力 | 进行中 |
| Phase 3 | Multi-Agent、Advanced RAG、Advanced Memory | 未开始 |
| Phase 4 | Skill System、Model-backed Eval、工程化发布 | 未开始 |

## Phase 1：核心 Agent CLI

### 1.1 Agent Loop

目标：

- 建立最小 ReAct / Tool Calling 循环。
- 模型只能通过工具影响工作区。

输入：

- 用户 goal
- 系统 prompt
- 可用工具 schema

输出：

- LLM response
- tool call
- tool observation
- final answer

核心文件：

- `src/pyagentcli/agent/loop.py`
- `src/pyagentcli/agent/state.py`
- `src/pyagentcli/llm/**`

验收：

- 无 API key 时可走 local fallback。
- 有 API key 时可返回真实 tool call。
- 达到 max steps 后停止，避免无限循环。

测试：

```bash
.venv/bin/python -m pytest tests/test_agent_loop.py
```

### 1.2 Tool Registry 和本地工具

目标：

- 建立统一工具协议。
- 支持文件、命令、搜索工具。

小板块：

- `list_files`
- `read_file`
- `write_file`
- `edit_file`
- `run_shell`
- `search_files`
- `search_text`
- `search_index`

核心文件：

- `src/pyagentcli/tools/base.py`
- `src/pyagentcli/tools/registry.py`
- `src/pyagentcli/tools/filesystem.py`
- `src/pyagentcli/tools/shell.py`
- `src/pyagentcli/tools/search.py`

验收：

- 每个工具都有 schema。
- 每个工具通过 `ToolRegistry.execute()` 执行。
- 工具失败返回 observation，而不是直接抛出到 Agent 外层。

测试：

```bash
.venv/bin/python -m pytest tests/test_tools.py
```

### 1.3 Safety 和 HITL

目标：

- 建立本地 coding agent 的安全边界。

小板块：

- 路径围栏
- denylist 目录
- command 黑名单
- risk level
- 人工审批
- 审计日志

核心文件：

- `src/pyagentcli/safety/policy.py`
- `src/pyagentcli/safety/approval.py`
- `src/pyagentcli/safety/audit_log.py`

验收：

- 读工具默认允许。
- 写工具需要审批。
- shell 工具需要审批。
- 危险命令直接拒绝。
- `.git`、`.env`、`.venv` 等路径不可访问。

测试：

```bash
.venv/bin/python -m pytest tests/test_safety_policy.py tests/test_tools.py
```

### 1.4 RAG Lite

目标：

- 让 Agent 能检索代码上下文，而不是只靠用户粘贴。

小板块：

- 文件名搜索
- 文本搜索
- SQLite FTS 索引
- Python AST symbol chunk
- `@file`
- `@folder`
- `@symbol`
- stale index warning

核心文件：

- `src/pyagentcli/rag/chunker.py`
- `src/pyagentcli/rag/indexer.py`
- `src/pyagentcli/context_injection.py`

验收：

- 能索引 workspace。
- 能按 symbol 找到函数/类。
- 修改文件后能提示索引可能过期。

测试：

```bash
.venv/bin/python -m pytest tests/test_rag_chunker.py tests/test_rag_indexer.py tests/test_context_injection.py
```

### 1.5 Plan-and-Execute

目标：

- 把“计划”和“执行”分开，降低 Agent 一步到位乱改代码的风险。

小板块：

- `--plan`
- `--execute-plan`
- plan persistence
- resume
- retry step
- skip step
- set step status

核心文件：

- `src/pyagentcli/agent/planner.py`
- `src/pyagentcli/agent/plan_store.py`
- `src/pyagentcli/agent/plan_executor.py`

验收：

- plan 可预览。
- plan 可保存。
- failed plan 可恢复。
- step 可单独重试或跳过。

测试：

```bash
.venv/bin/python -m pytest tests/test_planner.py tests/test_plan_store.py tests/test_plan_executor.py tests/test_cli.py
```

### 1.6 Memory

目标：

- 让项目偏好、执行摘要和长期上下文可以跨任务保留。

小板块：

- `--remember`
- `--memory`
- project memory
- session summary
- memory context injection

核心文件：

- `src/pyagentcli/memory/project_memory.py`

验收：

- 用户显式记忆会写入 project memory。
- 后续 task 会注入 project memory。
- 执行后会产出 session summary。

测试：

```bash
.venv/bin/python -m pytest tests/test_memory.py
```

### 1.7 Reviewer

目标：

- 任务执行后自动复核改动、风险和建议测试。

核心文件：

- `src/pyagentcli/agent/reviewer.py`

验收：

- planned execution 后生成 review。
- review 写入 plan JSON。
- review markdown 写入 `.pyagent/reviews/`。

测试：

```bash
.venv/bin/python -m pytest tests/test_reviewer.py tests/test_plan_executor.py
```

### 1.8 Eval Harness

目标：

- 用固定任务集评估 Agent 平台能力。

核心文件：

- `src/pyagentcli/evals/cases.py`
- `src/pyagentcli/evals/runner.py`
- `src/pyagentcli/evals/metrics.py`

验收：

- `--eval` 可运行。
- 输出 summary。
- JSONL report 写入 `.pyagent/evals/`。

测试：

```bash
.venv/bin/python -m pytest tests/test_evals.py
```

## Phase 2：外部能力扩展

### 2.1 MCP v0.1：Client 和 Adapter

状态：

- 已完成。

目标：

- 让 PyAgentCLI 具备连接 MCP server 的底层能力。

已完成小板块：

- stdio transport
- JSON-RPC request/response
- `initialize`
- `notifications/initialized`
- `tools/list`
- `tools/call`
- MCP tool adapter
- read-only risk mapping
- non-read MCP 默认 deny

核心文件：

- `src/pyagentcli/mcp/client.py`
- `src/pyagentcli/mcp/adapter.py`
- `tests/test_mcp.py`
- `docs/mcp.md`

验收：

- fake MCP transport 能完成 handshake。
- MCP tool 能注册进 `ToolRegistry`。
- read-only MCP tool 可执行。
- network/critical MCP tool 被策略拒绝。

测试：

```bash
.venv/bin/python -m pytest tests/test_mcp.py
```

### 2.2 MCP Config 和 CLI 集成

状态：

- 已完成。

目标：

- 让用户通过项目配置声明 MCP server。
- Agent 启动时自动注册 read-only MCP 工具。

建议输入配置：

```toml
[mcp.servers.docs]
command = ["python", "scripts/docs_mcp_server.py"]
enabled = true
```

输出：

- Agent tools schema 中出现 `mcp_docs_<tool>`。
- read-only MCP tools 可被模型调用。
- 非 read-only MCP tools 在当前策略下拒绝执行。

允许修改：

- `src/pyagentcli/config.py`
- `src/pyagentcli/cli/main.py`
- `src/pyagentcli/mcp/**`
- `tests/test_config.py`
- `tests/test_mcp.py`
- `tests/test_cli.py`
- `docs/mcp.md`

不做：

- HTTP transport
- OAuth
- resources/prompts
- 写权限 MCP 自动放行

验收：

- 配置解析有测试。
- 默认无 MCP 配置时行为不变。
- 有 MCP 配置时能注册工具。
- server 启动失败时给出清晰错误，不影响本地默认工具。

测试：

```bash
.venv/bin/python -m pytest tests/test_config.py tests/test_mcp.py tests/test_cli.py
.venv/bin/python -m pytest
```

### 2.3 Browser v0.1

状态：

- 已完成。

目标：

- 让 PyAgentCLI 能检查本地 Web 应用页面。

小板块：

- browser tool schema
- open page
- get title/url
- text snapshot
- local URL guardrail

建议实现：

- v0.1 先使用标准库实现本地页面文本检查，保持无额外浏览器依赖。
- 只支持本地 URL：`localhost`、`127.0.0.1`、`file://`。
- 网络站点默认拒绝或审批。

允许修改：

- `src/pyagentcli/tools/browser.py` 或 `src/pyagentcli/browser/**`
- `src/pyagentcli/tools/registry.py`
- browser tests
- `docs/browser.md`

验收：

- 能打开本地测试页面。
- 能返回标题和文本。
- 风险等级明确。

测试：

```bash
.venv/bin/python -m pytest tests/test_browser.py
```

### 2.4 Model-backed Eval v0.2

状态：

- 已完成第一版 deterministic scorer。

目标：

- 从“平台能力 eval”升级为“真实任务成功率 eval”。

小板块：

- fixture workspace
- task definition
- expected diff
- expected tool sequence
- success scorer
- safety scorer
- report summary

允许修改：

- `src/pyagentcli/evals/**`
- `tests/test_evals.py`
- `examples/eval_workspaces/**`
- `docs/evals.md`

验收：

- eval 能跑固定 coding tasks。
- 能判断目标文件是否按预期改变。
- 能记录工具调用是否越权。
- 能输出 task success rate。

## Phase 3：智能体能力增强

### 3.1 Multi-Agent v0.2

状态：

- 已完成第一版 contract 和 Reviewer gate。

目标：

- 从单 Agent 执行升级到 Planner、Executor、Reviewer 分工。

小板块：

- agent role contract
- Planner output schema
- Executor input schema
- Reviewer gate
- failure handoff
- retry loop

核心设计：

```text
User Goal
  -> Planner Agent
  -> Plan JSON
  -> Executor Agent
  -> Tool Calls
  -> Reviewer Agent
  -> Pass / Needs Fix / Needs Human
```

验收：

- Reviewer 可以阻止 plan 直接标记 success。
- Planner/Executor/Reviewer 消息边界清楚。
- 单 Agent 模式仍然可用。

### 3.2 Advanced RAG

状态：

- 已完成第一版 embedding provider interface 和 hybrid retrieval 结果结构。

目标：

- 从 Lite 检索升级到更接近 coding agent 的代码理解。

小板块：

- embedding provider interface
- vector store
- hybrid search
- import graph
- multi-language chunker
- reranker hook

验收：

- 没有 embedding key 时 FTS 仍可用。
- embedding 搜索可选开启。
- import graph 不阻塞基础检索。

### 3.3 Advanced Memory

目标：

- 从简单记忆升级到可维护、可压缩、可删除的记忆系统。

小板块：

- memory compressor
- stale memory detection
- memory review command
- delete memory command
- user memory

验收：

- 用户能查看、编辑、删除 memory。
- 长 session 能压缩。
- memory 不应无限膨胀。

## Phase 4：工程化和生态

### 4.1 Skill System

目标：

- 让 Agent 根据任务加载局部技能说明。

小板块：

- skill metadata
- skill loader
- skill selection
- prompt injection
- builtin skills

验收：

- 可加载本地 skill。
- skill 不直接绕过工具安全。
- skill 的启用可追踪。

### 4.2 发布和安装

目标：

- 让项目从 GitHub demo 变成可安装 CLI。

小板块：

- package metadata
- versioning
- release notes
- GitHub Actions test matrix
- PyPI 准备

验收：

- clean checkout 后可安装。
- CI 通过。
- README quick start 可复现。

## 每次开发的标准交接格式

每完成一个小板块，最终回复或 PR 描述应包含：

```text
完成模块：
改动文件：
用户可见行为：
安全边界：
测试结果：
未做事项：
下一步建议：
```

## 当前下一步执行卡片

名称：

- Advanced RAG Import Graph

目标：

- 加入 Python import/dependency graph 信号，让检索能回答“哪些文件互相依赖”。

第一小步：

- 在索引阶段提取 Python import 关系，写入 SQLite。

第二小步：

- 增加 dependency query 方法，比如查某文件 imports / imported_by。

第三小步：

- 让 HybridRetriever 或新工具能返回 dependency context。

完成标准：

- 当前 FTS/RAG Lite 行为不回退。
- 非 Python 文件不受影响。
- import graph 可解释。
- 全量测试通过。
