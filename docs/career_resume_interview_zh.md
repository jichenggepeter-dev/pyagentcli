# PyAgentCLI 简历篇与面试篇

本文把 PaiCLI 学习路线中的“先跑项目、再写简历、围绕简历准备面试”的方法，映射到 PyAgentCLI 项目。

注意：本文不是对 PaiCLI 原文的复制，而是基于 PyAgentCLI 当前实现整理的原创求职材料。

## 00. 按学习路线组织 PyAgentCLI

PaiCLI 学习路线的核心结构可以抽象成五步：

```text
先跑起来
  -> 写到简历
  -> 围绕简历深挖源码和面试题
  -> 动手 debug / 改 bug / 加功能
  -> 整理成自己的知识库
```

PyAgentCLI 也按这套结构来沉淀。

### 0.1 先把 PyAgentCLI 跑起来

你需要先证明项目真的能在本地跑，而不是只停留在“我看懂了”的层面。

推荐命令：

```bash
python -m pip install -e ".[dev]"
pyagent --help
pyagent --eval
pyagent --plan "fix failing tests"
pyagent --check-browser
```

跑通后你应该能看到：

- CLI 帮助信息正常输出。
- `--eval` 输出 platform eval、coding task eval、RAG retrieval eval、trace eval。
- `--plan` 能生成计划但不执行。
- `--check-browser` 能说明 Playwright 是否可用。

这一步对应的学习目标：

- 理解 CLI entry point。
- 理解项目如何从命令行进入 `main.py`。
- 理解无 API key 时的 local fallback。
- 理解测试和 eval 的区别。

### 0.2 再把项目写到简历上

跑通后不要急着从头到尾读源码。先决定简历写什么。

原因很简单：

> 简历写什么，面试官就大概率问什么；你也就知道应该重点深挖哪些模块。

PyAgentCLI 最适合写进简历的模块，按优先级是：

1. ReAct / Tool Calling Agent Loop
2. Tool Registry / HITL / Safety / Audit Log
3. RAG 代码检索 / AST symbol / import graph
4. Memory / Context Injection / Compression
5. Plan-and-Execute / Reviewer Gate / Retry Proposal
6. Multi-Agent handoff
7. MCP Client / Tool Adapter
8. Skill System
9. Browser Tools
10. Eval Harness / Trace Eval

每个模块都要能继续往下展开：

- 入口文件在哪里？
- 核心数据结构是什么？
- 安全边界是什么？
- 怎么测试？
- 遇到过什么坑？

### 0.3 围绕简历深挖源码和面试题

不要漫无目的地通读所有文件。推荐按简历模块读源码：

| 简历模块 | 重点源码 | 面试方向 |
| --- | --- | --- |
| ReAct Loop | `agent/loop.py`, `llm/base.py` | ReAct、Function Calling、模型是否执行代码 |
| Tool Registry | `tools/registry.py`, `tools/base.py` | 工具 schema、工具分发、失败恢复 |
| Safety | `safety/policy.py`, `safety/approval.py` | HITL、路径围栏、命令黑名单 |
| RAG | `rag/indexer.py`, `rag/chunker.py`, `context_injection.py` | FTS、AST chunk、向量检索、stale index |
| Memory | `memory/project_memory.py` | Memory vs Context、压缩、删除、过期 |
| Plan | `agent/planner.py`, `agent/plan_store.py` | Plan-and-Execute、持久化、重试 |
| Multi-Agent | `agent/contracts.py`, `agent/plan_executor.py`, `agent/reviewer.py` | Planner / Executor / Reviewer 分工 |
| MCP | `mcp/client.py`, `mcp/adapter.py` | MCP 协议、工具生态、安全映射 |
| Skill | `skills/loader.py` | Skill vs Tool、prompt guidance |
| Browser | `tools/browser.py` | local-only 浏览器 inspection |
| Eval | `evals/runner.py`, `evals/cases.py` | Agent 效果评估、trace、safety violation |

### 0.4 动手 debug、改 bug、加功能

我们开发 PyAgentCLI 的过程里已经做过很多“真实项目动作”，这些都可以反过来成为面试素材：

- 加工具：从 `inspect_page` 扩展到 `browser_dom_snapshot`、`browser_query_selector`。
- 加安全：限制外部 URL、限制 screenshot 输出到 `.pyagent/browser/`。
- 加配置：新增 role-level model / prompt config。
- 加评估：从 deterministic eval 扩展到 trace eval。
- 修测试：`pytest.importorskip` 放在模块级会导致单文件运行 exit code 5，于是改成函数内 skip。
- 处理权限：普通 sandbox 不能联网 push，后续改用用户手动 push 或授权通道。
- 处理工具限制：Computer Use 能看 Safari，但 Terminal 被安全策略禁止操作。

这些不是“杂事”，而是真实工程能力：

> 能发现约束、解释约束、在约束内找到稳定实现方式。

### 0.5 整理成自己的知识库

最后一步是输出。建议把 PyAgentCLI 学习资料沉淀成几类：

- 简历材料：项目描述、技术栈、核心职责、bullet。
- 面试题库：按 ReAct、Tool、RAG、Memory、MCP、Eval 分类。
- 架构图：Agent Loop、Tool Calling、Plan-and-Execute、Multi-Agent、MCP。
- 踩坑记录：环境、权限、测试、模型、浏览器、GitHub push。
- 复盘文章：每个模块写一篇“为什么做、怎么做、怎么测”。

这份文档就是 PyAgentCLI 的第一版学习知识库。

## 01. 项目定位

PyAgentCLI 可以定位为：

> Python 版 Claude Code / Codex mini，本地运行的 AI Coding Agent CLI。

它不是一个普通聊天壳，而是围绕模型构建了一套本地 Agent Runtime：

- ReAct / Tool Calling 主循环
- 文件、命令、搜索、浏览器工具
- 工具注册、风险分级、人工审批、审计日志
- RAG 代码检索和上下文注入
- Project Memory 和 Session Memory
- Plan-and-Execute
- Planner / Executor / Reviewer 多 Agent 协作
- MCP 客户端和工具适配
- Skill System
- Eval Harness
- 可选 Playwright 浏览器能力
- Release / Packaging 工程化

一句话讲清楚：

> 我从 0 到 1 实现了一个 Python 版本地 AI Coding Agent CLI，让模型不能直接改代码，而是通过受控工具调用完成文件读写、命令执行、代码检索、记忆注入、计划执行、复核评估和浏览器调试。

## 02. 简历篇

### 推荐项目名

中文：

> PyAgentCLI：Python 版本地 AI Coding Agent CLI

英文：

> PyAgentCLI: Local AI Coding Agent CLI in Python

### 推荐项目描述

版本 A：面向 AI Agent / 后端工程岗位

> 从 0 到 1 设计并实现 Python 版本地 AI Coding Agent CLI，定位类似 Claude Code / Codex mini。项目支持 ReAct 循环、OpenAI-compatible Function Calling、文件/命令/搜索/浏览器工具、RAG 代码检索、项目记忆、Plan-and-Execute、多 Agent 协作、MCP 工具扩展、人工审批、安全审计和 Eval Harness，可通过自然语言在本地代码仓库中完成代码理解、修改、验证和复核。

版本 B：面向平台/工具/基础设施岗位

> 设计并实现面向开发者的本地 AI Agent Runtime，将模型输出的工具调用转化为受控的本地文件操作、命令执行、代码检索和浏览器检查流程。系统内置工具权限、路径围栏、危险命令拦截、人工审批、审计日志、计划持久化、Reviewer gate 和可复现评估体系，强调安全、可观测和可扩展。

版本 C：一行简洁版

> 实现 Python 版 Claude Code / Codex mini，支持 ReAct、Tool Calling、RAG、Memory、MCP、Multi-Agent、HITL 安全审批和 Eval Harness。

### 技术栈

推荐写法：

> Python 3.12、OpenAI-compatible API、SQLite FTS、AST Parser、TOML、JSONL、MCP stdio、Playwright optional、pytest、GitHub Actions

如果想突出工程能力：

> Python、CLI、Agent Runtime、Tool Registry、Safety Policy、SQLite FTS、RAG、MCP、Eval Harness、pytest、GitHub Actions

### 核心职责

建议按从基础到高级的顺序写，面试官更容易追问。

1. 实现 ReAct / Tool Calling Agent Loop
   - 设计 `AgentLoop`，维护 system/user/assistant/tool 消息历史。
   - 支持 OpenAI-compatible Function Calling。
   - 模型只返回结构化 tool call，真实执行由本地工具层完成。
   - 设置 max steps 防止无限循环。

2. 设计 Tool Registry 和本地开发工具
   - 实现统一工具协议和 schema 输出。
   - 内置 `read_file`、`list_files`、`write_file`、`edit_file`、`run_shell`、`search_text`、`search_index`、`inspect_page` 等工具。
   - 工具失败转化为 observation 返回模型，而不是让 Agent 崩溃。

3. 构建安全边界和 HITL 审批机制
   - 实现路径围栏，禁止访问 `.git`、`.env`、`.venv`、`node_modules` 等敏感路径。
   - 对写文件和 shell 命令进行人工审批。
   - 对危险命令如 `rm -rf`、`sudo`、管道执行脚本等直接拒绝。
   - 通过 JSONL 审计日志记录工具名、参数、风险等级、审批结果和执行结果。

4. 实现 RAG Lite 与代码上下文注入
   - 基于 SQLite FTS 构建本地代码索引。
   - 支持 Python AST symbol chunk，识别函数、类和方法。
   - 支持 JavaScript / TypeScript 常见函数、类、箭头函数 chunk。
   - 支持 `@file`、`@folder`、`@symbol` 上下文注入。
   - 实现 stale index warning，避免 Agent 使用过期检索结果。

5. 设计 Hybrid Retrieval 和依赖上下文
   - 抽象 embedding provider，支持 disabled、hash、OpenAI-compatible 三种模式。
   - 实现 SQLite vector store 和 FTS/vector 混合检索。
   - 构建 Python import graph，支持 imported-by / imports 查询。
   - 新增 `search_dependencies` 工具，为代码理解提供依赖上下文。

6. 实现 Memory 系统
   - 支持 project memory、session summaries、显式 remember。
   - 任务执行前自动注入项目记忆。
   - 支持 session 压缩、记忆删除和 stale memory 检查。
   - 将记忆存储在 `.pyagent/memory/`，保证本地可审计、可删除。

7. 实现 Plan-and-Execute
   - 支持 `--plan` 预览计划。
   - 支持 `--execute-plan` 审批后执行。
   - 将 plan 持久化到 `.pyagent/plans/`。
   - 支持 resume、retry step、skip step、set step status。
   - 执行前检查 RAG index freshness，避免计划基于过期上下文。

8. 实现 Multi-Agent 协作
   - 抽象 Planner / Executor / Reviewer 三角色。
   - Planner 生成结构化 `PlanPreview`。
   - Executor 按 step contract 执行单步任务。
   - Reviewer 复核执行结果，生成 gate decision 和风险建议。
   - 持久化 agent handoff，记录 Planner、Executor、Reviewer 之间的交接。

9. 实现 Reviewer Gate 和 Retry Proposal
   - Reviewer 可阻止包含 failed / skipped / cancelled step 的计划被标记为成功。
   - 对 failed step 生成 `retry_step` proposal。
   - 对 skipped step 生成 `user_decision` proposal。
   - 对 cancelled step 生成 `resume_plan` proposal。
   - proposal 只写入 review，不自动执行工具，仍需用户审批。

10. 实现 MCP v0.1
    - 实现最小 stdio MCP client。
    - 支持 JSON-RPC initialize、tools/list、tools/call。
    - 将 MCP tool 适配进现有 ToolRegistry。
    - 根据 `readOnlyHint` 设置工具风险等级。
    - 非只读 MCP 工具默认按 NETWORK / CRITICAL 处理，安全策略默认拒绝。

11. 实现 Skill System
    - 支持 `.pyagent/skills/<skill>/skill.toml` 和 `SKILL.md`。
    - 根据任务关键词选择 skill。
    - 将 skill 作为低优先级 prompt guidance 注入任务上下文。
    - 明确 skill 不执行工具、不绕过安全策略、不覆盖用户任务。

12. 构建 Eval Harness
    - 内置平台 eval、coding task eval、RAG retrieval eval、trace eval。
    - 指标包括 task success、tool-call accuracy、safety violations。
    - 支持 JSONL report，方便后续回归和对比。

13. 构建 Browser 工具能力
    - 实现 `inspect_page`、`browser_dom_snapshot`、`browser_query_selector`。
    - 保持 local-only URL guardrail。
    - 可选接入 Playwright console logs 和 screenshot。
    - 没有 Playwright 时给出清晰降级提示。

14. 完成工程化发布准备
    - 配置 `pyagent` console script。
    - 增加 package metadata 测试。
    - 增加 GitHub Actions 测试和 CLI smoke。
    - 编写 release checklist。

### 简历 bullet 版本

如果简历空间有限，可以写 5 条：

- 从 0 到 1 实现 Python 版本地 AI Coding Agent CLI，支持 ReAct / Function Calling 循环、OpenAI-compatible 模型接入和本地 fallback 模式。
- 设计 Tool Registry 与安全执行层，内置文件读写、局部编辑、shell、搜索、浏览器工具，支持路径围栏、危险命令拦截、人工审批和 JSONL 审计日志。
- 构建 RAG 代码检索体系，基于 SQLite FTS、AST symbol chunk、import graph 和可选 embedding provider，实现 `@file/@folder/@symbol` 上下文注入与 stale index warning。
- 实现 Project Memory、Session Summary、Plan-and-Execute、Reviewer Gate 和 Retry Proposal，支持计划持久化、步骤重试、跳过、恢复和多 Agent handoff。
- 集成 MCP stdio client、Skill System、Eval Harness 和可选 Playwright 浏览器能力，构建 tool-call accuracy、task success、safety violation 等评估指标。

如果想更偏 AI Agent 岗：

- 实现本地 Agent Runtime，将 LLM 的结构化 tool call 转化为受控的本地工具执行，并通过 observation 回灌模型形成 ReAct 闭环。
- 设计 Planner / Executor / Reviewer 三角色协作机制，持久化 agent handoff，并通过 Reviewer gate 防止 skipped / failed step 被误判为成功。
- 构建上下文工程体系，将 RAG 检索、项目记忆、Skill guidance 和用户显式引用统一注入任务 prompt。
- 实现 MCP tool adapter，支持外部工具生态接入，并根据工具 read-only hint 映射风险等级。
- 构建 deterministic eval harness，评估 Agent 的工具调用准确率、任务完成率和安全违规率。

如果想更偏后端工程：

- 基于 Python 设计 CLI 工具架构，完成配置加载、插件注册、持久化存储、审计日志、测试和发布工程。
- 使用 SQLite FTS 和 AST 解析构建轻量代码索引，支持符号级检索、依赖关系查询和多语言 chunk。
- 通过路径围栏、命令黑名单、风险等级和 HITL 审批实现本地代码执行安全控制。
- 使用 pytest 构建 150+ 自动化测试，覆盖 Agent loop、工具、安全、RAG、Memory、MCP、Reviewer、Browser 和 Eval。
- 配置 GitHub Actions、console script 和 release checklist，保证 clean checkout 后可安装、可测试、可演示。

## 03. 面试篇

### 准备原则

面试准备不要从头背源码，而是围绕简历上的模块准备。

推荐顺序：

1. ReAct / Function Calling
2. Tool Registry / HITL / Safety
3. RAG / Context Injection
4. Memory / Context Compression
5. Plan-and-Execute / Multi-Agent
6. MCP / Skill System
7. Browser Tools
8. Eval Harness
9. Packaging / Engineering Quality

每个模块都要能讲清楚四件事：

- 为什么要做？
- 具体怎么设计？
- 有什么安全边界？
- 怎么证明它有效？

### 1. ReAct 和 Function Calling

面试官可能问：

- 什么是 ReAct？
- Function Calling 的本质是什么？
- 模型到底会不会执行代码？
- Agent Loop 如何防止无限循环？
- Tool Call 失败后怎么办？

回答框架：

> ReAct 是 Reasoning + Acting。模型不是一次性回答，而是在推理过程中发出动作意图。Function Calling 的本质是模型输出结构化调用意图，比如工具名和参数。真正执行工具的是 PyAgentCLI 的本地 ToolRegistry。执行结果会作为 observation 回到消息历史，模型再基于真实结果继续推理。

结合 PyAgentCLI：

- `AgentLoop` 维护消息历史。
- 每轮调用 LLM。
- 如果有 tool call，就交给 `ToolRegistry.execute()`。
- 工具结果转成 tool message。
- 如果没有 tool call，就认为任务完成。
- `max_steps` 防止死循环。

可以强调：

> 模型不会直接读文件、不会直接运行命令、不会直接改代码。它只能提出 tool call，PyAgentCLI 在本地做安全检查、审批、执行和审计。

### 2. Tool Call、HITL 和安全策略

面试官可能问：

- 工具调用怎么设计？
- 为什么不能让模型直接执行 shell？
- HITL 审批怎么做？
- 如何防止 Agent 删除用户文件？
- 工具权限如何分级？

回答框架：

> 工具调用的关键不是“能不能执行”，而是“能不能安全地执行”。PyAgentCLI 把工具分成 READ、WRITE、EXECUTE、NETWORK、CRITICAL 等风险等级。读工具默认允许，写文件和 shell 需要审批，危险命令直接拒绝。

结合 PyAgentCLI：

- `SafetyPolicy` 做路径围栏和命令黑名单。
- `.git`、`.env`、`.venv`、`node_modules` 等路径默认拒绝。
- `write_file`、`edit_file` 生成 diff preview。
- `run_shell` 需要用户审批。
- 审计日志记录每次工具调用。

经典回答：

> LLM 输出的是意图，工具层负责执行。安全策略必须在工具执行前做，而不是相信模型自己守规矩。

### 3. Plan-and-Execute

面试官可能问：

- ReAct 和 Plan-and-Execute 有什么区别？
- 为什么要先 plan 再 execute？
- 计划失败后怎么恢复？
- step retry 怎么设计？

回答框架：

> ReAct 适合短任务和探索性任务。Plan-and-Execute 适合复杂任务，先把目标拆成可审查的步骤，再让用户批准执行。这样可以降低 Agent 一上来就乱改代码的风险。

结合 PyAgentCLI：

- `--plan` 只生成计划，不执行。
- `--execute-plan` 先展示计划，再请求用户审批。
- Plan 持久化到 `.pyagent/plans/`。
- 支持 `--resume-plan`、`--retry-step`、`--skip-step`。
- 执行后由 Reviewer 复核。

可以补一句：

> 我们没有让 Agent 自动越权重试。retry proposal 只生成建议，真正执行仍然需要用户审批。

### 4. Multi-Agent

面试官可能问：

- Multi-Agent 有什么价值？
- Planner、Executor、Reviewer 怎么分工？
- 为什么不直接一个 Agent 干到底？
- Reviewer 如何避免形式主义？

回答框架：

> Multi-Agent 的价值不在于堆角色，而在于把职责边界拆清楚。Planner 负责拆解任务，Executor 负责按步骤执行，Reviewer 负责复核执行结果和风险。这样每个角色的输入输出都可以审计。

结合 PyAgentCLI：

- Planner 输出 `PlanPreview`。
- Executor 通过 `ExecutorStepContract` 执行单步。
- Reviewer 输出 `ReviewReport` 和 `ReviewerGateDecision`。
- Agent handoff 被持久化到 plan。
- Reviewer gate 会把含 failed / skipped / cancelled step 的 success plan 降级为 failed。

回答亮点：

> Reviewer 不是“写一段总结”而已，它参与最终状态判定，能阻止失败步骤被误判为成功。

### 5. Memory 和 Context

面试官可能问：

- Memory 和 Context 有什么区别？
- 长上下文满了怎么办？
- 记忆会不会污染模型？
- 如何删除错误记忆？

回答框架：

> Context 是当前请求里真正发给模型的内容；Memory 是跨任务保存的信息。Memory 必须经过筛选和注入才能变成 Context。不能把所有历史都塞给模型，否则会浪费 token，也可能引入过期信息。

结合 PyAgentCLI：

- Project Memory 存项目偏好。
- Session Summary 存任务摘要。
- `--remember` 显式写入记忆。
- `--compress-memory` 压缩 session。
- `--delete-memory-line` 删除错误记忆。
- `--stale-memory-days` 检查过期记忆。

可以强调：

> 我们把记忆放在 `.pyagent/memory/`，用户可以看到、审查、删除，而不是让 Agent 有不可见的黑箱记忆。

### 6. RAG 和代码检索

面试官可能问：

- RAG 为什么不只是向量检索？
- 代码检索怎么 chunk？
- 为什么要 AST symbol？
- index stale 怎么处理？

回答框架：

> 代码 RAG 不能只靠语义向量。很多时候用户要找的是精确符号、文件名、函数名、依赖关系。PyAgentCLI 采用 FTS 精确检索、AST symbol chunk、import graph 和可选 embedding 的混合方案。

结合 PyAgentCLI：

- SQLite FTS 做本地索引。
- Python AST 提取函数、类、方法。
- JS/TS 支持常见函数、类、箭头函数。
- `@file/@folder/@symbol` 显式注入上下文。
- `search_dependencies` 查询 import graph。
- 文件修改后提示 stale index。

回答亮点：

> 对 coding agent 来说，RAG 的目标不是“召回一段相似文本”，而是给模型足够准确、足够新鲜、足够可控的代码上下文。

### 7. MCP

面试官可能问：

- MCP 解决了什么问题？
- MCP 和普通 Tool Registry 有什么区别？
- MCP 工具如何做安全控制？

回答框架：

> MCP 是一种把外部工具暴露给模型/Agent 的协议。普通 Tool Registry 是本地内置工具；MCP 让工具可以由外部 server 提供。关键是协议统一和工具生态扩展。

结合 PyAgentCLI：

- 实现 stdio MCP client。
- 支持 initialize、tools/list、tools/call。
- 通过 adapter 注册进 ToolRegistry。
- 根据 `readOnlyHint` 映射风险等级。
- 非只读 MCP 工具默认拒绝或高风险处理。

可以强调：

> MCP 扩展的是能力边界，但不能扩展安全边界。外部工具进来之后仍然要走 PyAgentCLI 的 risk policy。

### 8. Skill System

面试官可能问：

- Skill 和 Tool 有什么区别？
- Skill 和 MCP 有什么区别？
- Skill 会不会绕过安全？

回答框架：

> Tool 是可执行能力，Skill 是提示和流程说明。MCP 是外部工具协议，Skill 是本地 prompt guidance。Skill 不能执行工具，也不能绕过审批。

结合 PyAgentCLI：

- `.pyagent/skills/<skill>/skill.toml` 存 metadata。
- `SKILL.md` 存指导文本。
- 根据 trigger 选择 skill。
- 注入任务上下文。
- 明确低优先级，不覆盖用户任务和安全策略。

回答亮点：

> Skill 的价值是复用项目经验，而不是增加隐形权限。

### 9. Browser Tools

面试官可能问：

- Coding Agent 为什么需要浏览器工具？
- 为什么默认不开放外部 URL？
- Playwright 如何接入？

回答框架：

> 前端和本地 web app 调试需要浏览器能力，但浏览器也是高风险入口。PyAgentCLI 先从本地只读 inspection 做起，支持 workspace HTML、localhost、DOM snapshot、selector query，再可选接入 Playwright console log 和 screenshot。

结合 PyAgentCLI：

- `inspect_page` 提取 title 和文本。
- `browser_dom_snapshot` 提取 headings、links、controls。
- `browser_query_selector` 支持 tag、id、class 查询。
- `browser_console_logs` 和 `browser_screenshot` 依赖可选 Playwright。
- 外部 URL 默认拒绝。

可以强调：

> 浏览器工具先做“观察”，再考虑“交互”。点击和输入必须更谨慎，后续需要用户审批和更强限制。

### 10. Eval Harness

面试官可能问：

- Agent 怎么评估？
- 怎么判断任务成功？
- tool-call accuracy 怎么算？
- safety violation 怎么测？

回答框架：

> Agent 不能只看最终回答好不好听，要评估工具调用、文件结果、安全行为和可复现 trace。PyAgentCLI 通过 deterministic eval、本地 coding task、RAG retrieval、trace eval 多维度评估。

结合 PyAgentCLI：

- platform eval 覆盖工具注册、安全、RAG、Memory。
- coding task eval 检查文件是否按预期改变。
- RAG retrieval eval 检查符号、依赖、TS chunk。
- trace eval 检查工具调用序列和 forbidden tools。
- 输出 JSONL report。

回答亮点：

> 对 coding agent 来说，最终文本不是唯一指标。更重要的是有没有调用正确工具、有没有改对文件、有没有越权。

## 04. 一分钟项目介绍

可以这样说：

> 我做了一个 Python 版本地 AI Coding Agent CLI，定位类似 Claude Code / Codex mini。它的核心是一个 ReAct / Function Calling loop，模型不能直接改代码，只能返回工具调用意图，真正执行由本地 ToolRegistry 完成。工具层支持文件读写、局部编辑、shell、搜索、RAG 检索和浏览器 inspection，同时接入路径围栏、危险命令拦截、人工审批和审计日志。
>
> 在基础 loop 之上，我做了 Plan-and-Execute、多 Agent 协作、Memory、MCP、Skill System 和 Eval Harness。Planner 负责拆任务，Executor 按步骤执行，Reviewer 做 gate 和 retry proposal。RAG 方面用 SQLite FTS、AST symbol chunk、import graph 和可选 embedding 做混合检索。评估方面有 task success、tool-call accuracy、safety violation 和 trace eval。
>
> 这个项目让我系统理解了 AI Agent 从模型调用到工具执行、安全控制、上下文工程、多 Agent 协作和效果评估的完整链路。

## 05. 面试高频题清单

必背问题：

1. ReAct 和 Function Calling 的关系是什么？
2. 模型到底会不会执行代码？
3. Tool Call 失败后 Agent 怎么恢复？
4. 为什么要有人类审批？
5. 如何防止 Agent 删除用户文件？
6. ReAct 和 Plan-and-Execute 的区别是什么？
7. Multi-Agent 里 Planner / Executor / Reviewer 怎么分工？
8. Memory 和 Context 的区别是什么？
9. 长上下文满了怎么办？
10. RAG 为什么不只是向量检索？
11. 代码检索为什么要 AST symbol？
12. MCP 解决了什么问题？
13. Skill 和 Tool 的区别是什么？
14. Browser 工具为什么默认只允许 local？
15. Agent Eval 应该评估哪些指标？
16. 怎么计算 tool-call accuracy？
17. 怎么判断 coding task 是否成功？
18. 如何设计 retry proposal？
19. 如何保证 plan 状态不会误判 success？
20. 如果让你继续优化这个项目，你下一步做什么？

## 06. 追问时的回答模板

如果被问实现细节：

> 这个模块我不是只停留在概念上，而是做了完整闭环：数据结构、工具接口、安全策略、持久化、CLI 命令、测试和文档都实现了。

如果被问项目难点：

> 难点不在于调用模型，而在于把模型输出接入真实工程环境时的安全和可控。比如写文件必须有 diff preview，shell 必须审批，RAG index 要提示 stale，Reviewer 要能阻止 skipped step 被误判成功。

如果被问和 LangChain / LangGraph 的区别：

> 我这个项目刻意没有直接用重型框架，而是从底层实现 Agent loop、Tool Registry、Plan Store、Reviewer Gate 和 Eval，这样更能理解 Agent Runtime 的本质。后续也可以把某些模块替换成 LangGraph，但核心边界我已经自己实现过。

如果被问还有什么不足：

> 目前真实模型 eval 和浏览器交互还在增强中。现在已经有 deterministic eval、trace eval、可选 Playwright 工具外壳和 selector query，下一步会做 model-backed eval、浏览器成功路径验证和更完整的本地前端交互审批。

## 07. 学习与复盘路线

建议你后续这样复盘：

1. 先跑通 CLI：
   - `pyagent --help`
   - `pyagent --eval`
   - `pyagent --plan "fix failing tests"`

2. 再围绕简历模块看源码：
   - Agent Loop
   - Tool Registry
   - Safety Policy
   - RAG Indexer
   - Memory
   - Planner / Executor / Reviewer
   - MCP Adapter
   - Eval Runner

3. 然后按模块背面试题。

4. 最后自己讲一遍项目：
   - 架构图
   - 一个任务从输入到工具调用再到 review 的完整链路
   - 一次失败 step 如何被 Reviewer 拦截并生成 retry proposal

## 08. 开发过程问题复盘

这一节专门记录我们开发 PyAgentCLI 过程中遇到的问题，以及这些问题如何反补学习材料。

### 8.1 sandbox 网络权限导致无法 push

现象：

- 普通 `git push` 在 sandbox 中无法解析 GitHub。
- 早期可以用授权网络方式推送。
- 后来权限配置变化，`sandbox_approval` 被设为自动拒绝，无法再申请联网 push。

解决方式：

- 本地继续 commit。
- 用户手动在本机 Terminal 执行 `git push`。
- 文档和最终回复中明确 `main...origin/main [ahead N]` 状态。

面试可讲点：

> 本地 agent 工具必须尊重运行环境权限。不能为了完成任务绕过 sandbox；正确做法是识别权限边界，保持本地状态可恢复，并让用户完成需要外部授权的动作。

### 8.2 Computer Use 不能操作 Terminal

现象：

- 用户安装了 Computer Use 插件。
- 工具能读取 Safari 状态。
- 但操作 Terminal 时返回安全限制：不允许使用 `com.apple.Terminal`。

解决方式：

- 不强行绕过。
- 改为让用户手动执行 `git push`。
- 对 Safari 页面只做结构提炼，不复制全文。

面试可讲点：

> Desktop automation 也要有权限边界。Agent 能看见不代表能操作，能操作不代表应该操作。

### 8.3 Playwright 可选依赖不能影响核心测试

现象：

- Browser console logs 和 screenshot 需要 Playwright。
- 但项目不能强制所有用户安装大体积浏览器依赖。
- 模块级 `pytest.importorskip` 会导致单独运行测试文件时 exit code 5。

解决方式：

- 把 Playwright 放进 optional extra：`.[browser]`。
- 新增 `pyagent --check-browser` 做能力检测。
- 可选测试里把 `importorskip` 放到测试函数内。
- 没装 Playwright 时 skip，不影响核心套件。

面试可讲点：

> 可选能力要做成 graceful degradation。核心 CLI 不依赖浏览器，浏览器成功路径可单独验证。

### 8.4 Browser 工具默认只允许 local

现象：

- 浏览器工具很容易被误用成外部网页抓取工具。
- Coding Agent 的主要需求是本地 HTML / localhost app 调试。

解决方式：

- `inspect_page`、`browser_dom_snapshot`、`browser_query_selector` 都默认拒绝外部 URL。
- 只允许 workspace file、workspace `file://`、localhost、127.0.0.1、::1。
- screenshot 输出限制在 `.pyagent/browser/`。

面试可讲点：

> Browser tool 的第一优先级不是能力最大化，而是安全和任务边界清晰。先做只读 inspection，再考虑交互。

### 8.5 Reviewer gate 防止假成功

现象：

- Plan 执行过程中可能出现某些 step skipped / failed。
- 如果只看最终执行函数返回，容易把计划误标为 success。

解决方式：

- Reviewer 检查所有 step status。
- failed / skipped / cancelled 会 block success。
- 成功 plan 可被 Reviewer 降级为 failed。
- 生成 retry proposal，但不自动执行。

面试可讲点：

> Agent 不应该只靠“最终回答”判断成功。需要引入状态机、复核器和可审计的 gate。

### 8.6 Retry Proposal 只生成建议，不自动执行

现象：

- Agent 如果自动 retry，可能绕过用户审批。
- failed、skipped、cancelled 的处理方式不同。

解决方式：

- failed -> `retry_step`
- skipped -> `user_decision`
- cancelled -> `resume_plan`
- proposal 写入 review 和 handoff，但不调用工具。

面试可讲点：

> 自动化建议和自动化执行要分开。尤其是 coding agent，建议可以自动生成，但执行必须保留审批边界。

### 8.7 RAG index stale 问题

现象：

- 用户修改文件后，SQLite FTS index 可能过期。
- 如果 Agent 继续相信旧索引，就可能基于错误上下文行动。

解决方式：

- `CodeIndexer.stale_paths()` 检查索引新鲜度。
- plan / execute / retry 前提示 stale warning。
- 不自动重建索引，让检索上下文变化保持显式。

面试可讲点：

> RAG 的问题不只是召回率，还包括上下文新鲜度和可审计性。

### 8.8 Memory 需要可审查和可删除

现象：

- 长期记忆如果不可见，会变成黑箱。
- 错误记忆会污染后续任务。

解决方式：

- Project memory 存在 `.pyagent/memory/project.md`。
- 提供 `--memory` 查看。
- 提供 `--delete-memory-line` 删除。
- 提供 `--stale-memory-days` 检查过期记忆。

面试可讲点：

> Memory 不是越多越好，而是要可控、可见、可删除。

### 8.9 Skill 不能变成隐形权限

现象：

- Skill 很容易被误解为插件或工具。
- 如果 Skill 能执行工具，就会绕开 Tool Registry 安全策略。

解决方式：

- Skill 只作为 prompt guidance。
- 根据 trigger 选择并注入。
- 明确不执行工具、不覆盖用户任务、不绕过审批。

面试可讲点：

> Skill 是知识和流程复用，不是能力授权。

### 8.10 Trace Eval 从静态检查走向 Agent 行为评估

现象：

- 早期 eval 主要检查函数、工具注册和模拟 case。
- 但 Agent 真正难评估的是行为链路：有没有调用正确工具、有没有 forbidden tool、最终结果是否包含关键信息。

解决方式：

- 在 Agent loop 中捕获 trace。
- trace 包含 user、assistant tool_call、tool observation、final。
- eval 根据 trace 计算 expected tools、forbidden tools、final contains。

面试可讲点：

> Agent eval 不能只看输出文本，要看行为轨迹。Trace 是连接可复现评估和真实 Agent 行为的关键。

## 09. 模块化学习清单

为了更像一份知识库，可以把 PyAgentCLI 拆成下面这些专题复习。

### 专题 A：Agent 内核

- `AgentLoop` 如何组织消息？
- tool call 如何进入 ToolRegistry？
- max steps 如何防止死循环？
- trace 如何记录一次 Agent run？

### 专题 B：工具和安全

- tool schema 如何暴露给模型？
- READ / WRITE / EXECUTE / NETWORK / CRITICAL 如何分级？
- path guardrail 如何防止越界？
- diff preview 为什么重要？

### 专题 C：RAG 和上下文工程

- FTS 和向量检索如何互补？
- AST symbol chunk 解决什么问题？
- `@symbol` 和 `search_index` 有什么区别？
- stale index 为什么不能自动忽略？

### 专题 D：Memory

- project memory 和 session summary 如何分工？
- memory 什么时候注入？
- 为什么要支持删除和 stale 检查？

### 专题 E：Plan / Multi-Agent / Reviewer

- Planner 输出什么？
- Executor 如何按 step 执行？
- Reviewer gate 如何影响最终状态？
- retry proposal 为什么不自动执行？

### 专题 F：MCP / Skill / Browser

- MCP 是工具协议，Skill 是 prompt guidance。
- Browser tool 为什么 local-first？
- Playwright optional 如何设计？

### 专题 G：Eval

- deterministic eval 检查什么？
- coding task eval 检查什么？
- trace eval 解决什么问题？
- safety violation 如何衡量？

## 10. 参考来源

本文参考了 PaiCLI 学习路线和相关面试/简历文章的结构与主题方向，但所有项目表述均改写为 PyAgentCLI 的实现：

- https://paicoding.com/paicli-learning-path
- https://paicoding.com/column/17/14
- https://paicoding.com/article/detail/2613300022282240
- https://paicoding.com/memory-context
- https://paicoding.com/article/detail/2614100053739520
