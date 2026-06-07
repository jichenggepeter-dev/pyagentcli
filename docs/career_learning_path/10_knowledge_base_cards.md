# 10 知识库沉淀：怎么把 PyAgentCLI 讲成自己的项目

这一篇用于把 PyAgentCLI 拆成知识库卡片。

适合导入 OCDN、Obsidian 或其他个人知识库。

## 卡片 1：PyAgentCLI 是什么

标题：

> PyAgentCLI：Python 版本地 AI Coding Agent CLI

核心内容：

- 类似 Claude Code / Codex mini
- 本地 CLI
- ReAct / Tool Calling
- 文件、命令、搜索、浏览器工具
- RAG、Memory、MCP、Skill、Multi-Agent、Eval

一句话：

> PyAgentCLI 是一个把 LLM tool call 安全接入本地开发环境的 Agent Runtime。

## 卡片 2：Agent Loop

关键词：

- ReAct
- Function Calling
- Tool Call
- Observation
- max steps

核心图：

```text
User Goal
  -> LLM
  -> tool_call
  -> ToolRegistry
  -> observation
  -> LLM
  -> final answer
```

面试句：

> 模型不执行代码，它只输出工具调用意图。

## 卡片 3：Tool Registry

关键词：

- schema
- dispatch
- preview
- approval
- audit

核心问题：

- 工具如何注册？
- 工具如何暴露给模型？
- 工具失败如何变成 observation？

面试句：

> Tool Registry 是 Agent 能力目录，也是安全策略入口。

## 卡片 4：Safety Policy

关键词：

- risk level
- path guardrail
- command denylist
- HITL
- audit log

核心规则：

- READ 允许
- WRITE 审批
- EXECUTE 审批
- NETWORK / CRITICAL 默认拒绝

面试句：

> 安全不能靠 prompt，必须在工具执行层做。

## 卡片 5：RAG

关键词：

- SQLite FTS
- AST symbol chunk
- import graph
- embedding provider
- stale index

核心句：

> 代码 RAG 不能只靠向量，精确符号和依赖关系同样重要。

## 卡片 6：Memory

关键词：

- Project Memory
- Session Summary
- Compression
- Deletion
- Stale Memory

核心句：

> Memory 不是黑箱长期记忆，而是可见、可审查、可删除的项目上下文。

## 卡片 7：Plan-and-Execute

关键词：

- plan preview
- approval
- persistence
- resume
- retry step

核心句：

> 复杂任务先计划再执行，可以让用户在高风险动作前审查 Agent 意图。

## 卡片 8：Multi-Agent

关键词：

- Planner
- Executor
- Reviewer
- handoff
- gate

核心句：

> Multi-Agent 的价值不是角色数量，而是职责边界和可审计 handoff。

## 卡片 9：Reviewer Gate

关键词：

- failed
- skipped
- cancelled
- retry proposal
- false success

核心句：

> Reviewer 不是总结器，而是最终状态 gate。

## 卡片 10：MCP

关键词：

- stdio
- JSON-RPC
- tools/list
- tools/call
- adapter

核心句：

> MCP 扩展工具来源，但不能绕过本地安全策略。

## 卡片 11：Skill

关键词：

- skill.toml
- SKILL.md
- trigger
- prompt guidance

核心句：

> Skill 是知识复用，不是工具执行。

## 卡片 12：Browser Tools

关键词：

- inspect_page
- dom_snapshot
- selector query
- console logs
- screenshot
- local-only

核心句：

> Browser tool 先做本地只读观察，再考虑交互。

## 卡片 13：Eval Harness

关键词：

- task success
- tool-call accuracy
- safety violation
- trace eval
- JSONL report

核心句：

> Agent Eval 要评估行为轨迹，而不是只看最终回答。

## 卡片 14：开发踩坑

关键词：

- sandbox push
- Computer Use Terminal block
- Playwright optional
- importorskip
- stale index
- false success

核心句：

> 真实项目能力来自处理约束，而不是只实现 happy path。

## 推荐知识库结构

```text
PyAgentCLI/
  00 项目总览
  01 Agent Loop
  02 Tool Registry
  03 Safety HITL
  04 RAG
  05 Memory
  06 Plan Execute
  07 Multi Agent
  08 MCP Skill
  09 Browser
  10 Eval
  11 简历
  12 面试题
  13 开发踩坑
```

## 复习方法

每天选一个模块，按下面顺序复习：

1. 用一句话讲清楚它是什么。
2. 画出流程图。
3. 找到对应源码。
4. 说出一个我们开发时遇到的问题。
5. 回答 3 个面试题。

这样复习一轮后，你就不是“背项目”，而是真的能讲项目。

