# PyAgentCLI MVP v0.1 任务拆解

## v0.1 目标

v0.1 的目标是跑通一个最小可用的 AI Coding Agent CLI：

> 用户在终端输入任务，Agent 能调用模型，模型能选择工具，工具能读取/写入文件和执行命令，高风险动作会请求用户审批，最终 Agent 给出结果。

v0.1 明确参考 PaiCLI 第一期的路线：先做最小 ReAct + Tool Call，但 Python 版本要在 MVP 阶段就加入路径围栏、审批和审计，避免 Agent 一开始就拥有无边界的文件和命令权限。

## v0.1 不追求

- 不做完整 RAG
- 不做长期 Memory
- 不做 MCP
- 不做浏览器自动化
- 不做复杂多 Agent
- 不做漂亮 UI
- 不做完整 Plan-and-Execute
- 不做工具并行执行

## 里程碑 1：项目骨架

### 任务

- 创建 `pyproject.toml`
- 创建 `src/pyagentcli` 包结构
- 添加 `README.md`
- 添加 `.env.example`
- 配置基础依赖：
  - `typer`
  - `rich`
  - `pydantic`
  - `python-dotenv`
  - `openai`
  - `pytest`

### 验收标准

- 能运行 `pyagent --help`
- 能运行 `pytest`
- 项目可以以 editable 模式安装

## 里程碑 2：CLI 与 REPL

### 任务

- 实现 `pyagent` 命令
- 支持单次任务：`pyagent "summarize this project"`
- 支持交互模式：`pyagent`
- REPL 支持退出命令：
  - `/exit`
  - `/quit`
  - Ctrl+C

### 验收标准

- 用户能进入交互式 CLI
- 用户输入会传入 Agent Loop
- Agent 响应能打印到终端

## 里程碑 3：LLM Client

### 任务

- 定义 `LLMClient` 抽象接口
- 实现 OpenAI-compatible client
- 支持读取：
  - `OPENAI_API_KEY`
  - `OPENAI_BASE_URL`
  - `PYAGENT_MODEL`
- 支持 tool schema 传入
- 统一返回模型文本和 tool calls

### 验收标准

- 可以发送普通 prompt 并得到回答
- 可以把工具 schema 传给模型
- 模型返回 tool call 时，Agent 能识别

## 里程碑 4：Tool 基础设施

### 任务

- 定义 `Tool`
- 定义 `ToolContext`
- 定义 `ToolResult`
- 实现 `ToolRegistry`
- 工具 schema 能转成 OpenAI-compatible function schema
- 工具执行结果统一包含：
  - `ok`
  - `content`
  - `error`
  - `metadata`

### 验收标准

- 能注册多个工具
- 能通过工具名查找并执行
- 工具失败不会导致整个 Agent 崩溃

## 里程碑 5：文件系统工具

### 任务

- `list_files(path: str = ".")`
- `read_file(path: str)`
- `write_file(path: str, content: str)`
- 路径统一解析为 workspace 内绝对路径
- 阻止 `../` 越界访问
- 写文件前接入审批

### 验收标准

- Agent 能读取 README 或代码文件
- Agent 能列出目录
- Agent 写入 workspace 内文件成功
- Agent 写入 workspace 外路径会被拒绝

## 里程碑 6：Shell 工具

### 任务

- `run_shell(command: str, timeout_seconds: int = 30)`
- 命令执行在 workspace 中进行
- 捕获 stdout、stderr、exit code
- 设置超时
- 接入命令黑名单
- 默认需要审批

### 验收标准

- Agent 能运行 `pwd`、`ls`、`pytest` 等命令
- 超时命令会被终止
- 高风险命令会被拒绝或要求审批
- stdout/stderr 会返回给模型

## 里程碑 7：Safety 与 Approval

### 任务

- 定义 `RiskLevel`
- 定义 `SafetyDecision`
- 实现基础策略：
  - read 默认允许
  - write 默认询问
  - shell 默认询问
  - critical 默认拒绝
- 实现 Rich 审批提示
- 支持 non-interactive 模式默认拒绝高风险动作

### 验收标准

- 读文件不打断用户
- 写文件前出现审批
- 命令执行前出现审批
- 用户拒绝后工具不会执行

## 里程碑 8：Audit Log

### 任务

- 创建 `.pyagent/audit.log.jsonl`
- 记录：
  - timestamp
  - user goal
  - tool name
  - tool args
  - risk level
  - approval decision
  - result status
  - error

### 验收标准

- 每次工具调用都有日志
- 审批结果可追踪
- 工具失败可追踪

## 里程碑 9：Agent Loop

### 任务

- 最大步数限制
- messages 管理
- tool call 执行
- tool result 回填
- 工具错误恢复提示
- 最终回答生成

### 验收标准

- Agent 至少能完成：
  - 列文件并总结项目
  - 读取指定文件并解释
  - 修改一个文本文件
  - 运行一个安全命令
- 工具失败后 Agent 能解释失败原因
- 超过最大步数会停止并说明原因

## 里程碑 10：测试与演示

### 任务

- 单元测试：
  - 路径围栏
  - 命令风险识别
  - 工具注册与执行
- 集成测试：
  - read-only 任务
  - write-file 任务
  - shell 任务
- 写 README 演示脚本

### 验收标准

- `pytest` 通过
- README 能指导用户跑通 v0.1
- 有一个完整 demo transcript

## 推荐开发顺序

1. 项目骨架
2. CLI / REPL
3. Tool 基础设施
4. 文件工具
5. Safety / Approval
6. Shell 工具
7. LLM Client
8. Agent Loop
9. Audit Log
10. 测试和 README

这个顺序的好处是：先把本地可测的工具与安全边界做好，再接模型，调试成本更低。

## PaiCLI 参考后的 v0.1 最小闭环

为了保持实现聚焦，v0.1 的核心闭环应该只包含：

```text
User Input
  -> Agent Loop
  -> LLM with tool schemas
  -> tool_calls?
    -> Safety Policy
    -> Approval if needed
    -> Tool Execution
    -> Audit Log
    -> Tool Result back to LLM
  -> Final Answer
```

v0.1 可以先不实现 `create_project`，因为创建项目结构会自然引出模板、依赖安装、命令执行和多文件写入，范围会膨胀。更合适的做法是先支持 `write_file` 和 `run_shell`，等安全审批稳定后再把 `create_project` 作为组合工具加入。

## v0.1 后的紧邻升级

v0.1 完成后，下一步不是马上做全部高级能力，而是按 PaiCLI 的经验补三个最容易形成项目亮点的模块：

1. Plan Preview：让模型先输出步骤，用户能看懂 Agent 准备怎么做。
2. RAG Lite：先做 `@file`、`@folder`、ripgrep 检索，不急着上 embedding。
3. Diff Approval：写文件前展示变更摘要，让人工审批有依据。

## v0.1 Definition of Done

- `pyagent` 可以启动
- 可以与 OpenAI-compatible 模型通信
- 模型可以调用工具
- 支持 `list_files/read_file/write_file/run_shell`
- 写入和命令执行有审批
- 路径越界会被拒绝
- 工具调用写入审计日志
- 至少 3 个测试用例通过
- README 中有可复现 demo
