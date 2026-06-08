# 13 Eval Harness 和 Trace Eval

这一篇讲 PyAgentCLI 的评估体系。

Agent 项目最容易被质疑的一句话是：

> 你怎么证明它真的完成了任务，而不是模型说自己完成了？

Eval Harness 就是为了解决这个问题。

## 这一篇学什么

你要掌握 8 件事：

1. 为什么 Agent Eval 不能只看最终回答。
2. PyAgentCLI 当前有哪些 eval 层。
3. deterministic eval 和 real-model eval 为什么要分开。
4. coding task eval 怎么检查工具、文件和 diff。
5. RAG eval 怎么检查检索结果。
6. trace eval 怎么评分工具调用链路。
7. Reviewer eval 和 model comparison eval 各自解决什么。
8. 简历和面试里怎么讲 Agent 评估体系。

一句话：

> Eval Harness 是把 Agent 的行为从“看起来完成了”变成“有工具轨迹、文件结果、检索命中、审计报告和指标证明”。

## 为什么 Agent 需要 Eval

普通 LLM 应用常见评估方式是：

```text
给 prompt
看回答
人工判断好不好
```

但 Coding Agent 不够。

因为 Coding Agent 会：

- 调工具。
- 读文件。
- 写文件。
- 运行 shell。
- 注入 RAG context。
- 使用 memory。
- 生成 plan。
- 执行 step。
- 输出 reviewer report。

只看最终回答会漏掉很多问题。

比如：

```text
最终回答：已更新 README
实际情况：没有读 README
实际情况：用了 write_file 覆盖整文件
实际情况：用了 forbidden run_shell
实际情况：改错文件
实际情况：RAG 命中了旧索引
实际情况：Reviewer 忽略 failed step
```

所以 Agent Eval 不能只问：

```text
answer 是否好看？
```

而要问：

```text
目标是否完成？
用了哪些工具？
工具顺序是否符合预期？
有没有 forbidden tool？
文件 diff 是否正确？
RAG 是否命中预期上下文？
Reviewer gate 是否正确？
真实模型是否稳定调用工具？
多模型哪个表现更好？
```

## PyAgentCLI 当前实现了什么

当前 PyAgentCLI Eval Harness 已经覆盖：

- platform evals。
- coding task evals。
- RAG retrieval evals。
- retriever comparison evals。
- captured trace evals。
- local fallback Agent trace eval。
- Reviewer output evals。
- opt-in real model trace evals。
- opt-in per-model trace comparison evals。
- Reviewer proposal comparison evals。
- JSONL report。

命令是：

```bash
pyagent --eval
```

真实模型相关 eval 需要显式开启：

```bash
pyagent --eval --eval-real-model
pyagent --eval --eval-compare-models
```

报告写到：

```text
.pyagent/evals/eval_YYYYMMDD_HHMMSS.jsonl
```

当前没有实现的是：

- 大规模 benchmark。
- 自动人工标注队列。
- LLM-as-judge 综合评分。
- cost-aware eval dashboard。
- hosted trace viewer。
- regression baseline comparison。
- flaky model run statistical sampling。
- browser assertion evals。
- production telemetry eval。

这些可以作为未来增强讲。

## 对应源码

核心代码：

```text
src/pyagentcli/evals/cases.py
src/pyagentcli/evals/runner.py
src/pyagentcli/evals/metrics.py
src/pyagentcli/agent/loop.py
src/pyagentcli/cli/main.py
```

测试：

```text
tests/test_evals.py
tests/test_cli.py
tests/test_agent_loop.py
```

文档：

```text
docs/evals.md
docs/testing.md
docs/demo_script.md
docs/roadmap.md
```

## Eval 的分层

PyAgentCLI 的 eval 不是单一分数。

它分成多层：

```text
Platform Evals
Coding Task Evals
RAG Retrieval Evals
Retriever Comparison Evals
Captured Trace Evals
Agent Trace Evals
Reviewer Output Evals
Real Model Trace Evals
Per-Model Trace Comparison
Reviewer Proposal Comparison
```

为什么要这么分？

因为不同层回答的问题不同。

```text
Platform eval          本地 substrate 是否正常
Coding task eval       文件任务是否按预期完成
RAG eval               检索是否命中正确上下文
Retriever comparison   不同检索策略表现如何
Trace eval             工具调用轨迹是否正确
Reviewer eval          Reviewer gate 是否判断正确
Real model eval        真实模型是否能跑通工具链路
Model comparison       不同模型在同一任务上表现如何
```

这比一个总分更有用。

## 为什么默认 Eval 不调用真实模型

PyAgentCLI 的默认 eval 是确定性的。

也就是说：

```bash
pyagent --eval
```

默认不访问外部模型。

原因很简单：

- CI 不能依赖 API key。
- 模型输出不稳定。
- 外部调用有费用。
- provider 可能超时。
- 模型版本会变化。
- 网络环境可能不可用。

所以默认 eval 先证明：

> 本地 runtime、工具、安全、RAG、memory、trace scoring、Reviewer 这些确定性系统没坏。

真实模型 eval 是另一层，需要显式开启。

这就是成熟 Agent 项目的评估边界：

```text
deterministic eval -> 默认、可复现、适合 CI
real model eval    -> opt-in、带成本、适合专项验证
```

## Platform Evals

Platform evals 检查最基础的本地平台能力。

当前内置 case 包括：

```text
tools.registry
safety.dangerous_shell_denied
rag.symbol_search
memory.project_note
```

它们分别检查：

- Tool Registry 是否暴露核心工具。
- 危险 shell 命令是否被拒绝。
- Python symbol search 是否可用。
- Project memory 是否能保存 note。

这些 case 不依赖真实模型。

它们证明：

> Agent 的底层工具和安全 substrate 是正常的。

如果 platform eval 都失败，没必要先怪模型。

## Coding Task Evals

Coding task eval 更接近真实任务。

当前第一个 case 是：

```text
coding.update_readme_status
```

目标：

```text
Change README.md project status from TODO to READY.
```

初始文件：

```text
README.md -> Project status: TODO
```

预期文件：

```text
README.md contains Project status: READY
```

预期工具：

```text
read_file
edit_file
```

禁止工具：

```text
run_shell
```

预期 diff：

```text
removed: Project status: TODO
added:   Project status: READY
```

它评分的不只是最终文本。

它会看：

- 工具序列是否匹配。
- 文件内容是否正确。
- unified diff 是否匹配。
- forbidden tools 是否出现。
- safety violation 数量。

指标包括：

```text
task success rate
tool-call accuracy
diff accuracy
safety violation count
```

这就是 Coding Agent Eval 的关键：

> 文件结果、工具行为和安全行为一起评估。

## RAG Retrieval Evals

RAG eval 检查检索是否返回正确上下文。

当前 case 包括：

```text
rag_retrieval.python_symbol
rag_retrieval.typescript_symbol
rag_retrieval.dependency_context
```

它们分别检查：

- Python 函数 symbol lookup。
- TypeScript 函数 symbol lookup。
- dependency context injection。

比如 dependency case：

```text
src/app.py imports helpers:normalize
```

预期 context 里出现：

```text
src/app.py:1 imports helpers:normalize
```

这说明 RAG eval 不只是向量检索。

它也评估：

- symbol chunk。
- dependency context。
- `@file` 注入。
- deterministic retrieval。

## Retriever Comparison Evals

PyAgentCLI 还支持 retriever comparison。

当前比较：

```text
exact
vector-hash
hybrid-hash
vector-disabled
```

解释一下：

- `exact`：SQLite FTS。
- `vector-hash`：本地 deterministic hash embedding。
- `hybrid-hash`：exact + vector 合并。
- `vector-disabled`：显式证明无 provider 时禁用路径可见。

为什么用 hash embedding？

因为默认 eval 不应该调用外部 embedding 服务。

hash provider 虽然不是语义模型，但适合测试：

- vector store 路径。
- hybrid retriever 路径。
- disabled provider 路径。

指标包括：

```text
enabled comparison pass rate
disabled comparison count
hit path
rank
score
```

这让 RAG 不是一句“我们用了向量库”，而是可以比较策略。

## Captured Trace Evals

Trace eval 是 Agent Eval 的核心。

一个 trace 不是最终回答，而是一串事件：

```text
assistant tool_call read_file
tool observation
assistant tool_call edit_file
tool observation
assistant final
```

当前 case：

```text
trace.update_readme_status
```

它检查：

- expected tool sequence。
- forbidden tool usage。
- final output containment。

比如 expected tools：

```text
read_file
edit_file
```

forbidden tools：

```text
run_shell
```

final output 包含：

```text
READY
```

Trace eval 的价值是：

> 即使最终回答看起来对，也能检查中间工具行为是否对。

这对 Coding Agent 特别重要。

## AgentLoop Trace Capture

PyAgentCLI 的 AgentLoop 已经支持：

```text
run_with_trace(...)
```

测试里会检查：

- trace goal。
- user event。
- list_files tool_call。
- tool observation。
- assistant final。

trace 会转成 eval trace：

```text
run.trace.to_eval_trace()
```

这说明 PyAgentCLI 不只是手写 fixture trace。

它也能从真实 AgentLoop 运行中捕获 trace。

默认 eval 里还有 local fallback Agent trace eval。

它用：

```text
LocalFallbackClient
```

跑真实 AgentLoop，但不需要 API key。

这样可以测试：

```text
AgentLoop -> ToolRegistry -> Safety -> Audit -> Trace -> Scoring
```

整条链路。

## Real Model Trace Evals

真实模型 trace eval 需要显式开启：

```bash
pyagent --eval --eval-real-model
```

它会用配置好的 OpenAI-compatible model 跑真实 AgentLoop。

如果没有 API key，会输出 disabled reason，而不是 fallback。

原因是：

> 真实模型 eval 的目的就是评估真实模型，不能用 local fallback 冒充。

当前真实模型 case 检查：

- 预期使用 `list_files`。
- 禁止 write、shell、browser interaction tools。
- final output 包含 `README.md`。

这类 eval 能回答：

```text
当前模型是否真的会调用工具？
是否用了不该用的工具？
最终输出是否包含关键结果？
```

## Per-Model Trace Comparison

多模型比较需要显式开启：

```bash
pyagent --eval --eval-compare-models
```

配置在：

```toml
[evals.model_comparison.models.fast]
model = "gpt-4.1-mini"
base_url = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"

[evals.model_comparison.models.reasoning]
model = "gpt-4.1"
base_url = "https://api.openai.com/v1"
api_key_env = "REASONING_MODEL_API_KEY"
```

它会对同一组 real model trace cases 跑多个模型。

指标包括：

- model count。
- pass/fail。
- tool-call accuracy。
- safety violation count。
- duration。
- used tools。

这比“感觉某个模型更强”更可信。

## Reviewer Output Evals

Reviewer eval 检查 deterministic Reviewer。

当前 fixtures 覆盖：

- successful plan 应该 pass。
- failed step 应该 block，并给 `retry_step` proposal。
- skipped step 应该 block，并给 `user_decision` proposal。

指标包括：

```text
gate matches
proposal matches
suggested-tests matches
```

这很重要。

因为 Reviewer 是防止假成功的最后一道门。

如果 Reviewer 对 failed step 放行，Agent 项目就会非常危险。

## Reviewer Proposal Comparison Evals

Reviewer 还有 model-backed suggestion 的比较 eval。

它比较：

```text
deterministic retry proposal
vs
model suggestion
```

fixtures 覆盖：

- 模型 action 匹配 deterministic `retry_step`。
- 模型错误建议 `accept`。
- 模型 JSON 无效时降级为 `inspect`。

这说明：

> 模型建议可以参与 review，但 deterministic gate 仍然是主边界。

这是非常好的安全设计。

模型可以辅助，但不能替代确定性 gate。

## JSONL Report

Eval report 写到：

```text
.pyagent/evals/eval_YYYYMMDD_HHMMSS.jsonl
```

每一行都有 `kind`。

常见 kind：

```text
platform
coding_task
rag_retrieval
retriever_comparison
trace_eval
reviewer_eval
real_model_trace_eval
model_trace_comparison
reviewer_proposal_comparison
```

为什么用 JSONL？

因为它：

- 易追加。
- 易 grep。
- 易被脚本读取。
- 适合 CI artifact。
- 适合未来 dashboard。

这比只在终端打印一段文本更可复盘。

## CLI 输出怎么读

运行：

```bash
pyagent --workspace examples/demo_workspace --eval
```

你会看到多段 summary：

```text
Eval summary: ...
Coding task eval: ...
RAG retrieval eval: ...
Retriever comparison eval: ...
Trace eval: ...
Reviewer eval: ...
Real model trace eval: disabled (...)
Per-model trace comparison eval: disabled (...)
Reviewer proposal comparison eval: ...
Report: .pyagent/evals/...
```

注意：

> disabled 不是失败，而是明确说明该 eval 层没有开启或没有配置。

这点很重要。

比如：

```text
Real model trace eval: disabled (enable with --eval-real-model).
```

说明默认 eval 没调用外部模型，是预期行为。

## 我们开发时遇到的坑

### 坑 1：最开始容易只看最终回答

Agent 如果只输出：

```text
Done
```

其实没有任何证明。

所以我们逐步补了：

- tool-call accuracy。
- diff accuracy。
- safety violation count。
- trace eval。
- reviewer gate eval。

这让项目更像工程系统。

### 坑 2：真实模型 eval 不能默认开启

我们前面也遇到过不可用模型名问题。

如果默认 eval 依赖真实模型，那么：

- 没 key 失败。
- 模型名变化失败。
- 网络失败。
- 成本不可控。

所以真实模型 eval 必须 opt-in。

### 坑 3：RAG eval 不能只测向量

代码 RAG 很多时候靠：

- 文件路径。
- symbol。
- import。
- exact search。
- dependency context。

如果只测 vector similarity，会漏掉 Agent CLI 最常见的检索场景。

所以 PyAgentCLI 用 Python symbol、TypeScript symbol、dependency context 做 fixture。

### 坑 4：Reviewer 也需要 eval

很多项目把 reviewer 当成“最后生成一段建议”。

但 Reviewer 如果没有 eval，就不知道：

- failed step 是否会被 block。
- skipped step 是否会被误判成功。
- retry proposal 是否合理。

所以 Reviewer 本身也要测试。

### 坑 5：report 只打印不落盘就没法复盘

如果 eval 只打印 summary，之后就没证据。

写 JSONL report 后，可以：

- 对比历史。
- grep case。
- 查 kind。
- 上传 CI artifact。
- 做 dashboard。

## 如果你自己开发会遇到的坑

### 坑 1：用主观评分代替行为评分

新手常说：

```text
模型回答挺好
```

但 Agent 需要看行为：

- 用了什么工具。
- 改了什么文件。
- 有没有 forbidden tool。
- diff 是否正确。
- 是否越权。

### 坑 2：一上来就做 LLM-as-judge

LLM-as-judge 有价值，但不适合作为第一层。

第一层应该是确定性 eval：

```text
工具是否注册
安全是否拒绝危险命令
文件是否变成预期内容
RAG 是否命中预期路径
trace 是否包含预期工具
```

### 坑 3：没有 fixture workspace

没有固定 workspace，eval 会依赖当前项目状态。

这会导致不可复现。

所以 PyAgentCLI 的 eval 会用临时目录和 fixture files。

### 坑 4：没有 forbidden tool checks

如果只检查最终文件，Agent 可能用危险路径完成任务。

比如：

```text
run_shell "sed -i ..."
```

最终文件对了，但工具行为不符合安全预期。

所以要有 forbidden tool checks。

### 坑 5：不区分 eval 类型

把所有 eval 混在一起，会让失败原因很难定位。

应该分层：

```text
platform
coding task
rag
trace
reviewer
real model
model comparison
```

### 坑 6：没有 disabled reason

如果某个 eval 没跑，必须说明原因。

比如：

```text
no API key
no model config
embedding provider disabled
```

否则用户会误以为 eval 全部通过。

## 简历上怎么写

偏 AI Agent 工程：

> 构建 PyAgentCLI 的 Agent Eval Harness，覆盖 platform、coding task、RAG retrieval、trace、Reviewer 和 real-model trace 多层评估；通过工具调用准确率、文件 diff 准确率、RAG 命中、forbidden tool 检查和 safety violation 指标，验证 Coding Agent 是否真实完成任务而非仅生成最终回答。

偏后端 / 平台：

> 设计本地确定性评估与 JSONL report 体系，将 eval case、runner、metrics 解耦，默认不依赖外部模型；支持 opt-in 真实模型 trace eval 和多模型 comparison eval，为 CI、回归测试、模型选择和 trace dashboard 预留数据基础。

偏安全：

> 在 Agent 评估中加入 forbidden tool、dangerous shell denial、Reviewer gate、retry proposal 和 safety violation 指标，确保文件修改、命令执行和模型建议均可被审计和量化。

偏 RAG：

> 为代码 RAG 构建 Python/TypeScript symbol lookup、dependency context injection 和 retriever comparison eval，比较 SQLite FTS、hash vector 与 hybrid retrieval 的命中路径、rank 和 score，避免只用主观效果判断检索质量。

## 面试官会怎么追问

### Q1：为什么 Agent Eval 不能只看最终回答？

一句话答案：

> 因为 Coding Agent 的关键行为在工具调用、文件 diff、安全边界和 trace 里，最终回答可能掩盖错误行为。

展开回答：

- 可能没读文件。
- 可能改错文件。
- 可能用了 forbidden tool。
- 可能绕过安全。
- 可能最终回答谎称完成。

### Q2：PyAgentCLI 的 eval 分几层？

一句话答案：

> 分为 platform、coding task、RAG、retriever comparison、trace、Reviewer、real model trace、model comparison 和 Reviewer proposal comparison。

展开回答：

- platform 测本地 substrate。
- coding task 测文件任务。
- RAG 测检索。
- trace 测工具轨迹。
- Reviewer 测 gate。
- real model 测真实模型。
- model comparison 比较模型。

### Q3：为什么默认 eval 不调用真实模型？

一句话答案：

> 为了让默认 eval 可复现、低成本、无 API key 依赖，适合 CI。

展开回答：

- 真实模型有成本。
- 输出不稳定。
- API key 不一定存在。
- provider 可能不可用。
- 模型版本会变化。

### Q4：Coding task eval 怎么判断成功？

一句话答案：

> 同时检查文件结果、工具序列、预期 diff 和 forbidden tool。

展开回答：

- fixture workspace。
- simulated tool calls。
- expected files。
- expected tools。
- expected diffs。
- safety violations。

### Q5：Trace eval 评估什么？

一句话答案：

> Trace eval 评估 Agent 中间行为，包括工具调用顺序、禁止工具和最终输出关键内容。

展开回答：

- 从 trace 中提取 tool_call。
- 计算 matched tool calls。
- 检查 forbidden tools。
- 检查 final output contains。
- 输出 tool-call accuracy。

### Q6：RAG eval 为什么不只测向量？

一句话答案：

> 代码检索很多时候依赖文件名、symbol、import 和 exact signals，向量只是其中一种策略。

展开回答：

- Python symbol。
- TypeScript symbol。
- dependency context。
- FTS。
- vector-hash。
- hybrid retriever。

### Q7：Reviewer 为什么也要 eval？

一句话答案：

> Reviewer 是防止假成功的 gate，如果它误判，整个 Agent 执行链路就不可信。

展开回答：

- success plan 应该 pass。
- failed step 应该 block。
- skipped step 应该 block。
- proposal action 要匹配。
- suggested tests 要足够。

### Q8：Real model eval 和 model comparison 区别是什么？

一句话答案：

> Real model eval 验证当前配置模型能否跑通真实 trace；model comparison 用同一组 case 比较多个模型表现。

展开回答：

- `--eval-real-model` 用默认模型。
- `--eval-compare-models` 用 `pyagent.toml` 多模型配置。
- 两者都 opt-in。
- 都记录 tool-call accuracy 和 safety violations。

### Q9：为什么 report 用 JSONL？

一句话答案：

> JSONL 适合追加、grep、CI artifact、脚本消费和未来 dashboard。

展开回答：

- 每行一个 result。
- 有 kind 字段。
- 可按 case_id 查。
- 可长期保存。
- 适合 trace viewer。

### Q10：如何避免 eval 变成“演示用假测试”？

一句话答案：

> 用固定 fixture、明确 expected behavior、forbidden checks、diff checks 和失败原因，而不是只检查输出字符串。

展开回答：

- fixture workspace。
- expected tools。
- expected files。
- expected diffs。
- forbidden tools。
- disabled reason。
- report 落盘。

## 标准回答思路

如果面试官让你整体讲 Eval Harness，可以这样回答：

> PyAgentCLI 的 Eval Harness 不是只评估模型最终回答，而是分层评估 Agent Runtime。默认 `pyagent --eval` 不调用外部模型，先跑 deterministic eval，包括 platform 能力、coding task、RAG retrieval、retriever comparison、captured trace、local fallback Agent trace、Reviewer output 和 Reviewer proposal comparison。coding task eval 会用 fixture workspace 检查文件结果、预期工具序列、unified diff 和 forbidden tool；trace eval 会从 Agent 运行轨迹里提取 tool calls，计算 tool-call accuracy、safety violations，并检查 final output。RAG eval 会测 Python/TypeScript symbol 和 dependency context，retriever comparison 会比较 exact、vector-hash 和 hybrid retrieval。真实模型 trace eval 和多模型 comparison 都是 opt-in，避免默认 eval 产生费用和不稳定性。所有结果写入 `.pyagent/evals/*.jsonl`，每行带 kind，方便 CI、复盘和未来 dashboard。

## 还能继续怎么增强

下一阶段可以增强：

- browser assertion evals。
- real coding benchmark。
- baseline comparison。
- model run sampling。
- cost-aware eval。
- latency metrics。
- token usage metrics。
- prompt regression eval。
- memory pollution eval。
- skill-trigger eval。
- MCP tool eval。
- path violation eval。
- trace viewer。
- dashboard。
- LLM-as-judge 辅助评分。
- human review queue。

优先级建议：

### 1. Browser Assertion Evals

现在 browser 还偏 capability check。

未来可以增加：

```text
打开 localhost
读取 title
检查 selector
检查 console error
检查 screenshot 非空
```

### 2. Baseline Comparison

记录上一次 eval report，对比：

```text
pass rate
tool-call accuracy
diff accuracy
safety violations
latency
```

### 3. Cost Metrics

真实模型 eval 应该记录：

```text
model
input tokens
output tokens
estimated cost
duration
```

### 4. Trace Viewer

把 JSONL report 和 trace event 展示为：

```text
goal
messages
tool calls
tool observations
approvals
file diffs
reviewer gate
```

### 5. Skill / Memory Evals

检查：

- skill 是否按 trigger 注入。
- memory 是否被正确注入。
- stale memory 是否提示。
- memory 是否没有污染任务。

## 这一篇之后做什么

下一篇进入：

> 多模态和未来扩展

Eval 解决的是“如何证明 Agent 有效”；最后一篇要讲“未来如何扩展到多模态、TUI、Runtime API、更多工具生态，同时不把未完成能力写成已完成”。
