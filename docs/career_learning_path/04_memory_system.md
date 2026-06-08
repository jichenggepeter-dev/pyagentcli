# 04 Memory 系统

这一篇对应 PaiCLI 学习路线里的 Memory / Context Engineering 思路，但内容全部落到 PyAgentCLI 当前的 Python 实现。

先给结论：

> PyAgentCLI 当前实现的是本地、显式、可审查、可删除的 project memory 和 session memory。它不是黑箱长期记忆，也不是把所有历史对话都塞进 prompt。

Memory 这一块很容易被讲虚。真正值得讲的不是“Agent 会记住你”，而是：

- 记什么。
- 存哪里。
- 什么时候注入。
- 注入时优先级是什么。
- 怎么删除错误记忆。
- 怎么发现过期记忆。
- 怎么避免 memory 污染当前任务。

## 这一篇学什么

学完这一篇，你要能讲清楚：

- Memory 和 Context 的区别。
- 为什么 Memory 不是越多越好。
- PyAgentCLI 的 project memory 和 session memory 分别存什么。
- `--remember`、`--memory`、`--compress-memory`、`--delete-memory-line`、`--stale-memory-days` 怎么用。
- Memory 如何在任务前注入进 prompt。
- 为什么 memory 注入必须声明“可能 stale，不能覆盖当前任务”。
- 为什么错误 memory 比没有 memory 更危险。
- 当前 Memory v0.2 的边界和下一步增强方向。

## Memory 和 Context 的区别

Context 是当前这一次请求真正发给模型的内容。

Memory 是跨任务保留下来的信息。

两者关系可以这样理解：

```text
memory store
  -> select / bound / compress / inject
    -> current context
      -> LLM
```

所以一句面试答案是：

> Memory 不是直接等于 prompt。Memory 只有经过筛选、压缩和注入后，才成为当前请求的 context。

这也是为什么不能简单地把所有历史记录拼到 prompt 里。

原因有三个：

- token 有上限。
- 旧信息可能过期。
- 旧偏好不能覆盖用户当前指令。

## 为什么 Agent CLI 需要 Memory

没有 Memory 的 Agent 每次都像第一次进项目：

- 不知道项目偏好。
- 不知道常用测试命令。
- 不知道用户喜欢小步修改。
- 不知道前面任务改过什么。
- 不知道某些工具在这个项目里不可用。

有 Memory 后，Agent 可以减少重复探索。

例如：

```text
Prefer edit_file for localized changes.
Use focused pytest before broad test suites.
This workspace treats docs as learning artifacts, not just README notes.
```

但 Memory 也会带来风险：

```text
Always use write_file for edits.
Skip tests unless user asks.
The project already supports full DAG execution.
```

这些如果被记住，就会污染后续任务。

所以 PyAgentCLI 的策略是：

> Memory 必须可见、可审查、可删除、可检查 stale。

## PyAgentCLI 当前实现了什么

当前已经落地的能力：

- project memory：`.pyagent/memory/project.md`
- session memory：`.pyagent/memory/sessions/*.json`
- `--remember NOTE`：写入项目记忆。
- `--memory`：查看项目记忆和最近 session。
- `--compress-memory`：把最近 session 压缩成 project memory note。
- `--delete-memory-line LINE`：按行删除项目记忆。
- `--stale-memory-days DAYS`：找出超过指定天数的旧记忆。
- 普通 agent task 完成后记录 session summary。
- planned execution 完成后记录 plan session。
- 任务执行前自动注入 project memory。
- memory context 有明确 guardrail：可能过期，不能覆盖当前任务。
- memory 内容有最大注入字符数限制。

当前还没有落地的能力：

- user-level memory。
- 跨 workspace 的长期偏好。
- 模型辅助 memory summarization。
- 向量化 memory retrieval。
- memory importance scoring。
- 自动 stale memory 审批清理。
- memory 与 RAG 的统一检索排序。

所以最准确的表达是：

> PyAgentCLI 已实现本地 project-level memory 生命周期管理，并把 memory 作为受限上下文注入到 Agent 任务中。

## 最小运行例子

写入一条 project memory：

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --remember "Prefer edit_file for localized changes."
```

查看 memory：

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --memory
```

压缩最近 session：

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --compress-memory
```

删除某一行 memory：

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --delete-memory-line 3
```

查看 30 天前的 stale memory：

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --stale-memory-days 30
```

## Memory 存在哪里

PyAgentCLI 使用本地文件存 memory：

```text
.pyagent/
  memory/
    project.md
    sessions/
      2026-...json
```

project memory 是 Markdown：

```text
# Project Memory

- 2026-06-08T12:00:00+00:00: Prefer edit_file for localized changes.
```

session memory 是 JSON：

```json
{
  "timestamp": "2026-06-08T12:00:00+00:00",
  "goal": "update README",
  "mode": "agent",
  "status": "completed",
  "result_summary": "Read README and updated status.",
  "plan_id": null,
  "tools": ["read_file", "edit_file"],
  "paths": ["README.md"]
}
```

这样设计的好处：

- 用户能直接看到。
- 可以手动编辑或删除。
- 不依赖远程服务。
- 适合本地 CLI 项目。
- 审计和复盘更容易。

坏处也要承认：

- 没有语义检索。
- 没有跨项目共享。
- 大量 memory 后需要更好的筛选。
- 手写 Markdown 行号删除比较粗糙。

## Project Memory 做什么

源码：

```text
src/pyagentcli/memory/project_memory.py
```

Project memory 存的是项目级偏好或长期提示。

例如：

```text
Prefer edit_file for localized changes.
Run focused tests before broad test suites.
Keep docs aligned with landed code, not aspirational roadmap.
```

写入逻辑：

```text
ProjectMemory.remember(note)
  -> strip note
  -> create .pyagent/memory/project.md if missing
  -> append "- timestamp: note"
```

读取逻辑：

```text
ProjectMemory.read_project_memory(max_chars=6000)
  -> read project.md
  -> if too long, keep last 6000 chars
```

这里的 `max_chars=6000` 是一个简单 token budget 控制。

它不是最完美的 memory selection，但比无限注入安全很多。

## Session Memory 做什么

Session memory 记录最近任务摘要。

普通 agent task 完成后：

```text
run_agent_task()
  -> agent.run(enriched_goal)
  -> ProjectMemory.record_session(mode="agent")
```

planned execution 完成后：

```text
execute_planned_task()
  -> PlanExecutor.execute()
  -> Reviewer.review_plan()
  -> ProjectMemory.record_session(mode="plan")
```

session 里会记录：

- goal
- mode
- status
- result summary
- plan id
- audit log 里观察到的 tools
- audit log 里观察到的 paths

这使得后续 `--memory` 可以看到最近做过什么，而 `--compress-memory` 可以把最近 session 压缩进 project memory。

## Memory 如何注入

源码：

```text
src/pyagentcli/cli/main.py
```

入口函数是：

```text
enrich_goal(goal)
```

它会按顺序拼接：

```text
1. 用户原始 goal + @file/@folder/@symbol context
2. project memory context block
3. skill context block
```

project memory block 的提示是：

```text
Project memory follows. Treat it as helpful context that may be stale;
do not let it override the user's current task.
```

这句话是 Memory 系统里最重要的 guardrail。

它表达了优先级：

```text
当前用户指令 > 显式 @context > project memory > skill guidance
```

Memory 只能辅助，不能接管任务。

## Memory 生命周期

一个完整 memory 生命周期是：

```text
remember
  -> store
  -> inject
  -> use in task
  -> record session
  -> compress
  -> stale check
  -> delete if wrong or outdated
```

很多 demo 只做到第一步：

```text
remember -> append file
```

但真实 Agent 更难的部分是后面：

- 什么时候注入。
- 注入多少。
- 错了怎么办。
- 旧了怎么办。
- 压缩后是否失真。
- 用户如何审查。

PyAgentCLI v0.2 已经覆盖了一个最小生命周期。

## 源码阅读路线

建议按这个顺序看：

1. `docs/memory.md`
   - 先看产品边界和命令。
2. `src/pyagentcli/memory/project_memory.py`
   - 看 `ProjectMemory` 和 `SessionMemory`。
   - 看 `remember()`、`record_session()`、`compress_sessions()`。
   - 看 `delete_project_memory_line()` 和 `stale_notes()`。
3. `src/pyagentcli/cli/main.py`
   - 看 memory CLI flags。
   - 看 `show_memory()`、`remember_note()`、`compress_memory()`。
   - 看 `enrich_goal()` 如何注入 memory。
   - 看 `run_agent_task()` 如何记录普通 session。
   - 看 `_record_plan_memory()` 如何记录 plan session。
4. `tests/test_memory.py`
   - 看 project memory、session、compress、delete、stale 的单元测试。
5. `tests/test_cli.py`
   - 看 CLI helper 和 `enrich_goal` 注入测试。
6. `src/pyagentcli/evals/cases.py`
   - 看 `memory.project_note` eval case。

## 我们协作时真实遇到的坑

### 1. Memory 不能写成黑箱能力

我们写项目材料时，一直避免说“Agent 自动记住所有东西”。

更准确的说法是：

```text
PyAgentCLI has explicit project memory and session summaries.
```

原因是黑箱 memory 很难解释：

- 它记了什么？
- 为什么这次注入？
- 用户怎么删？
- 如果记错了怎么办？

面试时讲不清楚这些，很容易被认为只是套概念。

### 2. Memory 必须写清楚“可能 stale”

我们在 context block 里写了：

```text
may be stale
do not let it override the user's current task
```

这不是文案细节，而是安全边界。

旧记忆可能和当前任务冲突。当前用户指令永远优先。

### 3. 不能只做 remember，不做 delete

如果只提供 `--remember`，Memory 会变成 append-only 污染源。

所以 PyAgentCLI 同时提供：

```text
--memory
--delete-memory-line
--stale-memory-days
```

这说明 Memory 是生命周期管理，不只是存储。

### 4. Session compression 不能装成智能总结

当前 `compress_sessions()` 是 deterministic compression。

它会汇总：

- 最近 session 数量。
- recent goals。
- common tools。
- observed paths。

它不是 LLM 总结器。

所以文档里必须写清楚：

```text
已实现 deterministic session compression
未来可增强 model-assisted summarization
```

### 5. Plan session 和普通 agent session 都要记录

我们后面做 Plan-and-Execute 时，不能只让普通任务进入 memory。

planned execution 也会调用 `_record_plan_memory()`，把 plan id、status、review result 或 execution result 写进 session memory。

这样 Memory 才能覆盖真实工作流。

## 你自己开发时大概率会遇到的坑

### 1. 把 Memory 直接拼到最前面

错误做法：

```text
Project memory:
...

User task:
...
```

这样模型可能把旧 memory 当成最高优先级。

更合理的方式：

```text
User task first
Explicit context
Memory as helpful stale context
Skill guidance as auxiliary context
```

并明确：

```text
memory cannot override current task
```

### 2. 无限制注入所有历史

很多人会想：

```text
既然有长上下文，就把历史都塞进去。
```

问题是：

- token 成本增加。
- 模型注意力被稀释。
- 旧错误更容易被利用。
- 当前任务反而不清晰。

PyAgentCLI 使用 `MAX_MEMORY_CONTEXT_CHARS = 6000` 做基础限制。

### 3. 没有删除能力

如果记错了：

```text
Always skip tests.
This project uses npm, not pytest.
Full DAG execution is already implemented.
```

没有删除能力就很危险。

所以最低限度要有：

```text
show memory
delete memory
stale memory review
```

### 4. 把 session summary 当长期真理

Session summary 只说明某次任务发生了什么。

它不一定代表长期规则。

例如：

```text
Ran no tests because this was a docs-only edit.
```

不能压缩成：

```text
Do not run tests.
```

这就是 compression 的失真风险。

### 5. 不区分 project memory 和 user memory

Project memory 是当前 repo 的偏好。

User memory 是跨项目偏好。

这两者不能混：

```text
当前项目使用 pytest
```

不应该变成用户在所有项目里的永久偏好。

PyAgentCLI 当前只做 project memory，是一个保守边界。

### 6. Memory 文件没有放进 `.pyagent`

如果 memory 散落在项目根目录：

- 容易污染源码。
- 容易被误提交。
- 不好统一清理。
- 不好和 plan/review/audit 放在同一运行态目录。

PyAgentCLI 把它放在：

```text
.pyagent/memory/
```

这和 `.pyagent/plans/`、`.pyagent/reviews/` 是同一个本地 runtime 思路。

### 7. 不记录工具和路径

如果 session 只记录：

```text
goal: update README
result: done
```

后续复盘价值很低。

更有用的是：

```text
tools: read_file, edit_file
paths: README.md
```

PyAgentCLI 会从 audit log 里提取这些信息。

### 8. stale 检查只看文本，不看时间

如果 memory 没有 timestamp，就无法判断过期。

所以 project memory 每条 note 都带 UTC timestamp：

```text
- 2026-06-08T12:00:00+00:00: ...
```

`--stale-memory-days` 才能工作。

### 9. 让模型自动改 memory

这是一个危险设计。

模型可以建议写入 memory，但真正写入应该是显式动作。

在 PyAgentCLI 里：

```text
pyagent --remember "..."
```

是用户明确触发的命令。

未来即使做 tool-based memory write，也应该走审批。

### 10. Memory 和 RAG 边界混乱

Memory 存偏好和历史摘要。

RAG 检索代码事实。

不要把两者混成一个东西。

例如：

- “Prefer edit_file” 是 memory。
- “AgentLoop 在 src/pyagentcli/agent/loop.py” 是 RAG/code context。
- “上次 plan_abc 修改了 README” 是 session memory。

## 简历上怎么写

保守可信版：

> 为 PyAgentCLI 实现本地 Memory 系统，支持 project memory、session summary、显式 remember、上下文注入、session 压缩、stale memory 检查和按行删除，确保 Agent 跨任务复用项目偏好的同时保持记忆可见、可控、可审查。

更技术版：

> 设计 `.pyagent/memory/` 本地记忆层：使用 Markdown 持久化项目偏好、JSON 记录 session summary，从 audit log 提取工具和路径，任务执行前通过 `enrich_goal()` 注入受限 memory context，并提供 `--remember / --memory / --compress-memory / --delete-memory-line / --stale-memory-days` 管理记忆生命周期。

不要这么写：

> 实现长期个性化记忆和智能语义检索。

除非后续真的实现 user-level memory、embedding retrieval、importance scoring 和跨项目 memory。

## 面试官会怎么追问

### Q1：Memory 和 Context 有什么区别？

一句话答案：

> Memory 是跨任务保存的信息，Context 是当前请求真正发给模型的内容。

展开回答：

- Memory 不一定每次注入。
- 注入前要筛选、压缩、限制长度。
- Context 有 token budget。
- PyAgentCLI 把 project memory 作为受限 context block 注入。

### Q2：为什么 Memory 要可删除？

一句话答案：

> 因为错误 memory 会持续污染后续任务。

展开回答：

- Agent 可能记住错误偏好。
- 旧项目规则可能过期。
- 用户需要能查看和删除。
- PyAgentCLI 提供 `--memory` 和 `--delete-memory-line`。

### Q3：为什么 Memory 不能覆盖当前任务？

一句话答案：

> 当前用户指令是最高优先级，Memory 只是可能过期的辅助上下文。

展开回答：

- Memory 可能来自旧任务。
- 当前任务可能明确改变要求。
- PyAgentCLI 注入时写明 `may be stale` 和 `do not override current task`。

### Q4：Project memory 和 Session memory 区别是什么？

一句话答案：

> Project memory 存项目偏好，Session memory 存最近任务摘要。

展开回答：

- project memory 在 `.pyagent/memory/project.md`。
- session memory 在 `.pyagent/memory/sessions/*.json`。
- session 可以被压缩成 project memory note。
- project memory 会在任务前注入。

### Q5：Memory 怎么防止上下文爆炸？

一句话答案：

> 通过显式写入、有限读取、session 压缩和 stale 检查控制规模。

展开回答：

- 当前 project memory 注入有 `MAX_MEMORY_CONTEXT_CHARS`。
- session 只展示最近几条。
- compression 只压缩最近 session。
- 后续可以加 importance score 和 semantic retrieval。

### Q6：为什么当前不做 user-level memory？

一句话答案：

> 因为项目级 memory 更安全、更可控，也更容易解释边界。

展开回答：

- user memory 会跨项目影响行为。
- 错误 user memory 影响范围更大。
- PyAgentCLI 先把 project memory 做成可见、可删、可检查。
- user-level memory 可以作为后续增强。

### Q7：Memory 和 RAG 有什么区别？

一句话答案：

> Memory 记录偏好和历史，RAG 检索代码事实。

展开回答：

- Memory 例子：用户偏好、项目习惯、历史任务摘要。
- RAG 例子：文件内容、symbol、import graph。
- 两者都可以进入 context，但来源、可信度和更新方式不同。

### Q8：如何防止模型自动污染 memory？

一句话答案：

> Memory 写入必须显式触发，不能让模型静默写入长期状态。

展开回答：

- 当前通过 `--remember` 手动写入。
- session record 是 runtime 记录，不是模型自由写。
- 未来如果让模型建议 memory，也应该走审批和预览。

## 标准回答思路

如果面试官让你整体讲 Memory，可以按这个顺序：

1. 先区分 Memory 和 Context。
2. 说明 Memory 的风险：错误、过期、污染当前任务。
3. 讲 PyAgentCLI 的本地文件设计：`.pyagent/memory/project.md` 和 sessions JSON。
4. 讲 CLI 生命周期：remember、show、compress、delete、stale。
5. 讲注入：`enrich_goal()`，memory block 低优先级且标注 stale。
6. 讲 session：普通 agent task 和 planned execution 都会记录。
7. 讲边界：当前不是 user-level semantic memory。
8. 讲下一步：model-assisted summarization、review prompts、user-level memory、retrieval。

一版完整回答：

> 我把 Memory 和 Context 分开设计。Memory 是跨任务保存的信息，Context 是当前请求真正发给模型的内容。PyAgentCLI 当前实现的是本地 project memory 和 session memory：项目偏好写在 `.pyagent/memory/project.md`，每次 agent task 或 plan execution 会记录 session JSON，包括 goal、status、result summary、plan id、工具和路径。任务执行前，`enrich_goal()` 会把 project memory 作为受限 context block 注入，并明确告诉模型这段 memory 可能 stale，不能覆盖当前用户任务。为了避免错误记忆长期污染，我还提供了 `--memory` 查看、`--delete-memory-line` 删除、`--stale-memory-days` 检查旧记忆，以及 `--compress-memory` 把最近 session 做 deterministic summary。当前还没有做 user-level 长期记忆和语义检索，这是后续增强方向。

## 还能继续怎么增强

下一阶段可以增强：

- model-assisted session summarization。
- memory write approval。
- memory importance score。
- memory source metadata。
- stale memory review prompt。
- user-level memory。
- workspace-level memory inheritance。
- memory retrieval by query。
- memory 与 RAG 的统一 context budget。
- memory diff 和 rollback。
- memory eval case 扩展。

更工程化的方向：

- 给 memory note 增加 id，而不是按行删除。
- 给 memory note 增加 tags。
- 区分 preference、fact、warning、workflow。
- 对每次注入记录 provenance。
- 在 review report 中提示本次用了哪些 memory。

## 这一篇之后做什么

下一篇进入：

> [RAG 代码检索](05_rag_code_retrieval.md)

Memory 解决的是跨任务偏好和历史；RAG 解决的是当前代码库事实。一个 Coding Agent 如果只靠 Memory，会记住很多主观经验；如果没有 RAG，就很难拿到准确、新鲜的代码上下文。
