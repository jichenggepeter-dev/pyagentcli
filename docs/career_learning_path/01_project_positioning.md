# 01 项目定位：Python 版 Claude Code / Codex mini

## 项目一句话

PyAgentCLI 是一个用 Python 从 0 到 1 实现的本地 AI Coding Agent CLI，定位类似 Claude Code / Codex mini。

它让用户可以在本地代码仓库中用自然语言完成：

- 读取文件
- 搜索代码
- 修改文件
- 运行命令
- 注入代码上下文
- 生成计划
- 执行计划
- 复核结果
- 记录记忆
- 调试本地页面
- 评估 Agent 行为

但它不是简单地把用户问题转发给模型。

核心区别是：

> 模型不能直接改代码，也不能直接执行命令。模型只能返回结构化 tool call，真正执行的是 PyAgentCLI 本地工具层。

## 项目为什么值得做

AI Coding Agent 的难点不在于“调用一个大模型 API”，而在于把模型接到真实开发环境时，如何保证：

- 能读到正确代码上下文
- 能调用正确工具
- 能处理工具失败
- 能限制危险操作
- 能让用户审批高风险动作
- 能记录审计日志
- 能跨任务记住项目偏好
- 能评估 Agent 是否真的完成任务

这些问题就是 PyAgentCLI 的核心价值。

## 项目能力版图

当前 PyAgentCLI 已经具备这些模块：

```text
CLI / REPL
  -> Context Enrichment
    -> RAG references: @file / @folder / @symbol
    -> Project Memory
    -> Skill Guidance
  -> Agent Loop
    -> LLM Client
    -> Tool Registry
      -> Safety Policy
      -> Human Approval
      -> Audit Log
  -> Plan Executor
  -> Reviewer
  -> Eval Harness
```

展开后是：

- ReAct / Tool Calling 主循环
- OpenAI-compatible LLM client
- Local fallback client
- Tool Registry
- 文件工具
- shell 工具
- 搜索工具
- 浏览器工具
- Safety Policy
- Approval Handler
- Audit Logger
- RAG Lite
- Hybrid Retrieval
- Import Graph
- Memory
- Plan-and-Execute
- Reviewer Gate
- Retry Proposal
- Multi-Agent handoff
- MCP Client
- Skill System
- Eval Harness
- Trace Eval
- Release / Packaging

## 和普通 Chatbot 的区别

普通 chatbot：

```text
User asks
  -> Model answers
```

PyAgentCLI：

```text
User gives task
  -> Agent enriches context
  -> Model emits tool call intent
  -> Safety checks tool
  -> Human approves risky action
  -> Tool runs locally
  -> Observation returns to model
  -> Reviewer checks result
  -> Eval can score behavior
```

这就从“聊天应用”变成了“本地 Agent Runtime”。

## 和 PaiCLI 的关系

PaiCLI 是 Java 版 Agent CLI 学习项目。PyAgentCLI 借鉴的是它的学习路线和项目思路：

- 先跑起来
- 再写简历
- 围绕简历模块挖源码
- 准备 Agent 面试题
- 通过 debug、加功能、修 bug 形成真实工程经历

但 PyAgentCLI 不是复制 PaiCLI 文本，也不是 Java 版本翻译。

PyAgentCLI 的实现是 Python 版，并且结合了我们开发过程中的实际选择：

- Python 标准库优先
- SQLite FTS 做本地索引
- `.pyagent/` 做本地运行态
- pytest 做回归测试
- 可选 Playwright，不强制浏览器依赖
- Reviewer proposal 只生成建议，不自动执行

## 简历上的定位

推荐写：

> PyAgentCLI：Python 版 Claude Code / Codex mini，本地 AI Coding Agent CLI。

展开写：

> 从 0 到 1 设计并实现 Python 版本地 AI Coding Agent CLI，支持 ReAct 循环、Function Calling、文件/命令/搜索/浏览器工具、RAG 代码检索、项目记忆、Plan-and-Execute、多 Agent 协作、MCP 工具扩展、人工审批、安全审计和 Eval Harness，可通过自然语言在本地代码仓库中完成代码理解、修改、验证和复核。

## 面试时的主线

你可以用这条主线讲项目：

1. 我先实现了 Agent Loop，让模型能通过工具和本地代码交互。
2. 然后实现 Tool Registry 和 Safety，保证工具执行安全可控。
3. 接着做 RAG 和 Memory，让 Agent 有代码上下文和项目记忆。
4. 再做 Plan-and-Execute 和 Multi-Agent，让复杂任务可审查、可恢复。
5. 然后做 Reviewer Gate 和 Retry Proposal，避免假成功。
6. 最后做 MCP、Skill、Browser、Eval，把项目扩展成完整 Agent Runtime。

## 项目当前成熟度

按简历展示：

- 已经成熟。

按真实开源工具：

- 核心能力成熟，高级能力还在增强。

按商业级 Claude Code 替代品：

- 还差真实模型长期评估、复杂浏览器交互、更强 UI/UX、更多工具生态。

所以你可以诚实地说：

> 这是一个完整的本地 AI Coding Agent CLI 原型，重点展示 Agent Runtime 的关键工程能力，而不是声称已经完全替代 Claude Code。

