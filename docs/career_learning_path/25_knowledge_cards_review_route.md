# 25 知识库卡片和复习路线

这一篇是 PyAgentCLI 学习路线 v2 的收口文档。

前面 24 篇已经分别解决：

- 怎么跑项目。
- 怎么理解核心模块。
- 怎么写简历。
- 怎么应对面试追问。
- 怎么复盘开发问题。
- 怎么口播项目。

第 25 篇要解决最后一个问题：

> 这么多文档，怎么变成可以长期复习、面试前速查、Obsidian/OCDN 可沉淀的知识库？

## 最终知识库结构

推荐在 Obsidian/OCDN 中保留这个结构：

```text
PyAgentCLI/
  00 学习路线总览
  01 先跑通项目
  02-14 实战篇
  15 简历篇
  16-22 面试篇
  23 开发复盘
  24 项目口播
  25 复习路线
```

如果你想更像知识库，可以按主题重排：

```text
PyAgentCLI/
  A 项目总览
  B Agent Runtime
  C Tool Safety
  D Context Engineering
  E Plan Multi-Agent Reviewer
  F MCP Browser Skill
  G Eval Productization
  H Resume Interview
  I Pitfalls Review
```

但源码 repo 里建议继续保持数字顺序，因为最适合从 0 到 1 学。

## 01-25 章节地图

### 总览篇

| 章节 | 用途 | 面试价值 |
| --- | --- | --- |
| 00 学习路线总览 | 看全局路线 | 知道项目整体叙事 |
| 01 先跑通 PyAgentCLI | 安装、自检、演示 | 证明项目能跑 |

### 实战篇

| 章节 | 核心问题 | 面试价值 |
| --- | --- | --- |
| 02 ReAct 和 Tool Calling | 模型怎么调用工具 | 解释 Agent Loop |
| 03 Plan-and-Execute / DAG | 复杂任务怎么拆 | 解释计划、恢复、Reviewer |
| 04 Memory 系统 | 记忆怎么管理 | 区分 Memory 和 Context |
| 05 RAG 代码检索 | 代码上下文怎么找 | 解释 RAG 不只是向量 |
| 06 Tool Call、HITL、安全策略 | 怎么防越权 | 安全高频追问 |
| 07 Multi-Agent | 角色怎么协作 | Planner / Executor / Reviewer |
| 08 Browser Tools | 浏览器能力边界 | local-first、Playwright optional |
| 09 接入 MCP | 外部工具怎么接 | MCP 不绕过安全 |
| 10 Prompt / Skill | prompt 怎么治理 | Skill 不是工具 |
| 11 多模型适配 | 模型怎么切换 | LLMClient、fallback、eval |
| 12 产品化 | CLI 怎么像产品 | workspace、runtime state、release |
| 13 Eval Harness | 怎么证明有效 | trace eval、forbidden tools |
| 14 未来扩展 | 后续路线 | 不过度包装 |

### 简历和面试篇

| 章节 | 用途 | 面试价值 |
| --- | --- | --- |
| 15 简历篇 | 写项目 bullet | 把项目放进简历 |
| 16 ReAct / Plan / Multi-Agent | 面试第一组 | Agent loop 和任务拆解 |
| 17 Memory / RAG / Context | 面试第二组 | 上下文工程 |
| 18 Tool / HITL / Safety | 面试第三组 | 安全边界 |
| 19 MCP / Browser | 面试第四组 | 外部工具和浏览器 |
| 20 Prompt / Skill | 面试第五组 | Prompt governance |
| 21 CLI / Git / Runtime API | 面试第六组 | 产品化和未来 API |
| 22 多模型 / 成本 | 面试第七组 | 模型适配和成本 |
| 23 开发复盘 | 真实踩坑 | 工程判断 |
| 24 项目口播 | 15/30/60 秒介绍 | 开场表达 |
| 25 复习路线 | 速查和计划 | 面试前导航 |

## 核心知识卡片

下面这些卡片可以直接放进 Obsidian。

### 卡片 1：PyAgentCLI 是什么

一句话：

> PyAgentCLI 是一个 Python 版本地 AI Coding Agent CLI，把模型 tool calling 安全接入本地开发环境。

关键词：

- local CLI。
- mini Claude Code。
- Agent Runtime。
- Tool Calling。
- Safety。
- RAG。
- Memory。
- Eval。

关联章节：

- 00。
- 01。
- 12。
- 24。

### 卡片 2：Agent Loop

一句话：

> Agent Loop 是“模型提出动作，本地 runtime 执行动作，再把 observation 返回模型”的循环。

流程：

```text
User Goal
  -> LLMClient
  -> LLMResponse
  -> ToolCall
  -> ToolRegistry
  -> ToolResult
  -> Observation
  -> LLMClient
  -> Final
```

关键词：

- ReAct。
- Function Calling。
- ToolCall。
- Observation。
- max_steps。

关联章节：

- 02。
- 16。
- 18。

### 卡片 3：Tool Call 不等于执行权

一句话：

> 模型只输出结构化调用意图，真实执行由 ToolRegistry、安全策略、审批和审计控制。

必须会说：

> Function Calling 不是模型在执行函数。

关联章节：

- 02。
- 06。
- 18。

### 卡片 4：Safety / HITL

一句话：

> 安全不能靠 prompt，必须在工具执行层实现。

关键机制：

- RiskLevel。
- workspace path guardrail。
- sensitive path denylist。
- command denylist。
- diff preview。
- ApprovalHandler。
- AuditLogger。
- non-interactive deny。

关联章节：

- 06。
- 18。
- 23。

### 卡片 5：RAG 代码检索

一句话：

> 代码 RAG 不只是向量检索，还需要路径、符号、全文、依赖和新鲜度。

关键机制：

- SQLite FTS。
- chunk。
- Python AST symbol。
- JS/TS symbol。
- import graph。
- optional embedding。
- HybridRetriever。
- stale warning。
- `@file/@folder/@symbol`。

关联章节：

- 05。
- 17。

### 卡片 6：Memory

一句话：

> Memory 是可见、可审查、可删除的跨任务项目上下文，不是黑箱长期记忆。

关键命令：

```bash
pyagent --memory
pyagent --remember "..."
pyagent --compress-memory
pyagent --delete-memory-line 3
pyagent --stale-memory-days 30
```

关联章节：

- 04。
- 17。

### 卡片 7：Plan-and-Execute

一句话：

> `--plan` 无副作用预览，`--execute-plan` 审批后执行，失败后可以 resume/retry/skip。

关键命令：

```bash
pyagent --plan "..."
pyagent --execute-plan "..."
pyagent --show-plan <plan_id>
pyagent --resume-plan <plan_id>
pyagent --retry-step <plan_id> <step_id>
pyagent --skip-step <plan_id> <step_id>
```

关联章节：

- 03。
- 16。
- 21。

### 卡片 8：Multi-Agent

一句话：

> Multi-Agent 的价值不是角色数量，而是 Planner、Executor、Reviewer 的职责边界。

角色：

- Planner：生成结构化计划。
- Executor：执行 approved step。
- Reviewer：复核状态、审计和 diff。

边界：

> 当前是串行角色工作流，不是并发 Agent swarm。

关联章节：

- 07。
- 16。

### 卡片 9：Reviewer Gate

一句话：

> Reviewer 不只总结结果，而是用 step status、audit log 和 git diff 防止假成功。

关键机制：

- failed/skipped/cancelled block。
- git diff summary。
- changed-file risk scoring。
- suggested tests。
- retry proposal。

关联章节：

- 03。
- 07。
- 21。
- 23。

### 卡片 10：MCP

一句话：

> MCP 扩展外部工具生态，但不能绕过 PyAgentCLI 的安全链路。

链路：

```text
MCP server
  -> adapter
  -> risk mapping
  -> ToolRegistry
  -> Safety / Approval / Audit
```

关联章节：

- 09。
- 19。

### 卡片 11：Browser Tools

一句话：

> Browser Tools 当前是 local-first，服务 workspace HTML 和 localhost 调试，不是任意外网代理。

边界：

- workspace file。
- localhost。
- optional Playwright。
- screenshot 写到 `.pyagent/browser/`。
- external HTTP/HTTPS 默认拒绝。

关联章节：

- 08。
- 19。

### 卡片 12：Skill

一句话：

> Skill 是 prompt-only guidance，不是工具、插件或权限系统。

关键点：

- trigger 匹配。
- SKILL.md 注入。
- 不执行工具。
- 不授予权限。
- 不覆盖用户任务。

关联章节：

- 10。
- 20。

### 卡片 13：LLM Client / 多模型

一句话：

> 多模型适配不是罗列 provider，而是用 LLMClient 协议把 Agent Loop 和具体模型 SDK 解耦。

关键机制：

- Message。
- ToolCall。
- LLMResponse。
- OpenAI-compatible client。
- LocalFallbackClient。
- role-specific model。
- `--check-model`。
- `--eval-compare-models`。

关联章节：

- 11。
- 22。

### 卡片 14：Eval

一句话：

> Agent Eval 要评估行为轨迹，而不是只看最终回答。

关键指标：

- expected tools。
- forbidden tools。
- final output。
- RAG hit。
- browser assertion。
- reviewer gate。
- real model trace opt-in。

关联章节：

- 13。
- 22。

### 卡片 15：CLI 产品化

一句话：

> 产品化不是 argparse，而是让 Agent 能被安装、运行、恢复、复盘、评估和发布。

关键机制：

- `pyagent` console script。
- task / REPL mode。
- `--workspace`。
- `.pyagent/` runtime state。
- release checklist。
- packaging tests。

关联章节：

- 12。
- 21。

### 卡片 16：开发复盘

一句话：

> 真实项目能力来自处理约束，而不是只实现 happy path。

典型坑：

- 长对话上下文压缩。
- GitHub push 和 sandbox。
- Computer Use 权限。
- 不存在模型名。
- RAG stale。
- Memory 黑箱。
- Reviewer 假成功。
- optional dependency。

关联章节：

- 23。

## 面试前 30 分钟速查

如果面试前只剩 30 分钟，按这个顺序看：

1. [24 一分钟项目介绍和高频追问](24_pitch_and_followups_v2.md)
2. [18 Tool Call、HITL、安全策略](18_interview_tool_hitl_safety.md)
3. [17 Memory、RAG、长上下文工程](17_interview_memory_rag_context.md)
4. [16 ReAct、Plan-and-Execute、Multi-Agent](16_interview_react_plan_multi_agent.md)
5. [23 开发复盘](23_development_pitfalls_review.md)

只背 5 句话：

1. PyAgentCLI 是 Python 版本地 AI Coding Agent CLI，重点是可控 Agent Runtime。
2. 模型只输出 ToolCall，真实执行由本地 ToolRegistry、安全策略、审批和审计控制。
3. RAG 不只是向量检索，代码场景还需要符号、路径、全文、依赖和新鲜度。
4. Reviewer 不信最终回答，会看 step status、audit log 和 git diff 防止假成功。
5. 当前是本地 CLI v0.1，Runtime API、GitHub automation、TUI、多模态和 cost dashboard 是后续路线。

## 7 天复习计划

### Day 1：跑通项目和口播

看：

- 01。
- 24。

任务：

- 跑 `pyagent --help`。
- 跑 `pyagent --eval`。
- 背 15 秒、30 秒、60 秒版本。

### Day 2：Agent Loop 和 Tool Safety

看：

- 02。
- 06。
- 18。

任务：

- 画 Agent Loop。
- 讲清 ToolCall 不等于执行。
- 背 SafetyPolicy 链路。

### Day 3：RAG 和 Memory

看：

- 04。
- 05。
- 17。

任务：

- 讲清 RAG vs Memory。
- 讲清 `@file/@folder/@symbol`。
- 准备 stale index 和 memory 黑箱两个例子。

### Day 4：Plan、Multi-Agent、Reviewer

看：

- 03。
- 07。
- 16。

任务：

- 讲清 Planner / Executor / Reviewer。
- 背 `--plan` 无副作用。
- 讲 Reviewer gate。

### Day 5：MCP、Browser、Skill、多模型

看：

- 08。
- 09。
- 10。
- 19。
- 20。
- 22。

任务：

- 讲 MCP 不绕过安全。
- 讲 Browser local-first。
- 讲 Skill 不是 Tool。
- 讲 `LLMClient` 和 `--check-model`。

### Day 6：Eval 和产品化

看：

- 12。
- 13。
- 21。

任务：

- 讲 eval 为什么看 trace。
- 讲 CLI 产品化。
- 讲 Runtime API 下一步。

### Day 7：复盘和模拟面试

看：

- 23。
- 24。
- 25。

任务：

- 讲 3 个开发坑。
- 练一次 60 秒项目介绍。
- 让自己按 Safety、RAG、Plan、Eval 四条线追问。

## 简历 bullet 到章节映射

### Bullet 1：AI Coding Agent CLI

推荐写法：

> 从 0 到 1 构建 Python 版本地 AI Coding Agent CLI，支持 ReAct、Function Calling、本地工具执行、CLI/REPL 双模式和 `.pyagent/` 运行态持久化。

对应章节：

- 01。
- 02。
- 12。
- 21。
- 24。

### Bullet 2：Tool Safety

推荐写法：

> 设计 ToolRegistry、SafetyPolicy、ApprovalHandler 和 AuditLogger，按 READ/WRITE/EXECUTE/NETWORK/CRITICAL 风险分级控制文件写入、shell 执行、路径围栏、diff preview 和审计日志。

对应章节：

- 06。
- 18。

### Bullet 3：RAG / Memory / Context

推荐写法：

> 构建代码上下文工程能力，支持 `@file/@folder/@symbol` 显式注入、SQLite FTS、AST symbol chunk、import graph、可选 embedding、Project Memory、session summary、压缩、删除和 stale 检查。

对应章节：

- 04。
- 05。
- 17。

### Bullet 4：Plan / Reviewer / Multi-Agent

推荐写法：

> 实现 Planner / Executor / Reviewer 工作流，支持无副作用计划预览、审批后执行、step 状态持久化、resume/retry/skip、git diff review、changed-file risk scoring 和 retry proposal。

对应章节：

- 03。
- 07。
- 16。
- 21。

### Bullet 5：MCP / Browser / Skill

推荐写法：

> 实现 MCP v0.1 adapter、local-first Browser Tools 和 Skill System，将外部工具、浏览器观察与本地 prompt guidance 纳入统一安全边界。

对应章节：

- 08。
- 09。
- 10。
- 19。
- 20。

### Bullet 6：Eval / Trace / Multi-model

推荐写法：

> 构建 Eval Harness 和 Trace Eval，评估 expected/forbidden tools、RAG 命中、browser assertion、reviewer gate、真实模型 trace 和多模型 comparison，并通过 opt-in 控制外部模型成本。

对应章节：

- 11。
- 13。
- 22。

## 面试追问到章节映射

| 面试官问题 | 先看章节 |
| --- | --- |
| ReAct 和 Function Calling 怎么结合？ | 02、16 |
| 模型会不会直接执行代码？ | 02、18 |
| 怎么防止乱改文件？ | 06、18 |
| Shell 怎么安全执行？ | 06、18 |
| RAG 为什么不只是向量？ | 05、17 |
| Memory 和 Context 区别？ | 04、17 |
| Multi-Agent 有什么价值？ | 07、16 |
| Reviewer 怎么防假成功？ | 03、07、21 |
| MCP 是什么？ | 09、19 |
| Browser Tools 边界？ | 08、19 |
| Skill 是工具吗？ | 10、20 |
| Eval 怎么证明有效？ | 13、22 |
| CLI 怎么产品化？ | 12、21 |
| Runtime API 下一步？ | 14、21 |
| 成本怎么控制？ | 11、22 |
| 开发中遇到什么坑？ | 23 |
| 项目怎么介绍？ | 24 |

## 模块关系图

```text
User
  |
  v
CLI / REPL
  |
  +-- task mode
  +-- plan mode
  +-- eval mode
  +-- memory / index / browser check
  |
  v
Agent Runtime
  |
  +-- LLMClient
  +-- AgentLoop
  +-- Planner / Executor / Reviewer
  |
  v
Tool Layer
  |
  +-- ToolRegistry
  +-- Filesystem / Shell / Search
  +-- Browser / MCP
  |
  v
Safety Layer
  |
  +-- SafetyPolicy
  +-- ApprovalHandler
  +-- AuditLogger
  |
  v
Context Layer
  |
  +-- RAG
  +-- Memory
  +-- Skill
  |
  v
Evidence Layer
  |
  +-- .pyagent/plans
  +-- .pyagent/reviews
  +-- .pyagent/audit.log.jsonl
  +-- .pyagent/eval_reports
```

## 最后一页速记

如果只能记一页，就记这个：

```text
PyAgentCLI = Python local AI Coding Agent CLI

Core:
  LLM ToolCall -> ToolRegistry -> Safety -> Approval -> Audit -> Observation

Context:
  @file/@folder/@symbol + RAG + Memory + Skill

Execution:
  --plan no side effect
  --execute-plan with approval
  resume / retry / skip

Review:
  step status + audit log + git diff

Eval:
  expected tools + forbidden tools + trace + reviewer gate

Product:
  pyagent CLI + .pyagent runtime + release checklist

Boundary:
  local CLI v0.1
  Runtime API / GitHub automation / TUI / multimodal / cost dashboard are future work
```

## 学习路线 v2 完成标志

做到这里，v2 文档体系已经完成第一版闭环：

- 能跑项目。
- 能读源码。
- 能讲模块。
- 能写简历。
- 能答面试。
- 能复盘开发坑。
- 能做 15/30/60 秒口播。
- 能按知识卡片复习。

下一步不再是继续扩文档，而是进入两个方向：

1. 同步到 Obsidian/OCDN。
2. 回到代码项目继续 Phase 2。

Phase 2 推荐顺序：

```text
Runtime event model
  -> CLI JSONL event output
  -> Git status/diff read-only tool
  -> commit proposal with approval
  -> token/cost tracking
  -> Runtime API server
  -> TUI / dashboard
```
