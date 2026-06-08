# 16 面试题第一弹：ReAct、Plan-and-Execute、Multi-Agent

这一弹对应 PyAgentCLI 的核心 Agent Runtime。

如果面试官只追一个大方向，最可能先追这里：

```text
Agent 怎么循环？
工具怎么调用？
复杂任务怎么规划？
多 Agent 是真有价值还是堆概念？
Reviewer 怎么防止假成功？
```

你要把这一弹练到可以不用背稿，也能稳定讲清楚。

## 这一弹考什么

这一弹主要考 5 个能力：

1. 你是否真的理解 ReAct 和 Tool Calling 的关系。
2. 你是否知道模型不会直接执行工具。
3. 你是否能解释 Agent Loop 如何停止、失败如何恢复。
4. 你是否能讲清 ReAct 和 Plan-and-Execute 的适用边界。
5. 你是否能把 Multi-Agent 讲成职责隔离，而不是角色堆叠。

对应 PyAgentCLI 源码：

```text
src/pyagentcli/agent/loop.py
src/pyagentcli/agent/planner.py
src/pyagentcli/agent/plan_executor.py
src/pyagentcli/agent/contracts.py
src/pyagentcli/agent/plan_store.py
src/pyagentcli/agent/reviewer.py
src/pyagentcli/tools/registry.py
src/pyagentcli/cli/main.py
```

对应实战文档：

- [02 ReAct 和 Tool Calling](02_react_tool_calling.md)
- [03 Plan-and-Execute / DAG](03_plan_execute_dag.md)
- [07 Multi-Agent](07_multi_agent.md)

## 哪些简历句子会触发这一弹

如果简历里写了这些话，面试官很可能追问：

> 实现 ReAct / Function Calling Agent Loop，支持 OpenAI-compatible tool calls、本地工具执行、observation 回灌、max steps 防无限循环和 trace capture。

会追问：

- ReAct 和 Function Calling 区别是什么？
- 模型是怎么调用工具的？
- 工具失败后怎么办？
- 为什么需要 max steps？

如果写：

> 设计并实现 Plan-and-Execute 工作流，支持计划预览、用户审批、计划持久化、步骤级状态机、失败恢复、单步重试和 Reviewer gate。

会追问：

- ReAct 不够吗？
- 为什么要先 plan 再 execute？
- plan 怎么持久化？
- skipped step 为什么不能算 success？

如果写：

> 实现 Planner / Executor / Reviewer 多角色工作流，Planner 输出结构化 PlanPreview，Executor 以 step contract 串行执行 approved steps，Reviewer 基于 step status、audit log 与 git diff 生成 gate decision 和 retry proposal。

会追问：

- 这算 Multi-Agent 吗？
- Planner 为什么不能直接执行工具？
- Executor 怎么被限制住？
- Reviewer 是模型吗，还是 deterministic？
- Retry proposal 为什么不自动执行？

## 面试开场 30 秒回答

如果面试官让你“介绍一下 PyAgentCLI 的 Agent 架构”，可以先用这一版：

> PyAgentCLI 是一个本地 AI Coding Agent CLI。核心 runtime 是 ReAct/tool calling loop：模型只输出结构化 tool call，真正执行由 ToolRegistry、SafetyPolicy、ApprovalHandler 和 AuditLogger 控制，工具结果再作为 observation 回到模型。对短任务，AgentLoop 直接循环到 final answer；对复杂任务，我实现了 Plan-and-Execute：Planner 先生成结构化 PlanPreview，用户审批后 Executor 按 step contract 串行执行，每个 PlanRun 持久化到 `.pyagent/plans`，失败后支持 show、resume、retry、skip。执行后 Reviewer 会读取 step status、audit log 和 git diff 做 deterministic gate，防止 failed/skipped/cancelled step 被误判为成功。

这 30 秒要覆盖：

- 模型不直接执行。
- 工具执行受控。
- 短任务 ReAct。
- 复杂任务 Plan-and-Execute。
- Multi-Agent 是 Planner/Executor/Reviewer。
- Reviewer 是 gate。

## Q1：ReAct 和 Function Calling 是什么关系？

一句话答案：

> ReAct 是“推理-行动-观察”的 Agent 行为模式，Function Calling / Tool Calling 是模型输出结构化行动意图的协议。

展开回答：

ReAct 关注的是循环：

```text
Reason
  -> Act
  -> Observe
  -> Reason again
```

Function Calling 关注的是输出格式：

```json
{
  "name": "read_file",
  "arguments": {
    "path": "README.md"
  }
}
```

落到 PyAgentCLI：

- `AgentLoop` 把 tools schema 发给模型。
- 模型返回 `ToolCall`。
- `ToolRegistry.execute()` 执行工具。
- 工具结果作为 `Message.tool(...)` 回到模型。
- 没有 tool call 时结束。

边界：

> Function Calling 不是模型执行函数，它只是模型生成调用请求。

## Q2：模型到底会不会执行代码？

一句话答案：

> 不会。模型只生成 tool call，真正读写文件和运行命令的是本地 runtime。

展开回答：

模型返回：

```text
tool_name
arguments
```

PyAgentCLI 负责：

- 查 Tool Registry。
- 校验参数。
- 做 Safety Policy。
- 必要时人工审批。
- 调用本地工具。
- 写 audit log。
- 把 observation 传回模型。

这条边界特别重要，因为 Coding Agent 会接触真实文件和 shell。

面试加分点：

> 我把“模型意图”和“本地执行权”分开，所以换模型不会改变工具权限。

## Q3：Agent Loop 怎么防止无限循环？

一句话答案：

> 用 `max_steps` 做硬终止条件，同时让工具失败变成 observation，而不是让 runtime 崩溃。

展开回答：

PyAgentCLI 的循环逻辑是：

```text
messages -> LLM
  -> 如果有 tool_calls：执行工具，append observations，step + 1
  -> 如果没有 tool_calls：返回 final answer
  -> 如果达到 max_steps：停止
```

为什么需要 `max_steps`？

因为模型可能：

- 一直调用同一个工具。
- 遇到失败后反复重试。
- 不输出 final answer。
- 在错误路径里循环。

`max_steps` 是 runtime 级保护，不能只靠 prompt。

## Q4：Tool Call 失败后怎么办？

一句话答案：

> 失败应该变成 tool observation 回给模型，同时写 audit log，给模型修正机会。

展开回答：

常见失败：

- 文件不存在。
- `edit_file` 的 `old_text` 不唯一。
- 路径越界。
- shell 命令被拒绝。
- MCP server 失败。
- Browser capability 不可用。

PyAgentCLI 的策略：

- 工具返回 failure result。
- failure 不直接终止整个 Agent。
- failure 作为 tool message 回到 messages。
- 模型可以基于错误重新选择动作。
- audit log 记录失败。

边界：

> 失败可恢复，不等于无限重试；仍受 max steps 限制。

## Q5：ReAct 和 Plan-and-Execute 区别是什么？

一句话答案：

> ReAct 是边想边做，适合短任务；Plan-and-Execute 是先计划、审批、再执行，适合复杂和高风险任务。

展开回答：

ReAct 适合：

- 读取信息。
- 总结项目。
- 小范围修改。
- 探索性任务。

Plan-and-Execute 适合：

- 多步骤任务。
- 有写文件或 shell 风险。
- 用户希望先审查计划。
- 任务可能中断，需要恢复。

PyAgentCLI 里：

```bash
pyagent --plan "fix failing tests"
pyagent --execute-plan "fix failing tests"
```

`--plan` 不执行工具，只生成计划。

`--execute-plan` 会：

- 生成 plan。
- 保存 PlanRun。
- 展示给用户审批。
- Executor 串行执行 steps。
- Reviewer 复核。

## Q6：为什么要持久化 Plan？

一句话答案：

> 因为真实 coding task 会失败、中断、跳过、取消，持久化后才能 show、resume、retry 和复盘。

展开回答：

Plan 持久化到：

```text
.pyagent/plans/*.json
```

CLI 支持：

```bash
pyagent --list-plans
pyagent --show-plan PLAN_ID
pyagent --resume-plan PLAN_ID
pyagent --retry-step PLAN_ID STEP_ID
pyagent --skip-step PLAN_ID STEP_ID
pyagent --set-step-status PLAN_ID STEP_ID STATUS
```

这让 Agent 任务从一次性对话变成可恢复工作流。

面试加分点：

> 持久化 PlanRun 也让 Reviewer、Memory 和 Eval 可以复用执行证据。

## Q7：PyAgentCLI 现在实现 DAG 了吗？

一句话答案：

> 还没有完整 DAG；当前是串行 Plan-and-Execute，但已经有 step id、status、PlanStore、Executor 和 Reviewer，为 DAG 演进打基础。

展开回答：

当前已实现：

- step id。
- step status。
- risk。
- suggested tools。
- PlanStore。
- resume/retry。
- Reviewer gate。

还没实现：

- `depends_on`。
- 拓扑排序。
- 并行执行。
- 跨 step 文件冲突检测。
- DAG 可视化。

诚实表达：

> 我不会把它说成完整 DAG。现在是串行 workflow，下一步才是把 step dependencies 和并发调度补上。

## Q8：Multi-Agent 的价值是什么？

一句话答案：

> Multi-Agent 的价值不是角色多，而是职责隔离、handoff 可审计和失败可定位。

展开回答：

PyAgentCLI 当前有三个角色：

```text
Planner   -> 生成计划
Executor  -> 执行已批准 step
Reviewer  -> 复核结果和风险
```

价值：

- Planner 不执行工具，降低规划阶段副作用。
- Executor 每次只执行一个 approved step，避免越界发挥。
- Reviewer 不只是总结，而是 gate。
- handoff 写入 PlanRun，方便复盘。

边界：

> 这不是多个 Agent 并发聊天，也不是多进程 swarm，而是角色化 workflow。

## Q9：Planner 为什么不调用工具？

一句话答案：

> 因为 Planner 的职责是生成计划，不应该在规划阶段产生文件或命令副作用。

展开回答：

Planner 输入：

```text
user goal
context
role prompt
```

Planner 输出：

```text
PlanPreview
PlanStep[]
```

如果 Planner 也能调用工具，风险是：

- 计划还没审批就开始读写。
- 用户以为只是预览，实际已经执行。
- Planner 和 Executor 责任混乱。

所以 PyAgentCLI 把执行权放在 Executor。

## Q10：Executor 怎么避免越界？

一句话答案：

> Executor 每次只接收一个 `ExecutorStepContract`，按 approved step 执行，而不是拿完整大目标自由发挥。

展开回答：

Executor goal 会包含：

```text
Role: Executor Agent
Original goal
Approved step id/title/description/risk/tools
Instruction: execute only this step
```

这样可以限制：

- 当前只做一个 step。
- 不主动跳到下一步。
- 不扩大修改范围。
- 执行结果回写 step summary。

边界：

> 这是 prompt/contract 约束，真正的硬边界仍然来自 Tool Safety 和 Approval。

## Q11：Reviewer 为什么不是形式主义？

一句话答案：

> 因为 Reviewer 的 deterministic gate 会影响最终 PlanRun status，而不是只生成总结。

展开回答：

Reviewer 会检查：

- step status。
- failed / skipped / cancelled。
- audit log。
- git diff。
- risk notes。
- suggested tests。

如果 plan status 是 success，但有 step 是 skipped：

```text
Reviewer gate should block
PlanRun can be downgraded to failed
```

这可以防止：

> 中间步骤没做完，但最终回答说完成了。

## Q12：Retry Proposal 为什么不自动执行？

一句话答案：

> 因为建议和执行必须分开，自动 retry 可能绕过用户审批和安全边界。

展开回答：

Reviewer 可以建议：

- failed step -> `retry_step`
- skipped step -> `user_decision`
- cancelled plan -> `resume_plan`

但真正执行仍然要用户确认。

原因：

- retry 可能再次写文件。
- retry 可能运行 shell。
- skipped 可能是用户故意跳过。
- cancelled 可能代表用户改变主意。

所以 proposal 只是恢复建议，不是自动行动。

## Q13：如果面试官说“这不是真 Multi-Agent”，怎么答？

一句话答案：

> 如果把 Multi-Agent 定义为多自治体并发协作，那当前 PyAgentCLI 不是；但它实现了更适合本地 Coding Agent 的角色化 Agent workflow。

展开回答：

我会承认边界：

- 当前不是 swarm。
- 不是多进程。
- 不是 agent-to-agent 自由对话。

但它有实际工程价值：

- Planner / Executor / Reviewer 职责隔离。
- Handoff 持久化。
- Reviewer gate。
- Retry proposal。
- Role-specific model config。

面试加分点：

> 对本地 Coding Agent 来说，先做好可控 workflow，比堆并发 Agent 更重要。

## Q14：你们开发时这里遇到过什么真实问题？

可以讲 3 个。

### 1. skipped step 不能误判 success

我们写 Reviewer gate 时专门处理：

```text
PlanRun status = success
but one step status = skipped
```

Reviewer 必须 block。

这个问题说明：

> 不能只相信最终状态，要检查 step-level evidence。

### 2. Retry Proposal 的语义要清楚

failed step 和 skipped step 不一样。

```text
failed  -> retry_step
skipped -> user_decision
```

如果 skipped 也自动 retry，可能违背用户意图。

### 3. DAG 不能提前吹

项目目前有 Plan-and-Execute 串行工作流，但没有完整 DAG。

所以文档和简历都要写清楚：

```text
当前实现串行 plan workflow
未来增强 depends_on / topology / parallel execution
```

## Q15：如果让你现场画架构图，你怎么画？

可以画：

```text
User Goal
  |
  v
Context Enrichment
  |
  v
AgentLoop ---------------+
  |                      |
  v                      |
LLMClient                |
  |                      |
  v                      |
ToolCall                 |
  |                      |
  v                      |
ToolRegistry -> Safety -> Approval -> Tool Execution -> Audit
  |                                             |
  +---------------- Observation ----------------+

复杂任务：

User Goal
  |
  v
Planner -> PlanPreview -> PlanStore
  |
  v
User Approval
  |
  v
Executor(step contract) -> PlanRun step statuses
  |
  v
Reviewer -> GateDecision -> RetryProposal
```

讲图时注意：

- 模型只在 LLMClient 后面。
- Tool execution 在本地 runtime。
- PlanStore 是恢复和复盘的关键。
- Reviewer 是 gate。

## 必背 8 句

1. ReAct 是行为模式，Tool Calling 是结构化行动协议。
2. 模型不执行工具，只输出工具调用意图。
3. 工具执行权在 ToolRegistry、SafetyPolicy、ApprovalHandler 和 AuditLogger。
4. Agent Loop 必须有 max steps，不能靠模型自己停。
5. 工具失败应该变成 observation，而不是让 runtime 崩溃。
6. ReAct 适合短任务，Plan-and-Execute 适合多步骤和高风险任务。
7. Multi-Agent 的价值是职责隔离和可审计 handoff，不是角色越多越好。
8. Reviewer 是 deterministic gate，不是形式主义总结器。

## 一版完整回答

如果面试官问：

> 你们这个 Agent Runtime 是怎么设计的？

可以这样答：

> PyAgentCLI 的核心是一个受控的 ReAct/tool calling runtime。模型不会直接执行代码，它只返回结构化 tool call；本地 `AgentLoop` 拿到 tool call 后交给 `ToolRegistry.execute()`，再经过 `SafetyPolicy`、`ApprovalHandler` 和 `AuditLogger`，工具结果作为 observation 回到模型。为了防止无限循环，我设置了 max steps；工具失败不会让 runtime 直接崩溃，而是变成 observation，让模型有机会修正。短任务直接用 ReAct loop；复杂任务走 Plan-and-Execute：Planner 先输出结构化 `PlanPreview`，保存为 `PlanRun`，用户审批后 Executor 按 `ExecutorStepContract` 串行执行每个 approved step，执行结果写回 step status。最后 Reviewer 读取 step status、audit log 和 git diff，生成 deterministic gate 和 retry proposal，如果发现 failed、skipped、cancelled step，就会 block，甚至把 success plan 降级为 failed。当前它不是完整 DAG 或并发 swarm，而是一个可恢复、可审计的角色化 Agent workflow。

## 这一弹之后怎么复习

复习顺序：

1. 先读 [02 ReAct 和 Tool Calling](02_react_tool_calling.md)。
2. 再读 [03 Plan-and-Execute / DAG](03_plan_execute_dag.md)。
3. 再读 [07 Multi-Agent](07_multi_agent.md)。
4. 最后打开源码：

```text
src/pyagentcli/agent/loop.py
src/pyagentcli/agent/planner.py
src/pyagentcli/agent/plan_executor.py
src/pyagentcli/agent/reviewer.py
```

下一弹进入：

> Memory、RAG、长上下文工程
