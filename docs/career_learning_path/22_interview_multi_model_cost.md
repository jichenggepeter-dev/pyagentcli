# 22 面试题第七弹：多模型适配、运行时切换、成本控制

这一弹对应 PyAgentCLI 的 LLM Client 和多模型适配。

面试官问到这里，通常不是想听“我支持很多模型”，而是想判断：

```text
你的 Agent Runtime 是否和具体模型厂商解耦？
模型不支持 tool calling 怎么办？
没有 API key 怎么演示？
Planner、Executor、Reviewer 能不能用不同模型？
真实模型 eval 会不会默认烧钱？
模型名不存在时怎么定位？
```

这一弹要把“换模型”讲成工程边界，而不是 provider 名单。

## 这一弹考什么

这一弹主要考 8 个能力：

1. 你是否能解释为什么 Agent Loop 不应该直接绑定某个模型 SDK。
2. 你是否能讲清 `LLMClient`、`Message`、`ToolCall`、`LLMResponse` 的抽象。
3. 你是否知道 Function Calling 只是模型输出意图，执行权在 runtime。
4. 你是否能讲清 OpenAI-compatible client 的适配方式。
5. 你是否能解释 `LocalFallbackClient` 的价值和边界。
6. 你是否能讲清 role-specific model config。
7. 你是否能解释 `--check-model`、`--eval-real-model`、`--eval-compare-models`。
8. 你是否能诚实说明当前还没有完整 cost tracking、streaming、model router。

对应源码：

```text
src/pyagentcli/llm/base.py
src/pyagentcli/llm/openai_compatible.py
src/pyagentcli/llm/model_config.py
src/pyagentcli/config.py
src/pyagentcli/cli/main.py
src/pyagentcli/evals/runner.py
```

对应测试：

```text
tests/test_llm_model_config.py
tests/test_config.py
tests/test_cli.py
tests/test_agent_loop.py
```

对应实战文档：

- [11 多模型适配和 LLM Client](11_multi_model_llm_client.md)

## 哪些简历句子会触发这一弹

如果简历里写：

> 抽象 `LLMClient` 协议，统一 `Message`、`ToolCall`、`LLMResponse` 数据结构，将 Agent Loop 与具体模型 SDK 解耦；实现 OpenAI-compatible Chat Completions client、无 API key 的 `LocalFallbackClient`、`PYAGENT_MODEL` / `OPENAI_BASE_URL` / `OPENAI_API_KEY` 配置、planner/executor/reviewer role-specific model override，并通过 `--check-model`、`--eval-real-model`、`--eval-compare-models` 验证真实模型 tool calling 和多模型 trace 表现。

面试官会追问：

- 为什么需要 LLM Client 层？
- Tool Call 是模型执行了吗？
- OpenAI-compatible 具体怎么转消息？
- 没有 API key 为什么不直接报错？
- fallback 会不会误导用户？
- role-specific model 怎么配置？
- 为什么真实模型 eval 默认关闭？
- 成本控制做到哪里了？
- 模型名不可用怎么办？

## 面试开场 30 秒回答

如果面试官问“你们怎么做多模型适配”，可以先这样答：

> PyAgentCLI 里我没有把模型调用直接写在 Agent Loop 里，而是抽象成 `LLMClient` 协议。Agent Loop 只知道传入 `Message` 列表和工具 schema，拿回 `LLMResponse`，其中可能包含 `ToolCall`。真实模型目前通过 OpenAI-compatible Chat Completions client 接入，会把内部 message 转成 OpenAI 格式，把 tools 传给模型并解析 tool calls；没有 API key 时使用 `LocalFallbackClient`，保证 CLI、工具链路和本地 eval 可以演示，但不会假装它代表真实模型质量。配置上支持 `PYAGENT_MODEL`、`OPENAI_BASE_URL`、`OPENAI_API_KEY`，也支持在 `pyagent.toml` 给 planner/executor/reviewer 配不同 model。真实模型 trace eval 和多模型 comparison 都是显式 opt-in，避免默认产生费用和不稳定性。当前还不是自动 router，也没有完整 cost dashboard，后续会补 capability registry、token/cost tracking、streaming 和 fallback 策略。

## Q1：为什么 Agent CLI 需要 LLM Client 层？

一句话答案：

> 因为 Agent Runtime 不应该直接依赖某个模型 SDK，而应该依赖稳定的模型交互协议。

如果 Agent Loop 直接写：

```python
client.chat.completions.create(...)
```

会导致：

- 换 provider 要改 Agent Loop。
- 测试必须依赖真实网络。
- fallback 很难插入。
- 多模型 eval 很难复用。
- role-specific model 很难统一配置。
- tool call 解析逻辑散落在业务代码中。

PyAgentCLI 的做法是：

```text
AgentLoop
  |
  v
LLMClient Protocol
  |
  +-- OpenAICompatibleClient
  +-- LocalFallbackClient
```

Agent Loop 只关心：

```text
messages + tool schemas -> LLMResponse
```

不关心底层是谁。

## Q2：`LLMClient` 抽象了什么？

一句话答案：

> 它把不同模型统一成一个 `chat(messages, tools) -> LLMResponse` 接口。

核心协议：

```python
class LLMClient(Protocol):
    def chat(self, messages: list[Message], tools: list[dict[str, Any]]) -> LLMResponse:
        ...
```

这意味着：

- 输入是统一 message。
- 工具 schema 由 ToolRegistry 提供。
- 输出是统一 response。
- Agent Loop 不处理 provider 差异。

面试里要强调：

> LLMClient 不是为了炫技抽象，而是为了让 Agent Runtime、测试、fallback、eval 和多模型配置都复用同一条边界。

## Q3：`Message`、`ToolCall`、`LLMResponse` 分别是什么？

一句话答案：

> `Message` 表示上下文，`ToolCall` 表示模型想调用的工具，`LLMResponse` 表示模型一次回复。

`Message`：

```text
role
content
tool_calls
tool_call_id
```

role 包括：

```text
system
user
assistant
tool
```

`ToolCall`：

```text
id
name
arguments
```

它表示：

```text
模型想调用 list_files，并给出参数 {"path": "."}
```

`LLMResponse`：

```text
content
tool_calls
```

如果 `tool_calls` 不为空，Agent Loop 会进入工具执行链路。

## Q4：Function Calling 是模型执行函数吗？

一句话答案：

> 不是。模型只生成结构化调用意图，真正执行发生在本地 runtime。

正确链路：

```text
Model returns ToolCall
  |
  v
AgentLoop parses it
  |
  v
ToolRegistry finds the tool
  |
  v
SafetyPolicy checks risk
  |
  v
ApprovalHandler asks user if needed
  |
  v
Tool runs locally
  |
  v
AuditLogger records result
```

面试官如果问：

> 模型可以直接读写文件吗？

回答：

> 不可以。模型只能请求工具调用，真实文件读写、命令执行和网络动作都由 PyAgentCLI 的 ToolRegistry、安全策略、审批和审计控制。

## Q5：OpenAI-compatible client 怎么适配？

一句话答案：

> 它把 PyAgentCLI 内部 `Message` 转成 Chat Completions 请求，把返回的 `tool_calls` 解析回内部 `ToolCall`。

请求体大概是：

```json
{
  "model": "gpt-4.1-mini",
  "messages": [],
  "tools": [],
  "tool_choice": "auto"
}
```

关键点：

- `base_url` 末尾去掉 `/`。
- 请求地址是 `{base_url}/chat/completions`。
- Authorization 用 `Bearer <api_key>`。
- 有 tools 时传 `tools` 和 `tool_choice=auto`。
- HTTPError 转成清晰 RuntimeError。
- URLError 转成连接错误。
- tool arguments 从 JSON string parse 成 dict。
- malformed arguments 会保留在 `{"_raw": ...}`。

这说明项目不是只支持一个官方 SDK，而是支持 OpenAI-compatible provider。

## Q6：为什么没有 API key 时需要 `LocalFallbackClient`？

一句话答案：

> 因为本地 CLI 项目需要能先安装、跑通和演示 runtime 链路，而不是一开始就卡在 API key。

没有 fallback 的体验：

```text
安装项目
运行 pyagent
立刻报 OPENAI_API_KEY missing
用户看不到 CLI、ToolRegistry、Safety、Eval
```

有 fallback 的体验：

```text
没有 API key
  -> LocalFallbackClient
  -> 可以触发 list_files 这类简单工具调用
  -> 可以演示本地 runtime
  -> 明确提示真实模型未配置
```

但边界很重要：

> `LocalFallbackClient` 只能证明 CLI 和工具链路能跑，不能证明真实模型能力、推理质量或真实 provider 的 tool-calling 兼容性。

所以 PyAgentCLI 还有 `--check-model`。

## Q7：fallback 会不会误导用户？

一句话答案：

> 会，所以必须在输出和文档里明确它不是真实模型质量。

风险是：

- 用户以为项目已经调用真实模型。
- eval 看起来通过，但其实只测了 deterministic path。
- tool calling 兼容性没有被验证。
- 模型名、base_url、API key 问题被掩盖。

PyAgentCLI 的处理：

- `--check-model` 遇到 fallback 会提示 real tool calling 未检查。
- `--eval-real-model` 默认关闭。
- `--eval-compare-models` 默认关闭。
- troubleshooting 文档说明没有 API key 时会使用 fallback。

面试里可以说：

> fallback 是降低上手门槛，不是替代真实模型验证。

## Q8：模型配置从哪里来？

一句话答案：

> 默认模型来自环境变量和 `.env`，项目级角色和 eval 模型来自 workspace 的 `pyagent.toml`。

基础环境变量：

```bash
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
export PYAGENT_MODEL="gpt-4.1-mini"
export PYAGENT_MAX_STEPS="10"
```

加载顺序：

```text
current cwd .env
  -> workspace .env
  -> os.environ
  -> defaults
```

默认值：

```text
PYAGENT_MODEL = gpt-4.1-mini
OPENAI_BASE_URL = https://api.openai.com/v1
PYAGENT_MAX_STEPS = 10
```

注意：

> `.env` 只在环境变量不存在时设置，不覆盖用户已经 export 的值。

这对本地开发很重要，避免项目 `.env` 意外覆盖用户 shell 的真实配置。

## Q9：role-specific model 怎么实现？

一句话答案：

> `build_llm_client(config, role=...)` 会先看该角色有没有 model override，没有就回退到默认 `PYAGENT_MODEL`。

配置位置：

```toml
[agents.planner]
model = "planner-model"
system_prompt = "Plan with tiny safe steps."

[agents.executor]
model = "executor-model"

[agents.reviewer]
system_prompt = "Review conservatively."
```

逻辑：

```text
model = config.model
if role config has model:
  model = role_model

if api_key:
  OpenAICompatibleClient(model=model)
else:
  LocalFallbackClient()
```

为什么有价值？

- Planner 可能需要更强规划能力。
- Executor 可能需要稳定工具调用。
- Reviewer 可能需要更保守的分析能力。
- eval 可以比较不同角色配置。

边界：

> 当前只支持 role-specific model 和 system prompt，还没有 per-role temperature、max tokens、timeout、cost budget。

## Q10：为什么 Planner、Executor、Reviewer 不一定用同一个模型？

一句话答案：

> 因为它们的任务形态不同，最优模型能力也不同。

Planner：

- 需要拆任务。
- 需要识别风险。
- 不应该调用工具。
- 输出结构化 plan。

Executor：

- 需要严格遵守 step contract。
- 需要稳定 tool calling。
- 需要小步执行。

Reviewer：

- 需要保守复核。
- 需要识别风险。
- 需要生成测试建议。
- 不能覆盖 deterministic gate。

所以未来可以这样配置：

```text
planner  -> stronger reasoning model
executor -> cheaper stable tool-calling model
reviewer -> conservative review model
```

但不要夸大：

> 当前项目支持配置，不代表已经实现自动按任务路由模型。

## Q11：`--check-model` 解决什么问题？

一句话答案：

> 它用最小工具调用探针验证当前真实模型是否支持 tool calling。

命令：

```bash
pyagent --check-model
```

它会要求模型：

```text
Call list_files with path "." and do not answer directly.
```

可能结果：

```text
tool_call: list_files args={'path': '.'}
```

或者：

```text
No OPENAI_API_KEY configured. Local fallback is active; real tool calling was not checked.
```

或者：

```text
No tool call returned. Model answered: ...
```

面试里要讲：

> 多模型适配不能只看模型名，必须验证这个模型在当前 provider、base_url、API key 下真的能返回 tool call。

## Q12：模型名不存在时怎么办？

一句话答案：

> 不应该靠复杂任务时才发现，而应该通过 `--check-model`、清晰错误和配置校验尽早暴露。

我们真实遇到过一个类似问题：

```text
The model 'gpt-image-2' does not exist.
```

这类问题可能来自：

- 模型名写错。
- 当前账号没有权限。
- provider 不支持该模型。
- API 版本变化。
- 文档或界面更新导致旧配置不可用。
- 工具误选了不存在的模型。

在 PyAgentCLI 里应该这样处理：

1. 先运行：

   ```bash
   pyagent --check-model
   ```

2. 如果报 HTTP error，展示 provider 返回的 detail。

3. 检查：

   ```text
   OPENAI_BASE_URL
   PYAGENT_MODEL
   OPENAI_API_KEY
   ```

4. 不把 fallback 成功当成真实模型成功。

5. 在 eval 中把真实模型 case 标记为 disabled 或 failed，而不是吞掉。

这也是为什么多模型工程需要“诊断入口”。

## Q13：`--eval-real-model` 为什么默认关闭？

一句话答案：

> 因为真实模型 eval 会产生费用、网络依赖和非确定性，不能作为默认本地测试。

默认：

```bash
pyagent --eval
```

应该尽量：

- 不调用外部 API。
- 结果稳定。
- 能在 CI 或本地无 key 环境跑。
- 验证 runtime deterministic 部分。

真实模型 eval：

```bash
pyagent --eval --eval-real-model
```

需要用户显式 opt-in。

原因：

- 可能产生费用。
- 可能受网络影响。
- 可能受模型版本影响。
- 输出不完全稳定。
- 可能因为 API key 缺失失败。

面试里可以说：

> 我把真实模型 eval 做成显式开关，是为了把成本和不确定性从默认验证链路中隔离出去。

## Q14：`--eval-compare-models` 做什么？

一句话答案：

> 它根据 `pyagent.toml` 中的模型列表，对同一批 trace case 做多模型比较。

配置示例：

```toml
[evals.model_comparison.models.fast]
model = "gpt-4.1-mini"
base_url = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"

[evals.model_comparison.models.reasoning]
model = "gpt-4.1"
base_url = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"
```

命令：

```bash
pyagent --eval --eval-compare-models
```

价值：

- 比较不同模型是否能完成相同 tool calling case。
- 观察 used tools。
- 找出模型不支持 tool call 或参数不稳定的问题。
- 为未来 model router 和成本优化积累证据。

边界：

> 当前是 trace comparison，不是完整 benchmark 平台，也没有自动选择最优模型。

## Q15：成本控制当前做到哪里？

一句话答案：

> 当前做到 opt-in 控制和默认不调用外部模型，还没有完整 token/cost tracking。

已经有：

- 没有 API key 时 fallback。
- `pyagent --eval` 默认不跑真实模型 trace。
- `--eval-real-model` 显式开启真实模型。
- `--eval-compare-models` 显式开启多模型比较。
- role-specific model 可以手动选择更便宜或更强模型。
- `PYAGENT_MAX_STEPS` 控制 Agent Loop 步数上限。

还没有：

- input/output token 统计。
- estimated cost。
- per-run cost budget。
- per-role cost budget。
- provider price registry。
- prompt cache。
- streaming usage aggregation。
- cost dashboard。

面试表达：

> 当前 v0.1 的成本控制是防误触和显式 opt-in，不是完整 FinOps 系统。下一步会把 token usage、estimated cost 和 budget guardrail 加进 run event。

## Q16：为什么 `max_steps` 也算成本控制？

一句话答案：

> 因为 Agent Loop 每多一步都可能多一次模型调用和工具调用，步数上限同时是安全阀和成本阀。

没有 `max_steps`：

- 模型可能反复调用失败工具。
- 可能进入无限 ReAct 循环。
- token 和时间持续消耗。
- 用户无法预估成本。

有 `PYAGENT_MAX_STEPS`：

```text
最多执行 N 个 Agent step
超过后停止
返回当前结果/错误
```

这不是完整 budget，但很实用。

面试里可以补：

> 后续我会在 max_steps 之外加 token budget、tool budget、wall-clock timeout 和 cost budget。

## Q17：多模型适配和模型能力声明有什么关系？

一句话答案：

> 支持配置多个模型不等于知道每个模型能做什么，下一步需要 capability registry。

未来能力声明可以包括：

```toml
[models.gpt_4_1_mini]
provider = "openai"
model = "gpt-4.1-mini"
supports_tool_calling = true
supports_json_mode = true
supports_vision = false
supports_streaming = true
max_context_tokens = 128000
cost_per_input_token = 0.0000004
cost_per_output_token = 0.0000016
```

然后 `--check-model` 可以升级成：

```text
配置检查
  -> API connectivity
  -> tool calling probe
  -> context limit probe
  -> streaming probe
  -> cost metadata
```

这样 model selection 才有依据。

当前边界：

> PyAgentCLI 目前没有 capability registry，只做了统一 client、配置、fallback 和 eval comparison。

## Q18：如果 provider API 不完全兼容怎么办？

一句话答案：

> 不应该把 provider 差异泄露给 Agent Loop，而应该在 adapter 层处理或显式报错。

可能差异：

- tool call 字段格式不同。
- arguments 不是合法 JSON。
- base_url 路径不同。
- tool_choice 不支持。
- response usage 字段不同。
- streaming chunk 格式不同。
- 错误码格式不同。

当前 PyAgentCLI 的处理：

- 使用 OpenAI-compatible 格式。
- malformed arguments 放进 `_raw`。
- HTTPError 和 URLError 转成 RuntimeError。

未来可以增强：

- provider-specific adapter。
- compatibility tests。
- capability registry。
- clearer error classification。
- usage parsing。
- retry/backoff。

面试里可以说：

> 我不会让 Agent Loop 到处写 if provider == ...，provider 差异应该集中在 LLM adapter 层。

## Q19：如果模型不返回 Tool Call 怎么办？

一句话答案：

> Agent Loop 应该把它当成模型回复，不执行工具；诊断上通过 `--check-model` 和 eval 暴露。

可能原因：

- 模型不支持 tool calling。
- prompt 没要求清楚。
- provider 忽略了 tools。
- tool schema 太复杂。
- 模型选择了直接回答。

运行时：

```text
LLMResponse.content != None
tool_calls == []
  -> Agent can answer directly or stop
```

诊断时：

```bash
pyagent --check-model
```

如果没有 tool call，输出会告诉用户模型直接回答了什么。

面试重点：

> 不返回 tool call 不是 runtime 越权执行的理由。没有 tool call 就不能假装调用了工具。

## Q20：多模型 eval 怎么避免把结果讲虚？

一句话答案：

> 要讲清 eval case、是否真实模型、是否 opt-in、比较指标和 disabled reason。

不要说：

```text
我们做了多模型评测，所以知道哪个最好。
```

应该说：

```text
当前 eval comparison 用固定 trace case 比较不同模型是否正确使用工具、是否完成目标、used tools 是什么、失败原因是什么。它能帮助发现 tool calling 兼容性和基本完成度差异，但不是完整模型排行榜。
```

还要说明：

- 没配置模型时显示 disabled。
- API key 缺失时显示 disabled reason。
- 默认 eval 不调用外部模型。
- 真实模型结果可能有波动。

## Q21：开发中遇到的真实问题

一句话答案：

> 多模型适配最容易出问题的不是抽象，而是配置、可用性、费用和误判。

我们真实遇到或讨论过：

1. 模型名不可用。

   现象：

   ```text
   The model 'gpt-image-2' does not exist.
   ```

   复盘：

   - 不要继续调用不可用模型。
   - 先检查刚改了哪些文件。
   - 回到可用模型或本地文档任务继续。
   - 对项目来说，需要 `--check-model` 和清晰错误。

2. 真实模型和 fallback 容易混淆。

   复盘：

   - fallback 只证明 runtime 链路。
   - 真实模型能力必须单独 check。

3. 默认 eval 不能调用外部模型。

   复盘：

   - 否则本地测试会有费用、网络和稳定性问题。
   - 所以加 `--eval-real-model` 和 `--eval-compare-models`。

4. role-specific model 很容易过度包装。

   复盘：

   - 当前是配置能力。
   - 不是自动 router。
   - 不是 cost optimizer。

5. Provider 兼容性不能靠想象。

   复盘：

   - OpenAI-compatible 只是接口约定。
   - 真正是否支持 tool calling 要跑 probe。

## Q22：如果自己开发这个模块，最容易踩什么坑？

一句话答案：

> 最容易把“可配置模型名”误认为“多模型工程”。

常见坑：

- Agent Loop 直接写死某个 SDK。
- Message 格式到处手写 dict。
- Tool call 解析散落在代码里。
- 没有 fallback，项目无法无 key 演示。
- fallback 过强，误导用户以为是真模型。
- 没有 `--check-model`，复杂任务时才发现模型不支持工具。
- 默认 eval 调真实模型，导致费用和不稳定。
- role model 配置没有测试。
- provider 错误信息被吞掉。
- 没有区分“模型配置错误”和“工具执行失败”。
- 成本控制只停留在口头，没有 opt-in 或 step limit。

避免方式：

```text
先定义 LLMClient 协议
再统一 Message / ToolCall / LLMResponse
再接 OpenAI-compatible adapter
再做 LocalFallbackClient
再做 check-model
再做 opt-in real eval
最后考虑 model router 和 cost dashboard
```

## 现场画图

面试时可以画这张：

```text
AgentLoop
  |
  | messages + tool schemas
  v
LLMClient
  |
  +-- OpenAICompatibleClient
  |     |
  |     +-- /chat/completions
  |     +-- parse tool_calls
  |
  +-- LocalFallbackClient
        |
        +-- no-key demo path

LLMResponse
  |
  +-- content
  +-- tool_calls
          |
          v
      ToolRegistry
          |
          v
      Safety / Approval / Audit
```

如果继续讲 role config：

```text
PYAGENT_MODEL
  |
  +-- default model

pyagent.toml
  |
  +-- agents.planner.model
  +-- agents.executor.model
  +-- agents.reviewer.model
  |
  v
build_llm_client(config, role)
```

## 必背 8 句

1. 多模型适配不是罗列 provider，而是把 Agent Runtime 和具体模型 SDK 解耦。
2. `LLMClient` 统一 `chat(messages, tools) -> LLMResponse`。
3. `ToolCall` 是模型的结构化意图，不是执行权。
4. OpenAI-compatible client 负责消息转换、tools 传递和 tool_calls 解析。
5. `LocalFallbackClient` 只证明本地 runtime 能跑，不能证明真实模型质量。
6. `--check-model` 用最小工具调用探针验证真实模型 tool calling。
7. `--eval-real-model` 和 `--eval-compare-models` 默认关闭，是为了控制费用和不稳定性。
8. 当前还不是自动 model router，也没有完整 cost dashboard。

## 一版完整回答

如果面试官问：

> 你们多模型适配怎么做？怎么控制成本？

可以这样答：

> PyAgentCLI 里我没有把模型调用写死在 Agent Loop，而是定义了 `LLMClient` 协议，统一输入 `Message` 和 tools schema，输出 `LLMResponse`。`Message` 覆盖 system/user/assistant/tool，`ToolCall` 表示模型想调用的工具名和参数，`LLMResponse` 同时包含文本回复和 tool calls。这样 Agent Loop 不关心底层是哪个 provider，只负责把模型返回的 ToolCall 交给 ToolRegistry，再走 SafetyPolicy、ApprovalHandler 和 AuditLogger。也就是说 Function Calling 不是模型执行函数，执行权始终在本地 runtime。
>
> 真实模型目前通过 OpenAI-compatible Chat Completions client 接入，它会把内部 message 转成 OpenAI 格式，有工具时传 `tools` 和 `tool_choice=auto`，再把返回的 `tool_calls` 解析回内部 `ToolCall`。配置上支持 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`PYAGENT_MODEL`，并且可以在 workspace 的 `pyagent.toml` 给 planner、executor、reviewer 配不同 model。如果没有 API key，系统会使用 `LocalFallbackClient`，让 CLI 和工具链路仍能演示，但它不会被当成真实模型质量；`--check-model` 会明确提示真实 tool calling 没有检查。
>
> 成本和稳定性方面，默认 `pyagent --eval` 不调用外部模型，只跑本地确定性评估；真实模型 trace eval 必须显式加 `--eval-real-model`，多模型 comparison 必须显式加 `--eval-compare-models` 并在 `pyagent.toml` 配模型。这样不会因为普通测试误烧 API，也能把网络和模型波动隔离出去。当前已经有 opt-in 和 `PYAGENT_MAX_STEPS` 这类基础成本阀，但还没有完整 token/cost tracking、provider price registry、streaming usage 或自动 router。下一步我会加 model capability registry、usage event、estimated cost 和 budget guardrail。

## 复习顺序

建议按这个顺序复习：

1. 先读 [11 多模型适配和 LLM Client](11_multi_model_llm_client.md)。
2. 看 `src/pyagentcli/llm/base.py`，理解 `Message`、`ToolCall`、`LLMResponse`。
3. 看 `src/pyagentcli/llm/openai_compatible.py`，理解 request 和 tool call parse。
4. 看 `src/pyagentcli/llm/model_config.py`，理解 role model override。
5. 看 `src/pyagentcli/config.py`，理解 env、`.env`、`pyagent.toml`。
6. 看 `tests/test_llm_model_config.py` 和 `tests/test_config.py`。
7. 背“完整回答”。

## 到这里，面试篇第一轮完成

第 16 到第 22 篇已经覆盖：

- ReAct、Plan-and-Execute、Multi-Agent。
- Memory、RAG、长上下文工程。
- Tool Call、HITL、安全策略。
- MCP、Browser Tools、CDP 思路。
- Prompt 分层、Skill 系统。
- CLI 产品化、Git、Runtime API。
- 多模型适配、运行时切换、成本控制。

下一阶段可以进入复盘篇：

> 23 开发复盘：我们真实遇到的问题。

这一篇会把项目开发中的协作坑、工具坑、模型坑、GitHub/sandbox 坑、长上下文坑、文档沉淀方法，以及“如果你自己开发会遇到什么坑”集中整理成复盘材料。
