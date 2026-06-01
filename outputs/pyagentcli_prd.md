# PyAgentCLI 产品需求文档

## 1. 项目概述

PyAgentCLI 是一个面向开发者的本地 AI Coding Agent CLI。它借鉴 Claude Code、Codex CLI、PaiCLI Agent 教程中的 Agent 思路，但不复制教程内容，而是从 0 到 1 用 Python 实现一个可运行、可扩展、可评估的 AI 编程助手。

项目核心目标不是做一个普通聊天 CLI，而是让 AI 能在本地项目中完成真实开发任务：理解需求、读取代码、检索上下文、调用工具、修改文件、执行命令、恢复错误，并在高风险动作前请求用户审批。

## 2. 产品定位

### 目标用户

- 想在终端中使用 AI 辅助开发的工程师
- 想学习 AI Agent 架构、Tool Calling、RAG、Memory、MCP 的开发者
- 想把 AI Agent 项目写进简历并能在面试中讲清楚的求职者

### 使用场景

- 在本地代码库中让 Agent 解释、修改、重构代码
- 让 Agent 自动读取文件、搜索符号、执行测试、修复报错
- 对高风险命令进行人工审批与审计
- 对项目建立索引，让 Agent 按 `@file`、`@folder`、`@symbol` 注入上下文
- 多 Agent 协作完成复杂任务：Planner 拆解、Executor 执行、Reviewer 检查

## 3. 核心价值

### 对开发者

- 降低手动找文件、读上下文、运行命令、修复错误的成本
- 用终端完成连续的 AI 编程工作流
- 本地执行、边界清晰、权限可控

### 对学习与面试

- 覆盖 ReAct、Function Calling、RAG、Memory、MCP、HITL、多 Agent、Eval 等 Agent 核心能力
- 项目边界足够完整，能体现系统设计能力
- 不依赖复杂前端，重点放在 Agent 工程实现

## 4. 产品原则

1. 本地优先：默认在用户本地项目中运行。
2. 安全优先：文件写入、命令执行、网络访问需要风险分级与审批。
3. 可解释：Agent 每一步决策、工具调用、结果都应可追踪。
4. 可扩展：工具、模型、MCP、Skill、多 Agent 都应能插件化扩展。
5. 可评估：不能只靠“感觉聪明”，需要任务成功率、工具调用成功率、人工介入率等指标。

## 5. 功能范围

### v0.1 MVP

目标：跑通最小 AI Coding Agent 闭环。

- CLI 启动与交互式 REPL
- OpenAI-compatible LLM 调用
- ReAct / Tool Calling Agent Loop
- 基础工具：
  - `list_files`
  - `read_file`
  - `write_file`
  - `run_shell`
- 工具注册表
- 简单路径围栏
- 基础人工审批
- 工具调用日志
- 最小端到端案例：读取项目、修改文件、运行测试或命令

### v0.2 Safety

目标：让 Agent 有明确安全边界。

- 工具风险分级：read / write / execute / network / destructive
- 命令黑名单与高风险模式识别
- 路径 allowlist / denylist
- 审批策略：
  - always allow
  - ask once
  - ask every time
  - deny
- 审计日志：用户请求、模型输出、工具调用、审批结果、执行结果

### v0.3 RAG

目标：让 Agent 能理解中大型代码库。

- 代码文件扫描与过滤
- chunk 策略
- SQLite 元数据存储
- embedding 接口
- 向量检索或轻量本地检索
- `@file`、`@folder`、`@symbol` 上下文注入
- 检索结果引用与去重

### v0.4 Memory

目标：让 Agent 在 session、project、user 三层保存经验。

- session memory：当前任务短期状态
- project memory：项目结构、约定、常用命令
- user memory：用户偏好
- 上下文压缩：把长对话总结成可复用状态

### v0.5 Multi-Agent

目标：支持角色分工。

- Planner：拆解任务和制定执行计划
- Executor：调用工具完成代码修改
- Reviewer：检查变更、风险、测试覆盖
- 简单调度器：控制 Agent 间消息流

### v0.6 Extensions

目标：开放扩展能力。

- MCP client
- Playwright 浏览器工具
- Skill loader
- Eval harness

## 6. 非目标

### MVP 不做

- 不做复杂图形界面
- 不做完整 IDE 插件
- 不做大型分布式 Agent 系统
- 不默认允许危险命令
- 不追求一次性覆盖所有模型厂商

### 项目长期也应谨慎做

- 不绕过用户系统权限
- 不自动执行破坏性操作
- 不把用户代码上传到非用户配置的服务

## 7. 用户体验

### 典型交互

```text
$ pyagent
PyAgentCLI ready. Workspace: /path/to/project

> 帮我看看这个项目怎么启动

Agent: 我先查看项目文件结构。
Tool: list_files(".")
Tool: read_file("README.md")
Agent: 项目使用 pytest 测试，入口在 src/...，建议先运行 ...

> 帮我修复 failing tests

Agent: 我会先运行测试定位失败。
Approval required: run_shell("pytest")
Approve? [y/N]
```

### CLI 模式

- `pyagent`：进入 REPL
- `pyagent "fix failing tests"`：单次任务
- `pyagent index`：建立代码索引
- `pyagent memory show`：查看项目记忆
- `pyagent eval run`：运行评估用例

## 8. 成功指标

### 产品指标

- 能在新项目中 5 分钟内完成安装与首次运行
- 能完成基础文件读写和命令执行任务
- 高风险工具调用前能稳定触发审批
- Agent Loop 能在失败后继续恢复，而不是直接崩溃

### 工程指标

- 工具调用有结构化日志
- 核心模块有单元测试
- MVP 有至少 3 个端到端评估用例
- 关键安全策略有测试覆盖

## 9. 风险与应对

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| Agent 无限循环 | 浪费 token，卡住任务 | 最大步数、超时、重复调用检测 |
| 工具误写文件 | 破坏用户项目 | 路径围栏、diff 预览、审批 |
| 命令执行危险操作 | 数据损坏 | 黑名单、风险分级、人工确认 |
| RAG 检索噪声大 | 上下文污染 | chunk 策略、重排、引用来源 |
| Memory 写入垃圾信息 | 长期误导 Agent | 显式保存、用户确认、定期清理 |

