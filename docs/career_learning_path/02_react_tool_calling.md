# 02 ReAct 和 Tool Calling

这一篇进入 PyAgentCLI 的第一个核心模块：

> 模型如何从“回答问题”升级成“通过工具观察真实环境，再继续推理”。

如果只用一句话概括：

> ReAct 是 Agent 的行为模式，Function Calling / Tool Calling 是模型输出工具调用意图的协议，PyAgentCLI 的 `AgentLoop` 负责把这个意图变成本地受控执行。

## 这一篇学什么

读完这一篇，你应该能讲清楚：

- ReAct 是什么。
- Tool Calling 和 Function Calling 的本质是什么。
- 模型到底会不会执行代码。
- PyAgentCLI 的 Agent Loop 怎么运行。
- 工具调用失败后为什么不能让 Agent 直接崩溃。
- `max_steps` 为什么是 Agent Loop 的必要安全阀。
- trace capture 为什么能帮助 eval。
- 这部分怎么写进简历。
- 面试官会怎么追问。

## 为什么 Agent CLI 需要 ReAct

普通 chatbot 的流程是：

```text
User asks
  -> LLM answers
```

这适合回答常识问题，但不适合 coding agent。

因为 coding agent 面对的是本地仓库：

- 文件内容模型不一定知道。
- 测试结果模型不一定知道。
- 当前目录结构模型不一定知道。
- 用户刚刚改过的代码模型不一定知道。

如果模型直接回答，很容易变成猜。

ReAct 的价值是让模型进入这个循环：

```text
Thought / reasoning
  -> Action / tool call
  -> Observation / tool result
  -> continue reasoning
```

PyAgentCLI 不要求模型输出裸文本格式的 `Thought:`、`Action:`、`Observation:`。它采用 OpenAI-compatible tool calling，把 action 变成结构化 tool call，把 observation 变成本地工具返回结果。

所以 PyAgentCLI 的实际循环是：

```text
messages + tool schemas
  -> LLM
  -> assistant response
    -> if tool_calls:
         ToolRegistry.execute(...)
         append tool observation
         continue
       else:
         final answer
```

## Tool Calling 的本质

Tool Calling 不是模型执行函数。

模型只输出一个结构化调用意图，例如：

```json
{
  "id": "call_1",
  "name": "read_file",
  "arguments": {
    "path": "README.md"
  }
}
```

真正执行的是 PyAgentCLI：

1. `AgentLoop` 收到 `LLMResponse.tool_calls`。
2. `ToolRegistry` 根据工具名找到本地工具。
3. `SafetyPolicy` 检查风险等级、路径围栏和命令规则。
4. `ApprovalHandler` 判断是否需要用户审批。
5. 工具在本地执行。
6. `ToolResult` 转成 observation。
7. observation 作为 tool message 回到消息历史。

面试时最重要的一句话：

> 模型不执行代码。模型只决定“想调用什么工具、传什么参数”，执行权在 Agent Runtime。

## PyAgentCLI 当前实现了什么

核心源码：

```text
src/pyagentcli/agent/loop.py
src/pyagentcli/agent/state.py
src/pyagentcli/agent/trace.py
src/pyagentcli/llm/base.py
src/pyagentcli/llm/openai_compatible.py
src/pyagentcli/tools/registry.py
src/pyagentcli/tools/base.py
```

当前 PyAgentCLI 已经实现：

- `AgentLoop.run()`：执行一次 Agent 任务并返回最终输出。
- `AgentLoop.run_with_trace()`：执行任务并捕获 trace。
- `AgentState`：保存用户目标、workspace、max steps、messages。
- `Message`：支持 system/user/assistant/tool 四种消息角色。
- `ToolCall`：保存工具调用 id、name、arguments。
- `LLMResponse`：保存模型文本和 tool calls。
- `ToolRegistry.schemas()`：把工具 schema 暴露给模型。
- `ToolRegistry.execute()`：执行工具，并接入 safety、approval、audit。
- `max_steps`：防止无限循环。
- `TraceEvent`：记录 user、assistant tool call、tool observation、final。

这已经形成一个最小但完整的 Agent Runtime。

## 对应源码怎么读

### 第一步：读 `llm/base.py`

先看数据结构：

- `ToolCall`
- `Message`
- `LLMResponse`
- `LLMClient`

你要理解：

- `Message.system()` 放系统提示词。
- `Message.user()` 放用户目标。
- `Message.assistant()` 可以携带 tool calls。
- `Message.tool()` 把工具执行结果回传给模型。
- `message_to_openai()` 把内部消息转成 OpenAI-compatible payload。

这一步解决：

> 模型和 Agent Runtime 之间到底传什么数据？

### 第二步：读 `agent/loop.py`

重点看 `run_with_trace()`。

核心逻辑是：

```text
初始化 messages
while step_count < max_steps:
    调 LLM
    记录 assistant message
    如果没有 tool_calls:
        返回 final answer
    对每个 tool call:
        记录 tool_call trace
        调 ToolRegistry.execute
        把 observation 作为 tool message 追加进 messages
达到 max_steps 后停止
```

这一步解决：

> ReAct loop 在代码里到底长什么样？

### 第三步：读 `tools/registry.py`

重点看：

- `schemas()`
- `execute()`
- `default_registry()`

`schemas()` 决定模型能看到哪些工具。

`execute()` 决定工具是否真的能执行。

`default_registry()` 决定 PyAgentCLI 当前内置哪些工具，例如：

- `list_files`
- `read_file`
- `search_files`
- `search_text`
- `search_index`
- `search_dependencies`
- `inspect_page`
- `browser_dom_snapshot`
- `browser_query_selector`
- `write_file`
- `edit_file`
- `run_shell`

这一步解决：

> 工具能力是怎么注册、暴露、执行和保护的？

### 第四步：读 `tests/test_agent_loop.py`

这个测试很适合面试前反复看。

它证明：

- local fallback agent 能调用 `list_files`。
- Agent 最终输出包含 `README.md`。
- trace 里能看到 user event。
- trace 里能看到 assistant tool call。
- trace 里能看到 tool observation。
- trace 最后有 assistant final。

这一步解决：

> 你怎么证明 Agent 真的发生了工具调用，而不是只输出了一段文本？

## 最小运行例子

先跑：

```bash
pyagent "summarize this workspace"
```

没有 API key 时，local fallback 会触发一个简单工具调用路径，用来验证 CLI、ToolRegistry 和 observation 回灌。

再跑 eval：

```bash
pyagent --eval
```

你要关注 trace 相关输出：

- trace eval
- real model trace eval
- per-model trace comparison

默认不需要真实模型也能跑本地 trace eval。真实模型 trace 需要显式 opt-in：

```bash
pyagent --eval --eval-real-model
```

多模型对比需要显式 opt-in：

```bash
pyagent --eval --eval-compare-models
```

面试时可以这样说：

> 我不仅实现了 Agent Loop，还把 tool call、observation、final output 捕获成 trace，用 eval 去检查工具调用序列、forbidden tools 和最终输出。

## Tool Call 失败后怎么办

真实 Agent 一定会遇到工具失败。

例如：

- 工具名不存在。
- `edit_file` 找不到 old text。
- `run_shell` 被 SafetyPolicy 拒绝。
- `browser_console_logs` 缺少 Playwright。
- 文件路径越过 workspace guardrail。

PyAgentCLI 的原则是：

> 工具失败不应该直接让 Agent 崩溃，而应该变成 observation 返回模型。

在 `ToolRegistry.execute()` 里：

- 未知工具会返回 `ToolResult.failure`。
- preview 失败会返回 failure。
- approval 拒绝会返回 failure。
- safety deny 会返回 failure。
- 工具运行抛异常也会转成 failure。
- audit log 仍然记录这次调用。

这让模型有机会看到真实错误，再决定下一步。

面试可以这样讲：

> Tool call 失败后，我不会让 Agent runtime 崩溃，而是把失败包装成 observation。这样 ReAct loop 能基于真实错误继续推理，同时审计日志保留失败原因。

## max steps 为什么必要

Agent Loop 不能相信模型一定会自己停。

如果模型持续调用工具，就可能出现：

- 无限读文件。
- 不断重试失败工具。
- 重复搜索。
- token 和时间浪费。
- 用户无法判断任务是否结束。

PyAgentCLI 在 `AgentState` 里保存 `max_steps`，在 `AgentLoop` 中使用：

```text
while state.step_count < state.max_steps:
    ...
```

达到上限后返回：

```text
任务达到最大步数 X，已停止。
```

面试回答：

> Agent Loop 必须有硬终止条件。`max_steps` 是最基础的安全阀，后续还可以叠加 token budget、工具预算、时间预算和用户中断。

## Trace 为什么重要

如果只看最终回答，你无法判断 Agent 是否真的做了正确动作。

例如最终回答说：

```text
我已经检查了 README。
```

但它到底有没有调用 `read_file`？

Trace 能回答这个问题。

PyAgentCLI 的 trace 包含：

- user goal
- assistant tool call
- tool observation
- final answer

Eval 可以基于 trace 检查：

- 是否使用了 expected tools。
- 是否调用了 forbidden tools。
- final output 是否包含关键信息。
- safety violations 是否为 0。

这就是为什么 PyAgentCLI 从 deterministic eval 继续扩展到了 captured trace eval、real model trace eval 和 per-model trace comparison。

## 我们开发时遇到的坑

### 坑 1：不能只相信最终输出

早期 eval 更像静态检查和模拟 case。

后来我们补了 trace eval，因为 Agent 行为的关键不是“最后说了什么”，而是：

- 中间有没有调用正确工具。
- 有没有调用不该调用的工具。
- 工具 observation 是否进入后续推理。
- 最终回答是否基于真实观察。

学习点：

> Agent eval 要评估行为轨迹，不只是评估最终文本。

### 坑 2：真实模型 eval 必须 opt-in

真实模型 trace eval 会消耗 API key、网络和费用。

所以 PyAgentCLI 把它做成显式 opt-in：

```bash
pyagent --eval --eval-real-model
```

如果没有 `OPENAI_API_KEY`，CLI 会显示 disabled reason，而不是报错。

学习点：

> 高成本或外部依赖能力应该默认关闭，并提供清晰的 capability check / disabled reason。

### 坑 3：模型名称和能力需要校验

我们之前遇到过不可用模型错误，例如 `gpt-image-2` 不存在。

这件事可以反补到 ReAct / Tool Calling 学习里：

- Agent 不能假设模型一定可用。
- 不同模型的 tool calling 能力可能不同。
- 真实模型 eval 要明确配置模型、base URL、API key。
- 多模型对比要记录模型名称和结果。

学习点：

> LLM Client 不只是发请求，还要处理模型能力、失败原因、fallback 和评估边界。

## 简历上怎么写

一条简洁版：

> 实现 ReAct / Function Calling Agent Loop，维护 system/user/assistant/tool 消息历史，支持 OpenAI-compatible tool calls、本地工具执行、observation 回灌、max steps 防无限循环和 trace capture。

偏 Agent 工程版：

> 设计本地 Agent Runtime，将 LLM 输出的结构化 tool call 转化为受控工具执行，通过 ToolRegistry、SafetyPolicy、ApprovalHandler 和 AuditLogger 完成工具分发、安全检查、人工审批、结果回灌和行为追踪。

偏后端平台版：

> 抽象 `LLMClient`、`ToolRegistry` 和 `AgentLoop`，实现模型调用、工具 schema 暴露、工具执行、失败包装、消息序列化和 trace eval，构建可测试、可审计的 Agent 执行闭环。

## 面试官会怎么追问

### Q1：ReAct 和 Function Calling 是什么关系？

一句话答案：

> ReAct 是推理-行动-观察的行为模式，Function Calling 是模型输出结构化工具调用意图的协议。PyAgentCLI 用 Function Calling 实现 ReAct loop 中的 Action。

展开回答：

- ReAct 关心 Agent 怎么循环。
- Function Calling 关心模型怎么表达工具调用。
- ToolRegistry 关心本地怎么执行工具。
- SafetyPolicy 关心是否允许执行。
- Observation 再回到模型，形成下一轮推理。

### Q2：模型到底会不会执行代码？

一句话答案：

> 不会。模型只输出工具名和参数，真正执行的是 PyAgentCLI 的本地工具层。

展开回答：

- 模型看到工具 schema。
- 模型返回 tool call。
- AgentLoop 解析 tool call。
- ToolRegistry 执行本地工具。
- 工具结果作为 tool message 回到模型。

### Q3：Tool Call 失败后怎么办？

一句话答案：

> 失败会被包装成 observation，而不是让 Agent 崩溃。

展开回答：

- 未知工具、审批拒绝、安全拒绝、工具异常都会变成 `ToolResult.failure`。
- failure 仍然进入 audit log。
- 模型看到 observation 后可以修正。
- Reviewer / Eval 后续可以检查失败是否被正确处理。

### Q4：怎么防止无限循环？

一句话答案：

> 用 `max_steps` 做硬终止条件。

展开回答：

- 每轮 LLM 调用后 step count 增加。
- 无 tool call 时正常结束。
- 到达 max steps 后停止。
- 后续还可以加 token budget、工具预算、时间预算。

### Q5：怎么证明 Agent 真的调用了工具？

一句话答案：

> 用 trace capture。

展开回答：

- trace 记录 user goal。
- trace 记录 assistant tool call。
- trace 记录 tool observation。
- trace 记录 final answer。
- eval 可以检查 expected tools、forbidden tools、final contains。

## 标准回答思路

如果面试官让你整体讲 ReAct / Tool Calling，可以按这个顺序：

1. 先区分 ReAct 和 Function Calling。
2. 再强调模型不执行代码。
3. 然后讲 PyAgentCLI 的 `AgentLoop`。
4. 再讲 `ToolRegistry.execute()` 的 safety / approval / audit。
5. 最后讲 trace 和 eval，证明行为可验证。

一版完整回答：

> ReAct 是 Agent 的行为模式，也就是模型在推理过程中选择动作，拿到 observation 后继续推理。Function Calling 是实现这个动作的一种结构化协议，模型不会真的执行函数，只会输出工具名和参数。PyAgentCLI 的 `AgentLoop` 会把工具 schema 发给模型，拿到 tool call 后交给 `ToolRegistry.execute()`，再经过 SafetyPolicy、ApprovalHandler 和 AuditLogger，最后把 ToolResult 包装成 tool message 回到模型。为了避免无限循环，我设置了 max steps；为了评估 Agent 是否真的调用了正确工具，我还捕获 trace，用 eval 检查工具序列、forbidden tools 和最终输出。

## 还能继续怎么增强

当前 PyAgentCLI 的 ReAct / Tool Calling 已经形成基础闭环，但还可以增强：

- 增加 token budget。
- 增加 per-tool call budget。
- 增加 tool retry policy。
- 增加更细的 tool result summarization。
- 增加 streaming tool call 展示。
- 增加真实模型 tool-calling capability check。
- 增加多模型同任务 trace 对比报告。
- 增加对并行 tool calls 的顺序保持和冲突处理。

这些增强可以作为后续阶段，不要在简历里写成已经完成的事实。

## 这一篇之后做什么

下一篇进入：

> [Plan-and-Execute / DAG](03_plan_execute_dag.md)

ReAct 适合短任务和探索任务；复杂任务需要先拆计划、审批、执行、恢复和复核。这就是下一篇要解决的问题。
