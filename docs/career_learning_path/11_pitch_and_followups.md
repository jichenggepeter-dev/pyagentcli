# 11 一分钟项目介绍和面试追问模板

这一篇用于口播训练。

## 一分钟版本

> 我做了一个 Python 版本地 AI Coding Agent CLI，定位类似 Claude Code / Codex mini。它的核心是一个 ReAct / Function Calling loop，模型不能直接改代码，只能返回工具调用意图，真正执行由本地 ToolRegistry 完成。工具层支持文件读写、局部编辑、shell、搜索、RAG 检索和浏览器 inspection，同时接入路径围栏、危险命令拦截、人工审批和审计日志。
>
> 在基础 loop 之上，我做了 Plan-and-Execute、多 Agent 协作、Memory、MCP、Skill System 和 Eval Harness。Planner 负责拆任务，Executor 按步骤执行，Reviewer 做 gate 和 retry proposal。RAG 方面用 SQLite FTS、AST symbol chunk、import graph 和可选 embedding 做混合检索。评估方面有 task success、tool-call accuracy、safety violation 和 trace eval。
>
> 这个项目让我系统理解了 AI Agent 从模型调用到工具执行、安全控制、上下文工程、多 Agent 协作和效果评估的完整链路。

## 30 秒版本

> PyAgentCLI 是我从 0 到 1 实现的 Python 版本地 AI Coding Agent CLI，类似 Claude Code / Codex mini。它支持 ReAct、Function Calling、本地工具执行、RAG、Memory、Plan-and-Execute、Multi-Agent、MCP、Skill、Browser Tools 和 Eval Harness。项目重点不是简单调用模型，而是实现安全、可审计、可评估的 Agent Runtime。

## 10 秒版本

> 我做了一个 Python 版 Claude Code mini，让模型通过受控工具调用在本地代码仓库中读代码、改代码、跑命令、做检索、记忆、复核和评估。

## 如果面试官问：你这个项目最大的难点是什么？

回答：

> 最大难点不是调模型，而是把模型接入真实开发环境后的安全和可控。模型会输出 tool call，但工具执行涉及文件修改、shell 命令、浏览器访问和外部工具调用，所以我做了路径围栏、风险分级、人工审批、审计日志、Reviewer gate 和 eval harness，保证 Agent 行为可追踪、可恢复、可评估。

## 如果面试官问：你和直接用 LangChain 有什么区别？

回答：

> 我这个项目刻意没有直接用重型 Agent 框架，而是自己实现了 Agent loop、Tool Registry、Safety Policy、Plan Store、Reviewer Gate、MCP Adapter 和 Eval Harness。这样我能讲清楚 Agent Runtime 的底层边界。后续当然可以接 LangGraph 这类框架，但核心机制我已经自己实现过。

## 如果面试官问：模型会不会执行代码？

回答：

> 不会。模型只返回结构化 tool call，比如工具名和参数。真正执行代码的是 PyAgentCLI 的本地工具层。执行前会经过 SafetyPolicy 和 ApprovalHandler，执行后 observation 再回到模型。

## 如果面试官问：怎么防止 Agent 乱改文件？

回答：

> 我做了几层控制。第一，路径围栏限制所有路径必须在 workspace 内，并拒绝 `.git`、`.env`、`.venv` 等敏感路径。第二，写文件工具需要审批，并展示 diff preview。第三，shell 工具有命令黑名单和审批机制。第四，所有工具调用都会写入审计日志。第五，计划执行后 Reviewer 会复核结果。

## 如果面试官问：RAG 怎么做？

回答：

> 我没有只做向量检索。代码场景需要精确检索，所以我用 SQLite FTS 做全文索引，用 AST 提取 Python 函数、类、方法作为 symbol chunk，还支持 JS/TS 常见 symbol chunk 和 Python import graph。用户可以通过 `@file/@folder/@symbol` 显式注入上下文，索引过期时会提示 stale warning。

## 如果面试官问：Memory 怎么设计？

回答：

> 我把 Memory 做成可见、可审查、可删除的本地项目记忆。Project memory 存项目偏好，session summary 存任务摘要，任务前会注入相关 memory。同时提供 `--memory`、`--remember`、`--compress-memory`、`--delete-memory-line`、`--stale-memory-days`，避免记忆变成黑箱。

## 如果面试官问：Multi-Agent 有什么价值？

回答：

> 我没有把 Multi-Agent 做成概念堆叠，而是拆成 Planner、Executor、Reviewer 三个边界。Planner 生成结构化计划，Executor 按 step contract 执行，Reviewer 检查 step 状态和风险。handoff 会持久化，Reviewer gate 会阻止 failed/skipped/cancelled step 被误判为 success。

## 如果面试官问：Eval 怎么做？

回答：

> 我把 eval 分成几个层次：platform eval 检查工具、安全、RAG、Memory；coding task eval 检查文件是否按预期改变；RAG retrieval eval 检查 symbol 和 dependency context；trace eval 检查工具调用序列、forbidden tools 和 final output。这样可以评估 Agent 行为，而不是只看最终回答。

## 如果面试官问：你开发过程中遇到过什么真实问题？

回答：

> 遇到过几个很典型的问题。比如 sandbox 网络权限导致不能直接 push GitHub，我们就把本地 commit 和用户手动 push 分开。Computer Use 插件能看 Safari 但不能操作 Terminal，说明桌面自动化也有安全边界。Playwright 很重，所以我把它做成 optional extra，并写了 `--check-browser` 和可选测试。还有 Reviewer gate 防止 skipped step 被误判 success，RAG stale warning 防止使用过期索引。这些问题都被写进了文档和测试。

## 如果面试官问：这个项目还有什么不足？

回答：

> 目前核心 Agent Runtime 已经完整，但真实模型长期评估、复杂浏览器交互和更丰富的工具生态还可以继续增强。下一步我会做 model-backed eval，把 deterministic eval 和真实 Agent run trace 结合起来，同时增强 Browser 工具的 Playwright 成功路径和受控交互能力。

## 最后收束

可以这样结尾：

> 这个项目最有价值的地方，是我把 AI Agent 从“概念”落到了工程实现：模型调用、工具执行、安全审批、上下文工程、记忆、计划、多 Agent、MCP、浏览器和评估都形成了闭环。

