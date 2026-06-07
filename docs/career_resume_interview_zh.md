# PyAgentCLI 简历篇与面试篇

本文把 PaiCLI 学习路线中的“先跑项目、再写简历、围绕简历准备面试”的方法，映射到 PyAgentCLI 项目。

注意：本文不是对 PaiCLI 原文的复制，而是基于 PyAgentCLI 当前实现整理的原创求职材料。

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

## 08. 参考来源

本文参考了 PaiCLI 学习路线和相关面试/简历文章的结构与主题方向，但所有项目表述均改写为 PyAgentCLI 的实现：

- https://paicoding.com/paicli-learning-path
- https://paicoding.com/column/17/14
- https://paicoding.com/article/detail/2613300022282240
- https://paicoding.com/memory-context
- https://paicoding.com/article/detail/2614100053739520
