# 12 产品化：CLI UX、Git、Runtime API

这一篇讲 PyAgentCLI 的产品化。

前面 11 篇已经把核心能力拆开讲了：

- Agent Loop
- Plan-and-Execute
- Memory
- RAG
- Tool Safety
- Multi-Agent
- Browser
- MCP
- Skill
- 多模型适配

但一个项目能不能写进简历，不能只看“功能列表”。

真正会被追问的是：

> 这个东西是不是一个可以被开发者安装、运行、排错、演示、评估、发布和复盘的 CLI 产品？

这就是产品化要解决的问题。

## 这一篇学什么

你要掌握 8 件事：

1. CLI UX 不只是 `argparse`，而是命令结构、默认行为、错误提示和演示路径。
2. PyAgentCLI 当前有哪些可用命令。
3. 为什么 `.pyagent/` 是本地 runtime state，而不是普通源码。
4. Git 和 Reviewer 为什么有关。
5. GitHub push、sandbox、审批为什么属于真实产品化问题。
6. Packaging、console script、release checklist 怎么支撑项目发布。
7. Runtime API 目前是什么状态，未来应该怎么设计。
8. 简历和面试里怎么把“工程化”讲清楚。

一句话：

> 产品化不是给 Agent 加更多能力，而是让能力变得可运行、可解释、可验证、可恢复、可发布。

## 为什么 Agent CLI 需要产品化

很多 Agent demo 的问题是：

```text
能跑一次，但很难复现
能演示，但无法安装
能调用模型，但不能排错
能写文件，但没有审计
能回答问题，但没有 eval
能做计划，但失败后不能 resume
```

这样的项目看起来像 demo，不像开发者工具。

PyAgentCLI 的目标不是“做一个聊天壳”，而是做一个本地 AI Coding Agent CLI。

所以它必须回答：

- 用户怎么安装？
- 用户怎么知道有哪些命令？
- 没有 API key 能不能先跑？
- 真实模型怎么检查？
- 工作区怎么指定？
- 运行态文件放哪里？
- 失败后怎么恢复？
- 改了哪些文件怎么复核？
- eval report 放哪里？
- 发布前怎么检查？
- GitHub 推送失败怎么办？
- 未来怎么接 Runtime API？

这些问题都属于产品化。

## PyAgentCLI 当前产品化实现了什么

当前已经实现：

- `pyagent` console script。
- `python -m pyagentcli` 模块入口。
- `--help` 命令文案。
- task mode：直接传 goal。
- REPL mode：不传 goal 进入交互。
- `--workspace` 指定工作区。
- `--no-input` 非交互模式。
- `--check-model` 模型 tool-calling 探针。
- `--plan` 只预览计划。
- `--execute-plan` 审批后执行计划。
- `--show-plan` / `--list-plans`。
- `--resume-plan` / `--retry-step`。
- `--set-step-status` / `--skip-step`。
- `--index` 构建 RAG index。
- `--memory` / `--remember` / `--compress-memory`。
- `--delete-memory-line` / `--stale-memory-days`。
- `--eval`。
- `--eval-real-model`。
- `--eval-compare-models`。
- `--list-skills`。
- `--check-browser`。
- `scripts/demo.sh`。
- `docs/release_checklist.md`。
- packaging metadata tests。
- optional browser extra。

当前还没有实现：

- TUI。
- LSP integration。
- Git commit / branch / PR 自动工具。
- Runtime API server。
- Web dashboard。
- plugin marketplace。
- token/cost dashboard。
- distributed agent run。
- hosted trace viewer。

这些要标注为未来增强，不能写成已完成。

## 对应源码

CLI 入口：

```text
src/pyagentcli/cli/main.py
src/pyagentcli/cli/repl.py
src/pyagentcli/__main__.py
```

Packaging：

```text
pyproject.toml
tests/test_packaging.py
```

Demo / release / troubleshooting：

```text
scripts/demo.sh
docs/demo_script.md
docs/dev_setup.md
docs/testing.md
docs/release_checklist.md
docs/troubleshooting.md
README.md
```

Plan runtime：

```text
src/pyagentcli/agent/plan_store.py
src/pyagentcli/agent/reviewer.py
```

Local runtime state：

```text
.pyagent/
```

## CLI UX 的核心设计

一个 CLI 工具首先要做到：

```text
用户知道怎么开始
用户知道自己在哪个 workspace
用户知道命令会不会产生副作用
用户知道失败后怎么恢复
用户知道结果在哪里
```

PyAgentCLI 的 CLI surface 不是随机长出来的，而是按几类使用场景组织。

### 1. 直接任务模式

最直接的使用方式：

```bash
pyagent "summarize this workspace"
```

如果传了 goal，CLI 进入 task mode。

执行路径：

```text
parse args
  |
  v
run_agent_task
  |
  v
enrich_goal
  |
  v
AgentLoop.run
  |
  v
ProjectMemory.record_session
```

这条路径适合短任务。

### 2. REPL 模式

如果不传 goal：

```bash
pyagent
```

会进入 REPL：

```text
PyAgentCLI ready. Type /exit or /quit to leave.
>
```

REPL 适合连续对话式任务。

它的产品化价值是：

- 用户不用每次重新启动。
- 每次输入都能经过 `goal_transform`。
- 出错时 CLI 不直接崩溃，而是打印 `Error: ...` 后继续。

这很像真实工具的容错体验。

### 3. Workspace 模式

命令都可以指定：

```bash
pyagent --workspace examples/demo_workspace --index
```

为什么 workspace 很重要？

因为 Agent CLI 不是普通 chatbot。

它会读写文件、保存 memory、生成 plans、写 audit log。

所有这些都必须有一个明确边界：

```text
workspace_root
```

否则很容易出现：

- 读错目录。
- 写错项目。
- 把运行态写到用户当前 shell 的任意位置。
- RAG index 和 memory 混乱。
- 安全策略无法做路径围栏。

所以 `--workspace` 是产品化命令，不只是技术参数。

### 4. 非交互模式

PyAgentCLI 支持：

```bash
pyagent --no-input "read README"
```

非交互模式下：

- read-only 工具可以运行。
- 需要审批的写入和执行默认拒绝。

这适合：

- CI。
- eval。
- demo automation。
- 只读诊断。

重要边界：

> 非交互模式不能悄悄绕过人工审批。

这体现了安全产品化。

## 命令分组

PyAgentCLI 的命令可以按产品功能分成 8 组。

### 1. 运行和帮助

```bash
pyagent --help
pyagent
pyagent "task"
```

作用：

- 查看 CLI surface。
- 进入 REPL。
- 执行一次性任务。

### 2. 模型检查

```bash
pyagent --check-model
```

作用：

- 验证真实模型是否能返回 tool call。
- 避免复杂任务中才发现模型不可用。

### 3. Plan-and-Execute

```bash
pyagent --plan "fix failing tests"
pyagent --execute-plan "fix failing tests"
pyagent --list-plans
pyagent --show-plan PLAN_ID
pyagent --resume-plan PLAN_ID
pyagent --retry-step PLAN_ID STEP_ID
pyagent --set-step-status PLAN_ID STEP_ID STATUS
pyagent --skip-step PLAN_ID STEP_ID
```

作用：

- 计划预览。
- 人工审批。
- 执行恢复。
- 手动状态管理。

这是 Agent CLI 和普通 chatbot 的重要区别。

### 4. RAG

```bash
pyagent --index
```

作用：

- 构建 SQLite FTS code index。
- 为 `@file/@folder/@symbol` 提供基础。

### 5. Memory

```bash
pyagent --remember "Prefer edit_file for small edits."
pyagent --memory
pyagent --compress-memory
pyagent --delete-memory-line 2
pyagent --stale-memory-days 30
```

作用：

- 管理项目记忆。
- 清理过期记忆。
- 防止 memory 污染长期上下文。

### 6. Eval

```bash
pyagent --eval
pyagent --eval --eval-real-model
pyagent --eval --eval-compare-models
```

作用：

- 默认 deterministic eval。
- 显式真实模型 eval。
- 显式多模型比较。

### 7. Skill

```bash
pyagent --list-skills
```

作用：

- 查看 `.pyagent/skills` 下的 prompt-only skills。
- 诊断 skill 是否被加载。

### 8. Browser

```bash
pyagent --check-browser
```

作用：

- 检查 optional Playwright browser capability。
- 避免用户以为 browser 能力默认完整可用。

## `.pyagent/` 本地运行态

PyAgentCLI 会在 workspace 下写：

```text
.pyagent/
```

它不是普通业务源码，而是本地 Agent runtime state。

里面可能包括：

```text
audit logs
plans
search index
memory
reviews
eval reports
browser artifacts
skills
```

为什么要集中放在 `.pyagent/`？

因为这让运行态可管理：

- 用户知道 Agent 产生了什么。
- RAG 可以跳过 `.pyagent/`，避免把 runtime state 注入模型。
- Git 可以默认忽略这些文件。
- Reviewer 和 Memory 可以读取 audit log。
- Eval report 有固定位置。
- 排查问题时有证据链。

这就是本地 Agent 的“产品后台”。

即使没有 Web UI，也要有运行态目录。

## Git 在 PyAgentCLI 里的角色

PyAgentCLI 当前没有实现 Git 工具自动 commit / push。

但 Git 已经进入了 Reviewer 逻辑。

Reviewer 会读取：

```text
git diff
```

并生成：

```text
Git diff summary
```

这样任务执行后可以复核：

- 哪些文件改了。
- 增加了多少行。
- 删除了多少行。
- 有没有 uncommitted diff。

这很重要。

Coding Agent 最危险的问题之一是：

> Agent 说完成了，但你不知道它到底改了什么。

Git diff 是本地事实。

Reviewer 把它纳入 review report，可以减少“假成功”。

## GitHub Push 是产品化坑

我们开发时遇到过 GitHub push 相关限制。

典型情况：

```text
本地 commit 可以做
远端 push 需要网络、认证或用户设备权限
sandbox 可能阻止网络
Computer Use 可以操作桌面，但也有能力边界
```

这不是小插曲，而是 Agent 产品化里很真实的问题。

因为 Coding Agent 经常会被要求：

```text
改代码
提交
推到 GitHub
开 PR
```

但这些步骤风险不同：

- 本地 diff review：低风险。
- git add / commit：中风险，需要确认提交范围。
- git push：涉及远端状态、认证、网络。
- 开 PR：涉及外部平台。
- merge：高风险。

所以产品化设计不能把它们混成一个“自动完成”。

更合理的分层是：

```text
local edit
  |
  v
local review
  |
  v
local commit
  |
  v
remote push
  |
  v
PR / release
```

每一步都应该有：

- 状态检查。
- 人工确认。
- 可回滚路径。
- 清晰错误提示。

我们现在的项目文档里已经把 GitHub push troubleshooting 写清楚：

```bash
git init
git add .
git commit -m "Initial PyAgentCLI project"
git remote add origin git@github.com:OWNER/REPO.git
git push -u origin main
```

但未来如果要把 Git 做成工具，应该走安全分级。

## Packaging

PyAgentCLI 的 packaging 在：

```text
pyproject.toml
```

核心信息：

```toml
[project]
name = "pyagentcli"
version = "0.1.0"
requires-python = ">=3.11"

[project.scripts]
pyagent = "pyagentcli.cli.main:main"
```

这意味着用户可以：

```bash
python -m pip install -e ".[dev]"
pyagent --help
```

而不是每次都写：

```bash
PYTHONPATH=src python -m pyagentcli ...
```

这一步很小，但对产品化非常重要。

因为一个 CLI 项目要让别人用，必须有稳定入口。

## Packaging Tests

PyAgentCLI 有：

```text
tests/test_packaging.py
```

它检查：

- project name。
- version。
- requires-python。
- readme。
- description。
- console script。
- `__main__.py`。
- browser optional dependency。
- README quick start。

这说明什么？

> 发布工程不是只靠人工记忆，而是可以测试的。

这类测试虽然不复杂，但很适合简历讲：

> 我不只是写功能，还把 CLI 安装、入口和 release metadata 纳入回归测试。

## Release Checklist

PyAgentCLI 有：

```text
docs/release_checklist.md
```

它覆盖：

1. Metadata。
2. Local verification。
3. Documentation。
4. GitHub Release。
5. Known v0.1 Scope。

发布前命令包括：

```bash
python -m pip install -e ".[dev]"
python -m pytest
pyagent --help
pyagent --workspace examples/demo_workspace --index
pyagent --workspace examples/demo_workspace --eval
```

这就是产品化的另一个关键：

> 发布不是“感觉差不多了”，而是有 checklist。

Known scope 也很重要。

比如：

- 没 API key 时 local fallback。
- 真实模型需要 OpenAI-compatible env。
- MCP 是 v0.1。
- Browser 是 local inspection 优先。

这能避免过度承诺。

## Demo Script

项目有：

```text
scripts/demo.sh
docs/demo_script.md
```

它们提供一条可演示路径：

```text
help
index
symbol context injection
memory
plan preview
eval
real model demo
architecture close
```

这很重要。

因为面试或展示时，不能临时想：

```text
我应该先跑哪个命令？
这个命令会不会要 API key？
这个 demo workspace 能不能复现？
```

产品化项目应该有一条固定 demo script。

它能证明：

- CLI 能启动。
- RAG 能 index。
- context injection 能工作。
- memory 能写入和查看。
- plan 能预览。
- eval 能跑。

## Runtime API 当前状态

当前 PyAgentCLI 还没有独立 Runtime API server。

也就是说，项目现在主要是：

```text
CLI / REPL
  |
  v
Python runtime functions
  |
  v
local state under .pyagent/
```

不是：

```text
HTTP API server
  |
  v
agent run database
  |
  v
web dashboard
```

这点要讲清楚。

但是当前代码已经有一些 Runtime API 的雏形：

- `run_agent_task(...)`
- `plan_task(...)`
- `execute_planned_task(...)`
- `resume_plan(...)`
- `retry_step(...)`
- `run_evals(...)`
- `index_workspace(...)`
- `show_memory(...)`
- `remember_note(...)`
- `check_browser(...)`

这些函数都是 CLI 命令背后的可调用入口。

未来如果要做 Runtime API，可以把这些函数包成服务层。

## 未来 Runtime API 应该怎么设计

一个合理的 Runtime API 可以包括：

```text
POST /runs
GET  /runs/{run_id}
GET  /runs/{run_id}/events
POST /plans
GET  /plans/{plan_id}
POST /plans/{plan_id}/approve
POST /plans/{plan_id}/resume
POST /plans/{plan_id}/steps/{step_id}/retry
GET  /memory
POST /memory
POST /index
POST /evals
GET  /evals/{eval_id}
```

核心不是“加个 FastAPI 就完了”。

真正关键的是事件模型：

```text
run.started
llm.requested
llm.responded
tool.requested
tool.approved
tool.denied
tool.completed
plan.created
step.started
step.completed
review.completed
run.completed
run.failed
```

有了事件模型，才能做：

- Web dashboard。
- streaming output。
- trace viewer。
- remote orchestration。
- audit export。
- human approval UI。
- eval replay。

所以 Runtime API 的本质是：

> 把现在 CLI 里的同步流程，升级成可观察、可恢复、可订阅的 Agent Run 状态机。

## CLI 产品化和安全的关系

产品化不能牺牲安全。

有些命令看起来只是 UX，但其实是安全边界。

例如：

```bash
--workspace
```

它决定路径围栏。

```bash
--no-input
```

它决定是否允许需要人工审批的工具。

```bash
--plan
```

它允许用户先看计划，不执行工具。

```bash
--execute-plan
```

它要求执行前审批。

```bash
--eval-real-model
```

它防止默认 eval 产生外部模型费用。

```bash
--check-browser
```

它防止用户误以为 browser 能力默认完整启用。

所以 CLI flags 不是随便加的。

它们是用户控制 Agent 风险的界面。

## CLI 产品化和学习路线的关系

PaiCLI 学习路线里很强调从项目实践走到简历和面试。

PyAgentCLI 这里对应的是：

```text
不是只讲 Agent 概念
而是能用命令演示每个模块
```

比如：

```text
ReAct / Tool Calling -> pyagent "task"
Plan-and-Execute    -> --plan / --execute-plan
RAG                 -> --index / @symbol
Memory              -> --remember / --memory
Skill               -> --list-skills
Browser             -> --check-browser
Eval                -> --eval
Multi-model         -> --check-model / --eval-compare-models
```

这就是学习文档和产品化的连接点。

每个概念都应该能落到一个命令。

## 我们开发时遇到的坑

### 坑 1：远端 GitHub push 不是纯代码问题

我们遇到过：

- 网络权限受限。
- sandbox 普通请求被 block。
- 需要用户设备或账号授权。
- Computer Use 插件并不等于可以无边界操作所有东西。

这说明：

> 外部平台操作天然需要 HITL 和权限边界。

合理做法是：

- 本地继续完成文档和 commit。
- 保持 git status 干净。
- 需要远端 push 时让用户确认或手动完成。
- 不绕过 sandbox。

### 坑 2：过长对话会让项目状态变模糊

我们讨论过长上下文、自动压缩和 fork 新对话的问题。

这其实也是产品化问题。

如果项目只靠聊天上下文，状态会变得脆弱。

所以我们把状态沉淀到：

- docs。
- roadmap。
- execution plan。
- git commits。
- Obsidian 文档。
- `.pyagent/` runtime state。

这样即使上下文压缩，也能继续。

### 坑 3：文档和代码不同步

Agent 项目特别容易出现：

```text
文档写得很宏大
代码只实现了一点点
```

我们在每一篇都尽量写：

- 当前已实现。
- 当前没实现。
- 未来增强。

这可以防止简历过度包装。

### 坑 4：CLI 命令太多但没有分组

命令多了以后，如果文档不分组，用户会迷路。

所以第 12 篇把命令分成：

- run/help
- model check
- plan
- RAG
- memory
- eval
- skill
- browser

产品化不是少命令，而是让命令有结构。

### 坑 5：把 release 当成最后一步

很多项目只在最后才想：

```text
怎么发布？
怎么跑测试？
README 对不对？
版本号对不对？
```

但真正的工程项目要提前准备：

- pyproject metadata。
- console script。
- package tests。
- release checklist。
- demo script。

PyAgentCLI 已经把这些作为 v0.1 的一部分。

## 如果你自己开发会遇到的坑

### 坑 1：只实现功能，不设计 CLI 信息架构

新手容易把所有命令堆在一起：

```text
--do-this
--do-that
--magic
--run-agent
--agent-run
```

最后用户不知道怎么开始。

更好的方式是先按用户任务分组：

```text
run
plan
memory
index
eval
diagnostics
```

### 坑 2：没有 demo workspace

如果没有固定 demo workspace，每次演示都依赖当前项目状态。

这会导致：

- 演示不可复现。
- RAG index 结果不同。
- Memory 被污染。
- eval 不稳定。

所以要有：

```text
examples/demo_workspace
```

### 坑 3：没有 release checklist

没有 checklist 的发布容易漏：

- 版本号。
- README。
- console script。
- test。
- known limitations。

对 Agent 项目尤其危险，因为能力边界很多。

### 坑 4：把 Git 自动化做得太激进

如果你一开始就让 Agent 自动：

```text
git add .
git commit
git push
```

风险很高。

更合理的是：

1. 先做 git diff review。
2. 再做 scoped add。
3. 再做 commit message。
4. 再请求 push 审批。
5. 最后才考虑 PR 自动化。

### 坑 5：没有本地 runtime state

如果 plans、memory、audit、eval 都只是打印到终端，就没法复盘。

Agent 产品一定需要持久化：

```text
.pyagent/
```

哪怕一开始只是 JSONL 和 JSON 文件。

### 坑 6：太早做 Web UI

Web UI 很诱人，但如果 runtime 没有稳定事件模型，UI 只是壳。

更好的顺序是：

```text
CLI
  -> local state
  -> event model
  -> Runtime API
  -> dashboard / TUI / web UI
```

## 简历上怎么写

偏 AI Agent 工程：

> 将 PyAgentCLI 产品化为可安装的本地 AI Coding Agent CLI，设计 `pyagent` console script、任务/REPL 双模式、workspace 边界、Plan/Memory/RAG/Eval/Skill/Browser 等命令体系，并通过 `.pyagent/` 本地运行态持久化 plans、audit logs、memory、reviews 和 eval reports，提升 Agent 执行的可复盘性和可恢复性。

偏后端 / 平台：

> 构建 PyAgentCLI 的 CLI 产品化和发布工程：基于 `pyproject.toml` 配置 package metadata、console entrypoint 与 optional browser extra，补充 packaging tests、demo script、release checklist 和 troubleshooting 文档，形成从本地安装、功能演示、回归测试到 GitHub release 的交付链路。

偏 Agent 安全：

> 设计 Agent CLI 的用户控制面：通过 `--workspace` 固定路径围栏，`--no-input` 约束非交互执行，`--plan/--execute-plan` 分离计划与执行，`--eval-real-model` 显式控制外部模型调用，避免本地自动化在文件、命令、模型和远端平台操作中越权。

偏 Runtime API 方向：

> 在 CLI runtime 基础上抽象 plan、run、eval、memory、index 等可调用入口，为后续 Runtime API、trace event stream、human approval UI 和 Web dashboard 预留服务层边界。

## 面试官会怎么追问

### Q1：你说产品化，具体做了什么？

一句话答案：

> 我把 PyAgentCLI 从能跑的 agent loop 扩展成可安装、可演示、可评估、可恢复、可发布的本地 CLI 工具。

展开回答：

- `pyagent` console script。
- task mode 和 REPL mode。
- `--workspace`。
- plan show/list/resume/retry。
- `.pyagent/` runtime state。
- demo script。
- release checklist。
- packaging tests。

### Q2：CLI UX 里最重要的设计是什么？

一句话答案：

> 让用户知道命令是否会产生副作用，并且能在失败后恢复。

展开回答：

- `--plan` 不执行工具。
- `--execute-plan` 执行前审批。
- `--no-input` 不绕过审批。
- `--workspace` 固定边界。
- plan 持久化后可 resume/retry。

### Q3：`.pyagent/` 是什么？

一句话答案：

> `.pyagent/` 是工作区内的本地 Agent runtime state 目录。

展开回答：

- 保存 audit logs。
- 保存 plans。
- 保存 memory。
- 保存 eval reports。
- 保存 reviews。
- RAG 应该跳过它。
- Git 通常应忽略它。

### Q4：为什么 Git diff 对 Reviewer 重要？

一句话答案：

> 因为 Git diff 是任务执行后最可靠的本地事实之一，可以防止 Agent 假成功。

展开回答：

- Reviewer 读取 plan status。
- 读取 audit log。
- 读取 git diff。
- 如果有 uncommitted diff，提醒用户 review。
- 如果没有 diff，也会明确说明。

### Q5：为什么不直接让 Agent 自动 push GitHub？

一句话答案：

> 因为 push 涉及远端状态、认证、网络和不可逆协作影响，需要更高等级的人工确认。

展开回答：

- 本地 edit 和 remote push 风险不同。
- sandbox 和网络权限可能阻止 push。
- Agent 可以准备 commit。
- push / PR 应该显式审批。
- merge 更应该由用户决定。

### Q6：Runtime API 当前实现了吗？

一句话答案：

> 当前还没有独立 HTTP Runtime API，但 CLI 背后的函数已经形成服务层雏形。

展开回答：

- `run_agent_task`。
- `plan_task`。
- `execute_planned_task`。
- `resume_plan`。
- `run_evals`。
- `index_workspace`。
- `remember_note`。
- 未来可包装成 API。

### Q7：如果以后做 Runtime API，最关键是什么？

一句话答案：

> 最关键不是 HTTP endpoint，而是 Agent Run 的事件模型和状态机。

展开回答：

- run started。
- llm requested。
- tool requested。
- tool approved。
- tool completed。
- step completed。
- review completed。
- run completed。
- run failed。

有了事件模型，才能做 trace viewer、streaming、approval UI 和 replay。

### Q8：发布前怎么保证项目可用？

一句话答案：

> 用 release checklist 和 packaging tests，把安装、入口、README、eval 和 known limitations 都纳入检查。

展开回答：

- `python -m pip install -e ".[dev]"`。
- `python -m pytest`。
- `pyagent --help`。
- `pyagent --index`。
- `pyagent --eval`。
- README 和 roadmap 同步。
- 版本号和 tag 对齐。

### Q9：产品化和安全有什么关系？

一句话答案：

> CLI flags 本身就是用户控制 Agent 风险的界面。

展开回答：

- `--workspace` 控制路径边界。
- `--no-input` 控制审批行为。
- `--plan` 控制执行前预览。
- `--eval-real-model` 控制外部模型费用。
- `--check-browser` 控制可选浏览器能力诊断。

### Q10：这个项目现在产品化到什么程度？

一句话答案：

> v0.1 已经具备可安装 CLI、核心命令、文档、demo、eval、release checklist 和本地 runtime state，但还不是完整平台。

展开回答：

已实现：

- CLI。
- REPL。
- packaging。
- local runtime。
- eval。
- release checklist。

未实现：

- TUI。
- Runtime API server。
- Web dashboard。
- GitHub PR automation。
- hosted trace viewer。

## 标准回答思路

如果面试官让你整体讲产品化，可以这样回答：

> PyAgentCLI 的产品化不是只把 Agent Loop 包成命令行，而是把它做成一个开发者能安装、演示、排错、评估和发布的本地 CLI。入口上我用 `pyproject.toml` 声明 `pyagent` console script，也支持 `python -m pyagentcli`；使用方式上分 task mode 和 REPL mode，并用 `--workspace` 固定工作区边界。核心能力都落成 CLI 命令，比如 `--plan/--execute-plan` 管理计划，`--index` 管理 RAG，`--memory/--remember` 管理记忆，`--eval` 跑确定性评估，`--check-model` 检查模型 tool calling，`--check-browser` 检查可选浏览器能力。运行态集中写入 `.pyagent/`，包括 plans、audit logs、memory、reviews 和 eval reports，方便复盘和恢复。发布层面有 demo script、release checklist 和 packaging tests。当前还没有 Runtime API server，但 CLI 背后的 `run_agent_task`、`plan_task`、`run_evals` 等函数已经形成服务层雏形，后续可以抽象成 run event stream、approval UI 和 trace dashboard。

## 还能继续怎么增强

下一阶段可以增强：

- TUI。
- Git scoped add / commit proposal。
- GitHub PR integration。
- Runtime API server。
- run event stream。
- trace viewer。
- approval web UI。
- cost dashboard。
- config diagnostics。
- command groups / subcommands。
- shell completion。
- structured JSON output。
- dry-run mode。
- export audit report。
- release automation。

优先级建议：

### 1. CLI subcommands

现在 flags 已经很多。

未来可以改成：

```bash
pyagent run "task"
pyagent plan "task"
pyagent memory list
pyagent memory add "note"
pyagent index rebuild
pyagent eval run
pyagent model check
```

这样信息架构更清楚。

### 2. JSON output

给 CI 和其他工具用：

```bash
pyagent --eval --json
pyagent --show-plan PLAN_ID --json
```

### 3. Runtime API

先抽事件模型，再做 HTTP API。

不要先做 UI 壳。

### 4. Git Tooling

从低风险开始：

```text
git status
git diff summary
commit message proposal
scoped git add preview
commit after approval
push after approval
```

### 5. Trace Viewer

把 Agent run 的：

- messages。
- tool calls。
- approvals。
- observations。
- plan steps。
- reviewer report。

展示成可读 trace。

## 这一篇之后做什么

下一篇进入：

> [Eval Harness 和 Trace Eval](13_eval_harness_trace_eval.md)

产品化解决的是“这个 CLI 怎么被使用、交付和复盘”；Eval 要解决的是“怎么证明 Agent 真的完成了任务，以及怎么衡量工具调用、检索、Reviewer 和真实模型表现”。
