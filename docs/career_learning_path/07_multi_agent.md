# 07 Multi-Agent

这一篇对应 PaiCLI 学习路线里的 Multi-Agent 思路，但内容全部落到 PyAgentCLI 当前的 Python 实现。

先给结论：

> PyAgentCLI 当前实现的是角色化 Multi-Agent 工作流：Planner 负责计划，Executor 负责按步骤执行，Reviewer 负责复核和 gate。它不是多个自治 Agent 并发聊天，也不是多进程 Agent swarm。

这句话很重要。

Multi-Agent 很容易被讲虚。真正有价值的不是“我起了三个 Agent 名字”，而是：

- 每个角色的输入输出是什么。
- 谁能调用工具。
- 谁能改变状态。
- 谁能阻断成功。
- handoff 如何持久化。
- 失败后谁给恢复建议。

## 这一篇学什么

学完这一篇，你要能讲清楚：

- Multi-Agent 为什么不是堆概念。
- Planner / Executor / Reviewer 的职责边界。
- `PlanPreview`、`ExecutorStepContract`、`ReviewReport` 分别是什么。
- 为什么 Planner 不调用工具。
- 为什么 Executor 每次只执行一个 approved step。
- 为什么 Reviewer 不是总结器，而是 gate。
- Agent handoff 为什么要写进 plan JSON。
- model-backed reviewer suggestion 为什么不能覆盖 deterministic gate。
- 当前 Multi-Agent 的边界和下一步增强方向。

## 为什么需要 Multi-Agent

单个 Agent 处理复杂任务时，容易混在一起：

```text
一边规划
一边执行
一边自我评价
一边宣布完成
```

问题是：

- 规划阶段可能提前执行工具。
- 执行阶段可能越过计划。
- 复核阶段可能只是说“看起来不错”。
- 失败后不知道谁负责给恢复建议。

Multi-Agent 的价值不是让系统显得复杂，而是拆清职责：

```text
Planner: decide what should happen
Executor: do exactly the approved step
Reviewer: check whether the result is acceptable
```

一句面试答案：

> Multi-Agent 的价值在于职责隔离和可审计 handoff，而不是增加几个角色名。

## PyAgentCLI 当前实现了什么

当前已经落地的能力：

- `AgentRole`：`planner / executor / reviewer`。
- Planner 输出 `PlanPreview` 和 `PlanStep`。
- Planner 不调用工具。
- Executor 接收 `ExecutorStepContract`。
- Executor prompt 明确写 `Role: Executor Agent`。
- Executor 每次只执行一个 approved step。
- PlanExecutor 串行执行 steps。
- Executor handoff 记录 start、success、skipped、failed、finished。
- Reviewer 输出 `ReviewReport`。
- Reviewer 输出 `ReviewerGateDecision`。
- Reviewer gate 阻断 failed / skipped / cancelled。
- Review result 写回 plan JSON。
- Markdown review artifact 写到 `.pyagent/reviews/PLAN_ID.md`。
- optional model-backed reviewer suggestion。
- model suggestion 只能 advisory，不能覆盖 deterministic gate。
- role config 支持 planner / executor / reviewer 独立 model 和 system prompt。

当前还没有落地的能力：

- 多 Agent 并发执行。
- 多 Agent 对话协商。
- Scheduler Agent。
- Architect / Coder / Tester 更多角色。
- 跨进程 Agent runtime。
- Agent message bus。
- 真实 DAG 并行调度。
- Reviewer 自动调用工具复测。

所以最准确的表达是：

> PyAgentCLI 已实现 Planner / Executor / Reviewer 的角色化工作流和持久化 handoff，为后续更完整的 Multi-Agent 调度打基础。

## 角色总览

当前角色链路：

```text
Planner Agent
  -> PlanPreview / PlanStep
  -> planner handoff

Executor Agent
  -> ExecutorStepContract
  -> step execution
  -> executor handoffs

Reviewer Agent
  -> ReviewReport
  -> ReviewerGateDecision
  -> retry proposal
  -> reviewer handoff
```

持久化位置：

```text
.pyagent/plans/*.json
.pyagent/reviews/*.md
```

用户可以通过：

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --show-plan PLAN_ID
```

查看 plan、execution result、review result 和 handoffs。

## Planner Agent

源码：

```text
src/pyagentcli/agent/planner.py
```

Planner 的职责：

- 把用户目标拆成步骤。
- 输出 JSON plan。
- 给每个 step 标注 risk。
- 建议工具。
- 保持步骤小、可审查、可执行。

Planner 不做：

- 不调用工具。
- 不读文件。
- 不写文件。
- 不跑 shell。

Planner prompt 明确要求：

```text
Do not call tools.
Do not edit files.
Return only JSON.
```

Planner 输出：

```text
PlanPreview
  summary
  steps[]
    id
    title
    description
    suggested_tools
    risk
    status
    result_summary
```

如果模型没有返回合法 JSON，会 fallback 到：

```text
S1 Inspect workspace
S2 Apply minimal change
S3 Verify result
```

这说明 Planner 也不能完全信任模型输出。

## Executor Agent

源码：

```text
src/pyagentcli/agent/plan_executor.py
src/pyagentcli/agent/contracts.py
```

Executor 的职责：

- 接收一个 approved step。
- 使用工具读取或修改 workspace。
- 执行完成后总结当前 step。
- 更新 step status。

Executor 不应该：

- 自己重写计划。
- 跨 step 执行。
- 跳过审批。
- 自动重试高风险操作。

Executor 的输入 contract：

```text
ExecutorStepContract
  original_goal
  step_id
  title
  risk
  suggested_tools
  instructions
```

格式化后的 prompt 会写：

```text
Role: Executor Agent
Execute exactly this approved plan step.
Stop after this step and summarize what happened.
```

这个 contract 的意义是：

> Executor 不是拿到整个任务后自由发挥，而是被约束在当前 approved step 内。

## Reviewer Agent

源码：

```text
src/pyagentcli/agent/reviewer.py
src/pyagentcli/agent/contracts.py
```

Reviewer 的职责：

- 检查 plan status。
- 检查 step status。
- 汇总 audit log 里的工具和路径。
- 汇总 git diff。
- 生成 risk notes。
- 建议测试。
- 生成 gate decision。
- 生成 retry proposal。

Reviewer 不是：

- 不是文本总结器。
- 不是自动修复器。
- 不是自动 retry executor。
- 不是 deterministic gate 的替代者。

Reviewer gate 规则：

```text
failed -> block
skipped -> block
cancelled -> block
all success -> pass
```

WRITE / EXECUTE 风险本身不会 block，但会产生 risk notes 和 suggested tests。

如果 execution 标记 success，但 Reviewer 发现 skipped step：

```text
final plan status -> failed
```

这是 Reviewer 的工程价值。

## Handoff 是什么

源码：

```text
AgentHandoff
```

handoff 字段：

```text
role
summary
status
detail
step_id
next_action
```

它回答几个问题：

- 谁产生了计划。
- 谁开始执行。
- 哪一步完成了。
- 哪一步失败了。
- 哪一步被跳过。
- Reviewer 建议下一步做什么。

handoff 会写进：

```text
.pyagent/plans/*.json
```

也会通过 `--show-plan` 展示。

这让 Multi-Agent 不只是运行时概念，而是可复盘的工作流记录。

## Role Config

文档：

```text
docs/multi_agent.md
```

配置示例：

```toml
[agents.planner]
model = "gpt-4.1-mini"
system_prompt = "Plan with small, safe, reviewable steps."

[agents.executor]
model = "gpt-4.1-mini"
system_prompt = "Execute exactly the approved step and stop."

[agents.reviewer]
model = "gpt-4.1-mini"
system_prompt = "Review conservatively and recommend the next action."
```

当前行为：

- Planner 使用 planner model / prompt。
- Planned execution 使用 executor model / prompt。
- Reviewer deterministic gate 始终存在。
- 如果 reviewer 配了 model 且有 API key，会追加 model-backed suggestion。
- 如果角色没有配置 model，使用默认 `PYAGENT_MODEL`。

## Model-Backed Reviewer Suggestion

Reviewer 可以有模型建议，但只是 advisory。

模型收到的是 bounded JSON：

- user goal
- plan status
- step statuses
- risks
- deterministic gate result
- deterministic retry proposal
- git diff metadata

模型必须返回：

```json
{
  "summary": "...",
  "risk_notes": [],
  "suggested_tests": [],
  "recommended_action": "retry_step",
  "confidence": "high"
}
```

允许的 action：

```text
accept
retry_step
resume_plan
user_decision
inspect
```

但它不能：

- 覆盖 deterministic gate。
- 声称执行工具。
- 自动 retry。

如果模型输出不是 JSON，会降级成：

```text
recommended_action = inspect
confidence = low
```

## Retry Proposal

Reviewer 根据 step status 生成 proposal：

```text
failed -> retry_step
skipped -> user_decision
cancelled -> resume_plan
success -> none
```

例子：

```text
Retry proposal:
- Recommended action: retry_step
- Target step: S2
- Reason: The step failed during execution.
- Suggested command: `pyagent --retry-step PLAN_ID S2`
- Requires approval: yes
```

proposal 只是建议，不自动执行。

为什么？

> 自动 retry 可能绕过审批，尤其是写文件和 shell 操作。

## 和 Plan-and-Execute 的区别

第 03 篇讲的是 Plan-and-Execute：

- plan preview
- plan persistence
- execution
- resume
- retry
- skip
- status machine

这一篇讲的是 Multi-Agent：

- roles
- contracts
- handoffs
- reviewer gate
- role config
- advisory model reviewer

两者关系：

```text
Plan-and-Execute 是工作流骨架
Multi-Agent 是角色分工和交接协议
```

## 源码阅读路线

建议按这个顺序看：

1. `docs/multi_agent.md`
   - 先看角色总览和 role config。
2. `src/pyagentcli/agent/contracts.py`
   - 看 `AgentRole`、`ExecutorStepContract`、`ReviewerGateDecision`。
3. `src/pyagentcli/agent/planner.py`
   - 看 `PlanPreview`、`PlanStep`、`AgentHandoff`、`PlanRun`。
4. `src/pyagentcli/agent/plan_executor.py`
   - 看 executor handoff 和 step execution。
5. `src/pyagentcli/agent/reviewer.py`
   - 看 deterministic gate、retry proposal、model suggestion。
6. `src/pyagentcli/cli/main.py`
   - 看 planner/executor/reviewer role config 如何串起来。
7. `tests/test_planner.py`
   - 看 planner 不传 tools、fallback plan、retry reset。
8. `tests/test_plan_executor.py`
   - 看 executor serial steps、failure、resume、approval denied。
9. `tests/test_reviewer.py`
   - 看 gate、retry proposal、git diff、model suggestion。

## 我们协作时真实遇到的坑

### 1. Multi-Agent 不能写成“多个 Agent 名字”

我们一直避免把项目写成：

```text
有 Planner、Executor、Reviewer 三个 Agent
```

就结束。

更有说服力的是：

```text
Planner 输出 PlanPreview
Executor 接收 ExecutorStepContract
Reviewer 输出 ReviewReport 和 gate
handoff 写入 plan JSON
```

面试官听的是职责和边界，不是角色名。

### 2. Reviewer 不能只是“看起来不错”

我们专门做了 deterministic gate：

```text
failed / skipped / cancelled -> block
```

这避免 Reviewer 变成形式主义总结器。

### 3. skipped step 的 next action 容易写错

我们开发时曾把 skipped 的建议误写成 `retry_step`。

后来修正成：

```text
failed -> retry_step
skipped -> user_decision
cancelled -> resume_plan
```

这说明恢复策略要区分失败来源。

### 4. Model reviewer 不能覆盖 deterministic gate

模型可以给建议，但 gate 必须稳定。

否则模型一句：

```text
I think this is fine.
```

就可能绕过 skipped / failed 状态。

### 5. Executor 必须被 step contract 限制

如果 Executor 拿到整个原始目标，它可能做多步、越过审批、或者提前执行验证。

所以 PyAgentCLI 让它每次只执行一个 step，并要求：

```text
Stop after this step.
```

## 你自己开发时大概率会遇到的坑

### 1. 多个 Agent 共用同一个 prompt

如果 Planner、Executor、Reviewer 都用同一套 system prompt，角色只是名字。

至少要区分：

- planner prompt
- executor prompt
- reviewer prompt

PyAgentCLI 允许 role config。

### 2. Planner 可以调用工具

Planner 如果开始读文件、写文件，就和 Executor 混在一起。

Plan preview 阶段应该无副作用。

### 3. Executor 自由发挥

如果 Executor 拿到完整 plan，它可能一次做完所有步骤。

这会破坏 step status、审批和恢复。

正确做法是传 `ExecutorStepContract`。

### 4. Reviewer 没有 gate 权力

Reviewer 如果只返回文字：

```text
looks good
```

它对系统没有约束。

至少要有：

```text
passed: bool
reasons: list
```

### 5. Handoff 不持久化

如果 handoff 只存在内存里，任务结束后无法复盘。

PyAgentCLI 把 handoff 写入 plan JSON。

### 6. 自动执行 retry proposal

这是危险设计。

proposal 应该是建议，执行仍需用户审批。

### 7. 不区分 failed / skipped / cancelled

这三个状态恢复策略不同：

- failed：可以 retry。
- skipped：要用户重新决策。
- cancelled：要重新 resume approval。

### 8. Reviewer 自己调用工具修改文件

Reviewer 的职责是复核，不是偷偷修复。

如果未来让 Reviewer 调工具，也必须变成新的 approved step。

### 9. 忽略 git diff

Reviewer 不看 git diff，很难知道实际改了什么。

PyAgentCLI Reviewer v0.3 已加入 git diff summary。

### 10. 把当前实现夸成 Agent swarm

当前 PyAgentCLI 是角色化串行工作流。

不要写成：

```text
多 Agent 自主协商并并发完成任务
```

除非后续真的实现 message bus、scheduler、并发执行和冲突处理。

## 简历上怎么写

保守可信版：

> 设计 PyAgentCLI 的 Planner / Executor / Reviewer 多角色工作流：Planner 生成结构化计划，Executor 基于 step contract 执行已审批步骤，Reviewer 基于 step status、audit log 与 git diff 进行 deterministic gate，并将 handoff、review result 和 retry proposal 持久化到本地 plan runtime。

更技术版：

> 实现角色化 Multi-Agent contract：`PlanPreview` 约束 Planner 输出，`ExecutorStepContract` 限制 Executor 单步执行，`ReviewerGateDecision` 阻断 failed / skipped / cancelled step 的假成功；支持 planner/executor/reviewer 独立 role config、model-backed reviewer suggestion 和 `.pyagent/plans` 中的持久化 handoff。

不要这么写：

> 实现多 Agent 自主协作和并行调度。

除非后续真的实现并发 Agent、DAG scheduler、message bus 和冲突处理。

## 面试官会怎么追问

### Q1：Multi-Agent 的价值是什么？

一句话答案：

> 价值是职责隔离、可审计 handoff 和更可靠的复核，而不是堆角色名。

展开回答：

- Planner 负责计划。
- Executor 负责执行 approved step。
- Reviewer 负责 gate 和恢复建议。
- Handoff 持久化到 plan JSON。

### Q2：Planner 为什么不能调用工具？

一句话答案：

> Planner 处在预览阶段，不能在用户批准前产生副作用。

展开回答：

- `--plan` 应该 read-only。
- Planner 只输出 JSON。
- 工具执行交给 Executor。
- 这样用户能先审查计划。

### Q3：Executor 如何防止越权？

一句话答案：

> Executor 每次只接收一个 `ExecutorStepContract`，并被要求执行完当前 step 就停止。

展开回答：

- contract 包含 original goal、step id、risk、suggested tools、instructions。
- prompt 写明 `Role: Executor Agent`。
- tool-level approval 仍然保留。
- step status 写回 PlanRun。

### Q4：Reviewer 如何避免形式主义？

一句话答案：

> Reviewer 有 deterministic gate，会影响最终 PlanRun status。

展开回答：

- failed / skipped / cancelled 会 block。
- success plan 也可能被降级为 failed。
- Reviewer 生成 risk notes、suggested tests、retry proposal。
- model suggestion 不能覆盖 gate。

### Q5：为什么 Retry Proposal 不自动执行？

一句话答案：

> 自动 retry 可能绕过用户审批，尤其涉及写文件和 shell。

展开回答：

- proposal 是 read-only recommendation。
- failed 建议 retry_step。
- skipped 建议 user_decision。
- cancelled 建议 resume_plan。
- 真正执行仍需要用户确认。

### Q6：你们现在是多个 Agent 并发吗？

一句话答案：

> 不是。当前是串行的角色化工作流，已经具备 Multi-Agent contract 和 handoff，但没有并发调度。

展开回答：

- 当前链路是 Planner -> Executor -> Reviewer。
- PlanExecutor 串行执行 step。
- 后续可以加 DAG scheduler 和并发执行。
- 文档和简历不会夸成 Agent swarm。

### Q7：model-backed reviewer 有什么用？

一句话答案：

> 它补充风险说明和测试建议，但不改变 deterministic gate。

展开回答：

- deterministic gate 先运行。
- model suggestion 读取 bounded review context。
- 输出 allowed recommended action。
- 非 JSON 或非法 action 会降级。

## 标准回答思路

如果面试官让你整体讲 Multi-Agent，可以按这个顺序：

1. 先说 Multi-Agent 不是堆角色，而是职责隔离。
2. 讲 Planner：只输出结构化计划，不执行工具。
3. 讲 Executor：按 `ExecutorStepContract` 执行单步。
4. 讲 Reviewer：deterministic gate 和 retry proposal。
5. 讲 handoff：写入 plan JSON，可通过 `--show-plan` 复盘。
6. 讲 role config：planner/executor/reviewer 可配置不同 model/prompt。
7. 讲边界：当前不是并发 swarm。
8. 讲下一步：DAG scheduler、message bus、更多角色。

一版完整回答：

> PyAgentCLI 里的 Multi-Agent 不是多个 Agent 随便聊天，而是 Planner / Executor / Reviewer 的角色化工作流。Planner 只负责把任务拆成结构化 `PlanPreview`，不调用工具；Executor 每次只接收一个 `ExecutorStepContract`，按已审批 step 执行并停止；Reviewer 在执行后读取 PlanRun、step status、audit log 和 git diff，生成 `ReviewReport` 和 deterministic `ReviewerGateDecision`。如果出现 failed、skipped、cancelled step，Reviewer 会 block，甚至把执行成功的 plan 降级为 failed，并给出 retry proposal。每个角色的 handoff 会写入 `.pyagent/plans`，用户可以 `--show-plan` 复盘。当前这是串行角色工作流，不是并发 Agent swarm；后续可以扩展 DAG scheduler、message bus 和更多角色。

## 还能继续怎么增强

下一阶段可以增强：

- DAG Scheduler Agent。
- Architect / Coder / Tester / Reviewer 更多角色。
- message bus。
- role-specific tool allowlist。
- role-specific memory。
- reviewer tool-assisted verification。
- multi-agent trace eval。
- parallel READ steps。
- conflict detection for WRITE steps。
- model debate only for review suggestions。
- handoff visualization。

更工程化的方向：

- 每个 handoff 增加 input/output artifact id。
- Reviewer 关联具体 git diff hunk。
- Executor 输出结构化 step result。
- Multi-Agent eval 比较 deterministic reviewer 和 model reviewer。
- Role config 加 fallback model。

## 这一篇之后做什么

下一篇进入：

> Browser Tools 和联网搜索

Multi-Agent 解决的是任务角色如何分工；Browser/Search 解决的是 Agent 如何观察本地页面、DOM、截图、console、network，以及如何处理浏览器能力和登录态边界。
