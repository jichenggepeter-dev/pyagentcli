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
- Phase 4.1：Skill System v0.1

当前推荐继续：

- Phase 4.16：Imported-By Dependency Context

## Roadmap 总览

| 大阶段 | 目标 | 状态 |
| --- | --- | --- |
| Phase 0 | 产品需求、架构设计、路线拆解 | 已完成 |
| Phase 1 | Agent Loop、工具、安全、RAG Lite、Memory、Reviewer、Eval | 已完成 |
| Phase 2 | MCP、Browser、真实扩展能力 | 进行中 |
| Phase 3 | Multi-Agent、Advanced RAG、Advanced Memory | 进行中 |
| Phase 4 | Skill System、Model-backed Eval、工程化发布 | 进行中 |

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

### 3.1 Multi-Agent v0.3

状态：

- 已完成 role contract、Reviewer gate、Planner/Executor/Reviewer 持久化 handoff、Reviewer 下一步建议。
- 已完成角色级 model/prompt 配置入口：Planner 和 Executor 已接入，Reviewer 配置已保留给 proposal 生成。
- 已完成只读 Reviewer retry proposal：failed/skipped/cancelled 生成建议命令，但不自动执行。

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

状态：

- 已完成 v0.1：本地 `skill.toml`、`SKILL.md`、关键词选择、上下文注入、`--list-skills`。

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

状态：

- 已完成 v0.1：包元数据测试、`pyagent` 入口 smoke、CI smoke、release checklist。

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

- Imported-By Dependency Context

目标：

- 在 RAG dependency context 中加入 imported-by 反向依赖，让 Agent 能知道“谁依赖当前文件/模块”。

第一小步：

- 设计 imported-by 查询输出：target module、importing file、line、imported name。

第二小步：

- 将 reverse dependency context 接入 `@file` / context injection。

第三小步：

- 补 RAG indexer / retriever / context injection 测试。

完成标准：

- `search_dependencies` 支持 imported-by 场景。
- `@src/helpers.py` 能注入谁 import 了 helpers。
- 全量测试通过。

## 最近完成：Browser Assertion Evals

完成内容：

- 新增 browser assertion eval case，调用真实 `browser_assert` 工具路径。
- 覆盖本地静态 HTML expected_text、selector、expected_status 通过场景。
- 覆盖外部 URL denial，expected failure 被计为 eval pass。
- 新增 Browser assertion summary：passed、failed、expected denials。
- JSONL report 新增 `browser_assertion` 类型。
- CLI `--eval` 输出 Browser assertion summary 和每条 case 明细。
- 默认 eval 不依赖 Playwright，也不访问外部网站。
- 补充 eval / CLI 测试，并同步 `docs/evals.md`、`docs/browser.md`、`docs/roadmap.md`。

## 最近完成：Richer Changed-File Risk Scoring

完成内容：

- Reviewer 新增 `ChangedFileRisk`，按 path、file type、diff size、删除行数计算 risk level 和 score。
- Safety 路径小 diff 也标为 high；tools 路径叠加中型 diff 标为 high。
- 文档小 diff 标为 low，并建议 review rendered documentation。
- 风险评分写入 Review artifact 的 `Changed-file risk scoring` 区块。
- 风险评分进入 `Risks` 和 `Suggested tests` 汇总，但不改变 deterministic gate。
- model-backed Reviewer prompt 同步接收 file risk metadata。
- 补充 docs / safety / tools 不同风险等级测试，并同步 `docs/reviewer.md`、`docs/roadmap.md`。

## 最近完成：Per-Retriever Comparison Reports

完成内容：

- 新增 retriever comparison eval fixture，对比 exact、vector-hash、hybrid-hash。
- 默认 eval 不调用外部 embedding 服务，vector 使用 deterministic `hash` provider。
- 新增 `vector-disabled` 结果，明确记录无 embedding provider 时的 disabled reason。
- CLI `--eval` 新增 Retriever comparison summary 和每条 retriever 明细。
- JSONL report 新增 `retriever_comparison` 类型，记录 retriever name、rank、hit path、score。
- 补充 eval / CLI 测试，并同步 `docs/evals.md`、`docs/rag_lite.md`、`docs/roadmap.md`。

## 最近完成：Richer Browser Assertions

完成内容：

- 新增 `browser_assert` 只读工具，支持 expected_text、selector、expected_status。
- 工具保持 local-only URL 边界，拒绝外部 HTTP/HTTPS。
- 无 Playwright 时使用静态 HTML fallback，可断言文本、简单 selector 和页面状态。
- 有 Playwright 时使用真实渲染页面，可检查 JS 更新后的 DOM 和 CSS selector。
- 补充核心 browser assertion 测试和可选 Playwright 成功路径测试。
- 同步 `docs/browser.md`、`docs/roadmap.md`。

## 最近完成：Git Diff-Aware Reviewer

完成内容：

- Reviewer 新增 git diff 摘要：changed files、added/removed lines、bounded hunk headers。
- 非 git workspace 不报错，并在 review artifact 中说明 workspace 不是 git 仓库。
- git 仓库无 diff 时给出 `no uncommitted git diff found`。
- 有 diff 时 ReviewReport summary、risk notes、suggested tests 和 Markdown artifact 都会反映变更文件。
- 可选 model-backed Reviewer prompt 也接收 bounded git diff metadata，但不能覆盖 deterministic gate。
- 补充 git repo / 非 git repo / 无 diff 三类测试，并同步 `docs/reviewer.md`、`docs/roadmap.md`。

## 最近完成：Per-Model Trace Comparison

完成内容：

- 新增 `--eval-compare-models` 显式开关，默认 `pyagent --eval` 不调用外部模型。
- 支持在 `pyagent.toml` 的 `[evals.model_comparison.models.*]` 中配置 model、base_url、api_key_env。
- 缺少模型配置或 API key 时输出 disabled summary，不回退到本地模型假装比较。
- Eval runner 支持多个模型 client 的 trace comparison，并输出 model count、tool-call accuracy、safety violations。
- JSONL report 新增 `model_trace_comparison` 类型。
- 补充 config、runner、CLI 测试，并同步 `docs/evals.md`、`docs/roadmap.md`。

## 最近完成：Browser Network Logs

完成内容：

- 新增 `browser_network_logs` 只读工具。
- 工具保持 local-only URL 边界，只允许 workspace file 和 localhost。
- 输出 method、url、status、resource_type、failure。
- 不记录 request/response body，也不记录 header。
- 未安装 Playwright 时清晰降级；可选测试覆盖本地页面发起请求和响应状态。

## 最近完成：Reviewer Proposal Comparison Eval

完成内容：

- 新增 proposal comparison eval fixture：matched retry、mismatched action、invalid JSON downgrade。
- 新增 comparison result 字段：deterministic_action、model_action、matched、confidence。
- CLI `--eval` 输出 Reviewer proposal comparison summary。
- JSONL report 新增 `reviewer_proposal_comparison` 类型。
- fake reviewer model 稳定覆盖 model suggestion 的 matched / mismatched / inspect 降级路径。

## 最近完成：Real Model Trace Capture

完成内容：

- 新增 `--eval-real-model` 显式开关，默认 `pyagent --eval` 不调用外部 API。
- 新增 opt-in real model trace case：要求真实模型调用 `list_files` 并最终输出 `README.md`。
- 无 `OPENAI_API_KEY` 时输出清晰 disabled 原因，不 fallback 到本地模型。
- JSONL report 新增 `real_model_trace_eval` 类型。
- fake LLM 测试覆盖 opt-in trace capture 和 scoring 路径。

## 最近完成：Advanced Browser Interaction

完成内容：

- 新增 `browser_interact` 工具，支持 click、type/fill、wait。
- 工具保持 local-only URL 边界，只允许 workspace file 和 localhost。
- `browser_interact` 标记为 `EXECUTE` 风险，必须走审批链路。
- 未安装 Playwright 时清晰降级，不影响核心测试。
- 可选 Playwright 测试覆盖本地 HTML 输入、点击和状态读取。

## 最近完成：Model-backed Reviewer Proposal

完成内容：

- 新增 `ModelReviewSuggestion`，支持 summary、risk notes、suggested tests、recommended action、confidence。
- Reviewer 可选接入 reviewer role model，仅在 API key 和 `[agents.reviewer].model` 同时存在时启用。
- 模型建议写入 review artifact，但 deterministic gate 仍是最终安全边界。
- 无模型配置时 Reviewer 行为保持不变。
- 测试覆盖 fake model 输出和坏 JSON 降级路径。

## 最近完成：Reviewer Output Scoring

完成内容：

- 新增 Reviewer eval fixture：success / failed / skipped plan。
- 将 Reviewer gate、retry proposal、suggested tests 写入 eval summary。
- JSONL report 新增 `reviewer_eval` 类型。
- CLI `--eval` 输出 Reviewer eval summary 和每个 case 的评分结果。
