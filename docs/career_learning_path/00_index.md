# 00 PyAgentCLI 学习路线总览

这组文档的 v2 目标，是把 PyAgentCLI 写成一条真正能学习、能复盘、能写简历、能应对面试追问的项目路线。

它参考 PaiCLI 登录态学习路线的栏目节奏，但不复制原文，也不照搬 Java 实现。PyAgentCLI 的材料必须回到我们自己的 Python 项目事实：

- 本地 CLI
- ReAct / Tool Calling
- Tool Registry
- 文件、命令、搜索、浏览器工具
- Safety Policy、HITL、Audit Log
- RAG、Memory、Context Injection
- Plan-and-Execute
- Planner / Executor / Reviewer
- MCP Client
- Skill System
- Eval Harness / Trace Eval
- Release、测试、GitHub、Obsidian 沉淀

一句话：

> PyAgentCLI 是一个 Python 版 Claude Code / Codex mini。学习这条路线，不是为了背 Agent 概念，而是把一个本地 AI Coding Agent CLI 从运行、源码、功能、踩坑、简历到面试完整吃透。

## 这条路线解决什么问题

如果只看项目功能清单，你会知道 PyAgentCLI “有什么”。

但面试时真正会被追问的是：

- 这个模块为什么要做？
- 你具体怎么实现？
- 模型和工具的边界在哪里？
- 出错后怎么恢复？
- 怎么防止越权？
- 怎么证明 Agent 真的完成任务？
- 简历上的每一句话能不能落到源码、命令和测试？

所以 v2 文档不再只是“资料包”，而是按下面的学习路径展开：

```text
第一天：跑通项目，写出第一版简历
第一周：吃透核心 Agent Runtime
第二周：补高级能力，准备面试追问
长期：把开发复盘沉淀进 Obsidian
```

## 第一天：跑通和写简历

目标不是把所有源码看懂，而是先证明项目是真能跑的。

你要完成：

- 安装项目。
- 跑 `pyagent --help`。
- 跑 `pyagent --eval`。
- 跑 `pyagent --plan "fix failing tests"`。
- 跑 `pyagent --index`。
- 跑 `pyagent --memory`。
- 跑 `pyagent --check-browser`。
- 写出一版项目描述和 3-5 条简历 bullet。

对应文档：

- [01 先跑通 PyAgentCLI](01_run_project.md)
- [15 PyAgentCLI 如何写到简历上](03_resume_ai_agent.md)
- [一分钟项目介绍和追问模板](11_pitch_and_followups.md)

第一天的成果应该是：

> 我能在本地演示 PyAgentCLI 的 CLI、Eval、Plan、RAG、Memory 和 Browser capability check，并能用 30 秒讲清楚它不是普通 chatbot，而是本地 Agent Runtime。

## 第一周：吃透核心 Agent Runtime

第一周重点吃透最核心的 Agent 闭环。

推荐顺序：

1. [ReAct 和 Tool Calling](02_react_tool_calling.md)
2. Tool Registry 和本地工具执行
3. Safety Policy、HITL、Audit Log
4. Plan-and-Execute
5. Memory 和 Context
6. RAG 代码检索
7. Reviewer Gate 和 Eval Harness

这一周的学习方式不是“通读所有源码”，而是每个模块都按同一个问题链拆：

```text
为什么需要它
PyAgentCLI 里怎么实现
从哪个 CLI 命令能看到效果
对应哪些源码
有哪些安全边界
我们开发时遇到过什么坑
简历上怎么写
面试官会怎么追问
```

第一周结束，你应该能回答：

- ReAct 和 Function Calling 的关系是什么？
- 模型到底会不会执行代码？
- Tool Call 失败后怎么恢复？
- 为什么写文件和 shell 需要审批？
- RAG 为什么不只是向量检索？
- Memory 和 Context 的区别是什么？
- Reviewer 为什么能防止“假成功”？
- Eval 为什么不能只看最终回答？

## 第二周：高级能力和面试追问

第二周开始补高级模块和产品化能力。

推荐顺序：

1. Multi-Agent：Planner / Executor / Reviewer
2. MCP：外部工具协议和安全映射
3. Browser Tools：local-first、Playwright optional、登录态边界
4. Prompt 分层和 Skill System
5. 多模型适配和 Model Config
6. CLI 产品化、Git、Runtime API 方向
7. 多模态和未来扩展

第二周的重点是把项目讲得更像“工程系统”，而不是“功能堆叠”。

你需要能讲清楚：

- Multi-Agent 不是堆角色，而是职责边界。
- MCP 扩展的是工具生态，不是放松安全边界。
- Skill 是 prompt guidance，不是隐形工具权限。
- Browser 能力要区分截图、DOM、点击、登录态和页面脚本权限。
- 多模型适配要有统一接口、能力声明、fallback 和成本控制。
- 产品化不只是能跑，还包括 CLI 体验、测试、发布、审计和可观测。

## v2 文档总目录

下面是目标目录。当前不会一次性全部重写，而是按阶段逐篇落地。

### 总览篇

- [00 PyAgentCLI 学习路线总览](00_index.md)
- [01 先跑通 PyAgentCLI：安装、命令、演示、自检](01_run_project.md)

### 实战篇

- [02 ReAct 和 Tool Calling](02_react_tool_calling.md)
- [03 Plan-and-Execute / DAG](03_plan_execute_dag.md)
- [04 Memory 系统](04_memory_system.md)
- [05 RAG 代码检索](05_rag_code_retrieval.md)
- [06 Tool Call、HITL 和安全策略](06_tool_hitl_safety.md)
- [07 Multi-Agent](07_multi_agent.md)
- [08 Browser Tools 和联网搜索](08_browser_search.md)
- [09 接入 MCP](09_mcp_integration.md)
- [10 Prompt 分层和 Skill System](10_prompt_skill_system.md)
- [11 多模型适配和 LLM Client](11_multi_model_llm_client.md)
- [12 产品化：CLI UX、Git、Runtime API](12_productization_cli_git_runtime.md)
- [13 Eval Harness 和 Trace Eval](13_eval_harness_trace_eval.md)
- [14 多模态和未来扩展](14_multimodal_future_extensions.md)

### 简历篇

- 15 PyAgentCLI 如何写到简历上

### 面试篇

- [16 面试题第一弹：ReAct、Plan-and-Execute、Multi-Agent](16_interview_react_plan_multi_agent.md)
- [17 面试题第二弹：Memory、RAG、长上下文工程](17_interview_memory_rag_context.md)
- [18 面试题第三弹：Tool Call、HITL、安全策略](18_interview_tool_hitl_safety.md)
- [19 面试题第四弹：MCP、Browser Tools、CDP 思路](19_interview_mcp_browser_cdp.md)
- 20 面试题第五弹：Prompt 分层、Skill 系统、提示词工程
- 21 面试题第六弹：CLI 产品化、Git、Runtime API
- 22 面试题第七弹：多模型适配、运行时切换、成本控制

### 复盘篇

- 23 开发复盘：我们真实遇到的问题
- 24 一分钟项目介绍和高频追问
- 25 知识库卡片和复习路线

## 每篇实战文档怎么写

每篇实战篇都使用这个模板：

```text
这一篇学什么
为什么 Agent CLI 需要这个模块
PyAgentCLI 当前实现了什么
对应源码和命令
最小运行例子
源码阅读路线
我们开发时遇到的坑
简历上怎么写
面试官会怎么追问
标准回答思路
还能继续怎么增强
```

这样写的好处是：每一篇都能同时服务学习、开发、简历和面试。

## 每篇面试文档怎么写

每篇面试篇都使用这个模板：

```text
这一弹考什么
面试官为什么会问
简历里哪句话会触发这个追问
问题 01
  - 先给一句话答案
  - 再讲原理
  - 再落到 PyAgentCLI
  - 最后讲边界和不足
问题 02...
最后：本弹必背 5 句
```

面试文档不应该只是 FAQ。它应该像一次真实追问：从简历上的一句话开始，追到架构、实现、失败恢复、安全边界和效果评估。

## 当前项目完成度怎么讲

按求职展示：

- 核心 Agent Runtime：可讲。
- Tool Calling 和本地工具执行：可讲。
- Safety / HITL / Audit：可讲。
- RAG / Memory / Context：可讲。
- Plan / Reviewer / Eval：可讲。
- MCP / Skill / Browser：可讲基础版。
- 多模型、复杂浏览器交互、TUI、Runtime API、多模态：作为增强方向讲。

一句话边界：

> PyAgentCLI 已经足够作为完整 AI Agent 项目写进简历，但不应该夸成商业级 Claude Code 替代品。它的价值在于从底层实现并验证了 Agent Runtime 的关键工程链路。

## 我们自己的开发经历怎么用

v2 文档要把开发过程中的真实问题穿插进对应模块，而不是只放在最后。

例如：

- Browser 篇：Computer Use 能读 Safari，但点击/滚动受前台窗口和状态刷新影响。
- Browser 篇：Safari `do JavaScript` 需要额外开启 Apple Events 权限。
- Tool/HITL 篇：sandbox 网络权限导致不能直接 push，需要用户手动完成。
- Safety 篇：不能用 prompt 代替工具执行层的路径围栏和命令黑名单。
- Eval 篇：从 deterministic eval 扩展到 trace eval。
- Reviewer 篇：failed / skipped / cancelled step 不能被误判为 success。
- Memory 篇：记忆必须可见、可删除、可检查 stale。
- Skill 篇：Skill 是 prompt guidance，不是隐形工具权限。
- 多模型篇：不可用模型错误说明需要 model capability check。

这些经历会让项目更像真实工程，而不是概念拼盘。

## 来源说明

本路线参考 PaiCLI 登录态学习路线的组织方式和主题顺序，尤其是“实战篇 / 简历篇 / 面试篇”的结构。

参考页面：

- https://paicoding.com/paicli-learning-path
- https://paicoding.com/paicli-resume-write
- https://paicoding.com/react-plan-multi-agent
- https://paicoding.com/memory-context
- https://paicoding.com/tool-call-hitl
- https://paicoding.com/paicli-interview-mcp
- https://paicoding.com/paicli-interview-prompt-skill
- https://paicoding.com/paicli-interview-productization
- https://paicoding.com/paicli-interview-multi-model

注意：

- 只参考结构和主题顺序。
- 不复制付费正文。
- 不照搬 Java 技术栈。
- 所有 PyAgentCLI 文档都必须回到本仓库的 Python 实现、测试和真实开发经历。

## 下一步

接下来先重写：

1. [01 先跑通 PyAgentCLI](01_run_project.md)
2. [ReAct 和 Tool Calling](02_react_tool_calling.md)
3. [Plan-and-Execute / DAG](03_plan_execute_dag.md)
4. [Memory 系统](04_memory_system.md)
5. [RAG 代码检索](05_rag_code_retrieval.md)
6. [Tool Call、HITL 和安全策略](06_tool_hitl_safety.md)

等核心实战篇成型后，再重写简历篇和七弹面试篇。
