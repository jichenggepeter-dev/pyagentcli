# PyAgentCLI 简历表达与面试题清单

## 1. 简历项目标题

### 中文

PyAgentCLI：从 0 到 1 设计并实现 Python 版 AI Coding Agent CLI

### 英文

PyAgentCLI: A Python-based AI Coding Agent CLI with Tool Calling, RAG, Memory, and Human-in-the-loop Safety

## 2. 简历一句话版本

从 0 到 1 设计并实现 Python 版 AI Coding Agent CLI，支持 ReAct 循环、函数调用、文件/命令工具执行、RAG 代码检索、记忆压缩、人工审批和多 Agent 协作，构建工具权限、路径围栏、审计日志与任务成功率评估体系。

## 3. 简历 Bullet 版本

### 偏工程实现

- 设计并实现 Python 版本地 AI Coding Agent CLI，基于 ReAct / Tool Calling Agent Loop 支持文件读取、代码修改、命令执行和错误恢复。
- 构建工具注册与权限控制系统，为 `read_file`、`write_file`、`run_shell` 等工具定义 schema、风险等级、路径围栏、命令黑名单和人工审批流程。
- 实现代码库检索能力，对项目文件进行 chunk、索引和召回，支持 `@file`、`@folder`、`@symbol` 等上下文注入方式，提升复杂代码任务的上下文命中率。
- 设计 session/project/user 三层 Memory 机制，通过上下文压缩保存任务状态、项目约定和用户偏好，降低长任务中的上下文丢失。
- 引入 Planner、Executor、Reviewer 多 Agent 协作模式，将任务拆解、工具执行和结果审查解耦，提高复杂任务的可控性和可解释性。
- 建立 Agent Eval Harness，记录工具调用成功率、任务完成率、人工介入率和失败类型，用数据评估 Agent 能力边界。

### 偏产品与架构

- 从开发者工作流出发，设计本地 AI Coding Agent CLI 的产品架构，覆盖任务理解、上下文检索、工具执行、安全审批、审计日志和效果评估闭环。
- 将高风险工具调用纳入 HITL 审批机制，通过工具风险分级、路径围栏和命令策略降低 AI Agent 自动执行带来的安全风险。
- 设计可扩展工具系统和 MCP Adapter，使文件系统、Shell、浏览器、外部 MCP 工具可以以统一协议接入 Agent Loop。

## 4. 面试讲项目的 60 秒版本

这个项目是我从 0 到 1 做的一个 Python 版 AI Coding Agent CLI，可以理解为一个 mini Claude Code / Codex CLI。它不是普通聊天机器人，而是能在本地代码库中读取文件、搜索代码、修改文件、执行命令，并根据工具结果继续推理。

核心架构分为 Agent Loop、LLM Client、Tool Registry、Safety Policy、RAG、Memory 和 Eval。Agent Loop 负责 ReAct 或 Tool Calling 循环；Tool Registry 统一管理文件、Shell、搜索等工具；Safety 层对写文件和执行命令做风险分级、路径围栏、命令黑名单和人工审批；RAG 负责把代码库相关上下文召回给模型；Memory 保存 session、project、user 三层信息；最后用评估用例衡量任务成功率和工具调用质量。

这个项目最大的价值是把 AI Agent 从“能聊天”推进到“能安全地完成开发任务”，同时我也重点处理了无限循环、工具失败恢复、上下文污染和高风险操作审批这些真实工程问题。

## 5. 面试题清单

### Agent Loop

1. ReAct 和 Function Calling 有什么区别？你的项目为什么同时考虑两者？
2. Agent Loop 的一次完整循环是什么？
3. 如何判断 Agent 任务完成了？
4. 如何防止 Agent 无限循环？
5. 如果模型反复调用同一个失败工具，你怎么处理？
6. Tool result 应该原样塞回上下文吗？什么时候需要压缩？

### Tool Calling

1. 你如何设计工具 schema？
2. Tool Registry 的职责是什么？
3. 工具调用失败后，Agent 应该重试还是终止？
4. 如何处理工具参数不合法？
5. read-only 工具和 write/execute 工具有哪些不同的安全策略？
6. 如果模型 hallucinate 了不存在的工具名，你怎么处理？

### 安全与 HITL

1. Coding Agent 最大的安全风险是什么？
2. 为什么执行 Shell 命令需要人工审批？
3. 路径围栏如何实现？
4. 命令黑名单有什么局限？
5. 如何设计工具风险分级？
6. 审计日志应该记录哪些字段？
7. 如何在用户体验和安全之间平衡？

### RAG

1. 为什么 Coding Agent 需要 RAG？
2. RAG 为什么不只是向量检索？
3. 代码 chunk 和普通文本 chunk 有什么不同？
4. 如何支持 `@file`、`@folder`、`@symbol`？
5. 检索结果太多会有什么问题？
6. 如何减少错误上下文污染模型？

### Memory

1. Memory 和 Context Window 有什么区别？
2. session memory、project memory、user memory 分别保存什么？
3. 什么信息应该进入长期记忆？
4. 如何避免 Memory 记住错误信息？
5. 上下文压缩怎么做？

### Multi-Agent

1. 为什么需要多 Agent？一个 Agent 不够吗？
2. Planner、Executor、Reviewer 如何分工？
3. 多 Agent 会带来哪些额外问题？
4. 如何避免多 Agent 互相甩锅或循环？
5. Reviewer 应该依赖模型判断还是测试结果？

### MCP

1. MCP 解决了什么问题？
2. MCP Tool 和本地 Tool 有什么区别？
3. 如何把 MCP 工具接入你的 Tool Registry？
4. MCP 工具也需要安全审批吗？
5. 如果 MCP server 不稳定，Agent 如何降级？

### Eval

1. 如何评估一个 Coding Agent 是否有效？
2. 任务成功率怎么定义？
3. 工具调用成功率和最终任务成功率有什么区别？
4. 如何构造 Eval case？
5. 如何分析 Agent 失败原因？
6. 只看人工主观体验有什么问题？

## 6. 高频追问回答要点

### Q: 你这个和普通 ChatGPT CLI 有什么区别？

普通 ChatGPT CLI 主要是对话输入输出，而 PyAgentCLI 的重点是 Agentic Workflow：模型可以调用工具读取代码、修改文件、执行命令，并根据工具结果继续推理。它还有安全审批、RAG、Memory、Eval 等工程机制，更接近 Coding Agent。

### Q: 为什么不用 LangChain / CrewAI 直接搭？

这个项目的目标是理解和实现 Coding Agent 的核心机制，所以我选择自己实现 Agent Loop、Tool Registry、Safety Policy 和 Memory。这样能更清楚地控制工具调用、审批、安全边界和评估逻辑。后续可以兼容外部框架或 MCP，但核心链路不依赖黑盒框架。

### Q: ReAct 和 Tool Calling 你怎么选？

ReAct 更强调显式推理和行动过程，适合教学和可解释；Tool Calling 更适合工程实现，因为模型能结构化输出工具名和参数。我的设计里用 Tool Calling 承载真实执行，用日志和状态记录保留 ReAct 风格的可解释性。

### Q: Coding Agent 为什么容易危险？

因为它不只是生成文本，而是能操作真实文件和执行命令。错误的路径、误删命令、未经确认的依赖安装、网络脚本执行都可能破坏项目或系统。所以我把工具分成 read、write、execute、critical 等风险等级，并对写入和命令执行加入审批、路径围栏、黑名单和审计日志。

### Q: RAG 模块你会怎么落地？

先从简单可控的本地索引开始：扫描项目文件，过滤无关目录，对代码按函数、类或固定窗口 chunk，存入 SQLite。检索时结合关键字、文件路径、符号名和 embedding 召回。相比只做向量检索，代码场景更需要结构化信号，比如文件路径、语言、符号、import 关系和最近编辑文件。

### Q: 如何防止 Agent 一直循环？

我会设置最大步数、工具调用超时、重复调用检测和失败计数。如果同一个工具用相同参数连续失败，就把失败摘要反馈给模型并要求换策略；如果仍无法推进，就停止并向用户解释当前阻塞点。

### Q: 你怎么评估项目效果？

我会设计 Eval case，每个 case 有初始文件树、用户任务、期望文件变化和成功判定函数。指标包括任务成功率、工具调用成功率、平均步数、人工审批次数、失败类型分布。这样能知道 Agent 是真的能完成任务，还是只是回答得像完成了。

