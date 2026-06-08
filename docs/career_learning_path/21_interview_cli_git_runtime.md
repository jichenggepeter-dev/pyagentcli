# 21 面试题第六弹：CLI 产品化、Git、Runtime API

这一弹对应 PyAgentCLI 的产品化能力。

面试官问到这里，通常不是想听“我会用 argparse 写命令行”，而是想判断：

```text
这个 Agent 项目是不是一个真的开发者工具？
用户怎么安装、运行、恢复、复盘？
副作用怎么可见？
Git diff 怎么纳入复核？
Runtime API 现在做到哪里，未来怎么设计？
```

这一弹要把 CLI 讲成 Agent Runtime 的用户入口，而不是一个命令行壳子。

## 这一弹考什么

这一弹主要考 7 个能力：

1. 你是否能解释 CLI 产品化和 demo 的区别。
2. 你是否能讲清 PyAgentCLI 的命令结构和使用场景。
3. 你是否理解 workspace、本地 runtime state、非交互模式的安全意义。
4. 你是否能讲清 Plan 的 show/list/resume/retry/skip 为什么是产品能力。
5. 你是否能讲清 Git diff 与 Reviewer 的关系。
6. 你是否能诚实区分“已实现 Git diff review”和“未实现 GitHub 自动化”。
7. 你是否能设计 Runtime API，而不是只加一个 HTTP 壳。

对应源码：

```text
src/pyagentcli/cli/main.py
src/pyagentcli/cli/repl.py
src/pyagentcli/__main__.py
src/pyagentcli/config.py
src/pyagentcli/agent/plan_store.py
src/pyagentcli/agent/plan_executor.py
src/pyagentcli/agent/reviewer.py
src/pyagentcli/evals/runner.py
pyproject.toml
tests/test_packaging.py
docs/release_checklist.md
README.md
```

对应实战文档：

- [12 产品化：CLI UX、Git、Runtime API](12_productization_cli_git_runtime.md)

## 哪些简历句子会触发这一弹

如果简历里写：

> 从 0 到 1 构建 Python 版本地 AI Coding Agent CLI，提供 `pyagent` console script、task/REPL 双模式、workspace 运行边界、Plan Preview、审批后执行、计划恢复/重试/跳过、RAG index、Memory、Eval、Browser capability check 和 release checklist；使用 `.pyagent/` 持久化 plans、audit logs、memory、reviews、eval reports，实现可运行、可复盘、可验证的 Agent Runtime。

面试官会追问：

- 你所谓“产品化”具体做了什么？
- CLI UX 和 argparse 有什么区别？
- 为什么要有 `--workspace`？
- `.pyagent/` 存什么？
- `--no-input` 有什么用？
- Git diff 怎么被 Reviewer 使用？
- 为什么不直接让 Agent 自动 git push？
- Runtime API 现在实现了吗？未来怎么做？

## 面试开场 30 秒回答

如果面试官问“你这个 CLI 怎么产品化”，可以先这样答：

> PyAgentCLI 的 CLI 不是只把 AgentLoop 包一层 argparse，而是把开发者使用 Agent 的核心链路做成可安装、可演示、可恢复、可复盘的本地工具。`pyagent` 支持 task mode 和 REPL mode，`--workspace` 明确文件读写和 `.pyagent/` 运行态边界，`--plan` 只生成无副作用计划，`--execute-plan` 需要审批后执行，执行后的 plan 可以 show、list、resume、retry、skip。RAG、Memory、Eval、Browser check 也都有独立命令。Reviewer 会读取 PlanRun、audit log 和 git diff，生成风险、测试建议和 gate decision。当前已经实现的是本地 CLI runtime 和 git diff review，还没有做自动 commit/push/PR，也没有 Runtime API server；未来 Runtime API 我会先设计 run event model，再接 HTTP/Web dashboard。

## Q1：CLI 产品化和 demo 的区别是什么？

一句话答案：

> demo 证明能力存在，产品化证明能力能被安装、运行、排错、恢复、验证和发布。

展开回答：

很多 Agent demo 是：

```text
写一个脚本
传一个 prompt
调用一次模型
打印结果
```

这能证明“模型可以调用工具”，但不等于开发者工具。

开发者工具要回答：

- 用户怎么安装？
- 不传任务时怎么办？
- 没有 API key 能不能跑？
- 工作区怎么指定？
- 哪些命令会产生副作用？
- 失败后怎么恢复？
- 运行日志在哪里？
- 改了哪些文件怎么复核？
- 发布前怎么检查？

PyAgentCLI 的产品化重点就是把这些问题落到 CLI、runtime state、review、eval 和 docs。

## Q2：PyAgentCLI 当前 CLI surface 有哪些？

一句话答案：

> 它不是单命令工具，而是一组围绕 Agent Runtime 的入口：任务执行、REPL、Plan、RAG、Memory、Eval、Skill、Browser 和模型检查。

当前命令入口包括：

```bash
pyagent --help
pyagent "summarize this workspace"
pyagent
pyagent --workspace examples/demo_workspace --index
pyagent --workspace examples/demo_workspace --memory
pyagent --remember "Prefer focused diffs."
pyagent --plan "fix failing tests"
pyagent --execute-plan "fix failing tests"
pyagent --list-plans
pyagent --show-plan <plan_id>
pyagent --resume-plan <plan_id>
pyagent --retry-step <plan_id> <step_id>
pyagent --skip-step <plan_id> <step_id>
pyagent --eval
pyagent --eval-real-model
pyagent --eval-compare-models
pyagent --list-skills
pyagent --check-model
pyagent --check-browser
```

这背后的设计不是“命令越多越好”，而是覆盖开发者使用 Agent 的生命周期：

```text
安装 -> 检查 -> 运行 -> 计划 -> 执行 -> 失败恢复 -> 复核 -> 评估 -> 发布
```

## Q3：CLI UX 为什么不是简单 argparse？

一句话答案：

> argparse 只是参数解析，CLI UX 是用户能不能安全、清楚、可恢复地使用这个 Agent。

PyAgentCLI 的 CLI UX 包括：

- 默认行为：传 goal 就执行任务，不传 goal 就进 REPL。
- 边界控制：`--workspace` 明确工作区。
- 副作用提示：`--plan` 只预览，`--execute-plan` 才执行。
- 非交互安全：`--no-input` 下审批动作默认不能偷偷执行。
- 恢复路径：`--resume-plan`、`--retry-step`、`--skip-step`。
- 自检路径：`--check-model`、`--check-browser`。
- 验证路径：`--eval`、release checklist。

所以面试里不能只说：

```text
我用 argparse 做了 CLI。
```

更好的说法是：

```text
我把 Agent runtime 的关键状态和副作用边界暴露成 CLI 操作，让用户能预览、审批、恢复和复盘。
```

## Q4：task mode 和 REPL mode 有什么区别？

一句话答案：

> task mode 适合一次性目标，REPL mode 适合连续交互；两者都复用同一套 AgentLoop 和工具安全链路。

task mode：

```bash
pyagent "summarize README"
```

特点：

- 一次命令对应一个 goal。
- 适合脚本化、演示、eval。
- 完成后退出。

REPL mode：

```bash
pyagent
```

特点：

- 不传 goal 时进入交互。
- 用户可以连续输入任务。
- 每轮输入都会经过上下文增强。
- 出错后可以继续输入。

面试重点：

> REPL 不是另一个 Agent，它只是同一个 Agent runtime 的交互式入口。

## Q5：`--workspace` 为什么重要？

一句话答案：

> 因为 Coding Agent 会读写文件、执行命令、保存运行态，所以必须有明确的工作区边界。

如果没有 workspace，Agent 很容易出现：

- 读错目录。
- 写错项目。
- memory 和 eval report 混到另一个项目。
- 路径围栏无法判断越权。
- audit log 没有项目归属。

PyAgentCLI 通过 workspace 控制：

```text
workspace_root
  -> SafetyPolicy path guardrail
  -> ToolContext
  -> .pyagent/
  -> RAG index
  -> memory
  -> plans
  -> reviews
  -> eval reports
```

这也是为什么命令示例经常写：

```bash
pyagent --workspace examples/demo_workspace --eval
```

面试时可以补一句：

> 对 Coding Agent 来说，workspace 不是普通配置项，而是安全边界、运行态边界和上下文边界。

## Q6：`.pyagent/` 是什么？

一句话答案：

> `.pyagent/` 是本地 runtime state 目录，用来保存 Agent 运行过程中的可复盘证据。

它可以包含：

```text
.pyagent/
  audit.log.jsonl
  plans/
  reviews/
  memory/
  rag/
  eval_reports/
  browser/
  scheduled/
```

不同内容的意义：

- `plans/`：PlanPreview、PlanRun、step status、handoff。
- `reviews/`：Reviewer 生成的 markdown 复核报告。
- `audit.log.jsonl`：工具调用、审批、失败、耗时。
- `memory/`：项目记忆、session summary。
- `rag/`：本地检索 index。
- `eval_reports/`：评估报告。
- `browser/`：浏览器截图、console/network artifact。

面试官可能追问：

> 为什么不把这些都放 stdout？

回答：

> stdout 适合即时反馈，但 Agent 的计划、审计、复核和 eval 需要跨命令读取。`.pyagent/` 让运行态可恢复、可复盘、可删除，也能避免污染源码目录结构。

## Q7：`--no-input` 的安全意义是什么？

一句话答案：

> `--no-input` 让 CLI 进入非交互模式，任何需要人工审批的动作都不能假装用户同意。

为什么重要？

Agent CLI 可能跑在：

- CI。
- 脚本。
- eval harness。
- 后台任务。
- 用户不在终端前的场景。

如果这个时候模型请求写文件或执行 shell，CLI 不能自动批准。

所以 PyAgentCLI 的思路是：

```text
interactive=True
  -> WRITE/EXECUTE 可以展示 preview 后问用户

interactive=False
  -> 需要审批的动作默认 denied
```

这能防止：

- 非交互脚本中偷偷改文件。
- eval 过程中执行危险命令。
- 模型把无用户确认当成同意。

## Q8：为什么 `--plan` 必须无副作用？

一句话答案：

> Plan Preview 是给用户审查的，如果预览阶段已经执行工具，就破坏了审批意义。

`--plan` 的职责：

```text
goal
  -> Planner
  -> PlanPreview
  -> persist plan
  -> print plan
```

它不应该：

- 写文件。
- 执行 shell。
- 调用会产生副作用的工具。
- 修改项目状态，除了保存 plan runtime artifact。

`--execute-plan` 才进入：

```text
preview plan
  -> ask approval
  -> Executor step run
  -> Reviewer
```

面试里可以这样说：

> `--plan` 和 `--execute-plan` 的拆分，是把“决策前透明”和“审批后执行”分开，避免 Agent 在用户没看计划前就产生副作用。

## Q9：show/list/resume/retry/skip 为什么是产品化能力？

一句话答案：

> 因为真实 coding task 会失败，产品化工具必须给用户恢复和接管路径。

如果只有：

```bash
pyagent --execute-plan "fix bug"
```

一旦中间失败，用户只能重新开始。

PyAgentCLI 增加：

```bash
pyagent --list-plans
pyagent --show-plan <plan_id>
pyagent --resume-plan <plan_id>
pyagent --retry-step <plan_id> <step_id>
pyagent --skip-step <plan_id> <step_id>
pyagent --set-step-status <plan_id> <step_id> <status>
```

意义是：

- `list`：知道有哪些历史计划。
- `show`：复盘计划和 step status。
- `resume`：从失败或暂停处继续。
- `retry`：重置某一步和后续步骤。
- `skip`：用户接管某一步后继续。
- `set-step-status`：手动修正 runtime state。

这和真实开发体验一致：

> Agent 不可能永远一次成功，所以恢复能力比“看起来很智能”更重要。

## Q10：Packaging 怎么做？

一句话答案：

> PyAgentCLI 通过 `pyproject.toml` 声明包元数据、console script 和 optional extras，并用 packaging tests 防止发布配置漂移。

当前 metadata：

```toml
[project]
name = "pyagentcli"
version = "0.1.0"
requires-python = ">=3.11"

[project.scripts]
pyagent = "pyagentcli.cli.main:main"

[project.optional-dependencies]
dev = ["pytest>=8"]
browser = ["playwright>=1.44"]
```

对应测试：

```text
tests/test_packaging.py
```

验证：

- project name。
- version。
- Python version。
- README。
- console script。
- `src/pyagentcli/__main__.py`。
- browser optional dependency。
- README quickstart 命令。

面试时可以说：

> 我没有只写 README 声称能安装，而是用 tests/test_packaging.py 检查 console script、metadata 和 quickstart，避免发布时入口坏掉。

## Q11：Release checklist 解决什么问题？

一句话答案：

> Release checklist 把“我觉得能发”变成一组可重复验证的发布步骤。

当前 checklist 包括：

```bash
python -m pip install -e ".[dev]"
python -m pytest
pyagent --help
pyagent --workspace examples/demo_workspace --index
pyagent --workspace examples/demo_workspace --eval
```

还要求检查：

- `pyproject.toml` metadata。
- README quickstart。
- roadmap。
- execution plan。
- 新 CLI flag 是否有文档。
- GitHub Actions 是否绿色。
- release notes 是否写 known limitations。

这对面试很重要：

> 它证明你知道项目不是写完代码就结束，而是要能被别人安装、验证、复现。

## Q12：Git diff 和 Reviewer 有什么关系？

一句话答案：

> Reviewer 会读取 git diff，把实际改动纳入复核，而不是只相信 Agent 的文字总结。

Reviewer 读取：

```text
PlanRun
step status
audit log
git diff
changed files
changed-file risk scoring
```

当前逻辑包括：

- 判断 workspace 是否是 git repo。
- 读取 `git diff HEAD --numstat`。
- 读取 diff hunk 摘要。
- 解析 changed files。
- 对改动路径做风险评分。
- 给出 suggested tests。

比如：

```text
src/pyagentcli/safety/policy.py
  -> high risk
  -> safety boundary path changed
  -> suggest tests/test_safety_policy.py

docs/guide.md
  -> low risk
  -> documentation changed
  -> suggest rendered wording check
```

这能避免一个常见问题：

> Agent 说自己完成了，但实际 git diff 改了高风险文件，或者改动范围和计划不一致。

## Q13：为什么 Reviewer 不直接等于 GitHub PR review？

一句话答案：

> 当前 Reviewer 是本地执行后的复核报告，不是 GitHub PR 自动化系统。

它已经做：

- 本地 git diff summary。
- 改动文件风险评分。
- risk notes。
- suggested tests。
- gate decision。
- retry proposal。
- review markdown artifact。

它还没有做：

- 自动创建 branch。
- 自动 `git add`。
- 自动 commit。
- 自动 push。
- 自动创建 PR。
- 自动评论 GitHub review thread。

面试里要诚实：

> 我现在实现的是 local reviewer gate，把执行后的文件改动和 plan 状态纳入复核。GitHub 自动化是下一阶段，应该从只读 status/diff 开始，再到 commit proposal，push 和 PR 必须强审批。

## Q14：为什么不直接让 Agent 自动 push GitHub？

一句话答案：

> 因为 push/PR 是外部副作用，涉及网络、身份、远端仓库状态和不可轻易回滚的协作影响，不能默认自动执行。

直接自动 push 的风险：

- 推错分支。
- 推送未审查 diff。
- 泄露本地文件。
- 覆盖用户未提交变更。
- 网络认证失败。
- 触发 CI 或自动部署。
- 让用户误以为远端已经同步。

我们开发时也遇到过真实问题：

```text
本地 commit 可以完成
但 GitHub push 会受到网络、认证、sandbox、用户环境影响
```

这说明 GitHub 自动化不能被包装成“模型想推就推”。

更合理的路线：

```text
git status / git diff read-only
  -> commit proposal
  -> user approves selected files
  -> git add selected
  -> git commit after approval
  -> push only after explicit approval
  -> PR creation with explicit target branch
```

## Q15：Runtime API 当前实现了吗？

一句话答案：

> 当前 PyAgentCLI 还没有 Runtime API server，但 CLI 代码里已经有可以复用的 service function，未来可以把它们包装成 API。

当前已存在的可调用函数包括：

```text
run_agent_task(...)
plan_task(...)
execute_planned_task(...)
resume_plan(...)
retry_step(...)
set_step_status(...)
run_evals(...)
index_workspace(...)
show_memory(...)
remember_note(...)
compress_memory(...)
list_skills(...)
check_browser(...)
```

这些函数说明：

> CLI 不是所有逻辑都写在 argparse 分支里，已经有一批可被未来 API/TUI/后台任务复用的入口。

但边界也要说清楚：

> 还没有 HTTP server、WebSocket、run subscription、trace viewer 或 remote worker。

## Q16：未来 Runtime API 应该怎么设计？

一句话答案：

> 先设计事件模型和 run lifecycle，再设计 HTTP 路由，而不是先套 FastAPI。

为什么？

Agent run 不是普通同步函数。

它会产生：

- LLM request。
- tool call。
- approval request。
- tool result。
- plan update。
- memory update。
- review result。
- eval result。
- failure/retry。

所以 Runtime API 的核心应该是事件流：

```text
run.started
llm.requested
llm.responded
tool.requested
tool.approval_required
tool.approved
tool.denied
tool.completed
tool.failed
plan.created
step.started
step.completed
step.failed
review.completed
eval.completed
run.completed
run.failed
```

HTTP 路由可以是：

```text
POST /runs
GET /runs/{run_id}
GET /runs/{run_id}/events
POST /runs/{run_id}/approvals/{approval_id}
POST /plans
POST /plans/{plan_id}/resume
POST /plans/{plan_id}/steps/{step_id}/retry
GET /memory
POST /memory
POST /evals
```

但真正重要的是：

> 前端、CLI、后台 worker、eval harness 看到的是同一条 run event stream。

## Q17：Runtime API 怎么处理 HITL 审批？

一句话答案：

> API 不能绕过审批，而是要把审批变成显式 pending event。

错误设计：

```text
POST /runs
  -> server 自动批准所有 tool calls
```

正确设计：

```text
tool.approval_required
  -> API 暂停该 tool call
  -> UI/CLI 展示 preview
  -> user approve/deny
  -> tool.approved 或 tool.denied
  -> runtime 继续
```

也就是说：

- approval 是 run lifecycle 的一部分。
- preview 必须可见。
- deny 也要记录。
- 非交互模式不能假装 approve。
- 审批结果要进入 audit log。

这和当前 CLI 的 `ApprovalHandler` 思路一致。

## Q18：Runtime API 和 CLI 的关系是什么？

一句话答案：

> CLI 是当前产品入口，Runtime API 是未来把同一套 Agent 能力开放给 TUI、Web dashboard、后台 worker 和外部系统的接口。

合理关系：

```text
CLI
  -> service functions
  -> Agent runtime

Runtime API
  -> same service layer
  -> same Agent runtime

TUI / Web dashboard
  -> Runtime API
```

不应该：

```text
CLI 一套逻辑
API 另一套逻辑
Dashboard 再写一套逻辑
```

否则会出现：

- 安全策略不一致。
- eval 结果不一致。
- memory 写入不一致。
- plan state 不一致。
- audit log 不完整。

面试里可以说：

> 我会把 CLI 当成第一版 runtime consumer，未来 Runtime API 应该复用同一组 run/plan/eval/memory service，而不是复制业务逻辑。

## Q19：如果做 TUI 或 Web dashboard，顺序是什么？

一句话答案：

> 先把 run event model 和 local artifact 打通，再做界面。

推荐顺序：

```text
1. 定义 run event schema
2. CLI 运行时写 event stream
3. Reviewer/Eval 读取同一套 event
4. 本地 dashboard 展示 runs/plans/tools/reviews
5. 加 approval UI
6. 再考虑远程 Runtime API
```

为什么不能先做漂亮 dashboard？

因为没有事件模型时，dashboard 只能展示静态结果。

真正有价值的是：

- 实时看 Agent 正在做什么。
- 看 tool call 参数和 preview。
- 审批或拒绝风险动作。
- 看 step 状态。
- 看 reviewer gate。
- 看 eval trace。

所以 TUI/Web 的核心不是 UI，而是 runtime observability。

## Q20：怎么讲当前产品化程度而不过度包装？

一句话答案：

> 已实现的讲成事实，未实现的讲成路线，并说明为什么这个顺序合理。

可以讲：

```text
已实现：
- pyagent console script
- python -m pyagentcli
- task mode / REPL mode
- workspace boundary
- no-input safety behavior
- plan preview / execute / resume / retry / skip
- RAG / Memory / Eval / Skill / Browser check
- .pyagent local runtime state
- Reviewer git diff summary and changed-file risk scoring
- packaging tests
- release checklist

未实现：
- Runtime API server
- TUI
- Web dashboard
- GitHub PR automation
- automatic commit/push
- hosted trace viewer
- cost dashboard
```

面试中这样表达更可信：

> 当前 v0.1 是本地 CLI runtime，重点是把 Agent 的工具调用、安全审批、计划执行、复核和评估做成可运行闭环。下一阶段我会先补 runtime event model 和只读 git status/diff，再做 commit proposal、Runtime API 和 dashboard。

## Q21：开发中遇到过哪些真实问题？

一句话答案：

> 最大的问题不是“代码写不出来”，而是长项目里状态、边界、工具权限和远端环境很容易被混在一起。

我们真实遇到过：

1. 长对话会压缩上下文。

   解决方式：

   - 把 roadmap、execution plan、学习文档落盘。
   - 每次继续前检查 `git status` 和关键文档。
   - 用 commit 记录每个阶段。

2. GitHub push 不等于本地 commit。

   解决方式：

   - 本地提交由 repo 完成。
   - push 涉及网络、认证、sandbox 和用户环境。
   - 不把 push 成功包装成 Agent 自动能力。

3. 定时任务不等于 Agent 自动恢复。

   解决方式：

   - cron 可以提醒或写 handoff。
   - 但不能保证 Codex 对话自动恢复。
   - 真正可靠的是把 handoff 文档写清楚。

4. Computer Use / 登录态不是稳定数据源。

   解决方式：

   - 能看网页就参考结构和栏目。
   - 不能把对方原文复制进项目。
   - 最终文档必须回到 PyAgentCLI 自己的实现事实。

5. 不存在的模型调用会中断流程。

   解决方式：

   - 避免依赖不可用模型。
   - 出错后先检查刚改了什么文件。
   - 回到 git status 和当前任务继续。

这些坑都可以写进面试：

> 我在项目里不仅实现功能，也不断把协作和运行过程中遇到的问题沉淀成文档、检查清单和恢复流程。

## Q22：如果自己开发这个模块，最容易踩什么坑？

一句话答案：

> 最容易把 CLI 写成命令集合，而不是围绕 Agent 生命周期设计的产品入口。

常见坑：

- 只写 `run`，没有 `plan`。
- 只有执行，没有预览。
- 只有成功路径，没有失败恢复。
- 没有 workspace，直接操作当前目录。
- `.pyagent/` 运行态结构混乱。
- eval report、review report、audit log 放置不一致。
- 非交互模式默认批准风险动作。
- Git push 和 commit 没有人审。
- Runtime API 先写 HTTP，后补事件，结果无法实时追踪。
- CLI、API、dashboard 各写一套逻辑。

避免方式：

```text
先画 Agent lifecycle
再定义 runtime state
再暴露 CLI commands
再补 recovery commands
最后考虑 API / dashboard
```

## 现场画图

面试时可以画这张：

```text
User
  |
  v
pyagent CLI
  |
  +-- task mode
  +-- REPL mode
  +-- plan / execute-plan
  +-- memory / index / eval
  |
  v
Service functions
  |
  v
Agent Runtime
  |
  +-- AgentLoop
  +-- Planner / Executor / Reviewer
  +-- ToolRegistry
  +-- SafetyPolicy / Approval / Audit
  +-- Memory / RAG / Skill
  |
  v
.pyagent local state
  |
  +-- plans
  +-- reviews
  +-- audit logs
  +-- memory
  +-- eval reports
  +-- browser artifacts
```

如果继续讲未来 Runtime API：

```text
CLI / TUI / Web dashboard
  |
  v
Runtime API
  |
  v
Run Event Stream
  |
  +-- tool.approval_required
  +-- tool.completed
  +-- step.completed
  +-- review.completed
  +-- run.completed
```

## 必背 8 句

1. CLI 产品化不是 argparse，而是让 Agent 能被安装、运行、恢复、复盘和验证。
2. `--workspace` 是 Coding Agent 的安全边界、运行态边界和上下文边界。
3. `.pyagent/` 保存 plans、reviews、audit logs、memory、eval reports 和 browser artifacts。
4. `--plan` 必须无副作用，`--execute-plan` 才进入审批后执行。
5. show/list/resume/retry/skip 是为真实失败恢复设计的，不是装饰性命令。
6. Reviewer 读取 git diff 和 changed files，避免只相信 Agent 的文字总结。
7. 当前实现了本地 git diff review，还没有实现自动 commit/push/PR。
8. Runtime API 应该先设计 run event model，再设计 HTTP 路由。

## 一版完整回答

如果面试官问：

> 你这个项目怎么体现 CLI 产品化？Git 和 Runtime API 做到哪里？

可以这样答：

> PyAgentCLI 的产品化不是简单把 AgentLoop 包成 argparse，而是围绕本地 Coding Agent 的完整生命周期设计 CLI。它提供 `pyagent` console script 和 `python -m pyagentcli`，支持一次性 task mode 和 REPL mode；所有命令都可以用 `--workspace` 指定工作区，这个 workspace 同时是工具路径围栏、RAG、Memory 和 `.pyagent/` 本地运行态边界。对于复杂任务，`--plan` 只生成无副作用的 PlanPreview，`--execute-plan` 会展示计划并要求审批后执行；失败后可以 `--show-plan`、`--list-plans`、`--resume-plan`、`--retry-step`、`--skip-step`，所以不是一次失败就重来。RAG、Memory、Eval、Skill、Browser capability check 也都有独立 CLI 入口。
>
> Git 方面，我当前没有把自动 commit/push/PR 包装成已实现能力，因为这些是外部副作用，涉及分支、认证、网络和 CI。已实现的是 Reviewer 在执行后读取本地 git diff、numstat、changed files 和 hunk 摘要，对文件路径和改动大小做风险评分，并生成 risk notes、suggested tests 和 gate decision。比如改到 safety policy 或 tool execution path 会被标成高风险，提示跑对应测试。未来 GitHub 自动化会从只读 status/diff 开始，再到 commit proposal，只有用户强审批后才 add/commit/push。
>
> Runtime API 现在还没有 HTTP server，但 CLI 代码已经拆出 `run_agent_task`、`plan_task`、`execute_planned_task`、`resume_plan`、`run_evals`、`index_workspace`、`remember_note` 等 service function。下一步如果做 API，我不会先套一个 FastAPI 壳，而是先定义 run event model，比如 `run.started`、`tool.approval_required`、`tool.completed`、`step.completed`、`review.completed`、`run.completed`，让 CLI、TUI、Web dashboard 和 eval harness 都消费同一条事件流。这样安全审批、审计、恢复和可观测不会被不同入口写散。

## 复习顺序

建议按这个顺序复习：

1. 先读 [12 产品化：CLI UX、Git、Runtime API](12_productization_cli_git_runtime.md)。
2. 再看 `src/pyagentcli/cli/main.py`，理解每个 flag 对应的 runtime function。
3. 看 `tests/test_packaging.py`，理解 release-ready metadata 怎么测试。
4. 看 `docs/release_checklist.md`，记住发布前验证命令。
5. 看 `src/pyagentcli/agent/reviewer.py`，重点读 git diff summary 和 changed-file risk scoring。
6. 最后背“完整回答”。

## 下一弹

下一弹：

> 面试题第七弹：多模型适配、运行时切换、成本控制。

重点会讲：

- OpenAI-compatible client。
- Local fallback。
- role-specific model config。
- eval real model opt-in。
- model comparison。
- 模型能力声明。
- 成本和稳定性边界。
