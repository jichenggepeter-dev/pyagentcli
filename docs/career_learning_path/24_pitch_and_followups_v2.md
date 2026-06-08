# 24 一分钟项目介绍和高频追问

这一篇是 PyAgentCLI 的口播训练稿。

前面 23 篇已经把项目拆得很细：

- ReAct。
- Tool Calling。
- Safety。
- RAG。
- Memory。
- Plan-and-Execute。
- Multi-Agent。
- MCP。
- Browser。
- Skill。
- Eval。
- CLI 产品化。
- 多模型适配。
- 开发复盘。

但面试现场不会让你从第 1 篇讲到第 23 篇。

你需要先用很短的话把项目讲清楚，然后根据面试官追问展开。

这篇就是为了训练：

```text
15 秒讲得准
30 秒讲得像项目
60 秒讲得像系统
追问时能落到源码和边界
```

## 口播总原则

讲 PyAgentCLI 时，最容易犯两个错误：

1. 讲太大。

   比如：

   ```text
   我做了一个完整 Claude Code。
   ```

   这样会被追问穿。

2. 讲太散。

   比如：

   ```text
   我做了 ReAct、RAG、Memory、MCP、Browser、Eval...
   ```

   听起来像功能堆叠。

更好的讲法是：

> 我做的是一个本地 AI Coding Agent CLI，重点是把模型 tool calling 接到真实开发环境，并用安全审批、上下文工程、计划执行、复核和评估把它变成可控的 Agent Runtime。

这句话有 4 个关键词：

- 本地 CLI。
- tool calling。
- 真实开发环境。
- 可控 Agent Runtime。

## 15 秒版本

适合：

- 面试开场。
- 简历项目快速介绍。
- 对方只问“这个项目是什么”。

口播：

> PyAgentCLI 是我从 0 到 1 实现的 Python 版本地 AI Coding Agent CLI，类似一个 mini Claude Code。它让模型通过受控 tool calling 在本地代码仓库里读文件、改代码、跑命令、做 RAG 检索、记忆、计划执行、复核和评估。

这版只回答：

```text
是什么
给谁用
做什么
```

不要在 15 秒里解释所有模块。

## 30 秒版本

适合：

- 简历项目展开。
- 面试官让你“多讲一点”。
- HR 或非深度技术面。

口播：

> PyAgentCLI 是一个 Python 版本地 AI Coding Agent CLI，定位类似 Claude Code / Codex mini。核心是 ReAct 和 Function Calling loop：模型不会直接改文件，只会返回工具调用意图，真正执行由本地 ToolRegistry 控制。工具层支持文件读写、局部编辑、shell、搜索、RAG、Memory 和浏览器检查，同时接入 workspace 路径围栏、危险命令拦截、人工审批和审计日志。项目重点不是简单调模型，而是把 Agent 做成安全、可恢复、可评估的本地开发者工具。

这版要让对方听懂：

- 你做的是 Agent CLI。
- 模型不直接执行。
- 有工具和安全层。
- 有工程化目标。

## 60 秒版本

适合：

- 技术面试。
- 面试官问“完整讲讲你的项目”。
- 你想主动展示系统性。

口播：

> 我做了一个 Python 版本地 AI Coding Agent CLI，叫 PyAgentCLI，定位类似 mini Claude Code。它的底层是 ReAct / Function Calling loop，模型输入任务后可以返回结构化 ToolCall，但不会直接操作本地环境；真正执行由 ToolRegistry 完成，所有文件、命令、搜索、浏览器和 MCP 工具都会经过风险分级、路径围栏、审批和审计。
>
> 在基础 loop 上，我做了几层 Agent Runtime 能力。第一是上下文工程：支持 `@file/@folder/@symbol` 显式注入、SQLite FTS / AST symbol / import graph 的 RAG 检索，以及可查看、可删除、可压缩的 Project Memory。第二是复杂任务执行：`--plan` 只生成无副作用计划，`--execute-plan` 审批后串行执行，PlanStore 持久化 step 状态，失败后可以 resume、retry、skip。第三是 Reviewer 和 Eval：Reviewer 会看 step status、audit log 和 git diff，防止假成功；Eval Harness 会检查工具调用、禁止工具、RAG 命中、trace 和 reviewer gate。
>
> 当前 v0.1 已经完成本地 CLI runtime、MCP v0.1、Skill、Browser capability check、多模型配置和 release checklist；Runtime API、GitHub PR 自动化、TUI、多模态和 cost dashboard 是下一阶段增强。

这版必须讲出边界：

```text
已完成什么
还没完成什么
为什么这个顺序合理
```

## 90 秒版本

适合：

- 项目深挖开场。
- 面试官明显对 Agent 工程感兴趣。
- 你想把简历 bullet 全部串起来。

口播：

> PyAgentCLI 是我从 0 到 1 做的 Python 版本地 AI Coding Agent CLI。它不是一个聊天壳，而是一个本地 Agent Runtime。用户可以通过 `pyagent` 在 workspace 里运行任务、进入 REPL、生成计划、执行计划、建立 RAG index、管理 memory、跑 eval、检查模型和浏览器能力。
>
> 核心链路是模型输出 ToolCall，本地 runtime 执行。模型只负责生成工具名和参数，不能直接读写文件或执行 shell。ToolRegistry 会根据工具 risk level 走 SafetyPolicy，READ 默认允许，WRITE/EXECUTE 需要 preview 和人工审批，危险命令和 `.env/.git/.venv` 等敏感路径会被拒绝，所有调用都会写 audit log。
>
> 为了让 coding task 不只是一次 ReAct，我实现了 Plan-and-Execute：Planner 生成结构化 PlanPreview，Executor 按 step contract 执行，Reviewer 读取 PlanRun、audit log 和 git diff 生成 gate decision 和 retry proposal。上下文方面，项目有 RAG、Memory 和 Skill：RAG 不只是向量检索，还包括 SQLite FTS、Python AST symbol、JS/TS symbol、import graph 和可选 embedding；Memory 是可见可删除的本地项目记忆；Skill 是 prompt-only guidance，不授予权限。
>
> 评估方面，我做了 Eval Harness 和 Trace Eval，检查 expected tools、forbidden tools、final output、RAG retrieval 和 reviewer proposal。产品化方面，有 `pyagent` console script、`.pyagent/` 本地运行态、packaging tests 和 release checklist。当前我会诚实讲它是本地 CLI v0.1，不是完整云平台；Runtime API、GitHub automation、TUI、多模态和成本仪表盘是后续路线。

## 技术面试推荐版本

如果只允许讲一次，推荐背这个 45-60 秒版本：

> PyAgentCLI 是我从 0 到 1 实现的 Python 版本地 AI Coding Agent CLI，定位类似 mini Claude Code。核心是 ReAct / Function Calling loop：模型只输出结构化 ToolCall，真正执行由本地 ToolRegistry 控制，并经过 SafetyPolicy、ApprovalHandler 和 AuditLogger，所以文件写入、shell 命令、MCP、Browser 等工具都受 workspace 路径围栏、风险分级、diff preview、人工审批和审计保护。
>
> 在 loop 之上，我做了上下文和任务执行能力：RAG 支持 SQLite FTS、AST symbol chunk、import graph 和 `@file/@folder/@symbol` 注入；Memory 是可查看、可删除、可压缩的项目记忆；Plan-and-Execute 支持无副作用 `--plan`、审批后执行、resume、retry、skip；Reviewer 会读取 step status、audit log 和 git diff 防止假成功；Eval Harness 会检查工具调用、禁止工具、RAG 命中和 trace。当前它是本地 CLI v0.1，Runtime API、GitHub PR 自动化和 cost dashboard 是下一阶段增强。

## 产品经理面试版本

如果对方更偏产品或 AI Agent PM，可以这样说：

> PyAgentCLI 是一个面向开发者的本地 AI Coding Agent CLI。它解决的问题不是“让模型回答代码问题”，而是让模型在本地代码仓库中安全地执行开发任务。用户可以让 Agent 读代码、检索上下文、生成计划、改文件、跑命令、复核结果和产出 eval report。产品设计上我把风险动作显式化：计划先 preview，写文件有 diff，shell 有危险命令拦截，非交互模式默认拒绝审批动作，所有行为都有 audit log。这样 Agent 从黑箱助手变成一个可控、可复盘、可评估的开发者工具。

产品版本重点：

- 用户是谁。
- 解决什么痛点。
- 为什么安全和可控是产品价值。
- 如何证明结果。

## 后端工程面试版本

如果对方偏后端 / 平台，可以这样说：

> PyAgentCLI 可以看成本地 Agent Runtime 的 CLI 入口。它把模型、工具、状态和审计拆成清晰边界：LLMClient 负责模型适配，ToolRegistry 负责工具 schema 和执行入口，SafetyPolicy/Approval/Audit 控制副作用，PlanStore 持久化计划状态，ProjectMemory 和 RAG 管理上下文，EvalRunner 做行为评估。CLI 只是第一层 consumer，未来 Runtime API 可以复用 `run_agent_task`、`plan_task`、`execute_planned_task`、`run_evals` 这些 service function，把 run event stream 暴露给 TUI、Web dashboard 或后台 worker。

后端版本重点：

- 分层。
- 状态。
- 边界。
- 可观测。
- 未来 API。

## AI Agent 岗位版本

如果岗位明确是 AI Agent / Agent Infra，可以这样说：

> 这个项目完整覆盖了 Agent Runtime 的核心链路：ReAct loop、tool calling、tool schema、tool execution、observation feedback、context injection、memory、RAG、planner/executor/reviewer handoff、MCP adapter、browser tools、trace eval 和 reviewer gate。我的重点不是调一个模型，而是把模型输出的动作接入真实本地环境，并用安全策略、审批、审计、恢复和评估保证行为可控。

Agent 岗版本重点：

- runtime。
- tool calling。
- context engineering。
- safety。
- eval。

## 高频追问地图

面试官通常会从这 8 条线追：

```text
项目定位
  -> 为什么做 CLI，不做 web app？

Agent Loop
  -> ReAct 和 Function Calling 怎么结合？

Tool Safety
  -> 怎么防止乱改文件和乱跑命令？

Context
  -> RAG 和 Memory 怎么做？怎么防 stale？

Plan / Multi-Agent
  -> Planner、Executor、Reviewer 怎么协作？

Eval
  -> 怎么证明 Agent 真的完成目标？

Productization
  -> CLI 怎么发布、恢复、复盘？

Boundary
  -> 当前没做什么？下一步是什么？
```

你要做的是：

> 每条线都用一句话先答，再落到 PyAgentCLI 的源码、命令和边界。

## 高频追问 01：为什么做 CLI，不做 Web？

一句话答案：

> 因为 Coding Agent 的第一使用场景是在本地 workspace 里读写文件、跑命令和复盘 diff，CLI 是最直接、最低摩擦、最贴近开发者工作流的入口。

展开：

- CLI 可以直接绑定当前 workspace。
- 更适合本地文件和 shell。
- 更容易接入 git diff。
- 更容易保留 `.pyagent/` runtime state。
- Web dashboard 可以作为后续 runtime API consumer。

边界：

> 当前是本地 CLI v0.1，不是云端 Agent 平台。

## 高频追问 02：模型会不会直接执行代码？

一句话答案：

> 不会。模型只返回 ToolCall，真正执行由本地 runtime 控制。

展开：

```text
Model ToolCall
  -> AgentLoop
  -> ToolRegistry
  -> SafetyPolicy
  -> ApprovalHandler
  -> Tool execution
  -> AuditLogger
  -> observation back to model
```

可补源码：

```text
src/pyagentcli/agent/loop.py
src/pyagentcli/tools/registry.py
src/pyagentcli/safety/policy.py
src/pyagentcli/safety/approval.py
src/pyagentcli/safety/audit_log.py
```

## 高频追问 03：怎么防止 Agent 乱改文件？

一句话答案：

> 通过 workspace 路径围栏、敏感路径拒绝、风险分级、diff preview、人工审批和审计日志控制。

展开：

- 所有路径必须 resolve 到 workspace 内。
- `.env`、`.git`、`.venv`、`node_modules` 等拒绝。
- `write_file`、`edit_file` 是 WRITE risk。
- 审批前展示 diff preview。
- 非交互模式默认拒绝审批动作。
- audit log 记录成功、失败、拒绝和 preview failure。

一句收束：

> 模型可以建议修改，但不能绕过本地安全链路。

## 高频追问 04：Shell 命令怎么管？

一句话答案：

> shell 是 EXECUTE risk，会先经过危险命令检查，再进入审批和审计。

展开：

- 拦截危险模式。
- 审批后执行。
- stdout/stderr 返回 observation。
- 失败也写 audit。
- 非交互模式下不能自动批准。

可以补：

> 当前不是给模型一个无限终端，而是给它一个受控 shell 工具。

## 高频追问 05：RAG 为什么不只用向量库？

一句话答案：

> 代码检索需要精确符号、路径和依赖关系，不能只靠语义向量。

展开：

PyAgentCLI RAG 包括：

- 文件遍历。
- chunk。
- SQLite FTS。
- Python AST symbol chunk。
- JS/TS symbol chunk。
- Python import graph。
- optional embedding。
- HybridRetriever。
- `@file/@folder/@symbol` 显式注入。

边界：

> 当前是本地轻量 RAG，不是大规模代码搜索平台。

## 高频追问 06：Memory 和 RAG 有什么区别？

一句话答案：

> RAG 检索当前代码库事实，Memory 保存跨任务偏好和历史总结。

展开：

RAG：

- 来自文件。
- 关注当前代码事实。
- 需要 index freshness。

Memory：

- 来自用户或 session。
- 关注偏好、历史和项目约定。
- 可能 stale。
- 可查看、删除、压缩。

收束：

> Memory 不能覆盖当前用户任务，RAG 也不能替代显式上下文。

## 高频追问 07：Planner、Executor、Reviewer 为什么要分开？

一句话答案：

> 因为计划、执行和复核是三种不同职责，混在一个 loop 里容易失控。

展开：

- Planner：只生成 PlanPreview，不执行工具。
- Executor：按 approved step contract 执行。
- Reviewer：检查 step status、audit log、git diff，给 gate decision。

边界：

> 当前是串行角色工作流，不是并发 Agent swarm。

## 高频追问 08：Reviewer 怎么防止假成功？

一句话答案：

> 它不只看最终回答，而是看 step status、audit log 和 git diff。

展开：

- failed / skipped / cancelled 会 block。
- git diff summary 展示真实改动。
- changed-file risk scoring 提示高风险文件。
- suggested tests 给验证建议。
- retry proposal 给恢复路径。

收束：

> Agent 说完成不等于任务完成，Reviewer 要看证据。

## 高频追问 09：Eval 怎么做？

一句话答案：

> Eval 不只看最终文本，而是评估工具调用、禁止工具、RAG 命中、trace 和 reviewer gate。

展开：

Eval 层次：

- platform eval。
- coding task eval。
- RAG retrieval eval。
- browser assertion eval。
- trace eval。
- reviewer eval。
- real model trace eval。
- model comparison eval。

边界：

> 默认 eval 不调用真实模型；真实模型 eval 需要 `--eval-real-model` 或 `--eval-compare-models` 显式开启。

## 高频追问 10：MCP 在这里做什么？

一句话答案：

> MCP 用来接外部工具生态，但接入后仍然必须映射回 PyAgentCLI 的安全、审批和审计链路。

展开：

- MCP server 来自 `pyagent.toml`。
- adapter 注册工具。
- risk mapping。
- preview。
- ToolRegistry 执行。
- SafetyPolicy / Approval / Audit。

收束：

> MCP 是扩展工具，不是绕过权限。

## 高频追问 11：Skill 是工具吗？

一句话答案：

> 不是。Skill 是 prompt-only workflow guidance，不执行工具、不授予权限。

展开：

Skill：

- 存在 `.pyagent/skills/<skill>/`。
- 有 trigger。
- 注入 SKILL.md 内容。
- 限制数量和长度。
- 不能覆盖用户任务。
- 不能绕过 safety。

收束：

> Tool 是可执行能力，Skill 是上下文指导。

## 高频追问 12：Browser Tools 边界是什么？

一句话答案：

> 当前是 local-first browser tools，服务本地 HTML 和 localhost 调试，不是任意外网浏览器代理。

展开：

允许：

- workspace file。
- workspace file URL。
- localhost。
- 127.0.0.1。
- ::1。

默认拒绝：

- 外部 HTTP/HTTPS。
- 任意登录态网页操作。

边界：

> Playwright 是 optional dependency，`--check-browser` 用来检测能力。

## 高频追问 13：多模型怎么做？

一句话答案：

> 用 `LLMClient` 协议把 Agent Loop 和具体模型 SDK 解耦。

展开：

- `Message`。
- `ToolCall`。
- `LLMResponse`。
- OpenAI-compatible client。
- LocalFallbackClient。
- `PYAGENT_MODEL`。
- role-specific model。
- `--check-model`。
- `--eval-compare-models`。

边界：

> 当前是配置化多模型适配，不是自动 router，也没有完整 cost dashboard。

## 高频追问 14：没有 API key 怎么办？

一句话答案：

> 使用 `LocalFallbackClient` 演示本地 runtime，但明确它不代表真实模型质量。

展开：

- CLI 能跑。
- 工具链路能演示。
- 本地 eval 能跑。
- `--check-model` 会提示真实 tool calling 未检查。

收束：

> fallback 是降低上手门槛，不是替代真实模型验证。

## 高频追问 15：这个项目怎么产品化？

一句话答案：

> 产品化体现在可安装、可运行、可恢复、可复盘、可评估和可发布。

展开：

- `pyagent` console script。
- `python -m pyagentcli`。
- task mode / REPL mode。
- `--workspace`。
- `.pyagent/` runtime state。
- plan resume/retry/skip。
- eval reports。
- packaging tests。
- release checklist。

收束：

> 这不是一次性 demo，而是本地开发者工具的 v0.1。

## 高频追问 16：当前没做什么？

一句话答案：

> 当前是本地 CLI v0.1，不是完整云平台。

明确没做：

- Runtime API server。
- TUI。
- Web dashboard。
- GitHub PR automation。
- 自动 commit/push。
- 完整 browser automation。
- 多模态 vision model。
- cost dashboard。
- 自动 model router。

推荐说法：

> 我会把这些作为 Phase 2，而不是把 roadmap 写成已实现。

## 高频追问 17：下一步做什么？

一句话答案：

> 下一步我会优先做 Runtime event model，再接 Git 只读/commit proposal 和成本统计。

推荐路线：

```text
run event schema
  -> CLI emits JSONL trace
  -> Runtime API
  -> approval event
  -> dashboard/TUI
  -> Git status/diff read-only
  -> commit proposal
  -> token/cost tracking
```

为什么：

> 先把运行事件打通，后面的 dashboard、API、eval、cost 和 GitHub 自动化才不会各写一套。

## 高频追问 18：这个项目和 LangChain / LangGraph 有什么区别？

一句话答案：

> 我刻意自己实现核心 runtime，是为了理解 Agent 的底层边界；后续可以接框架，但不会把框架当黑箱。

展开：

自己实现了：

- Agent Loop。
- Tool Registry。
- Safety Policy。
- Approval。
- Audit。
- Plan Store。
- Reviewer。
- RAG。
- Memory。
- Eval Harness。

收束：

> 这让我能解释每个边界，而不是只会调框架 API。

## 高频追问 19：最大难点是什么？

一句话答案：

> 最大难点不是调模型，而是让模型接入真实开发环境后仍然安全、可控、可恢复、可评估。

展开：

难点包括：

- 文件和命令副作用。
- 上下文 stale。
- Memory 黑箱。
- 工具失败恢复。
- 多 step 假成功。
- 真实模型不稳定。
- GitHub 和桌面权限。

收束：

> 所以项目的核心价值是边界、审计、恢复和 eval。

## 高频追问 20：你开发中踩过什么坑？

一句话答案：

> 我们踩过模型不可用、GitHub push 受限、Computer Use 权限、Playwright optional dependency、RAG stale、Reviewer 假成功这些真实坑，并把它们沉淀进文档和测试。

可展开 3 个例子：

1. GitHub push。

   > 本地 commit 和远端 push 分开，避免把网络认证问题包装成 Agent 能力。

2. 模型不可用。

   > 遇到不存在模型名后，不继续调用，回到 repo 状态和 `--check-model` 思路。

3. Reviewer 假成功。

   > 不信最终回答，检查 step status、audit log 和 git diff。

## 简历 bullet 对应追问

### Bullet 1

> 从 0 到 1 构建 Python 版本地 AI Coding Agent CLI，支持 ReAct、Function Calling、本地工具执行和 CLI 产品化。

会被问：

- ReAct 和 Function Calling 区别？
- 模型会不会执行工具？
- CLI 产品化体现在哪？

要答：

- `AgentLoop`。
- `LLMClient`。
- `ToolRegistry`。
- `pyagent` console script。

### Bullet 2

> 设计 ToolRegistry + SafetyPolicy + ApprovalHandler + AuditLogger，控制文件写入、shell 执行和高风险工具调用。

会被问：

- 怎么防止越权？
- 审批前展示什么？
- audit log 记录什么？

要答：

- risk level。
- workspace path guardrail。
- command denylist。
- diff preview。
- JSONL audit。

### Bullet 3

> 实现 RAG、Memory 和上下文注入，支持 `@file/@folder/@symbol`、SQLite FTS、AST symbol chunk 和 project memory。

会被问：

- RAG 为什么不只是向量？
- Memory 和 Context 区别？
- 怎么防 stale？

要答：

- code retrieval 需要 symbol/path/import。
- Memory 是跨任务偏好和 summary。
- stale warning。

### Bullet 4

> 实现 Planner / Executor / Reviewer 工作流，支持计划预览、审批后执行、状态持久化、恢复、重试和 reviewer gate。

会被问：

- Multi-Agent 价值是什么？
- Planner 会不会执行工具？
- Reviewer 怎么判断成功？

要答：

- 角色边界。
- PlanPreview 无副作用。
- step status + audit + git diff。

### Bullet 5

> 构建 Eval Harness 和 Trace Eval，评估工具调用准确性、禁止工具、RAG 命中、reviewer gate 和多模型表现。

会被问：

- Eval 指标是什么？
- 为什么不只看最终回答？
- 真实模型 eval 怎么控制成本？

要答：

- expected tools。
- forbidden tools。
- trace。
- `--eval-real-model` opt-in。

## 不要这样讲

不要说：

```text
我做了一个完整 Claude Code。
```

改成：

```text
我做了一个本地 AI Coding Agent CLI v0.1，定位类似 mini Claude Code，重点实现核心 runtime 和安全评估闭环。
```

不要说：

```text
支持所有模型。
```

改成：

```text
通过 OpenAI-compatible client 和 LLMClient 协议支持配置化模型接入，当前不是完整 provider matrix。
```

不要说：

```text
支持 GitHub 自动化。
```

改成：

```text
当前支持本地 git diff review，GitHub push/PR automation 是下一阶段。
```

不要说：

```text
Browser 可以任意上网。
```

改成：

```text
当前是 local-first browser tools，外部网页默认拒绝。
```

不要说：

```text
Eval 证明模型很强。
```

改成：

```text
Eval 证明 runtime 行为是否符合预期，并为真实模型对比提供 trace case。
```

## 面试官连续追问模拟

### 路线 A：Agent Loop

面试官：

> 你说 ReAct / Function Calling，具体怎么结合？

你：

> ReAct 是循环策略，Function Calling 是模型输出结构化工具意图的接口。PyAgentCLI 的 AgentLoop 每轮把 messages 和 tools schema 传给 LLMClient，模型返回 content 或 ToolCall。如果是 ToolCall，就交给 ToolRegistry 执行，observation 再作为 tool message 回到下一轮。

面试官：

> 模型返回工具名后就执行吗？

你：

> 不会直接执行。ToolRegistry 会先根据 risk level 走 SafetyPolicy，必要时生成 preview 并交给 ApprovalHandler，执行结果和失败都会写 AuditLogger。

面试官：

> 怎么防无限循环？

你：

> 有 `PYAGENT_MAX_STEPS`，每轮工具失败也会作为 observation 返回，后续还可以加 token budget、tool budget 和 wall-clock timeout。

### 路线 B：Safety

面试官：

> Agent 改文件很危险，你怎么控制？

你：

> 先用 workspace path guardrail 限制路径，再拒绝 `.env/.git/.venv` 等敏感路径。写文件和 edit_file 是 WRITE risk，审批前展示 unified diff preview，edit_file 要求 old_text 唯一匹配。非交互模式下需要审批的动作默认拒绝。

面试官：

> 如果 preview 失败呢？

你：

> preview failure 会变成 ToolResult failure，并写 audit，不会继续执行。

### 路线 C：RAG / Memory

面试官：

> 代码 RAG 怎么做？

你：

> 代码场景需要精确检索，所以我用了 SQLite FTS、AST symbol chunk、import graph 和可选 embedding，而不是只用向量。用户还可以显式 `@file/@folder/@symbol` 注入上下文。

面试官：

> Memory 会不会污染上下文？

你：

> 会，所以 Memory 是可见可删的，支持 `--memory`、`--delete-memory-line`、`--compress-memory` 和 stale check，并且不能覆盖当前用户任务。

### 路线 D：Plan / Reviewer

面试官：

> 为什么需要 Planner / Executor / Reviewer？

你：

> 因为复杂任务要先审查计划，再执行，再复核证据。Planner 只生成 PlanPreview，不执行工具；Executor 按 approved step contract 执行；Reviewer 看 step status、audit log 和 git diff，决定是否通过。

面试官：

> Reviewer 是模型判断吗？

你：

> deterministic gate 是主路径，model-backed reviewer suggestion 只是辅助，不能覆盖 deterministic gate。

### 路线 E：产品化

面试官：

> 这个项目怎么从 demo 变成产品？

你：

> CLI 上有 `pyagent` console script、task/REPL 双模式、workspace、plan/execute/resume/retry、memory/index/eval/check-model/check-browser。运行态集中在 `.pyagent/`，发布有 packaging tests 和 release checklist。

面试官：

> 未来 Runtime API 怎么做？

你：

> 我会先定义 run event model，比如 `tool.approval_required`、`tool.completed`、`step.completed`、`review.completed`，再做 HTTP API。否则 dashboard、CLI、eval 会各写一套状态逻辑。

## 最后收束句

如果项目介绍结束时需要一句收束，可以用：

> 这个项目最有价值的地方，不是我调了一个模型，而是我把 AI Agent 从“能回答问题”推进到“能在本地开发环境中安全、可审计、可恢复、可评估地行动”。

## 背诵顺序

建议这样背：

1. 背 15 秒版本。
2. 背技术面试推荐版本。
3. 背 8 条高频追问地图。
4. 每条追问只背一句话答案。
5. 对 Safety、RAG、Plan、Eval 各准备一个 2 分钟展开。
6. 最后背“当前没做什么”，防止过度包装。

## 下一篇

下一篇：

> 25 知识库卡片和复习路线。

它会把 01-24 篇变成：

- Obsidian/OCDN 复习入口。
- 模块关系图。
- 面试前 30 分钟速查。
- 7 天复习计划。
- 简历 bullet 到文档章节映射。
