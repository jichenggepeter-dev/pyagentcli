# Resume Bullets

## Chinese Version

### One-Line Summary

从 0 到 1 设计并实现 Python 版本地 AI Coding Agent CLI，支持 ReAct / Tool Calling、文件与命令工具、安全审批、RAG 代码检索、项目记忆、计划执行、自动复核与本地评估闭环。

### Engineering Bullets

- 设计并实现 Python 版本地 AI Coding Agent CLI，基于 OpenAI-compatible Tool Calling 构建 ReAct 执行循环，支持文件读写、代码编辑、命令执行和工具结果反馈。
- 构建 Tool Registry 与统一工具协议，为 `read_file`、`edit_file`、`run_shell`、`search_index` 等工具定义 schema、风险等级、执行上下文和结构化返回。
- 实现 Safety / HITL 安全层，通过 workspace 路径围栏、危险命令拒绝、写入与执行审批、JSONL 审计日志降低自动化代码操作风险。
- 实现 Plan-and-Execute 工作流，支持计划预览、人工确认、步骤级执行、失败恢复、单步重试和计划持久化。
- 构建 RAG Lite 检索层，基于 SQLite FTS 和 Python AST symbol chunk 支持代码索引、`@file` / `@folder` / `@symbol` 上下文注入和索引过期提醒。
- 实现本地 Memory 系统，支持项目记忆、session 摘要、任务前记忆注入和 `.pyagent/memory/` 可审计存储。
- 实现 deterministic Reviewer，在计划执行后自动输出风险提示、涉及工具/路径和建议测试，并将复核结果写回 plan 与 Markdown artifact。
- 建立 Eval Harness，使用 deterministic cases 验证工具注册、安全策略、RAG symbol 检索和 Memory 能力，输出可追踪 JSONL 评估报告。

### Product / PM Bullets

- 从开发者本地编码工作流出发，设计 AI Coding Agent 的核心产品闭环：任务理解、上下文检索、工具执行、安全审批、记忆沉淀、结果复核和效果评估。
- 将高风险 Agent 行为产品化为可解释权限系统，围绕工具风险分级、人工审批、审计日志和索引新鲜度提醒建立用户信任机制。
- 设计 Agent 能力分阶段路线，从 MVP 工具调用扩展到 RAG、Memory、Reviewer、Eval，并为 MCP、Browser、Multi-Agent 和 Skill System 留出架构扩展点。

## English Version

### One-Line Summary

Built PyAgentCLI, a local Python AI coding agent CLI with ReAct / tool calling, file and shell tools, HITL safety, code RAG, project memory, plan execution, reviewer feedback, and deterministic evals.

### Engineering Bullets

- Designed and implemented a Python-based local AI coding agent CLI with an OpenAI-compatible tool-calling loop for file reading, code editing, shell execution, and iterative tool feedback.
- Built a unified Tool Registry with schemas, risk levels, execution context, and structured results for filesystem, shell, search, and indexed code retrieval tools.
- Implemented a HITL safety layer with workspace path guardrails, dangerous command denial, write/execute approval, and JSONL audit logging.
- Developed a Plan-and-Execute workflow with plan preview, persisted plan runs, step status tracking, resume, retry, manual step status updates, and execution freshness warnings.
- Built a local code RAG layer using SQLite FTS and Python AST symbol chunks, supporting `@file`, `@folder`, and `@symbol` context injection with stale-index detection.
- Added local project memory and session memory under `.pyagent/memory/`, with explicit memory injection and auditable storage.
- Implemented a deterministic Reviewer that summarizes plan execution, risk notes, observed tools/paths, and suggested tests after planned execution.
- Created a deterministic Eval Harness with JSONL reports to validate core platform capabilities including tool registry, safety policy, RAG symbol search, and memory persistence.
