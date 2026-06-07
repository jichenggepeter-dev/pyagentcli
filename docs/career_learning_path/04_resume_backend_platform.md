# 04 简历篇：后端 / 平台 / 工具岗位写法

这一篇面向后端工程、平台工程、开发者工具、基础设施岗位。

同一个 PyAgentCLI 项目，如果投后端/平台岗位，重点要从“AI 概念”切换到：

- CLI 工程
- 工具注册
- 配置系统
- 安全策略
- 持久化
- 测试
- 发布
- 可观测性

## 项目描述

推荐版本：

> 设计并实现面向开发者的本地 AI Agent Runtime，将模型输出的工具调用转化为受控的本地文件操作、命令执行、代码检索和浏览器检查流程。系统内置工具权限、路径围栏、危险命令拦截、人工审批、审计日志、计划持久化、Reviewer gate 和可复现评估体系，强调安全、可观测和可扩展。

这个版本弱化“我会 AI”，强化“我会工程化落地 AI”。

## 技术栈写法

推荐：

> Python 3.12、CLI、SQLite、TOML、JSONL、pytest、GitHub Actions、MCP、Playwright optional

如果岗位偏平台：

> Python、Agent Runtime、Tool Registry、Safety Policy、Plan Store、Audit Log、Eval Harness、Packaging

## 后端/平台方向核心职责

### 1. CLI 和配置系统

可写：

> 设计 CLI 命令体系和项目配置加载机制，支持 `.env`、`pyagent.toml`、workspace root、模型配置、MCP server 配置、embedding 配置和角色级 model/prompt 配置。

可以展开：

- `pyagent --help`
- `pyagent --eval`
- `pyagent --index`
- `pyagent --plan`
- `pyagent --execute-plan`
- `pyagent --check-browser`

面试追问：

- CLI 参数如何组织？
- `.env` 和 shell env 谁优先？
- workspace root 如何解析？

### 2. Tool Registry

可写：

> 实现统一 Tool Registry，支持工具 schema 暴露、工具分发、执行计时、失败包装和审计日志记录。

可以展开：

- 工具实现统一 `schema()` 和 `run()`。
- registry 维护工具名到工具实例的映射。
- 工具失败不会让 Agent 崩溃，而是变成 observation。
- preview 失败也会被审计。

面试追问：

- 如何新增一个工具？
- 工具参数如何验证？
- 工具失败怎么处理？

### 3. Safety Policy

可写：

> 构建本地安全策略，按 READ / WRITE / EXECUTE / NETWORK / CRITICAL 对工具分级，并在执行前做路径围栏、命令黑名单和人工审批。

可以展开：

- READ 默认允许。
- WRITE 需要审批。
- EXECUTE 需要审批。
- NETWORK 和 CRITICAL 默认拒绝。
- shell 命令黑名单拦截危险模式。

面试追问：

- 为什么审批在工具执行前？
- 路径围栏怎么实现？
- 如何防止 prompt injection 要求删除文件？

### 4. 持久化和运行态

可写：

> 使用 `.pyagent/` 作为本地运行态目录，持久化计划、记忆、审计日志、评估报告、浏览器产物和 review markdown，保证 Agent 行为可追踪、可恢复、可删除。

可以展开：

- `.pyagent/plans/`
- `.pyagent/memory/`
- `.pyagent/evals/`
- `.pyagent/reviews/`
- `.pyagent/browser/`
- `.pyagent/audit.log.jsonl`

面试追问：

- 为什么运行态不提交到 git？
- 为什么 memory 要可删除？
- audit log 记录什么？

### 5. SQLite FTS 和索引

可写：

> 基于 SQLite FTS 构建轻量本地代码索引，结合 AST symbol chunk 和 import graph 支持文件、文本、符号和依赖关系检索。

可以展开：

- 不引入重型向量数据库。
- FTS 能满足很多精确检索场景。
- AST chunk 提升代码符号定位能力。
- import graph 帮助理解模块依赖。

面试追问：

- 为什么不用 Elasticsearch？
- SQLite FTS 优缺点是什么？
- 如何处理索引过期？

### 6. Eval Harness

可写：

> 构建 deterministic eval harness，覆盖平台能力、coding task、RAG retrieval、trace eval，并输出 JSONL report，用 task success、tool-call accuracy、safety violation 等指标评估 Agent 行为。

可以展开：

- 平台 eval：工具注册、安全、memory、RAG。
- coding eval：检查文件是否按预期改变。
- RAG eval：检查 symbol / dependency retrieval。
- trace eval：检查工具调用序列和 forbidden tools。

面试追问：

- Agent 评估为什么不能只看最终文本？
- 怎么判断工具调用是否准确？
- safety violation 怎么定义？

### 7. 发布工程

可写：

> 完成 Python packaging 和 release 工程化，配置 `pyagent` console script、package metadata 测试、GitHub Actions、CLI smoke 和 release checklist。

可以展开：

- `pyproject.toml`
- `project.scripts`
- optional dependency extra
- package metadata tests
- CI smoke
- release checklist

面试追问：

- editable install 和源码运行区别？
- optional dependency 为什么要拆？
- clean checkout 如何验证？

## 后端方向简历 bullet

```text
- 基于 Python 设计本地 Agent CLI 工程架构，完成配置加载、命令路由、工具注册、运行态持久化、审计日志、测试和发布工程。
- 实现 Tool Registry 和 Safety Policy，支持工具 schema 暴露、风险分级、路径围栏、危险命令拦截、人工审批和执行审计。
- 使用 SQLite FTS 和 AST 解析构建轻量代码索引，支持符号级检索、依赖关系查询和 stale index warning。
- 设计 `.pyagent/` 本地运行态，持久化 memory、plans、reviews、eval reports 和 browser artifacts，提升 Agent 行为可观测性。
- 构建 pytest + GitHub Actions 回归体系，覆盖 150+ 用例，并增加 CLI smoke、package metadata 和 optional browser tests。
```

## 面试时如何从 AI 拉回工程

如果面试官觉得 Agent 项目太“概念”，你可以这样讲：

> 这个项目不是只调模型。我花更多精力在工程边界上：工具如何注册、风险如何分级、路径如何限制、审计如何记录、计划如何持久化、测试如何回归、可选依赖如何降级。这些都是把 AI Agent 接进真实开发环境必须解决的问题。

这会让后端面试官更容易认可。

