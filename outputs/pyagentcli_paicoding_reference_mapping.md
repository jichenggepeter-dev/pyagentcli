# PaiCoding / PaiCLI 设计思路到 PyAgentCLI 的映射

## 1. 使用边界

本文不是复制 PaiCoding 教程内容，而是把 `https://paicoding.com/react-vs-toolcall` 以及 PaiCLI 系列暴露出的项目思路，抽象成 PyAgentCLI 的产品与工程设计。

参考来源包括：

- PaiCoding 当前页：`400 行 Java 代码手搓 AI Agent，ReAct 循环 + Tool Call，我跑起来了`
- PaiCLI 系列目录：ReAct、Plan-and-Execute、Memory、Multi-Agent、RAG、HITL、并发、联网搜索、MCP、DevTools MCP、Skill、多模态
- 搜索结果可见的同系列摘要：Plan-and-Execute、Memory、RAG、Multi-Agent、MCP、简历与面试表达

PyAgentCLI 的原则是：借鉴路线、重写实现、换成 Python 生态、补足安全与评估。

## 2. PaiCLI 的核心路线

PaiCLI 的项目路线可以抽象成一条从最小 Agent 到工程化 Coding Agent 的升级路径：

```text
ReAct + Tool Call
  -> Plan-and-Execute / DAG
  -> Memory
  -> RAG 代码检索
  -> Multi-Agent
  -> HITL 人工审批
  -> 并发执行
  -> WebSearch / WebFetch
  -> MCP
  -> DevTools / Browser
  -> Skill
  -> 多模态
```

这条路线的优点是非常适合教学和简历项目：

- 起点小：先用一个最小 CLI 跑通 Agent Loop。
- 增量自然：每一期都解决上一个版本暴露出的真实问题。
- 技术面完整：覆盖 Agent、工具、安全、上下文、协作、外部生态。
- 面试友好：每个模块都能抽象成系统设计问题。

PyAgentCLI 应该保留这条路线，但不要被 Java 版本的类名和代码结构限制。

## 3. 第一阶段：ReAct + Tool Call

### PaiCLI 思路

当前页最核心的设计是：Agent 不是直接把用户请求交给模型闲聊，而是在循环中执行三件事：

1. 把消息历史和工具定义发给 LLM。
2. 如果模型返回 `tool_calls`，程序解析工具名和参数。
3. 本地执行工具，把结果作为 `tool` 消息放回对话历史。

公开页面还明确提到基础工具包含：

- `read_file`
- `write_file`
- `list_dir`
- `execute_command`
- `create_project`

它的模块拆分是最小四层：

```text
CLI Main
Agent
LLM Client
Tool Registry
```

### PyAgentCLI 映射

PyAgentCLI v0.1 也应从这个最小闭环开始，但 Python 版本要把安全边界提前纳入。

```text
cli/main.py
agent/loop.py
llm/openai_compatible.py
tools/registry.py
tools/filesystem.py
tools/shell.py
safety/policy.py
safety/approval.py
```

工具命名建议用更通用的 Python CLI 风格：

| PaiCLI 工具 | PyAgentCLI 工具 | 说明 |
| --- | --- | --- |
| `read_file` | `read_file` | 保持一致 |
| `write_file` | `write_file` | 增加 diff preview / approval |
| `list_dir` | `list_files` | 更贴近文件树语义 |
| `execute_command` | `run_shell` | 更清楚地表示 shell 执行 |
| `create_project` | v0.2+ | MVP 先不内置，避免模板范围过大 |

## 4. 第二阶段：Plan-and-Execute / DAG

### PaiCLI 思路

同系列 Plan-and-Execute 的核心思想是“规划和执行分离”：复杂任务先生成计划，再按步骤执行。它解决 ReAct 在复杂任务中反复调用模型、上下文膨胀、状态不清晰的问题，并天然支持 DAG 并行。

从摘要可以看到几个关键点：

- 先由 Planner 生成完整计划。
- 每个任务有明确状态。
- 无依赖任务可以并行。
- 某一步失败可以单独重试。
- 代价是灵活性下降，必要时要重新规划。

### PyAgentCLI 映射

PyAgentCLI 不应该 v0.1 就做完整 DAG。推荐 v0.2/v0.3 引入：

```python
TaskStep:
  id: str
  title: str
  description: str
  dependencies: list[str]
  status: pending | running | success | failed | skipped
  assigned_agent: str | None
  tool_calls: list[ToolCall]
  result_summary: str | None
```

触发策略：

- 简单任务默认 ReAct。
- 出现“先、然后、并且、接着、最后、分别、多个文件、完整实现”等多步骤线索时启用 Plan。
- 如果 ReAct 连续失败或超过步数，也可以请求 Planner 重建计划。

PyAgentCLI 的取舍：

- v0.1：只实现 ReAct。
- v0.2：增加可选 plan preview，但仍串行执行。
- v0.4：把 plan 转成 DAG，支持依赖关系。
- v0.5：和 Multi-Agent 合并，Planner 生成计划，Executor/Worker 执行，Reviewer 审查。

## 5. 第三阶段：Memory

### PaiCLI 思路

PaiCLI Memory 系列强调三层能力：

- 短期记忆：当前对话历史和工具结果。
- 长期记忆：跨会话保存用户偏好、项目约定等知识。
- Context 压缩：上下文过长时自动摘要，避免窗口爆掉。

同系列摘要还提到：长期记忆可做项目级隔离，检索时可以结合 BM25 和向量相似度。

### PyAgentCLI 映射

PyAgentCLI 建议定义三层：

```text
Session Memory:
  当前任务目标、步骤、工具结果、失败原因

Project Memory:
  .pyagent/memory.md 或 .pyagent/memory.sqlite
  项目技术栈、启动命令、测试命令、代码风格、用户确认过的事实

User Memory:
  ~/.pyagent/memory.md
  用户偏好、常用模型、默认安全策略
```

写入原则：

- 不自动把模型猜测写进长期记忆。
- 只有用户明确要求“记住”或 Agent 从稳定事实中提取并经用户确认后才写入。
- 长期记忆要保留来源、时间、作用域。

压缩策略：

- v0.1：不做自动压缩，只限制最大轮数。
- v0.3：超过 token 预算时摘要旧工具结果。
- v0.4：保留最近 N 轮原文，旧消息压缩为 `TaskSummary`。

## 6. 第四阶段：RAG 代码检索

### PaiCLI 思路

PaiCLI RAG 的关键点不是“塞一个向量库”这么简单，而是代码场景的检索策略：

- 代码不能只按字数切，需要按结构切。
- CLI 项目里 SQLite 比重型向量库更合适。
- 纯向量检索对代码标识符不够稳，需要混合检索。
- 方法级 chunk 往往比文件级 chunk 更有价值。

同系列摘要提到的方向包括：文件/类/方法三级切块、SQLite、embedding、关键词加权、chunk 类型加权、双命中奖励。

### PyAgentCLI 映射

Python 版本可这样落地：

```text
rag/indexer.py      扫描文件、过滤目录
rag/chunker.py      按语言结构切块
rag/store.py        SQLite 存储 chunk、路径、符号、embedding
rag/retriever.py    混合检索
rag/embeddings.py   OpenAI-compatible 或本地 embedding
```

MVP 先做：

- 文件名检索
- 路径检索
- ripgrep 文本检索
- `@file` 和 `@folder`

v0.3 再做：

- tree-sitter 或 Python AST 结构切分
- SQLite FTS5
- embedding
- 混合打分

混合打分建议：

```text
score =
  semantic_score * 0.50
  + keyword_score * 0.25
  + path_score * 0.10
  + symbol_score * 0.10
  + chunk_type_bonus * 0.05
```

## 7. 第五阶段：HITL 人工审批

### PaiCLI 思路

同系列把人工审批放在 ReAct、Plan、Memory、RAG、Multi-Agent 之后，说明这是从“能跑”走向“能安全跑”的关键步骤。

对 Coding Agent 来说，审批不是附加 UI，而是工具系统的一部分：

- 文件写入可能破坏项目。
- Shell 命令可能删除文件、泄露信息或改变系统。
- MCP 和浏览器工具可能触达外部服务。

### PyAgentCLI 映射

PyAgentCLI 应该更早引入 HITL，因为本地 Python CLI 默认面对真实文件系统。

工具风险分级：

```text
READ: list/read/search
WRITE: write/edit/create
EXECUTE: shell/test/build
NETWORK: web_fetch/mcp/http
CRITICAL: delete, chmod, sudo, credential, publish, payment
```

审批决策：

```text
ALLOW: 直接执行
ASK: 暂停并请求确认
DENY: 拒绝执行
```

审批提示至少包含：

- 工具名
- 参数摘要
- 影响范围
- 风险原因
- 是否会写文件、执行命令或访问网络

## 8. 第六阶段：Multi-Agent

### PaiCLI 思路

同系列 Multi-Agent 的公开摘要说明，PaiCLI 采用更接近 CrewAI 的角色分工和主从架构：

- Orchestrator 负责任务分发和流程控制。
- Planner 拆任务。
- Worker 执行任务。
- Reviewer 检查结果。

公开摘要还提到：Planner 输出 JSON 计划，Worker 可并行，Reviewer 不合格时打回重做，只有 Worker 有工具调用权限。

### PyAgentCLI 映射

PyAgentCLI 推荐采用同样的“三角色 + 权限隔离”：

```text
AgentOrchestrator
  -> PlannerAgent: 只产出计划，不调用工具
  -> ExecutorAgent / WorkerAgent: 可调用工具
  -> ReviewerAgent: 检查 diff、测试结果、风险
```

关键原则：

- Planner 不写文件。
- Reviewer 不直接修代码，只给反馈。
- Executor 执行高风险工具仍要经过 Safety。
- 每个 SubAgent 有独立 message history，避免上下文互相污染。

## 9. 第七阶段：并发

### PaiCLI 思路

同系列并发章节提到三类并行点：

- 一次模型响应中的多个 tool call 可以并行。
- DAG 中无依赖的任务可以并行。
- Multi-Agent 中多个 Worker 可以并行。

### PyAgentCLI 映射

Python 版本建议分阶段：

- v0.1：全部串行，便于调试。
- v0.3：只读工具并行，例如同时 `read_file` 多个文件。
- v0.4：DAG batch 并行。
- v0.5：Worker 并行。

并发限制：

- 写工具默认不并行，除非路径不冲突。
- Shell 工具默认不并行，除非用户显式允许。
- 并发工具结果必须保留 tool_call_id，避免回填错位。

## 10. 第八阶段：MCP 与 Browser

### PaiCLI 思路

PaiCLI 后续接入 MCP，并支持 stdio 和 Streamable HTTP。浏览器方向则通过 DevTools MCP / CDP 让 Agent 能访问页面、执行 JS、截图、调试前端。

### PyAgentCLI 映射

PyAgentCLI 的 MCP 设计：

```text
mcp/client.py       连接 stdio/http MCP server
mcp/adapter.py      把 MCP tool 转成 PyAgentCLI Tool
tools/browser.py    Playwright 或 DevTools MCP adapter
```

统一原则：

- MCP 工具进入同一个 Tool Registry。
- MCP 工具使用同一套 RiskLevel。
- 网络、浏览器、外部系统动作默认进入审批策略。
- MCP 返回的大对象要做裁剪，避免污染上下文。

## 11. 对 PyAgentCLI 路线的修正建议

基于 PaiCLI 路线，PyAgentCLI 的路线可以微调为：

```text
v0.1 Minimal ReAct Agent
  CLI + LLM + Tool Registry + read/write/list/shell + approval + audit

v0.2 Plan Preview + Strong Safety
  Planner 输出步骤，Safety Policy 完整化，diff preview

v0.3 Code Search / RAG Lite
  ripgrep + @file/@folder + SQLite FTS

v0.4 Memory + Context Compaction
  session/project/user memory，压缩旧上下文

v0.5 DAG + Multi-Agent
  Planner/Executor/Reviewer，任务状态持久化

v0.6 MCP + Browser
  stdio/http MCP client，Playwright 或 DevTools adapter

v0.7 Eval Harness
  任务成功率、工具成功率、审批率、失败分类
```

## 12. 和 PaiCLI 的差异化

PyAgentCLI 不能只是“Java 改 Python”，需要有自己的亮点：

| 方向 | PaiCLI 思路 | PyAgentCLI 差异化 |
| --- | --- | --- |
| 技术栈 | Java CLI | Python 生态，Typer/Rich/Pydantic/pytest |
| 工具安全 | 后续强化 HITL | v0.1 就内置审批和审计 |
| RAG | JavaParser + SQLite | tree-sitter/Python AST + SQLite FTS + embedding |
| CLI 体验 | JLine | Rich prompt、diff preview、approval panel |
| MCP | stdio/http | MCP tool 统一纳入 Safety 和 Audit |
| Eval | 简历中强调 | 项目内置 eval case 作为一等模块 |
| 面试表达 | 类 Claude Code Java 版 | Python 版 Codex/Claude Code mini，重点突出工程可控性 |

