# 11 多模型适配和 LLM Client

这一篇讲 PyAgentCLI 里的多模型适配。

前面我们已经讲完了：

- ReAct / Tool Calling
- Plan-and-Execute
- Memory
- RAG
- Tool Safety
- Multi-Agent
- Browser Tools
- MCP
- Prompt / Skill

这些模块最后都会碰到同一个问题：

> Agent 到底调用哪个模型？如果模型不支持 Tool Calling 怎么办？如果模型名不可用怎么办？如果 Planner、Executor、Reviewer 想用不同模型怎么办？

这就是 LLM Client 层要解决的问题。

## 这一篇学什么

你要掌握 8 件事：

1. 为什么 Agent CLI 不能把模型调用写死在 loop 里。
2. PyAgentCLI 的 `LLMClient`、`Message`、`ToolCall`、`LLMResponse` 是怎么抽象的。
3. OpenAI-compatible client 如何把内部消息转成 Chat Completions 请求。
4. 没有 API key 时为什么需要 `LocalFallbackClient`。
5. `PYAGENT_MODEL`、`OPENAI_BASE_URL`、`OPENAI_API_KEY` 怎样进入配置。
6. Planner / Executor / Reviewer 如何使用 role-specific model。
7. `--check-model` 和 `--eval-compare-models` 为什么重要。
8. 面试里怎么讲多模型、fallback、成本控制和能力验证。

这一篇的重点不是“支持越多模型越厉害”，而是：

> 让模型选择、模型能力、工具调用和评估结果变成可配置、可验证、可替换的工程边界。

## 为什么 Agent CLI 需要 LLM Client 层

一个普通聊天应用可以直接写：

```python
client.chat.completions.create(...)
```

但 Coding Agent CLI 不适合这样写。

因为 Agent 不只是问模型一句话：

- 它要把 system prompt、用户任务、工具结果、memory、RAG context 都组合成消息。
- 它要把本地工具 schema 传给模型。
- 它要解析模型返回的 tool call。
- 它要把 tool result 再喂回模型。
- 它要处理模型不支持 tool calling 的情况。
- 它要在 eval 中比较不同模型。
- 它要允许 Planner / Executor / Reviewer 使用不同模型。
- 它要避免没有 API key 时整个 CLI 不能演示。

所以 PyAgentCLI 把模型访问做成一个边界：

```text
Agent Loop
  |
  v
LLMClient Protocol
  |
  +-- OpenAICompatibleClient
  |
  +-- LocalFallbackClient
```

Agent Loop 只依赖 `LLMClient`，不关心底层到底是 OpenAI、OpenAI-compatible provider，还是本地 fallback。

这就是多模型适配的第一层价值：

> 业务 runtime 不直接绑定某一个模型厂商。

## PyAgentCLI 当前实现了什么

当前 PyAgentCLI 已经实现了这些能力：

- `LLMClient` 协议。
- `Message` 数据结构。
- `ToolCall` 数据结构。
- `LLMResponse` 数据结构。
- OpenAI-compatible Chat Completions client。
- `.env` 和环境变量配置模型。
- 没有 API key 时启用 local fallback。
- role-specific model override。
- `--check-model` 检查真实模型是否返回 tool call。
- `--eval-real-model` 显式开启真实模型 trace eval。
- `--eval-compare-models` 显式开启多模型对比 eval。
- `pyagent.toml` 配置 eval comparison models。

当前没有实现的是：

- streaming response。
- 自动多模型 router。
- 模型能力 registry。
- 自动成本统计。
- prompt cache。
- remote provider failover。
- 针对不同 provider 的完整兼容矩阵。
- 图像、多模态模型适配。

这些没有实现的部分，不能在简历里写成“已完成”，但可以写成“预留扩展方向”。

## 对应源码

核心源码：

```text
src/pyagentcli/llm/base.py
src/pyagentcli/llm/openai_compatible.py
src/pyagentcli/llm/model_config.py
src/pyagentcli/config.py
src/pyagentcli/cli/main.py
```

测试：

```text
tests/test_llm_model_config.py
tests/test_config.py
tests/test_cli.py
```

相关文档：

```text
docs/dev_setup.md
docs/testing.md
docs/e2e_real_model_demo.md
docs/evals.md
docs/multi_agent.md
docs/troubleshooting.md
```

## 核心数据结构

先看 `src/pyagentcli/llm/base.py`。

这里定义了 4 个关键对象：

```text
ToolCall
Message
LLMResponse
LLMClient
```

它们分别负责：

```text
ToolCall     模型想调用哪个工具，以及参数是什么
Message      system/user/assistant/tool 消息
LLMResponse  模型一次回复的结果
LLMClient    所有模型客户端必须实现的接口
```

### ToolCall

`ToolCall` 表示模型返回的工具调用意图：

```text
id
name
arguments
```

注意这里是“意图”，不是执行。

模型返回：

```json
{
  "name": "list_files",
  "arguments": {
    "path": "."
  }
}
```

并不代表文件已经被读取。

真正的执行路径是：

```text
模型返回 ToolCall
  |
  v
Agent Loop 解析
  |
  v
Tool Registry 找工具
  |
  v
Safety Policy 判断风险
  |
  v
Approval Handler 必要时询问用户
  |
  v
Tool 执行
  |
  v
Audit Log 记录
```

这个边界非常关键。

面试官经常问：

> Function Calling 是不是模型在执行函数？

答案应该是：

> 不是。模型只生成结构化调用请求，真正执行由 runtime 控制。

### Message

`Message` 是 Agent 和模型之间传递上下文的统一格式。

它包含：

```text
role
content
tool_calls
tool_call_id
```

常见 role：

```text
system
user
assistant
tool
```

PyAgentCLI 里有便捷构造方法：

```text
Message.system(...)
Message.user(...)
Message.assistant(...)
Message.tool(...)
```

这样 Agent Loop 不需要每次手写 dict。

### LLMResponse

`LLMResponse` 是模型一次返回的统一结果。

它有两个核心字段：

```text
content
tool_calls
```

如果 `tool_calls` 不为空，Agent Loop 进入工具执行。

如果 `tool_calls` 为空，通常表示模型给出了最终回答。

简化理解：

```text
有 tool_calls -> 继续执行工具
无 tool_calls -> 结束或返回最终答案
```

### LLMClient

`LLMClient` 是协议：

```text
chat(messages, tools) -> LLMResponse
```

这意味着 Agent Loop 不关心底层 client 细节。

它只知道：

> 给你 messages 和 tools schema，你给我一个 LLMResponse。

这就是解耦。

## OpenAI-compatible Client

PyAgentCLI 当前的真实模型客户端是：

```text
OpenAICompatibleClient
```

它在：

```text
src/pyagentcli/llm/openai_compatible.py
```

它做了几件事：

1. 接收 `api_key`、`base_url`、`model`。
2. 拼接请求地址：`{base_url}/chat/completions`。
3. 把内部 `Message` 转成 OpenAI-compatible payload。
4. 如果有工具 schema，传入 `tools`。
5. 设置 `tool_choice = "auto"`。
6. 发送 HTTP POST。
7. 解析 response message。
8. 把 tool calls 转回 PyAgentCLI 的 `ToolCall`。

请求体大致是：

```json
{
  "model": "gpt-4.1-mini",
  "messages": [],
  "tools": [],
  "tool_choice": "auto"
}
```

这里有一个很重要的设计点：

> PyAgentCLI 选择的是 OpenAI-compatible 协议，而不是只绑定 OpenAI 官方 SDK。

这样很多兼容 Chat Completions 格式的 provider 都有机会接入。

但边界也要讲清楚：

> “OpenAI-compatible” 不等于所有 provider 都完全一致。

不同 provider 可能在这些地方不一致：

- tool call 字段格式。
- function arguments 是否总是合法 JSON。
- 错误码格式。
- timeout 行为。
- base_url 路径。
- 是否支持 `tool_choice`。
- 是否支持同一个模型名。

所以 PyAgentCLI 当前是基础适配，不是完整 provider compatibility layer。

## Tool Call 参数解析

OpenAI-compatible response 里，function arguments 常常是字符串：

```json
"arguments": "{\"path\":\".\"}"
```

PyAgentCLI 会尝试把它解析成 JSON。

如果解析失败，会放进：

```json
{
  "_raw": "..."
}
```

这说明一个现实问题：

> Tool Calling 是结构化输出，但不代表永远不会脏。

模型可能返回：

- 非 JSON。
- 缺字段。
- 参数类型不对。
- 工具名不存在。
- 参数路径越界。

所以 tool call 之后仍然需要：

- registry 校验。
- pydantic / schema 校验。
- safety policy。
- observation 错误反馈。
- max step 防无限循环。

这也是为什么 LLM Client 不能替代 Agent Runtime。

## LocalFallbackClient

PyAgentCLI 有一个本地 fallback：

```text
LocalFallbackClient
```

它的作用不是“假装自己是高级模型”，而是：

> 在没有 API key 的情况下，让 CLI、工具链、文档演示和基础测试仍然能跑。

它有两个典型行为：

1. 如果用户任务看起来像在问项目、文件、目录，它会返回一个 `list_files` tool call。
2. 如果已经收到 tool result，它会总结收到的工具结果。

这使得你即使没有配置 `OPENAI_API_KEY`，也可以演示：

```text
用户输入
  |
  v
Agent Loop
  |
  v
Tool Call
  |
  v
Tool 执行
  |
  v
Observation
  |
  v
最终回答
```

但是必须强调：

> LocalFallbackClient 只能证明 runtime 链路能跑，不能证明真实模型质量。

所以 eval 里真实模型相关能力不会默认 fallback。

这是一条很好的工程边界。

## 配置入口

配置在：

```text
src/pyagentcli/config.py
```

核心环境变量：

```bash
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
export PYAGENT_MODEL="gpt-4.1-mini"
export PYAGENT_MAX_STEPS="10"
```

默认值：

```text
PYAGENT_MODEL      gpt-4.1-mini
OPENAI_BASE_URL   https://api.openai.com/v1
PYAGENT_MAX_STEPS 10
```

`load_config()` 会读取：

1. 当前目录 `.env`
2. workspace 目录 `.env`
3. 环境变量
4. `pyagent.toml`

配置最终进入：

```text
AppConfig
```

其中和模型相关的字段包括：

```text
model
api_key
base_url
agent_roles
eval_models
embedding
```

注意：

> Chat model 和 embedding model 是两个配置域。

RAG embeddings 走：

```text
EmbeddingConfig
```

Agent chat 走：

```text
model / api_key / base_url
```

不要把两者混在一起。

## build_llm_client

模型 client 的构建入口是：

```text
src/pyagentcli/llm/model_config.py
```

核心逻辑：

```text
如果指定 role，并且 role 配置了 model：
    使用 role model
否则：
    使用默认 config.model

如果有 API key：
    返回 OpenAICompatibleClient
否则：
    返回 LocalFallbackClient
```

这段逻辑看起来很短，但非常关键。

它把三件事集中在一起：

- 默认模型。
- 角色模型覆盖。
- 无 key fallback。

这样 Planner、Executor、Reviewer 不需要各自写一套模型初始化逻辑。

## Role-specific Model

前面 Multi-Agent 篇说过，PyAgentCLI 有 Planner、Executor、Reviewer。

它们可以使用不同模型。

配置例子：

```toml
[agents.planner]
model = "gpt-4.1"
system_prompt = "You are a careful planning agent..."

[agents.executor]
model = "gpt-4.1-mini"
system_prompt = "You execute one approved step at a time..."

[agents.reviewer]
model = "gpt-4.1-mini"
system_prompt = "You review completed plans and risks..."
```

如果某个角色没有配置 model：

```text
使用默认 PYAGENT_MODEL
```

为什么需要这样设计？

因为不同角色对模型能力的要求不同。

Planner 可能更需要：

- 长上下文理解。
- 任务拆解。
- 风险识别。
- 依赖关系推理。

Executor 可能更需要：

- 稳定 tool calling。
- 严格遵守步骤。
- 低成本。
- 快速响应。

Reviewer 可能更需要：

- 审查风险。
- 找遗漏。
- 生成测试建议。

多模型不是为了炫技，而是为了：

> 把不同任务类型映射到合适的模型能力和成本档位。

## --check-model

模型配置以后，最容易犯的错是：

> 以为模型名能用，就等于它支持当前 Agent 需要的 tool calling。

PyAgentCLI 提供：

```bash
PYTHONPATH=src python -m pyagentcli --check-model
```

它会做一个很小的真实模型探针：

1. 加载 workspace config。
2. 注册默认工具和 MCP 工具。
3. 构建真实 LLM client。
4. 给模型一个 system prompt：请调用 `list_files`。
5. 传入 tools schema。
6. 检查模型是否真的返回 tool call。

如果没有 API key，它会输出：

```text
No OPENAI_API_KEY configured. Local fallback is active; real tool calling was not checked.
```

如果模型返回 tool call，会打印：

```text
tool_call: list_files args={...}
```

如果模型没有返回 tool call，会打印模型的普通回答。

这个命令的意义是：

> 在真正跑 Agent 之前，先验证模型和工具调用链路是否兼容。

这也呼应我们之前遇到的真实问题：

> 某次工具路径尝试调用了不可用的 `gpt-image-2`，结果报错 “The model 'gpt-image-2' does not exist.”

这个问题不是 PyAgentCLI 代码里的 bug，而是非常典型的多模型工程问题：

- 模型名可能不存在。
- 模型权限可能没有开。
- 模型版本可能变化。
- 当前工具路由可能选错模型。
- 不同能力类型不能混用模型。

所以工程上不能只靠“我记得这个模型能用”。

要做：

- 显式配置。
- 启动前检查。
- 失败时给清晰错误。
- eval 中记录模型名。
- 不把不可用模型当成默认路径。

## Real Model Eval 为什么要显式开启

PyAgentCLI 的普通 eval 默认不调用外部模型。

真实模型 trace eval 需要显式开启：

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --eval \
  --eval-real-model
```

如果没有 `OPENAI_API_KEY`，CLI 会显示 disabled reason，而不是 fallback 到 local client。

这是一个很重要的设计。

为什么？

因为 eval 和 demo 不一样。

如果 eval 默认调用真实模型，会有几个问题：

- 产生费用。
- 结果不稳定。
- CI 可能失败。
- 没有 API key 的用户无法跑测试。
- 模型更新会影响评估结果。

所以 PyAgentCLI 把 eval 分成：

```text
deterministic eval        默认开启
real model trace eval     显式开启
model comparison eval     显式开启
```

这体现了一个成熟项目的边界：

> 默认路径可复现，真实模型路径可选且可解释。

## Model Comparison Eval

多模型适配不只是“能换模型”，还要能比较模型效果。

PyAgentCLI 支持：

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --eval \
  --eval-compare-models
```

模型配置在 `pyagent.toml`：

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

这带来几个好处：

- 可以比较 fast model 和 reasoning model。
- 可以给不同 provider 配不同 `base_url`。
- 可以用不同环境变量管理 API key。
- 没配置 key 时不会硬报错。
- eval report 能记录每个模型的工具调用效果。

比较指标包括：

- final output pass/fail。
- tool-call accuracy。
- safety violation count。
- duration。
- used tools。

这比“我感觉某个模型更强”更工程化。

## 多模型适配和 Multi-Agent 的关系

Multi-Agent 负责角色分工：

```text
Planner
Executor
Reviewer
```

多模型适配负责模型选择：

```text
planner -> stronger model
executor -> cheaper tool-calling model
reviewer -> review-oriented model
```

两者结合后，架构是：

```text
User Goal
  |
  v
Planner(role=planner, model=planner-model)
  |
  v
Executor(role=executor, model=executor-model)
  |
  v
Reviewer(role=reviewer, model=reviewer-model)
```

但不要误解：

> 多 Agent 不一定必须多模型，多模型也不一定必须多 Agent。

你可以：

- 一个 Agent 用多个模型。
- 多个 Agent 用同一个模型。
- Planner 和 Reviewer 用强模型，Executor 用便宜模型。
- 全部先用默认模型，后续再优化成本。

PyAgentCLI 当前实现的是可配置基础，而不是自动调度器。

## 多模型适配和安全的关系

模型换了，安全边界不能变。

无论是：

- 默认模型。
- Planner 模型。
- Executor 模型。
- Reviewer 模型。
- MCP provider 背后的模型。
- eval comparison 里的模型。

都必须经过同一套 runtime：

```text
Tool Registry
Safety Policy
Approval Handler
Audit Log
Path Guardrail
Command Denylist
Max Steps
```

不能因为模型更强，就允许它绕过审批。

也不能因为模型是本地模型，就默认它安全。

面试时可以这样讲：

> PyAgentCLI 的安全策略不挂在具体模型上，而挂在工具执行 runtime 上。模型只产生 tool call，是否执行由 registry、policy、approval 和 audit 决定，所以换模型不会改变本地执行权限。

## 多模型适配和 Prompt 的关系

Prompt/Skill 篇讲的是：

> 给模型什么上下文和指导。

多模型篇讲的是：

> 选择哪个模型，以及如何验证它能完成这类任务。

两者要配合，但不能混淆。

错误做法：

```text
模型不支持 tool calling，于是疯狂改 prompt。
```

正确做法：

```text
先用 --check-model 验证 tool calling。
如果模型确实不支持，换模型或换 provider。
prompt 只解决行为指导，不解决能力缺失。
```

另一个错误做法：

```text
Planner 做不好拆解，就只换更强模型。
```

更好的做法：

```text
先检查 planner prompt、上下文注入、RAG 命中和任务边界。
如果上下文和 prompt 都合理，再比较模型。
```

模型能力重要，但不是唯一变量。

## 最小运行例子

### 1. 无 API key 跑本地 fallback

```bash
unset OPENAI_API_KEY
PYTHONPATH=src python -m pyagentcli "summarize this project"
```

你应该能看到 Agent 至少走通本地 fallback 和工具链路。

注意：

> 这只能证明 runtime 可用，不证明真实模型能力。

### 2. 配置真实模型

```bash
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
export PYAGENT_MODEL="gpt-4.1-mini"
```

然后跑：

```bash
PYTHONPATH=src python -m pyagentcli --check-model
```

### 3. 跑真实模型 eval

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --eval \
  --eval-real-model
```

### 4. 跑多模型比较

先在 workspace `pyagent.toml` 配置：

```toml
[evals.model_comparison.models.fast]
model = "gpt-4.1-mini"
base_url = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"
```

再执行：

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --eval \
  --eval-compare-models
```

## 源码阅读路线

建议按这个顺序读源码。

### 第一步：读 base.py

先看：

```text
src/pyagentcli/llm/base.py
```

重点看：

- `ToolCall`
- `Message`
- `LLMResponse`
- `LLMClient`
- `message_to_openai`

你要回答：

```text
内部消息如何变成 OpenAI-compatible message？
tool_calls 如何序列化？
tool message 如何带 tool_call_id？
```

### 第二步：读 openai_compatible.py

再看：

```text
src/pyagentcli/llm/openai_compatible.py
```

重点看：

- request body。
- timeout。
- error handling。
- `_parse_tool_calls`。
- `LocalFallbackClient`。

你要回答：

```text
如果 HTTP 失败怎么办？
如果 arguments 不是合法 JSON 怎么办？
如果没有 API key 怎么办？
```

### 第三步：读 config.py

再看：

```text
src/pyagentcli/config.py
```

重点看：

- `AppConfig`
- `AgentRoleConfig`
- `EvalModelConfig`
- `EmbeddingConfig`
- `load_config`
- `load_project_agent_role_configs`
- `load_project_eval_model_configs`

你要回答：

```text
默认模型从哪里来？
角色模型从哪里来？
eval comparison models 从哪里来？
embedding model 和 chat model 为什么分开？
```

### 第四步：读 model_config.py

再看：

```text
src/pyagentcli/llm/model_config.py
```

重点看：

```text
build_llm_client(config, role=None)
```

你要回答：

```text
什么时候用 role model？
什么时候 fallback 到 default model？
什么时候返回 LocalFallbackClient？
```

### 第五步：读 cli/main.py

最后看：

```text
src/pyagentcli/cli/main.py
```

重点看：

- `--check-model`
- `--eval-real-model`
- `--eval-compare-models`
- `plan_task`
- `execute_planned_task`
- Reviewer model 构建逻辑

你要回答：

```text
真实模型 eval 为什么是 opt-in？
多模型 comparison 如何跳过缺失 API key 的配置？
Planner/Reviewer 何时使用 role-specific model？
```

## 我们开发时遇到的坑

### 坑 1：不可用模型名导致工具链报错

我们实际遇到过一次：

```text
The model 'gpt-image-2' does not exist.
```

这个问题暴露的是：

> 工具能力、模型能力、模型名称和账号权限必须匹配。

不能假设某个模型名永远可用。

改进方式：

- 避免把不确定模型写死进默认路径。
- 对真实模型调用做显式检查。
- 保持错误信息可读。
- 把 model name 记录进 eval / trace。
- 对不同能力类型使用不同 client。

### 坑 2：把 fallback 当成真实模型效果

Local fallback 很有用，但它不是模型质量评估。

如果你看到 fallback 能调用 `list_files`，只能说明：

```text
Agent Loop -> Tool Registry -> Tool Execution
```

这条链路能跑。

不能说明：

```text
真实模型会正确规划任务
真实模型会正确调用工具
真实模型会遵守安全边界
```

所以真实模型 eval 必须单独开启。

### 坑 3：eval 默认调用真实模型会让项目不可复现

如果 `pyagent --eval` 默认就调用外部模型，会导致：

- CI 无 API key 时失败。
- 每次运行结果可能不同。
- 成本不可控。
- 文档演示门槛变高。

所以我们把真实模型 eval 设计为：

```text
--eval-real-model
--eval-compare-models
```

显式开启。

### 坑 4：角色模型配置和角色 prompt 容易混在一起

角色 prompt 解决：

```text
这个角色应该怎么思考和输出
```

角色 model 解决：

```text
这个角色用哪个模型
```

两者都在 `pyagent.toml` 里出现时，很容易误以为换 prompt 就等于换能力。

实际不是。

如果模型不支持 tool calling，再好的 Executor prompt 也没用。

### 坑 5：OpenAI-compatible 不等于完全兼容

不同 provider 都说自己兼容 OpenAI API，但细节可能不同。

开发时要特别注意：

- tool calls 格式。
- arguments JSON。
- error response。
- timeout。
- base_url。
- model name。
- tool_choice。

所以适配层要尽量集中，不要散落在 Agent Loop 各处。

### 坑 6：把 embedding 模型和 chat 模型混了

RAG 需要 embedding provider。

Agent Loop 需要 chat model。

它们都可能用 API key，但用途完全不同。

如果混在一起，会导致：

- 配置语义不清。
- RAG index 失败不好排查。
- chat model 切换影响 embedding。
- 简历和面试里讲不清架构。

PyAgentCLI 用 `EmbeddingConfig` 单独管理 RAG embedding。

## 如果你自己开发会遇到的坑

### 坑 1：直接在 Agent Loop 里写 provider SDK

新手常见写法：

```python
response = openai.chat.completions.create(...)
```

然后在 loop 里直接解析。

短期能跑，长期会很痛：

- 换 provider 要改 loop。
- eval 要 mock 很难。
- fallback 很难做。
- 多 Agent 角色模型很难插。
- 测试要依赖真实 API。

更好的做法是先定义：

```text
LLMClient Protocol
```

再写具体实现。

### 坑 2：只存 content，不存 tool_calls

普通聊天只需要 content。

Agent 必须保留 tool_calls。

否则你无法知道：

- 模型想调用哪个工具。
- 工具参数是什么。
- 工具结果应该对应哪个 call id。
- trace eval 如何判断工具调用是否正确。

### 坑 3：没有 check-model 命令

如果没有 `--check-model`，你会在真正跑任务时才发现：

- API key 错了。
- base_url 错了。
- model name 错了。
- 模型不支持 tool calling。
- provider 返回格式不兼容。

这样调试成本很高。

一个小 probe 命令可以节省大量时间。

### 坑 4：没有区分 deterministic eval 和 real-model eval

如果 eval 依赖真实模型，项目会很难维护。

你需要把测试分成：

```text
代码逻辑测试
确定性 eval
真实模型 eval
多模型比较 eval
```

它们的用途不同。

### 坑 5：没有保存模型配置来源

如果模型配置来自多个地方：

- `.env`
- 环境变量
- `pyagent.toml`
- CLI 参数

你最好能讲清楚优先级。

否则出了问题很难定位。

### 坑 6：没有把成本作为架构问题

多模型适配不是越强越好。

你需要考虑：

- 哪些路径默认不调用外部模型。
- 哪些 eval 需要 opt-in。
- 哪些角色可以用 cheaper model。
- 哪些任务必须用 stronger model。
- 是否需要 token/cost 统计。

PyAgentCLI 现在还没有完整 cost tracking，但已经通过 opt-in eval 和 role model 配置打下基础。

## 简历上怎么写

可以写成一条偏工程的 bullet：

> 设计并实现 PyAgentCLI 的 OpenAI-compatible LLM Client 抽象，封装 Message、ToolCall、LLMResponse 与统一 chat 接口，支持环境变量和项目配置驱动的模型选择、无 API key 本地 fallback、Planner/Executor/Reviewer 角色模型覆盖、真实模型 tool-calling 自检及 opt-in 多模型 trace eval。

如果简历空间有限，可以写短一点：

> 实现 OpenAI-compatible 多模型适配层，支持 role-specific model、tool-calling 自检、本地 fallback 与模型对比 eval，保证 Agent Runtime 不绑定单一 provider。

如果投 AI Agent 后端岗位，可以强调：

> 将 LLM 调用从 Agent Loop 中解耦为统一 Client Protocol，并通过配置化模型选择、工具调用解析、真实模型探针和评估开关，提升 Coding Agent 的可替换性、可测试性和成本可控性。

如果投平台 / 基础设施岗位，可以强调：

> 构建模型接入与评估治理层，支持 OpenAI-compatible provider、角色级模型路由、API key 隔离配置和多模型效果对比，为 Agent CLI 后续接入更多 provider、成本统计和模型能力 registry 预留扩展点。

## 面试官会怎么追问

### Q1：为什么要抽象 LLMClient？

一句话答案：

> 为了让 Agent Runtime 不直接依赖某个 provider，并让 tool calling、fallback、eval 和多 Agent 角色模型都能走统一接口。

展开回答：

- Agent Loop 只需要 `chat(messages, tools) -> LLMResponse`。
- provider 细节放在 client 实现里。
- 测试可以 mock client。
- 没 API key 可以用 fallback。
- 多模型比较可以复用同一个协议。

落到 PyAgentCLI：

> PyAgentCLI 在 `llm/base.py` 定义了 `LLMClient` Protocol，在 `openai_compatible.py` 实现真实模型 client 和 local fallback，在 `model_config.py` 根据配置创建 client。

### Q2：模型返回 tool call 后，是模型执行工具吗？

一句话答案：

> 不是，模型只返回结构化调用请求，工具执行由 Agent Runtime 控制。

展开回答：

- 模型返回 `ToolCall(name, arguments)`。
- Runtime 查 Tool Registry。
- Safety Policy 判断风险。
- Approval Handler 必要时要求人工确认。
- 工具执行后产生 observation。
- observation 再作为 tool message 回给模型。

可以补一句：

> 这也是为什么换模型不会改变权限边界。

### Q3：如果没有 API key，项目怎么跑？

一句话答案：

> PyAgentCLI 会使用 LocalFallbackClient，让 CLI 和工具链路仍然可以演示，但真实模型能力不会被假装通过。

展开回答：

- fallback 可以生成简单 tool call。
- fallback 可以总结 tool result。
- 它用于演示 runtime。
- `--check-model` 会明确提示 real tool calling 未检查。
- real-model eval 不会自动 fallback。

### Q4：怎么验证一个模型支持 Tool Calling？

一句话答案：

> 用 `--check-model` 发送一个最小工具调用任务，检查模型是否返回 `list_files` tool call。

展开回答：

- 注册 tools schema。
- system prompt 要求调用 `list_files`。
- 如果返回 tool call，说明基础链路可用。
- 如果只返回普通文本，说明模型或 provider 可能不支持 tool calling。
- 如果报错，检查 API key、base_url、model name 和 provider 格式。

### Q5：Planner、Executor、Reviewer 为什么可以用不同模型？

一句话答案：

> 因为它们承担的任务不同，模型能力和成本要求也不同。

展开回答：

- Planner 更依赖推理和任务拆解。
- Executor 更依赖稳定 tool calling 和成本控制。
- Reviewer 更依赖风险识别和测试建议。
- PyAgentCLI 通过 `AgentRoleConfig` 支持 role-specific model。
- 未配置时 fallback 到默认 `PYAGENT_MODEL`。

### Q6：如果模型名不可用怎么办？

一句话答案：

> 不应该等到复杂任务里才发现，应该通过配置校验、`--check-model`、清晰错误和 eval trace 记录来定位。

展开回答：

- 模型可能不存在。
- 账号可能没权限。
- provider 可能不支持该模型。
- 模型版本可能变化。
- 能力类型可能不匹配。

结合我们真实经历：

> 之前出现过 `gpt-image-2 does not exist`，这类问题提醒我们模型名和能力不能写死，要用可验证配置和明确错误路径。

### Q7：为什么真实模型 eval 要 opt-in？

一句话答案：

> 因为真实模型 eval 有成本、不稳定、依赖 API key，不适合作为默认 deterministic eval。

展开回答：

- 默认 eval 应该可复现。
- CI 不应该强依赖外部模型。
- 模型输出有随机性。
- 真实模型适合单独 trace。
- 多模型比较适合显式开启。

PyAgentCLI 的设计是：

```text
pyagent --eval                       默认 deterministic
pyagent --eval --eval-real-model      真实模型 trace
pyagent --eval --eval-compare-models  多模型比较
```

### Q8：OpenAI-compatible 的风险是什么？

一句话答案：

> 兼容协议不代表行为完全一致，尤其是 tool calls、arguments JSON、错误格式和 `tool_choice` 支持。

展开回答：

- 需要集中适配。
- 不要把 provider 特例散落到 Agent Loop。
- 对失败响应要有可读错误。
- 用 check/eval 验证 provider。
- 未来可以做 provider capability registry。

### Q9：多模型适配和 model router 有什么区别？

一句话答案：

> 当前 PyAgentCLI 实现的是配置化多模型适配和 eval comparison，还不是自动 model router。

展开回答：

- 适配层解决“能接入和调用”。
- role-specific model 解决“不同角色指定模型”。
- comparison eval 解决“比较模型表现”。
- router 还需要能力声明、成本、延迟、失败率、任务类型识别。

所以不能夸大当前实现。

### Q10：Chat model 和 embedding model 为什么分开？

一句话答案：

> Chat model 用于 Agent 推理和 tool calling，embedding model 用于 RAG 检索，两者能力、接口和评估指标不同。

展开回答：

- chat model 返回 content/tool_calls。
- embedding model 返回向量。
- RAG index 不应该受 chat model 切换影响。
- 配置分开更容易排查问题。
- 简历里讲架构也更清楚。

## 标准回答思路

如果面试官让你整体讲“多模型适配”，可以按这个顺序：

1. 先说为什么不能把模型调用写死在 Agent Loop。
2. 讲 `LLMClient` 协议：`chat(messages, tools) -> LLMResponse`。
3. 讲内部结构：`Message`、`ToolCall`、`LLMResponse`。
4. 讲 OpenAI-compatible client：Chat Completions、tools、tool_choice、parse tool calls。
5. 讲 local fallback：无 API key 可跑 runtime，但不假装真实模型能力。
6. 讲配置：`.env`、`PYAGENT_MODEL`、`OPENAI_BASE_URL`、`pyagent.toml`。
7. 讲 role-specific model：Planner/Executor/Reviewer。
8. 讲 `--check-model`：验证 tool calling。
9. 讲 eval：real model 和 model comparison 都是 opt-in。
10. 讲边界：没有 streaming、router、成本统计、capability registry。

一版完整回答：

> PyAgentCLI 里我没有把模型调用直接写在 Agent Loop 里，而是抽象成 `LLMClient` 协议，统一输入 messages 和 tools schema，输出 `LLMResponse`。内部用 `Message` 表达 system/user/assistant/tool 消息，用 `ToolCall` 表达模型想调用的工具和参数。真实模型目前通过 OpenAI-compatible Chat Completions client 接入，会把 tools 传给模型并解析 tool calls；没有 API key 时使用 LocalFallbackClient 保证 CLI 和工具链路可以演示，但不把它当真实模型质量。配置上支持 `PYAGENT_MODEL`、`OPENAI_BASE_URL` 和 `OPENAI_API_KEY`，也支持在 `pyagent.toml` 里给 Planner、Executor、Reviewer 配 role-specific model。为了避免模型名不可用或模型不支持 tool calling，项目提供 `--check-model` 做最小工具调用探针；真实模型 trace eval 和多模型 comparison eval 都是显式开启，避免默认 eval 产生费用和不稳定性。目前它是配置化多模型适配，不是自动 router，后续可以继续补 capability registry、cost tracking、streaming 和 fallback 策略。

## 还能继续怎么增强

下一阶段可以增强：

- streaming response。
- model capability registry。
- provider-specific adapters。
- automatic fallback。
- cost tracking。
- token usage tracking。
- latency tracking。
- model router。
- prompt cache。
- retry with backoff。
- response format validation。
- per-role temperature / max_tokens。
- eval report by model/version。
- model availability preflight。
- model config diagnostics。
- local model adapter。

其中最值得优先做的是：

### 1. Capability Registry

记录每个模型能力：

```text
supports_tool_calling
supports_vision
supports_json_schema
max_context_tokens
supports_streaming
cost_per_input_token
cost_per_output_token
```

这样 `--check-model` 可以从一次探针升级为系统诊断。

### 2. Cost Tracking

每次 LLM 调用记录：

```text
model
input_tokens
output_tokens
estimated_cost
latency_ms
role
task_id
```

这样多模型比较不只是看成功率，也能看成本。

### 3. Provider Adapters

当前 OpenAI-compatible client 是通用入口。

后续可以扩展：

```text
OpenAIClient
AnthropicClient
LocalOllamaClient
AzureOpenAIClient
OpenRouterClient
```

但不应该让 Agent Loop 感知这些 provider 差异。

### 4. Model Router

真正的 router 需要根据任务选择模型：

```text
small edit       -> cheap tool-calling model
large planning   -> stronger reasoning model
review/audit     -> stronger reviewer model
browser inspect  -> fast model
```

但 router 要建立在 eval 数据和成本数据上，不能凭感觉。

## 这一篇之后做什么

下一篇进入：

> [产品化：CLI UX、Git、Runtime API](12_productization_cli_git_runtime.md)

多模型适配解决的是“Agent 用哪个模型以及怎么验证”；产品化要解决的是“这个 CLI 怎么变成一个真正好用、可发布、可维护的开发者工具”。
