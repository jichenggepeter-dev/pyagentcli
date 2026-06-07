# 05 面试篇：ReAct、Plan-and-Execute、Multi-Agent

这一篇对应 Agent 核心架构。

如果面试只能重点准备一篇，先准备这一篇。

## 01 什么是 ReAct？

ReAct 是 Reasoning + Acting。

核心思想：

> 模型不只是一次性回答，而是在推理过程中发出动作意图，观察动作结果，再继续推理。

PyAgentCLI 中的 ReAct loop 可以概括为：

```text
messages -> LLM
  -> assistant response
    -> if tool_calls: execute tools
    -> append tool observations
    -> continue
    -> else final answer
```

## 02 Function Calling 的本质是什么？

Function Calling 的本质不是模型执行函数。

它只是模型输出一个结构化意图：

```json
{
  "name": "read_file",
  "arguments": {
    "path": "README.md"
  }
}
```

真正执行的是 PyAgentCLI：

- ToolRegistry 找到 `read_file`
- SafetyPolicy 检查风险
- ApprovalHandler 判断是否需要用户审批
- 工具读取本地文件
- 结果作为 observation 返回模型

一句面试答案：

> 模型不执行代码。模型只决定“想调用什么工具、传什么参数”，执行权在 Agent runtime。

## 03 ReAct 和 Chain-of-Thought 有什么区别？

CoT：

- 只推理
- 不接触真实环境
- 容易基于想象回答

ReAct：

- 推理 + 行动
- 可以调用工具
- 基于真实 observation 继续推理

PyAgentCLI 的关键点是：

> 不让模型猜文件内容。需要真实信息时必须调用工具。

## 04 Agent Loop 如何防止无限循环？

PyAgentCLI 使用 max steps。

每轮调用模型后：

- step count +1
- 如果没有 tool call，结束
- 如果达到 max steps，停止

面试回答：

> Agent loop 必须有终止条件。不能假设模型一定会自己停。PyAgentCLI 用 max steps 防止无限工具调用，同时工具失败会转成 observation，让模型有机会修正。

## 05 Tool Call 失败后怎么办？

失败不应该直接让 Agent 崩溃。

PyAgentCLI 的策略：

- 工具返回 `ToolResult.failure`
- failure 被转成 tool message
- 模型看到错误信息后继续推理
- 审计日志记录失败

例子：

- `edit_file` 找不到 old_text
- `run_shell` 被安全策略拒绝
- `browser_console_logs` 没装 Playwright

这些都应该变成 observation。

## 06 ReAct 和 Plan-and-Execute 区别

ReAct 适合：

- 短任务
- 探索性任务
- 读取信息后回答
- 小范围文件修改

Plan-and-Execute 适合：

- 多步骤任务
- 高风险任务
- 需要审批的任务
- 需要恢复/重试的任务

PyAgentCLI 中：

- `--plan` 只生成计划
- `--execute-plan` 先展示计划，再审批执行
- plan 持久化到 `.pyagent/plans/`

面试回答：

> ReAct 是边想边做，Plan-and-Execute 是先拆解再执行。后者更适合复杂任务，因为用户可以在执行前审查计划。

## 07 为什么要持久化 Plan？

因为真实任务会失败、中断、被拒绝、需要恢复。

PyAgentCLI 支持：

- `--show-plan`
- `--list-plans`
- `--resume-plan`
- `--retry-step`
- `--skip-step`
- `--set-step-status`

面试回答：

> Plan 持久化让任务从一次性对话变成可恢复工作流。失败后不用重新开始，可以从具体 step 继续。

## 08 Multi-Agent 的价值是什么？

Multi-Agent 不是为了堆概念。

它的价值是拆清楚职责：

- Planner：负责计划
- Executor：负责执行
- Reviewer：负责复核

PyAgentCLI 中：

- Planner 输出 `PlanPreview`
- Executor 接收 `ExecutorStepContract`
- Reviewer 输出 `ReviewReport`
- Handoff 被写入 plan

## 09 Reviewer 如何避免形式主义？

很多项目里的 Reviewer 只是总结一句“看起来不错”。

PyAgentCLI 的 Reviewer 有实际权力：

- 检查 step status
- failed / skipped / cancelled 会 block
- 成功 plan 可被降级为 failed
- 生成 retry proposal

面试回答：

> Reviewer 不是文本总结器，而是状态 gate。它会影响最终 PlanRun status。

## 10 Retry Proposal 为什么不自动执行？

因为自动 retry 可能绕过审批。

PyAgentCLI 做法：

- failed -> `retry_step`
- skipped -> `user_decision`
- cancelled -> `resume_plan`

但 proposal 只是建议。

真正执行仍然需要用户审批。

面试回答：

> 自动生成建议和自动执行必须分开。尤其是 coding agent，涉及写文件和 shell 时，执行权必须留给用户。

## 11 我们开发中遇到的相关问题

### skipped step 不能被误判成功

开发 Reviewer gate 时，我们专门写了测试：

- plan status 是 success
- 但其中一个 step 是 skipped
- Reviewer 应该把最终状态降级为 failed

这说明：

> Agent 不能只看最终回答，要看中间步骤状态。

### Retry Proposal 的测试预期修正

我们一开始在 CLI 测试里把 skipped step 的 next action 误写成 `retry_step`。

测试失败后发现：

- failed 才是 `retry_step`
- skipped 应该是 `user_decision`

这个问题很适合面试讲：

> 不同失败状态需要不同恢复策略，不能全部粗暴 retry。

## 高频面试题

1. ReAct 和 Function Calling 的关系是什么？
2. 模型到底会不会执行代码？
3. Agent Loop 如何停止？
4. Tool Call 失败后怎么办？
5. ReAct 和 Plan-and-Execute 区别是什么？
6. 为什么计划要持久化？
7. Multi-Agent 为什么有价值？
8. Planner / Executor / Reviewer 怎么分工？
9. Reviewer gate 如何防止假成功？
10. Retry Proposal 为什么不自动执行？

