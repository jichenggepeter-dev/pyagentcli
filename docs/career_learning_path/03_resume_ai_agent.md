# 03 简历篇：AI Agent 岗位写法

这一篇专门面向 AI Agent、LLM 应用、AI Infra、Agent Platform 方向。

核心目标：

> 让面试官一眼看出你不是只会调用模型 API，而是真的做过 Agent Runtime。

## 项目名称

中文：

> PyAgentCLI：Python 版本地 AI Coding Agent CLI

英文：

> PyAgentCLI: Local AI Coding Agent CLI in Python

## 项目描述

推荐版本：

> 从 0 到 1 设计并实现 Python 版本地 AI Coding Agent CLI，定位类似 Claude Code / Codex mini。项目支持 ReAct 循环、OpenAI-compatible Function Calling、文件/命令/搜索/浏览器工具、RAG 代码检索、项目记忆、Plan-and-Execute、多 Agent 协作、MCP 工具扩展、人工审批、安全审计和 Eval Harness，可通过自然语言在本地代码仓库中完成代码理解、修改、验证和复核。

更偏 Agent Runtime 的版本：

> 设计并实现本地 Agent Runtime，将 LLM 输出的结构化 tool call 转化为受控的本地文件操作、命令执行、代码检索和浏览器检查流程，并通过 Safety Policy、HITL 审批、Reviewer Gate 和 Eval Harness 保证 Agent 行为安全、可观测、可评估。

## 技术栈

推荐写：

> Python 3.12、OpenAI-compatible API、SQLite FTS、AST Parser、TOML、JSONL、MCP stdio、Playwright optional、pytest、GitHub Actions

如果岗位偏 Agent：

> ReAct、Function Calling、Tool Registry、RAG、Memory、MCP、Skill、Multi-Agent、Eval Harness、Trace Eval

## 核心职责写法

### Bullet 1：Agent Loop

可写：

> 实现 ReAct / Function Calling Agent Loop，维护 system/user/assistant/tool 消息历史，支持 OpenAI-compatible 模型和 local fallback，并通过 max steps 防止无限循环。

展开讲：

- 模型返回 tool call。
- ToolRegistry 执行工具。
- 工具结果作为 observation 回到模型。
- 没有 tool call 时结束任务。
- max steps 防止循环失控。

面试官可能追问：

- Function Calling 的本质是什么？
- 模型是否真的执行代码？
- ReAct 和 CoT 的区别是什么？

### Bullet 2：工具系统和安全

可写：

> 设计 Tool Registry 和工具安全执行层，内置文件读写、局部编辑、shell、搜索、浏览器工具，并实现路径围栏、危险命令拦截、人工审批和 JSONL 审计日志。

展开讲：

- READ 工具默认允许。
- WRITE / EXECUTE 需要审批。
- NETWORK / CRITICAL 默认拒绝。
- `.git`、`.env`、`.venv`、`node_modules` 禁止访问。
- `write_file` / `edit_file` 有 diff preview。

面试官可能追问：

- 为什么不能让模型直接执行 shell？
- HITL 审批如何设计？
- 怎么防止 Agent 删除项目？

### Bullet 3：RAG 和上下文工程

可写：

> 构建 RAG 代码检索体系，基于 SQLite FTS、AST symbol chunk、import graph 和可选 embedding provider，实现 `@file/@folder/@symbol` 上下文注入与 stale index warning。

展开讲：

- FTS 用来做精确检索。
- AST 用来做 symbol chunk。
- import graph 用来补依赖关系。
- embedding provider 可选，不依赖 API key。
- stale index warning 防止过期上下文。

面试官可能追问：

- RAG 为什么不只是向量检索？
- 代码 chunk 为什么要 AST？
- index stale 怎么处理？

### Bullet 4：Memory 和 Multi-Agent

可写：

> 实现 Project Memory、Session Summary、Plan-and-Execute 和 Planner / Executor / Reviewer 多 Agent 协作，支持计划持久化、步骤重试、跳过、恢复、Reviewer Gate 和 retry proposal。

展开讲：

- Memory 存在 `.pyagent/memory/`。
- Plan 存在 `.pyagent/plans/`。
- Planner 生成计划。
- Executor 执行步骤。
- Reviewer 检查结果。
- failed / skipped / cancelled 不允许误判 success。

面试官可能追问：

- Memory 和 Context 的区别是什么？
- Planner / Executor / Reviewer 怎么分工？
- Reviewer 如何避免形式主义？

### Bullet 5：MCP、Skill、Eval

可写：

> 集成 MCP stdio client、Skill System、Browser Tools 和 Eval Harness，支持外部工具适配、任务级 prompt guidance、local-only 页面 inspection，并通过 task success、tool-call accuracy、safety violation 和 trace eval 评估 Agent 行为。

展开讲：

- MCP 扩展外部工具生态。
- Skill 是 prompt guidance，不是工具。
- Browser 工具默认 local-only。
- Eval 不只看最终回答，还看工具调用和安全行为。

面试官可能追问：

- MCP 和 Tool Registry 的区别是什么？
- Skill 和 Tool 的区别是什么？
- Agent Eval 怎么做？

## 一版完整简历项目

可以直接写：

```text
PyAgentCLI：Python 版本地 AI Coding Agent CLI
技术栈：Python 3.12、OpenAI-compatible API、SQLite FTS、AST Parser、MCP stdio、Playwright optional、pytest、GitHub Actions

项目简介：从 0 到 1 设计并实现本地 AI Coding Agent CLI，定位类似 Claude Code / Codex mini。系统支持 ReAct 循环、Function Calling、文件/命令/搜索/浏览器工具、RAG 代码检索、项目记忆、Plan-and-Execute、多 Agent 协作、MCP 工具扩展、人工审批、安全审计和 Eval Harness，可通过自然语言在本地代码仓库中完成代码理解、修改、验证和复核。

核心职责：
1. 实现 ReAct / Function Calling Agent Loop，维护消息历史和工具 observation 回灌机制，并通过 max steps 防止无限循环。
2. 设计 Tool Registry 与安全执行层，内置文件读写、局部编辑、shell、搜索和浏览器工具，支持路径围栏、危险命令拦截、人工审批和 JSONL 审计日志。
3. 构建 RAG 代码检索体系，基于 SQLite FTS、AST symbol chunk、import graph 和可选 embedding provider，实现 @file/@folder/@symbol 上下文注入与 stale index warning。
4. 实现 Project Memory、Plan-and-Execute 和 Planner / Executor / Reviewer 多 Agent 协作，支持计划持久化、步骤重试、Reviewer Gate 和 retry proposal。
5. 集成 MCP stdio client、Skill System 和 Eval Harness，构建 task success、tool-call accuracy、safety violation 和 trace eval 等评估指标。
```

## 写简历时的注意点

不要写得太虚：

```text
熟悉 AI Agent、RAG、MCP、Memory 等技术。
```

要写成你真的实现过：

```text
实现 MCP stdio client，支持 initialize、tools/list、tools/call，并根据 readOnlyHint 将外部工具映射到本地风险等级。
```

不要只写概念：

```text
实现多 Agent 协作。
```

要写清楚角色和边界：

```text
抽象 Planner / Executor / Reviewer 三角色，持久化 agent handoff，并通过 Reviewer Gate 防止 skipped / failed step 被误判为成功。
```

## 我们开发经历可以怎么写进去

可以写：

> 在项目迭代中处理了 sandbox 网络权限、Computer Use 桌面操作限制、Playwright optional dependency、RAG index stale、Reviewer false success、trace eval 等真实工程问题，并将解决方案沉淀为文档和测试。

这句话非常有价值。

因为它说明你不是只照着教程写功能，而是真的经历了工程约束和调试过程。

