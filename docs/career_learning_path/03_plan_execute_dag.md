# 03 Plan-and-Execute / DAG

这一篇对应 PaiCLI 学习路线里的 Plan-and-Execute / DAG 思路，但内容全部落到 PyAgentCLI 当前的 Python 实现。

先给结论：

> PyAgentCLI 现在已经实现了 Plan Preview、计划持久化、审批后串行执行、步骤状态机、恢复/重试/跳过、Reviewer gate。真正的 DAG 依赖图和并行调度还没有实现，应该作为下一阶段增强讲。

这句话很重要。面试时不要把“路线图能力”说成“已经落地能力”。真正可信的项目表达，是把当前边界讲清楚。

## 这一篇学什么

学完这一篇，你要能讲清楚：

- ReAct 为什么不够处理复杂任务。
- Plan-and-Execute 把 Agent 从“一次性对话”升级成“可恢复工作流”。
- `--plan` 为什么必须只预览，不执行工具。
- `--execute-plan` 为什么要先审批，再逐步执行。
- 为什么 plan 要保存到 `.pyagent/plans/*.json`。
- step status 为什么比最终回答更可信。
- Reviewer gate 如何防止“计划看起来成功，但中间步骤被跳过”的假成功。
- DAG 是什么，PyAgentCLI 未来怎么从串行 step 演进到依赖图调度。

## 为什么 Agent CLI 需要 Plan-and-Execute

ReAct 的特点是边想边做：

```text
LLM -> tool call -> observation -> LLM -> tool call -> observation -> final
```

这对短任务很好，比如：

- 读一个 README。
- 改一个小 typo。
- 查询某个文件里的函数。
- 跑一个小测试后总结。

但复杂任务会出现几个问题：

- 用户不知道 Agent 准备改什么。
- Agent 可能在没确认方案前就开始写文件。
- 任务中断后很难恢复。
- 某一步失败后，无法只重试那一步。
- 高风险步骤和低风险步骤混在一起，审批体验很差。
- 最终回答说“完成了”，但中间可能有 step 被拒绝或跳过。

Plan-and-Execute 要解决的是：

> 先把任务拆成可审查的步骤，再经过用户批准，最后按步骤执行、记录、恢复和复核。

它不是为了显得复杂，而是为了让 Agent 的行为可控。

## PyAgentCLI 当前实现了什么

当前已经落地的能力：

- `--plan`：生成计划预览，不执行工具。
- `--execute-plan`：生成计划，展示给用户，用户批准后执行。
- `.pyagent/plans/*.json`：保存 plan run。
- step status：`pending / running / success / failed / skipped / cancelled`。
- `--show-plan`：查看某个计划。
- `--list-plans`：列出工作区里的计划。
- `--resume-plan`：继续执行可恢复计划。
- `--retry-step`：重试某一步，并重置它之后的步骤。
- `--set-step-status`：手动修正步骤状态。
- `--skip-step`：手动跳过步骤。
- step-level approval：READ 自动允许，WRITE / EXECUTE / NETWORK / CRITICAL 需要审批。
- tool-level approval：即使 step 被批准，具体写文件和 shell 工具仍保留审批。
- Reviewer gate：复核 step status、git diff、风险和测试建议。
- retry proposal：根据失败类型给出下一步建议。

当前还没有落地的能力：

- 真正的 DAG dependencies 字段。
- DAG 拓扑排序。
- 可并行 step 调度。
- 文件写冲突检测。
- 用户可视化编辑计划。
- Planner / Executor / Reviewer 的远程运行时隔离。

所以当前最准确的表达是：

> PyAgentCLI 已经实现了 Plan-and-Execute 的串行工作流基础，并预留了向 DAG 执行演进的结构。

## 最小运行例子

先只生成计划：

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --plan "Read README.md and change Project status from TODO to READY"
```

这个命令应该只输出计划，不读文件、不写文件、不跑 shell。

典型输出结构：

```text
PlanRun status: planned
Plan id: plan_...

Plan: Plan for: Read README.md and change Project status from TODO to READY

S1. [pending] Inspect workspace
   Risk: READ
   Tools: list_files, read_file
   List files and read the most relevant files before making changes.
S2. [pending] Apply minimal change
   Risk: WRITE
   Tools: edit_file, write_file
   Use edit_file for localized edits or write_file only for new files.
S3. [pending] Verify result
   Risk: EXECUTE
   Tools: run_shell
   Run a focused command or test if the user approves shell execution.
```

审批后执行计划：

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --execute-plan "Read README.md and change Project status from TODO to READY"
```

查看计划：

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --show-plan PLAN_ID
```

列出计划：

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --list-plans
```

恢复计划：

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --resume-plan PLAN_ID
```

重试某一步：

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --retry-step PLAN_ID S2
```

跳过某一步：

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --skip-step PLAN_ID S3
```

手动设置步骤状态：

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --set-step-status PLAN_ID S2 pending
```

## 核心数据结构

Plan 的最小结构可以理解成：

```text
PlanRun
  plan_id
  goal
  status
  plan
    summary
    steps[]
      id
      title
      description
      suggested_tools
      risk
      status
      result_summary
  execution_result
  review_result
  handoffs[]
  created_at
  updated_at
```

这里最关键的是 `step.status`。

一个 Agent 项目如果只保存最终输出，会很容易出现假成功：

```text
final answer: Done
actual step states: success, skipped, success
```

这不是完整成功。因为中间的 `skipped` 可能代表用户拒绝了写文件、命令被阻断，或者某个必要步骤没有执行。

PyAgentCLI 的 Reviewer 会读取这些状态，并把 `failed / skipped / cancelled` 作为 blocking status。

## 状态机怎么理解

PlanRun 的状态：

```text
planned -> approved -> running -> success
planned -> cancelled
running -> failed
```

Step 的状态：

```text
pending -> running -> success
pending -> skipped
pending -> failed
pending -> cancelled
```

恢复时的规则：

- 已经 `success` 的 step 跳过，不重复执行。
- `pending / failed / running` 的 step 可以继续执行。
- `skipped / cancelled` 不会被悄悄当成成功。

重试时的规则：

> `--retry-step PLAN_ID S2` 会把 S2 和它后面的 step 都重置成 `pending`，保留 S1 这种已经成功的前置步骤。

为什么要重置后续步骤？

因为后续步骤可能依赖 S2 的旧结果。只重试 S2、不清理下游状态，会留下过期成功。

## Planner 做什么

Planner 的职责是把用户目标拆成结构化步骤。

源码：

```text
src/pyagentcli/agent/planner.py
```

Planner prompt 明确要求：

- 不调用工具。
- 不编辑文件。
- 只返回 JSON。
- risk 必须是 `READ / WRITE / EXECUTE / NETWORK / CRITICAL`。
- 高风险写文件或 shell 动作要拆成单独步骤。

如果模型返回的 JSON 解析失败，PyAgentCLI 会使用 fallback plan：

```text
S1 Inspect workspace
S2 Apply minimal change
S3 Verify result
```

这个 fallback 很关键。因为真实模型输出不稳定，不能假设每次都给出合法 JSON。

## Executor 做什么

Executor 的职责是按 approved plan 执行每个 step。

源码：

```text
src/pyagentcli/agent/plan_executor.py
src/pyagentcli/agent/contracts.py
```

每一步都会被包装成 `ExecutorStepContract`：

```text
Role: Executor Agent
Execute exactly this approved plan step.

Original task:
...

Step S2: Edit README
Risk: WRITE
Suggested tools: edit_file, write_file
Step instructions:
...

Stop after this step and summarize what happened.
```

这解决一个很常见的问题：

> Executor 不能拿到整个大目标后自由发挥，否则它可能越过当前 step 做太多事情。

所以 PyAgentCLI 让 Executor 每次只执行一个已批准 step，执行完就停下总结。

## Reviewer 做什么

Reviewer 的职责不是写一句“看起来不错”。

源码：

```text
src/pyagentcli/agent/reviewer.py
```

Reviewer 会检查：

- plan status。
- step status。
- audit log 中观察到的工具。
- audit log 中观察到的路径。
- git diff。
- 风险提示。
- 建议测试。
- retry proposal。

Reviewer gate 的核心规则：

```text
failed / skipped / cancelled step -> block
all steps success -> pass
```

如果某个 step 失败：

```text
recommended_action = retry_step
suggested_command = pyagent --retry-step PLAN_ID S1
```

如果某个 step 被跳过：

```text
recommended_action = user_decision
suggested_command = pyagent --retry-step PLAN_ID S2
```

如果某个 step 被取消：

```text
recommended_action = resume_plan
suggested_command = pyagent --resume-plan PLAN_ID
```

这里的区别很适合面试讲：

> failed 是执行失败，可以建议 retry；skipped 通常来自用户拒绝或主动跳过，不能自动 retry，必须让用户重新决策；cancelled 需要重新确认是否恢复。

## 源码阅读路线

建议按这个顺序看：

1. `src/pyagentcli/agent/planner.py`
   - 看 `PlanStep`、`PlanPreview`、`PlanRun`。
   - 看 `PLANNER_PROMPT` 和 `_fallback_plan()`。
2. `src/pyagentcli/agent/plan_store.py`
   - 看 plan 如何保存到 `.pyagent/plans/*.json`。
   - 看 `save()`、`load()`、`list_runs()`。
3. `src/pyagentcli/agent/contracts.py`
   - 看 `ExecutorStepContract` 如何限制 Executor。
   - 看 `ReviewerInputContract` 如何抽取 step statuses。
4. `src/pyagentcli/agent/plan_executor.py`
   - 看串行 step 执行。
   - 看 step-level approval。
   - 看 failed / skipped 如何写回状态。
5. `src/pyagentcli/agent/reviewer.py`
   - 看 Reviewer gate。
   - 看 git diff summary。
   - 看 retry proposal。
6. `src/pyagentcli/cli/main.py`
   - 看 `--plan / --execute-plan / --resume-plan / --retry-step` 如何串起来。
7. `tests/test_plan_store.py`
   - 看计划持久化测试。
8. `tests/test_plan_executor.py`
   - 看串行执行、失败、恢复、审批拒绝。
9. `tests/test_reviewer.py`
   - 看 gate、diff、retry proposal、model suggestion。

## 我们协作时真实遇到的坑

### 1. skipped step 不能当成 success

开发 Reviewer gate 时，我们专门保留了一个判断：

```text
failed / skipped / cancelled -> block
```

原因是 `skipped` 很可能代表用户拒绝了某个高风险步骤。

如果最终 PlanRun 是 `success`，但其中一个 step 是 `skipped`，Reviewer 仍然应该阻断。这就是防止“假成功”的关键。

### 2. Retry Proposal 的语义一开始容易写错

我们曾经把 skipped step 的下一步误判成 `retry_step`。

后来修正成：

```text
failed -> retry_step
skipped -> user_decision
cancelled -> resume_plan
```

这个细节很小，但工程含金量很高。它说明我们不是把所有异常都粗暴重试，而是区分了失败来源。

### 3. 计划执行前要检查 RAG index 是否 stale

`--execute-plan` 执行前会检查本地 SQLite 搜索索引的新鲜度。

如果文件变了、删了、或者出现新文件，PyAgentCLI 会提示用户运行：

```bash
pyagent --index
```

但它不会静默重建索引。

原因是计划执行应该可预期，不能在用户审批一个任务时偷偷做额外的索引写入。

### 4. Reviewer 不能覆盖 deterministic gate

Reviewer 可以接 LLM 给建议，但 deterministic gate 才是硬规则。

LLM reviewer prompt 明确要求：

- 不覆盖 deterministic gate。
- 不声称自己执行工具。
- 不自动 retry。

这是为了避免模型一句“看起来可以接受”绕过状态机。

### 5. 不要把 DAG 写成已经完成

我们现在的实现是串行 step execution，不是真正 DAG。

文档和简历里必须说清楚：

```text
已实现：Plan-and-Execute 串行工作流
下一步：DAG dependencies、并行调度、冲突检测
```

这会让项目表达更可信。

## 你自己开发时大概率会遇到的坑

### 1. `--plan` 不小心执行了工具

Plan Preview 必须是 read-only runtime 行为。

错误做法：

```text
用户只想看计划
Planner 为了规划先读文件、跑命令、甚至写草稿
```

正确做法：

- `--plan` 只调用 LLM。
- `tools=[]`。
- 不进入 ToolRegistry。
- 不写 workspace 文件，除了保存 plan metadata。

### 2. Plan schema 太松，Executor 没法用

如果 plan 只是自然语言：

```text
1. 看一下项目
2. 改一下问题
3. 测一下
```

Executor 很难知道：

- step id 是什么。
- 风险等级是什么。
- 建议工具是什么。
- 哪一步需要审批。
- 失败后重试哪一步。

所以 PyAgentCLI 使用结构化字段：

```text
id, title, description, suggested_tools, risk, status, result_summary
```

### 3. 没有持久化，恢复能力就不存在

很多 demo agent 只把 plan 放在内存里。

一旦进程退出：

- plan id 没了。
- step status 没了。
- 执行结果没了。
- Reviewer 无法复盘。
- 用户不能 resume。

所以 PyAgentCLI 把 plan 保存到：

```text
.pyagent/plans/*.json
```

### 4. 状态机语义混乱

最常见的错误是把所有“不成功”都叫 failed。

但真实 Agent 里至少要区分：

- `failed`：执行了，但出错。
- `skipped`：没执行，可能是用户拒绝。
- `cancelled`：流程取消，需要重新确认。

这三个状态的恢复策略不同。

### 5. 重试时没有重置下游步骤

假设：

```text
S1 success
S2 failed
S3 success
```

如果你只把 S2 改回 pending，而保留 S3 success，就会出问题。

因为 S3 的 success 可能基于 S2 的旧失败状态或旧输出。

正确做法：

```text
retry S2 -> S2 pending, S3 pending
```

### 6. Plan-level approval 和 tool-level approval 混为一谈

用户批准一个 WRITE step，不代表所有写文件工具都可以无条件执行。

安全边界应该分两层：

- plan-level approval：用户同意这个步骤可以尝试。
- tool-level approval：具体工具调用仍然检查路径、命令、风险和 preview。

这能防止 Executor 在一个被批准的 step 里做超出预期的事。

### 7. Planner 输出过大步骤

坏 plan：

```text
S1: 修改整个项目并跑测试
```

好 plan：

```text
S1: Inspect relevant files
S2: Apply minimal code change
S3: Run focused tests
S4: Summarize diff and risks
```

Agent 计划要小、可审查、可恢复。

### 8. 声称 DAG 但没有依赖模型

真正 DAG 至少要有：

```text
step.id
step.depends_on[]
step.status
scheduler
cycle detection
conflict detection
```

如果只是按顺序执行 S1、S2、S3，不应该叫已实现 DAG。

### 9. 并行执行写同一个文件

未来做 DAG 并行时，最危险的是：

```text
S2 writes README.md
S3 also writes README.md
```

如果没有文件锁、diff merge 或冲突检测，两个 step 会互相覆盖。

所以 DAG 的难点不只是拓扑排序，还包括资源冲突。

### 10. Reviewer 只写总结，不影响状态

很多项目的 Reviewer 是形式主义：

```text
Review: looks good.
```

真正有用的 Reviewer 应该能影响 gate：

- block failed step。
- block skipped step。
- 给出 retry proposal。
- 列出 git diff。
- 建议测试。

PyAgentCLI 当前就是按这个方向做的。

## 简历上怎么写

保守可信版：

> 设计并实现 PyAgentCLI 的 Plan-and-Execute 工作流，支持计划预览、用户审批、计划持久化、步骤级状态机、失败恢复、单步重试和 Reviewer gate，提升本地 Coding Agent 在多步骤任务中的可控性与可复盘性。

更技术版：

> 为 Python AI Coding Agent CLI 实现 Planner / Executor / Reviewer 协作链路：Planner 输出结构化 PlanPreview，Executor 以 step contract 串行执行 approved steps，PlanStore 将 PlanRun 持久化到 `.pyagent/plans`，Reviewer 基于 step status、audit log 与 git diff 生成 gate decision 和 retry proposal。

不要这么写：

> 实现完整 DAG 并行调度系统。

除非后续真的加上 dependencies、scheduler、并发执行和冲突检测。

## 面试官会怎么追问

### Q1：ReAct 和 Plan-and-Execute 有什么区别？

一句话答案：

> ReAct 是边想边做，Plan-and-Execute 是先拆计划、让用户审查，再按步骤执行。

展开回答：

- ReAct 适合短任务和探索。
- Plan-and-Execute 适合多步骤、高风险、需要恢复的任务。
- PyAgentCLI 通过 `--plan` 和 `--execute-plan` 把两者区分开。
- 计划会保存到 `.pyagent/plans/*.json`，支持 show/list/resume/retry。

### Q2：为什么 `--plan` 不能执行工具？

一句话答案：

> 因为 plan preview 是用户审查阶段，不能在审查前产生副作用。

展开回答：

- 工具调用可能读敏感文件、写文件、跑命令。
- 用户还没有批准计划。
- 所以 Planner 只调用 LLM，不传 tools。
- 真正执行发生在 `--execute-plan` 审批之后。

### Q3：为什么要保存 plan？

一句话答案：

> 因为真实任务会失败、中断、被拒绝，plan 持久化让 Agent 可以恢复。

展开回答：

- plan id 能定位一次任务。
- step status 能知道完成到哪里。
- execution_result 能复盘每一步输出。
- reviewer 能基于历史状态做 gate。
- 用户可以 `--resume-plan` 或 `--retry-step`。

### Q4：为什么 skipped 不能算成功？

一句话答案：

> skipped 代表某个步骤没有执行，可能是用户拒绝了风险操作，不能假装任务完整完成。

展开回答：

- failed 是执行失败。
- skipped 是未执行。
- cancelled 是流程取消。
- 这三种都应该进入 Reviewer gate。
- PyAgentCLI 会对这些状态 block，并给出不同 retry proposal。

### Q5：Plan-level approval 和 tool-level approval 区别是什么？

一句话答案：

> 前者批准一个步骤的意图，后者批准具体工具的真实副作用。

展开回答：

- WRITE step 需要 plan-level approval。
- 执行 step 时，`edit_file` / `write_file` 仍要经过 ToolRegistry 的安全策略。
- 这样可以防止 Executor 在已批准步骤里做超出预期的文件修改或 shell 命令。

### Q6：你们现在实现 DAG 了吗？

一句话答案：

> 还没有完整 DAG；现在是 Plan-and-Execute 的串行工作流，已经具备向 DAG 演进的 step/status/store 基础。

展开回答：

- 已有 step id、risk、status、PlanStore、Executor、Reviewer。
- 还缺 depends_on、拓扑排序、循环检测、并行调度、资源冲突检测。
- 当前文档和简历不会夸大成完整 DAG。

### Q7：Reviewer 为什么不是形式主义？

一句话答案：

> 因为 Reviewer 的 gate 会影响最终状态，而不是只生成总结文本。

展开回答：

- 它检查 step status。
- failed / skipped / cancelled 会 block。
- 它读取 git diff 和 audit log。
- 它生成 suggested tests 和 retry proposal。
- LLM reviewer suggestion 不能覆盖 deterministic gate。

## 标准回答思路

如果面试官让你整体讲 Plan-and-Execute，可以按这个顺序：

1. 先讲 ReAct 的局限：短任务可以，复杂任务不可控。
2. 再讲 Plan-and-Execute 的目标：先计划、再审批、再执行、可恢复、可复核。
3. 落到 PyAgentCLI：`--plan / --execute-plan / .pyagent/plans`。
4. 讲数据结构：`PlanRun -> PlanPreview -> PlanStep`。
5. 讲状态机：`pending / running / success / failed / skipped / cancelled`。
6. 讲安全：plan-level approval 和 tool-level approval。
7. 讲 Reviewer gate：防止假成功。
8. 最后讲 DAG 边界：现在串行，未来加 dependencies 和并发调度。

一版完整回答：

> ReAct 适合短任务，因为它是边想边调用工具；但复杂 coding task 需要先让用户知道 Agent 准备做什么。PyAgentCLI 里我实现了 Plan-and-Execute 的基础工作流：`--plan` 只生成结构化计划，不执行工具；`--execute-plan` 会先保存 plan、展示给用户审批，然后把每个 approved step 交给 Executor 串行执行。每个 step 有 risk、suggested tools、status 和 result summary，PlanStore 会保存到 `.pyagent/plans`，所以失败后可以 show、resume、retry 或 skip。执行完成后 Reviewer 会检查 step status、audit log 和 git diff，如果发现 failed、skipped、cancelled，就 block 并生成 retry proposal。当前还不是完整 DAG，后续要加 depends_on、拓扑排序、并行调度和写文件冲突检测。

## 还能继续怎么增强

下一阶段可以做真正 DAG：

- 给 `PlanStep` 增加 `depends_on`。
- 增加 DAG schema validation。
- 检测循环依赖。
- 按拓扑顺序调度。
- 无依赖 READ step 并行执行。
- 对 WRITE step 做文件路径声明。
- 检测多个 step 写同一文件。
- 增加 step-level lock。
- 失败时只取消受影响的下游 step。
- 增加可视化 plan graph。
- 允许用户在执行前编辑 plan。

更远一点，可以把角色拆得更明显：

- Planner Agent：只负责拆计划。
- Executor Agent：只执行当前 approved step。
- Reviewer Agent：复核状态、diff 和风险。
- Scheduler：负责 DAG 调度。
- Safety Runtime：负责审批、路径围栏、命令黑名单和审计。

这时 PyAgentCLI 就会从“串行 Plan-and-Execute”进化成更完整的“可审计 Agent Workflow Runtime”。

## 这一篇之后做什么

下一篇进入：

> Memory 系统

Plan 解决的是任务步骤如何拆解、执行和恢复；Memory 解决的是 Agent 如何记住会话、项目和长期偏好，同时避免上下文无限膨胀。
