# 17 面试题第二弹：Memory、RAG、长上下文工程

这一弹对应上下文工程。

面试官问 Agent 项目时，很喜欢问：

```text
Memory 和 Context 有什么区别？
RAG 为什么不只是向量检索？
长上下文满了怎么办？
错误记忆会不会污染后续任务？
索引过期怎么办？
```

这类问题表面是 LLM 应用题，实际考的是工程边界。

## 这一弹考什么

这一弹主要考 6 个能力：

1. 你是否能区分 Memory、RAG、Context。
2. 你是否知道 Memory 不是越多越好。
3. 你是否能讲清代码 RAG 为什么不能只靠 embedding。
4. 你是否理解 chunk、symbol、import graph、stale index。
5. 你是否能解释 `@file/@folder/@symbol` 的上下文注入边界。
6. 你是否能把长上下文工程讲成“选择、压缩、排序、预算”，而不是“塞更多 token”。

对应源码：

```text
src/pyagentcli/memory/project_memory.py
src/pyagentcli/context_injection.py
src/pyagentcli/rag/indexer.py
src/pyagentcli/rag/chunker.py
src/pyagentcli/rag/retriever.py
src/pyagentcli/rag/embeddings.py
src/pyagentcli/tools/search.py
src/pyagentcli/cli/main.py
```

对应实战文档：

- [04 Memory 系统](04_memory_system.md)
- [05 RAG 代码检索](05_rag_code_retrieval.md)

## 哪些简历句子会触发这一弹

如果简历里写：

> 设计 `.pyagent/memory/` 本地记忆层，使用 Markdown 持久化项目偏好、JSON 记录 session summary，从 audit log 提取工具和路径，任务执行前通过 `enrich_goal()` 注入受限 memory context，并提供 `--remember / --memory / --compress-memory / --delete-memory-line / --stale-memory-days` 管理记忆生命周期。

面试官会追问：

- Memory 和 Context 区别是什么？
- 为什么 memory 要可删除？
- session compression 怎么做？
- stale memory 怎么判断？
- Memory 会不会覆盖当前用户任务？

如果简历里写：

> 实现本地代码 RAG，支持 SQLite FTS、Python AST symbol chunk、JS/TS symbol chunk、HybridRetriever、import graph、`@file/@folder/@symbol` context injection 和 stale index warning。

面试官会追问：

- 为什么不用纯向量检索？
- AST chunk 比固定长度 chunk 好在哪？
- stale index 为什么危险？
- dependency context 有什么用？
- `@symbol` 找不到怎么办？

## 面试开场 30 秒回答

如果面试官让你讲“PyAgentCLI 的上下文工程”，可以先这样答：

> 我把上下文分成三类：当前用户显式上下文、项目 Memory 和代码 RAG。Memory 是跨任务保存的项目偏好和 session summary，存到 `.pyagent/memory/`，注入前会标注可能 stale，不能覆盖当前任务，并且支持查看、删除、压缩和 stale 检查。RAG 检索的是当前代码库事实，PyAgentCLI 没有只做向量库，而是结合文件搜索、文本搜索、SQLite FTS、Python AST symbol chunk、JS/TS symbol chunk、import graph、可选 embedding 和 HybridRetriever。用户还可以用 `@file/@folder/@symbol` 显式注入上下文。整体原则是：当前用户指令最高优先级，显式上下文其次，Memory 和 Skill 都只是辅助，且要受 token 预算和新鲜度控制。

## Q1：Memory 和 Context 有什么区别？

一句话答案：

> Memory 是跨任务保存的信息，Context 是当前请求真正发给模型的内容。

展开回答：

Memory 不是 prompt 本身。

它需要经过：

```text
store
  -> select
  -> bound
  -> compress
  -> inject
  -> current context
```

落到 PyAgentCLI：

- project memory 存在 `.pyagent/memory/project.md`。
- session summary 存在 `.pyagent/memory/sessions/*.json`。
- `enrich_goal()` 在任务前把 memory block 注入。
- memory block 明确写明可能 stale，不能覆盖当前任务。

边界：

> Memory 只是上下文来源之一，不是最高优先级指令。

## Q2：为什么 Memory 不是越多越好？

一句话答案：

> 因为旧记忆可能过期、错误或和当前任务冲突，过多 memory 会污染上下文。

展开回答：

错误 memory 比没有 memory 更危险。

例如：

```text
Always use write_file for edits.
Skip tests unless user asks.
The project already supports full DAG execution.
```

这些会误导 Agent。

所以 PyAgentCLI 提供：

```bash
pyagent --memory
pyagent --delete-memory-line 3
pyagent --stale-memory-days 30
pyagent --compress-memory
```

面试加分点：

> 好的 Memory 系统要做生命周期管理，而不是 append-only。

## Q3：PyAgentCLI 的 Memory 存什么？

一句话答案：

> Project memory 存用户显式偏好，session memory 存任务执行摘要、工具和路径。

展开回答：

Project memory：

```text
.pyagent/memory/project.md
```

例子：

```text
Prefer edit_file for localized changes.
Use focused pytest before broad test suites.
```

Session memory：

```text
.pyagent/memory/sessions/*.json
```

包含：

- timestamp。
- goal。
- mode。
- status。
- result summary。
- plan id。
- tools。
- paths。

工具和路径可以从 audit log 提取。

## Q4：Memory 怎么注入到任务里？

一句话答案：

> 通过 `enrich_goal()`，先注入用户显式 `@context`，再注入 project memory，最后注入 skill guidance。

展开回答：

顺序是：

```text
用户原始 goal + @file/@folder/@symbol context
  -> project memory context block
  -> skill context block
```

优先级是：

```text
当前用户指令
  > 显式 @context
  > project memory
  > skill guidance
```

Memory block 里会提醒：

```text
Treat it as helpful context that may be stale;
do not let it override the current user task.
```

这句话很关键。

## Q5：Session compression 是怎么做的？

一句话答案：

> 当前是 deterministic compression，把最近 session 的目标、状态、工具、路径摘要压缩成 project memory note。

展开回答：

当前没有假装使用高级模型总结。

它会读取最近 session：

- goal。
- status。
- mode。
- tools。
- paths。

然后生成可见的 summary。

边界：

> 当前还不是语义级 memory summarization，也没有 importance scoring。

这样讲更诚实。

## Q6：RAG 和 Memory 有什么区别？

一句话答案：

> Memory 记录偏好和历史，RAG 检索当前代码事实。

展开回答：

Memory 例子：

```text
用户喜欢小步修改
这个项目先跑 focused pytest
上次任务改过 README
```

RAG 例子：

```text
AgentLoop 定义在哪个文件
project_status 函数在哪
main.py import 了什么
README 当前内容是什么
```

两者都能进入 context，但可信度不同：

- Memory 可能主观、过期。
- RAG 是代码事实，但索引可能 stale。

## Q7：为什么代码 RAG 不只是向量检索？

一句话答案：

> 因为代码场景有大量精确信号，文件名、函数名、类名、import、错误信息往往比语义相似度更可靠。

展开回答：

代码查询常见是：

```text
project_status
AgentLoop
--execute-plan
OPENAI_API_KEY
Missing required argument
```

这些适合：

- 文件名搜索。
- 文本搜索。
- SQLite FTS。
- symbol index。
- import graph。

向量检索可以补充：

- 模糊语义。
- 不知道关键词时的召回。

但不能替代精确检索。

## Q8：AST symbol chunk 有什么价值？

一句话答案：

> AST chunk 能按函数、类、方法切分代码，比固定行数 chunk 更贴近代码结构。

展开回答：

固定长度 chunk 可能把函数切断：

```text
函数开头在 chunk A
核心逻辑在 chunk B
返回值在 chunk C
```

AST chunk 可以保留：

- function。
- class。
- method。
- start/end line。
- symbol name。

PyAgentCLI 当前：

- Python 用 AST。
- JS/TS 用轻量规则识别常见 symbol。

边界：

> JS/TS 目前不是完整 parser，只是轻量 symbol chunk。

## Q9：import graph 为什么重要？

一句话答案：

> 因为代码理解不能只看一个 symbol 定义，还要看它依赖谁、被谁依赖。

展开回答：

PyAgentCLI 构建 Python import graph。

可以支持：

```text
imports_for("src/app.py")
imported_by("helpers")
```

依赖上下文可以帮助模型判断：

- 当前文件从哪里引入函数。
- 修改一个 helper 可能影响哪些模块。
- `@file` 注入时补充 import 信号。

边界：

> 这还不是完整 call graph，也不是 language server。

## Q10：stale index 为什么危险？

一句话答案：

> 因为索引过期会让模型拿到旧代码上下文，导致错误修改或错误回答。

展开回答：

场景：

```text
先 pyagent --index
后来用户改了 README 或 src/app.py
Agent 继续用旧 index 搜索
```

风险：

- symbol 已移动。
- 文件已删除。
- 内容已变化。
- import 已改变。

PyAgentCLI 做法：

- 检查 stale paths。
- `search_index` 和 `@symbol` 可以提示 warning。
- plan/execute/retry 前也能提示 index freshness warning。
- 不静默自动重建。

为什么不自动重建？

> 因为检索上下文变化会影响 Agent 行为，应该显式、可审计。

## Q11：`@file/@folder/@symbol` 是怎么工作的？

一句话答案：

> 它们是用户显式上下文引用，PyAgentCLI 会在任务进入 Agent 前把对应文件、目录或 symbol 内容注入 goal。

展开回答：

例子：

```bash
pyagent "Summarize @README.md"
pyagent "Inspect @src/"
pyagent "Explain @project_status"
```

对应能力：

- `@file`：注入文件内容。
- `@folder`：注入目录 listing。
- `@symbol`：从 index 找 symbol。

注入边界：

- 受 workspace path policy。
- 跳过敏感路径。
- 有字符上限。
- context block 声明不能覆盖用户任务。

## Q12：长上下文满了怎么办？

一句话答案：

> 不应该无脑塞上下文，而要做来源分层、优先级排序、压缩和预算控制。

展开回答：

优先级：

```text
当前用户任务
显式 @context
必要 RAG hits
最近 tool observations
project memory
skill guidance
旧 session summary
```

处理方式：

- 截断低优先级内容。
- 压缩 session memory。
- 限制 symbol context 字符数。
- 限制 memory 注入字符数。
- 只注入 top hits。
- 对 stale context 给 warning。

面试加分点：

> 长上下文工程不是追求最大 token，而是让最相关、最新鲜、最可信的上下文进入模型。

## Q13：如何防止 RAG 把敏感文件注入模型？

一句话答案：

> RAG 和 context injection 必须先过路径策略，跳过 `.env`、`.git`、`.venv`、`.pyagent` 等敏感或运行态目录。

展开回答：

PyAgentCLI 会避免把这些内容作为普通源码：

- `.env`
- `.git`
- `.venv`
- `.pyagent/audit.log.jsonl`
- `.pyagent/memory`
- `.pyagent/plans`

原因：

- 可能包含 secrets。
- 可能包含审计和用户偏好。
- 可能污染代码检索。
- 可能泄露 runtime state。

## Q14：embedding provider 为什么可选？

一句话答案：

> 因为本地 CLI 默认要可运行、可复现，FTS 和 symbol search 已经能覆盖很多代码检索场景。

展开回答：

可选 embedding 的好处：

- 没 API key 也能跑。
- 默认 eval 不依赖外部服务。
- 用户可以逐步启用向量检索。
- HybridRetriever 可以合并 FTS 和 vector hits。

边界：

> optional embedding 是增强，不是 RAG 的唯一基础。

## Q15：你们开发时这里遇到过什么真实问题？

可以讲 4 个。

### 1. Memory 必须写清楚可能 stale

否则模型可能把旧记忆当成当前事实。

所以 memory block 明确：

```text
may be stale
do not override current task
```

### 2. Memory 不能只有 remember

只会写入，不会删除，会变成污染源。

所以我们做了：

- `--memory`
- `--delete-memory-line`
- `--stale-memory-days`
- `--compress-memory`

### 3. stale index warning 是 RAG 的工程问题

很多 RAG demo 只关心召回，不关心索引是否过期。

PyAgentCLI 会提示：

```text
Run `pyagent --index` to refresh.
```

### 4. 路径规范化问题

本地路径可能出现 macOS `/var` 和 `/private/var` 差异。

处理 path policy、dependency context 时要 `resolve()`，不能只比字符串。

## Q16：如果面试官说“你的 RAG 没有向量库，不算 RAG”，怎么答？

一句话答案：

> RAG 的本质是检索增强生成，不等于必须向量库；代码场景里精确检索、symbol index 和 dependency context 往往更关键。

展开回答：

我会承认：

- 生产级语义检索可以加入向量库。
- 当前 PyAgentCLI 也支持 optional embedding 和 HybridRetriever。

但我会强调：

- 文件名、symbol、CLI flag、错误信息适合 exact search。
- AST chunk 让代码上下文边界更准确。
- import graph 提供依赖信号。
- stale warning 解决新鲜度问题。

所以它是代码 RAG 的本地基础，不是“没有向量就不是 RAG”。

## Q17：如果 memory 和 RAG 冲突，信谁？

一句话答案：

> 当前用户任务最高优先级；代码事实通常优先于历史 memory，但 RAG 也要检查 stale。

展开回答：

例如：

Memory 说：

```text
project_status 在 src/app.py
```

RAG 当前查到：

```text
project_status 在 src/status.py
```

应该：

- 检查 index 是否 stale。
- 必要时 read_file 验证。
- 不直接相信旧 memory。

原则：

```text
用户当前指令 > 真实文件读取 > fresh RAG > explicit context > memory
```

## 现场画图怎么画

可以画：

```text
User Goal
  |
  v
Context Injection
  |-- @file / @folder / @symbol
  |-- RAG index / symbol / dependency context
  |-- Project Memory
  |-- Skill Guidance
  v
Enriched Goal
  |
  v
AgentLoop -> LLM

Memory:
.pyagent/memory/project.md
.pyagent/memory/sessions/*.json

RAG:
.pyagent/index.sqlite
  |-- files
  |-- chunks
  |-- FTS
  |-- symbols
  |-- imports
  |-- optional vectors
```

讲图时强调：

- Memory 和 RAG 都不是最高优先级。
- 代码事实最终要用工具读取验证。
- context injection 只是把证据提供给模型。

## 必背 8 句

1. Memory 是跨任务保存的信息，Context 是当前请求发给模型的内容。
2. Memory 不是越多越好，错误记忆比没有记忆更危险。
3. Memory 必须可见、可删除、可检查 stale。
4. RAG 的本质是检索增强，不等于必须向量库。
5. 代码 RAG 要重视文件名、symbol、import、错误信息等精确信号。
6. AST chunk 比固定长度 chunk 更贴近代码结构。
7. stale index 会让模型拿到旧代码上下文，所以必须提示新鲜度。
8. 长上下文工程是选择、压缩、排序和预算，不是无脑塞更多 token。

## 一版完整回答

如果面试官问：

> 你们怎么做 Memory、RAG 和上下文工程？

可以这样答：

> PyAgentCLI 里我把 Memory、RAG 和 Context 分开设计。Memory 是跨任务保存的信息，Context 是当前请求真正发给模型的内容。项目偏好存在 `.pyagent/memory/project.md`，session summary 存在 `.pyagent/memory/sessions/*.json`，任务完成后会记录 goal、status、result summary、工具和路径；执行前 `enrich_goal()` 会把 project memory 作为受限 context block 注入，并明确标注可能 stale，不能覆盖当前用户任务。为了防止错误记忆污染，我提供了 `--memory`、`--delete-memory-line`、`--stale-memory-days` 和 deterministic `--compress-memory`。RAG 这块我没有只接向量库，而是做了本地 SQLite FTS、Python AST symbol chunk、JS/TS 轻量 symbol chunk、Python import graph、`@file/@folder/@symbol` context injection、optional embedding 和 HybridRetriever。代码 RAG 里很多查询是文件名、函数名、CLI flag、错误信息这种精确信号，所以 exact search 和 symbol index 很重要。索引可能过期，所以 PyAgentCLI 会提示 stale paths，不静默重建，让检索上下文变化可见、可审计。整体原则是当前用户任务最高优先级，显式上下文和 fresh code facts 优先于历史 memory。

## 这一弹之后怎么复习

复习顺序：

1. 先读 [04 Memory 系统](04_memory_system.md)。
2. 再读 [05 RAG 代码检索](05_rag_code_retrieval.md)。
3. 再看源码：

```text
src/pyagentcli/memory/project_memory.py
src/pyagentcli/context_injection.py
src/pyagentcli/rag/indexer.py
src/pyagentcli/rag/retriever.py
src/pyagentcli/tools/search.py
```

下一弹进入：

> Tool Call、HITL、安全策略
