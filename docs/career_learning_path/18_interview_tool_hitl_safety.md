# 18 面试题第三弹：Tool Call、HITL、安全策略

这一弹对应 Agent 的安全执行层。

Coding Agent 最容易被追问的不是“能不能调用工具”，而是：

```text
模型凭什么能改我的文件？
怎么防止它删库？
写文件前用户能不能看到 diff？
shell 命令怎么管？
外部工具会不会绕过安全？
audit log 记录什么？
```

这一弹要把“模型意图”和“本地执行权”彻底讲清楚。

## 这一弹考什么

这一弹主要考 6 个能力：

1. 你是否理解 Tool Call 不是执行权。
2. 你是否能讲清 Tool Registry、SafetyPolicy、ApprovalHandler、AuditLogger 的执行链路。
3. 你是否知道 Coding Agent 的风险分级。
4. 你是否能解释路径围栏、命令黑名单和非交互拒绝。
5. 你是否能讲清 plan approval 和 tool approval 的区别。
6. 你是否能解释 MCP、Browser、Skill 为什么不能绕过安全层。

对应源码：

```text
src/pyagentcli/tools/base.py
src/pyagentcli/tools/registry.py
src/pyagentcli/tools/filesystem.py
src/pyagentcli/tools/shell.py
src/pyagentcli/safety/policy.py
src/pyagentcli/safety/approval.py
src/pyagentcli/safety/audit_log.py
src/pyagentcli/agent/plan_executor.py
src/pyagentcli/mcp/adapter.py
src/pyagentcli/tools/browser.py
```

对应实战文档：

- [06 Tool Call、HITL 和安全策略](06_tool_hitl_safety.md)

## 哪些简历句子会触发这一弹

如果简历里写：

> 为 PyAgentCLI 构建 HITL 安全执行层，按 READ / WRITE / EXECUTE / NETWORK / CRITICAL 对工具分级，在 ToolRegistry 中统一接入路径围栏、危险命令拒绝、写入/执行审批、diff preview 和 JSONL audit log，降低本地 Coding Agent 自动化文件与命令操作风险。

面试官会追问：

- Tool Call 为什么不是执行？
- RiskLevel 怎么分？
- WRITE 和 EXECUTE 为什么需要审批？
- path guardrail 怎么做？
- audit log 记录什么？

如果简历里写：

> `write_file` / `edit_file` 在审批前生成 unified diff preview，`edit_file` 拒绝 ambiguous replacement，所有工具调用落盘到 `.pyagent/audit.log.jsonl` 并对敏感参数脱敏。

面试官会追问：

- 为什么 `edit_file` 要唯一匹配？
- diff preview 什么时候生成？
- preview 失败怎么办？
- audit 为什么要脱敏？

## 面试开场 30 秒回答

如果面试官问“你怎么保证 Coding Agent 安全”，可以先这样答：

> PyAgentCLI 里 Tool Call 只是模型输出的结构化意图，真正执行发生在本地 ToolRegistry。每个工具都有 RiskLevel：READ 默认允许，WRITE 需要审批，EXECUTE 先检查危险命令再审批，NETWORK 和 CRITICAL 在 v0.1 默认拒绝。所有文件路径都通过 `SafetyPolicy.resolve_workspace_path()` 解析到 workspace 内，并拒绝 `.env`、`.git`、`.venv` 等敏感路径。写文件和编辑文件会在审批前生成 unified diff preview，`edit_file` 要求 old_text 唯一匹配。非交互模式下需要审批的工具默认拒绝。所有工具调用和失败都会写 JSONL audit log，并对 content、token、password 等敏感字段脱敏。

## Q1：Tool Call 是不是模型在执行函数？

一句话答案：

> 不是。Tool Call 是模型输出的结构化调用意图，真正执行由本地 Agent Runtime 控制。

展开回答：

模型输出：

```json
{
  "name": "edit_file",
  "arguments": {
    "path": "README.md",
    "old_text": "TODO",
    "new_text": "READY"
  }
}
```

真正执行链路：

```text
ToolRegistry.execute()
  -> SafetyPolicy.evaluate_tool()
  -> Tool.preview()
  -> ApprovalHandler.request()
  -> Tool.run()
  -> AuditLogger.record()
  -> ToolResult
```

面试加分点：

> 模型可以提出动作，但不能拥有执行权。

## Q2：Tool Registry 在安全里起什么作用？

一句话答案：

> Tool Registry 既是工具能力目录，也是所有工具执行进入安全策略的统一入口。

展开回答：

Tool Registry 负责：

- 注册工具。
- 暴露 schema 给模型。
- 根据 tool name 分发调用。
- 调 SafetyPolicy。
- 调 preview。
- 调 ApprovalHandler。
- 调 Tool.run。
- 记录 audit log。

为什么重要？

如果每个工具自己随便执行，安全策略会散落、重复、漏掉。

统一入口可以保证：

> 所有工具都必须过 policy、approval、audit。

## Q3：RiskLevel 怎么分？

一句话答案：

> PyAgentCLI 把工具分成 READ、WRITE、EXECUTE、NETWORK、CRITICAL，不同风险等级对应不同默认动作。

展开回答：

当前策略：

```text
READ      -> allow
WRITE     -> ask approval
EXECUTE   -> deny dangerous commands, otherwise ask approval
NETWORK   -> deny
CRITICAL  -> deny
```

为什么 NETWORK / CRITICAL 默认 deny？

因为 v0.1 没有完善 allowlist、域名策略、OAuth 和外部动作审计。

保守默认更安全。

## Q4：为什么写文件要审批？

一句话答案：

> 因为写文件会改变真实工作区，可能覆盖代码、破坏配置或引入错误。

展开回答：

WRITE 工具包括：

- `write_file`
- `edit_file`
- 浏览器截图这类写 artifact 的工具也要限制输出路径。

PyAgentCLI 的写入策略：

- 先生成 preview。
- 展示 unified diff。
- 用户审批后执行。
- 写 audit log。

这让用户在副作用发生前看到：

```text
将删除什么
将新增什么
将写到哪个路径
```

## Q5：`write_file` 和 `edit_file` 为什么要 diff preview？

一句话答案：

> 因为用户审批前必须看到具体文件变化，而不是只看到“模型想写文件”。

展开回答：

`write_file` preview：

- 如果是新文件，展示新增内容。
- 如果是覆盖旧文件，展示 old vs new diff。

`edit_file` preview：

- 基于 `old_text` 和 `new_text` 生成 diff。

这样审批不是盲点确认。

边界：

> preview 失败时不应该继续执行，而要返回 failure 并记录 audit。

## Q6：`edit_file` 为什么要求 old_text 唯一匹配？

一句话答案：

> 因为同一段 old_text 如果出现多次，Agent 可能改错位置。

展开回答：

如果文件里有：

```text
status = "TODO"
...
status = "TODO"
```

模型只说：

```json
{"old_text": "status = \"TODO\"", "new_text": "status = \"READY\""}
```

就无法判断该改哪一个。

所以 PyAgentCLI 拒绝 ambiguous replacement。

这比“随便替换第一个”安全。

## Q7：路径围栏怎么实现？

一句话答案：

> 所有路径都先 resolve，再检查是否仍在 workspace 内，并拒绝敏感目录。

展开回答：

核心逻辑：

```text
candidate = workspace_root / raw_path
candidate.resolve()
candidate.relative_to(workspace_root)
```

如果：

```text
../outside.txt
```

逃出 workspace，就拒绝。

如果路径包含：

```text
.env
.git
.venv
node_modules
__pycache__
```

也拒绝。

面试加分点：

> 路径安全不能靠 prompt，必须在工具层做。

## Q8：shell 命令怎么管？

一句话答案：

> `run_shell` 是 EXECUTE 工具，先拒绝危险命令，再对其他命令走人工审批。

展开回答：

危险模式包括：

```text
rm -rf
sudo
chmod -R
chown -R
mkfs
dd if=
curl ... | sh/bash
wget ... | sh/bash
fork bomb
```

处理顺序：

```text
dangerous -> deny
otherwise -> ask approval
```

注意：

> 用户审批不是绕过 policy；policy deny 是硬拒绝。

## Q9：非交互模式为什么拒绝需要审批的工具？

一句话答案：

> 因为没有用户在场时，Agent 不能自己批准高风险副作用。

展开回答：

非交互模式适合：

- CI。
- eval。
- 只读诊断。
- 脚本化检查。

但如果工具需要审批：

```text
WRITE
EXECUTE
```

默认拒绝。

这避免：

```text
pyagent --no-input "fix everything"
```

在无人确认时修改大量文件。

## Q10：Audit log 记录什么？

一句话答案：

> Audit log 记录每次工具调用的目标、step、工具名、风险等级、参数摘要、审批结果、执行结果和错误。

展开回答：

路径：

```text
.pyagent/audit.log.jsonl
```

为什么 JSONL？

- 易追加。
- 易 grep。
- 易被 Reviewer 读取。
- 易被 Memory 提取工具和路径。
- 易被 Eval / Trace 复用。

为什么要 redaction？

因为参数里可能有：

- content。
- api_key。
- password。
- token。

这些不能完整写入日志。

## Q11：Plan approval 和 tool approval 有什么区别？

一句话答案：

> Plan approval 批准步骤意图，tool approval 批准具体副作用。

展开回答：

Plan approval：

```text
用户同意这个计划可以开始执行
```

Tool approval：

```text
用户同意这次具体 write_file / edit_file / run_shell
```

为什么两层都要？

因为计划里写：

```text
修改 README
```

不等于批准：

```text
覆盖整个 README
```

所以具体工具仍要 preview、policy、approval。

## Q12：MCP 工具会不会绕过安全？

一句话答案：

> 不应该。MCP 只是扩展工具来源，进入 PyAgentCLI 后仍要映射 RiskLevel 并走 ToolRegistry。

展开回答：

MCP tool 是外部 server 提供的工具。

风险：

- 外部工具能力未知。
- 可能访问网络。
- 可能读写外部系统。
- metadata 不完整。

PyAgentCLI 当前策略：

- `readOnlyHint` 可映射 READ。
- 否则默认 NETWORK。
- CRITICAL 情况保守拒绝。
- 调用仍写 audit。

面试加分点：

> MCP 扩展工具生态，不扩展权限边界。

## Q13：Skill 会不会绕过安全？

一句话答案：

> 不会，Skill 是 prompt guidance，不是可执行工具，也不能覆盖用户任务、安全策略或审批。

展开回答：

Skill 存在：

```text
.pyagent/skills/<skill>/skill.toml
.pyagent/skills/<skill>/SKILL.md
```

它做的是：

- 提供流程建议。
- 提供项目约定。
- 提供任务 guidance。

它不做：

- 执行工具。
- 授权工具。
- 绕过 approval。
- 覆盖 safety policy。

## Q14：Browser 工具有什么特殊安全点？

一句话答案：

> Browser 工具看似观察页面，但截图、点击、输入、登录态页面都可能有副作用。

展开回答：

当前 PyAgentCLI Browser 偏 local-first。

特殊风险：

- screenshot 会写文件。
- interaction 可能点击真实按钮。
- 登录态页面可能有真实账号权限。
- external URL 涉及网络。

所以：

- 截图输出限制到 `.pyagent/browser/`。
- 交互工具需要更高风险分级。
- 外部导航要谨慎。
- 仍要 audit。

## Q15：如果用户明确要求危险操作怎么办？

一句话答案：

> 用户要求不等于自动允许；policy deny 的操作仍然拒绝，必要时让用户手动执行。

展开回答：

例如用户说：

```text
rm -rf .
```

Agent 不应该因为用户要求就执行。

安全策略应该：

- 明确拒绝。
- 解释原因。
- 提供更安全替代方案。

边界：

> HITL 不是“用户说什么都执行”，而是把高风险动作交给用户明确控制。

## Q16：你们开发时这里遇到过什么真实问题？

可以讲 4 个。

### 1. GitHub push 和 sandbox 权限

我们遇到过普通 sandbox 请求无法 push GitHub 的情况。

这说明：

> 外部网络和远端平台操作不能当成本地文件操作。

正确处理：

- 本地继续 commit。
- 保持状态干净。
- push 由用户确认或手动完成。
- 不绕过 sandbox。

### 2. write_file / edit_file 必须 preview

如果只问：

```text
Approve write_file?
```

用户不知道会写什么。

所以要展示 diff。

### 3. edit_file 多匹配会改错

旧文本不唯一时，拒绝执行。

这比“模型猜第一个”更安全。

### 4. Skill 边界必须写清楚

Skill 很容易被误解成“给 Agent 新权限”。

所以我们文档和 context block 都写清：

```text
skills do not override safety policy or tool approvals
```

## Q17：如果面试官说“prompt 里写不要越权不就行了吗”，怎么答？

一句话答案：

> Prompt 只能约束模型行为倾向，不能作为安全边界；真实安全必须在工具执行层。

展开回答：

模型可能：

- 忘记 prompt。
- 被用户 prompt injection。
- 误判路径。
- 生成危险命令。

所以必须有：

- path guardrail。
- command denylist。
- approval。
- audit。
- risk level。

Prompt 是辅助，policy 是硬边界。

## 现场画图怎么画

可以画：

```text
LLM
  |
  v
ToolCall(name, args)
  |
  v
ToolRegistry
  |
  v
SafetyPolicy
  |-- READ allow
  |-- WRITE ask
  |-- EXECUTE deny dangerous / ask
  |-- NETWORK deny
  |-- CRITICAL deny
  |
  v
Tool.preview
  |
  v
ApprovalHandler
  |
  v
Tool.run
  |
  v
AuditLogger
  |
  v
Observation -> LLM
```

讲图时强调：

- 模型只在最上游。
- Policy deny 是硬拒绝。
- Approval 只处理 ask，不覆盖 deny。
- Audit 记录成功和失败。

## 必背 8 句

1. Tool Call 是模型意图，不是执行权。
2. Tool Registry 是能力目录，也是安全入口。
3. READ 默认允许，WRITE/EXECUTE 需要审批，NETWORK/CRITICAL 默认拒绝。
4. 路径安全必须用 resolve + workspace boundary，不能靠 prompt。
5. 危险 shell 命令先 deny，再谈审批。
6. 写文件审批前必须展示 diff preview。
7. Plan approval 批准步骤意图，tool approval 批准具体副作用。
8. MCP、Browser、Skill 都不能绕过 ToolRegistry、SafetyPolicy 和 Audit。

## 一版完整回答

如果面试官问：

> 你们怎么保证 Agent 调工具安全？

可以这样答：

> PyAgentCLI 里 Tool Call 只是模型输出的结构化意图，不是执行权。真正执行都经过 `ToolRegistry.execute()`，它会先根据工具的 RiskLevel 调 `SafetyPolicy`。READ 工具默认允许，WRITE 工具需要审批，EXECUTE 工具会先检查危险命令，比如 `rm -rf`、`sudo`、`curl | sh`，再对非危险命令走审批，NETWORK 和 CRITICAL 在 v0.1 默认拒绝。所有文件路径都会用 `resolve()` 解析并检查是否仍在 workspace 内，同时拒绝 `.env`、`.git`、`.venv` 等敏感路径。`write_file` 和 `edit_file` 在审批前会生成 unified diff preview，`edit_file` 还要求 `old_text` 唯一匹配，避免改错位置。非交互模式下需要审批的工具默认拒绝。无论成功、失败、拒绝还是 preview failure，都会写 `.pyagent/audit.log.jsonl`，并对 content、token、password 等敏感字段脱敏。外部 MCP 工具、Browser 工具和 Skill 都不能绕过这条执行链路。

## 这一弹之后怎么复习

复习顺序：

1. 先读 [06 Tool Call、HITL 和安全策略](06_tool_hitl_safety.md)。
2. 再看源码：

```text
src/pyagentcli/tools/registry.py
src/pyagentcli/safety/policy.py
src/pyagentcli/safety/approval.py
src/pyagentcli/safety/audit_log.py
src/pyagentcli/tools/filesystem.py
src/pyagentcli/tools/shell.py
```

下一弹进入：

> MCP、Browser Tools、CDP 思路
