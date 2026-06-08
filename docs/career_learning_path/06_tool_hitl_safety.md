# 06 Tool Call、HITL 和安全策略

这一篇对应 PaiCLI 学习路线里的 Tool Call / HITL / Safety 思路，但内容全部落到 PyAgentCLI 当前的 Python 实现。

先给结论：

> Tool Call 只是模型输出的结构化意图，不是执行权。PyAgentCLI 的执行权在 ToolRegistry、SafetyPolicy、ApprovalHandler 和 AuditLogger 组成的本地 runtime 里。

Coding Agent 和普通 chatbot 最大的区别，是它能真的读文件、写文件、改代码、跑命令。

所以安全边界不能靠 prompt 说一句“请小心”，必须落在工具执行层。

## 这一篇学什么

学完这一篇，你要能讲清楚：

- Tool Call 为什么不是执行。
- ToolRegistry 为什么是能力目录，也是安全入口。
- RiskLevel 为什么要分 READ / WRITE / EXECUTE / NETWORK / CRITICAL。
- SafetyPolicy 如何做路径围栏、命令黑名单和默认拒绝。
- ApprovalHandler 如何实现 HITL。
- 非交互模式为什么会拒绝需要审批的工具。
- AuditLogger 记录什么，为什么要 JSONL。
- `write_file` / `edit_file` 为什么要提供 diff preview。
- `edit_file` 为什么要求 old_text 唯一匹配。
- 为什么 MCP、Browser、Skill 都不能绕过安全层。

## Tool Call 的本质

模型输出的是意图：

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

模型没有真的打开文件，也没有真的改文件。

真正执行的是：

```text
ToolRegistry.execute()
  -> SafetyPolicy.evaluate_tool()
  -> Tool.preview()
  -> ApprovalHandler.request()
  -> Tool.run()
  -> AuditLogger.record()
  -> ToolResult
```

一句面试答案：

> Tool Call 是模型和真实世界之间的协议层，不是执行层；执行权必须留在本地 Agent Runtime。

## 为什么需要 HITL

HITL 是 Human-in-the-loop。

在 Coding Agent 里，高风险动作包括：

- 写文件。
- 修改代码。
- 执行 shell。
- 访问网络。
- 调用外部 MCP 工具。
- 截图或写入浏览器 artifact。
- 删除文件或改变权限。

这些动作一旦执行，就可能产生真实副作用。

所以 PyAgentCLI 的原则是：

> 模型可以建议做什么，但涉及副作用时，用户保留最终执行权。

## PyAgentCLI 当前实现了什么

当前已经落地的能力：

- `RiskLevel`：`READ / WRITE / EXECUTE / NETWORK / CRITICAL`。
- `SafetyPolicy.resolve_workspace_path()`：路径围栏。
- path denylist：`.git`、`.env`、`.venv`、`node_modules`、`__pycache__`。
- command deny patterns：`rm -rf`、`sudo`、`chmod -R`、`curl | sh` 等。
- READ 工具默认 allow。
- WRITE 工具 ask approval。
- EXECUTE 工具先查危险命令，再 ask approval。
- NETWORK / CRITICAL 默认 deny。
- `ApprovalHandler`：交互式审批。
- 非交互模式：需要审批则 deny。
- `AuditLogger`：写 `.pyagent/audit.log.jsonl`。
- tool preview：写文件和编辑文件展示 unified diff。
- `edit_file`：要求 `old_text` 正好匹配一次。
- tool failure 变成 observation，不让 Agent runtime 崩溃。
- audit args redaction：`content`、`api_key`、`password`、`token` 会脱敏。

当前还没有落地的能力：

- allowlist 配置文件。
- per-tool policy override。
- per-command allowlist。
- approval session cache。
- dry-run 模式。
- 文件级权限配置。
- shell 命令结构化 parser。
- 网络域名 allowlist。
- 审计日志 UI。

所以最准确的表达是：

> PyAgentCLI 已实现本地 Coding Agent 的最小安全执行层：路径围栏、风险分级、审批、危险命令拒绝和 JSONL 审计。

## 执行链路

源码：

```text
src/pyagentcli/tools/registry.py
src/pyagentcli/safety/policy.py
src/pyagentcli/safety/approval.py
src/pyagentcli/safety/audit_log.py
```

完整链路：

```text
LLM tool call
  -> ToolRegistry.get(name)
  -> SafetyPolicy.evaluate_tool(tool.name, tool.risk_level, args)
  -> Tool.preview(args, context)
  -> ApprovalHandler.request(...)
  -> Tool.run(args, context)
  -> AuditLogger.record(...)
  -> ToolResult.to_message_content()
  -> observation sent back to LLM
```

如果工具不存在：

```text
ToolResult.failure("Unknown tool")
```

如果 preview 失败：

```text
ToolResult.failure(...)
AuditLogger.record(decision="preview failed")
```

如果审批拒绝：

```text
ToolResult.failure("Denied by user.", approval="denied")
```

如果工具运行异常：

```text
ToolResult.failure(str(exc), exception_type=...)
```

这些失败都会变成 observation，而不是让 Agent 进程直接崩掉。

## RiskLevel 怎么分

源码：

```text
src/pyagentcli/tools/base.py
```

当前风险等级：

```text
READ
WRITE
EXECUTE
NETWORK
CRITICAL
```

PyAgentCLI 当前策略：

```text
READ -> ALLOW
WRITE -> ASK
EXECUTE -> DENY dangerous commands, otherwise ASK
NETWORK -> DENY
CRITICAL -> DENY
```

为什么 NETWORK / CRITICAL 默认拒绝？

因为 v0.1 的安全策略宁可保守。

MCP 和浏览器工具可能连接外部世界，一旦默认开放，很容易绕过本地边界。

## 路径围栏

源码：

```text
SafetyPolicy.resolve_workspace_path(raw_path)
```

核心逻辑：

```text
candidate = workspace_root / raw_path
candidate.resolve()
candidate.relative_to(workspace_root)
```

如果路径逃出 workspace：

```text
../outside.txt -> PermissionError
```

如果路径命中 denylist：

```text
.env -> PermissionError
.git/config -> PermissionError
node_modules/... -> PermissionError
```

面试回答：

> 本地 Coding Agent 的路径安全不能靠 prompt，必须在工具层 resolve 路径并检查 workspace boundary。

## 命令黑名单

源码：

```text
SafetyPolicy.command_deny_patterns
```

当前拒绝模式包括：

```text
rm -rf
sudo
chmod -R
chown -R
mkfs
dd if=
shell fork bomb pattern
curl ... | sh/bash
wget ... | sh/bash
```

`run_shell` 是 EXECUTE 工具。

执行前先检查危险命令：

```text
dangerous -> DENY
otherwise -> ASK
```

所以即使用户审批 handler 是 approve-all，`rm -rf .` 也会被 policy 拒绝。

这是一个重要边界：

> 用户审批不是绕过 policy；policy deny 是硬拒绝。

## ApprovalHandler 怎么做

源码：

```text
src/pyagentcli/safety/approval.py
```

ApprovalHandler 处理三种情况：

```text
ALLOW -> approved
DENY -> not approved
ASK + non-interactive -> not approved
ASK + interactive -> print preview and ask user
```

交互式审批会展示：

- tool name
- risk level
- reason
- summarized args
- preview

如果用户输入：

```text
y / yes
```

才执行。

非交互模式的行为：

```text
Approval required but session is non-interactive.
```

这很适合 CI、eval 或无人值守场景。

## Preview 为什么重要

写文件之前，用户需要知道会发生什么。

`write_file` preview：

```text
unified diff old file -> new file
```

`edit_file` preview：

```text
unified diff before replacement -> after replacement
```

如果 diff 太长，会截断：

```text
... <diff truncated>
```

这比只问一句：

```text
Approve write_file?
```

安全很多。

真正的 HITL 不是让用户盲批，而是给用户足够上下文做判断。

## edit_file 为什么要求唯一匹配

源码：

```text
EditFileTool._prepare_edit()
```

它要求：

```text
old_text count == 1
```

如果找不到：

```text
old_text was not found in the target file.
```

如果出现多次：

```text
old_text matched N times. Refusing ambiguous edit.
```

这能避免：

```text
把所有 x = 1 都替换成 x = 2
```

而用户本来只想改其中一处。

安全不只是审批，也包括减少误操作面。

## Audit Log 记录什么

源码：

```text
src/pyagentcli/safety/audit_log.py
```

审计日志路径：

```text
.pyagent/audit.log.jsonl
```

每条事件包含：

```text
timestamp
goal
step
tool_name
tool_args
risk_level
decision
ok
error
duration_ms
```

为什么用 JSONL？

- 追加写简单。
- CLI 友好。
- 可以 tail。
- 可以被 eval / reviewer / memory 读取。
- 不需要复杂数据库。

为什么要 redaction？

因为 tool args 里可能有：

- content
- api_key
- password
- token

这些会写成：

```text
<redacted:N chars>
```

## 和 Plan Approval 的关系

在 Plan-and-Execute 里有两层审批：

```text
plan-level approval
tool-level approval
```

plan-level approval：

```text
用户同意执行某个 step
```

tool-level approval：

```text
具体 write_file / edit_file / run_shell 仍然走 safety + preview + approval
```

这避免了一个问题：

> 用户批准了“修改 README”这个 step，但 Executor 在里面尝试运行危险 shell。

所以计划审批不能替代工具审批。

## 和 MCP / Browser / Skill 的关系

MCP：

> MCP 扩展工具来源，但不能绕过 ToolRegistry。

外部 MCP tool 进入 PyAgentCLI 后，也应该映射风险等级，走本地 policy、approval、audit。

Browser：

> 浏览器观察类工具可能是 READ，但交互、截图、网络日志等能力涉及副作用或敏感信息，需要更保守的 risk level 和输出路径限制。

Skill：

> Skill 是 prompt guidance，不是工具权限。

Skill 不能执行工具，不能覆盖用户任务，也不能覆盖 safety policy 或 approval。

## 源码阅读路线

建议按这个顺序看：

1. `src/pyagentcli/tools/base.py`
   - 看 `RiskLevel`、`ToolResult`、`ToolContext`、`Tool` protocol。
2. `src/pyagentcli/tools/registry.py`
   - 看 `ToolRegistry.execute()`。
   - 看 policy、preview、approval、run、audit 的顺序。
3. `src/pyagentcli/safety/policy.py`
   - 看 path guardrail、command deny patterns、risk action。
4. `src/pyagentcli/safety/approval.py`
   - 看 interactive 和 non-interactive 行为。
5. `src/pyagentcli/safety/audit_log.py`
   - 看 JSONL event 和 redaction。
6. `src/pyagentcli/tools/filesystem.py`
   - 看 `write_file` preview。
   - 看 `edit_file` unique old_text。
7. `src/pyagentcli/tools/shell.py`
   - 看 shell command 如何执行在 workspace 内。
8. `tests/test_safety_policy.py`
   - 看路径逃逸、`.env`、危险命令测试。
9. `tests/test_tools.py`
   - 看写文件审批、diff preview、ambiguous edit、approval denial。
10. `src/pyagentcli/evals/runner.py`
   - 看 safety violation 如何进入 eval 指标。

## 我们协作时真实遇到的坑

### 1. 不能把安全写成 prompt 规则

我们一直避免说：

```text
Prompt 会要求模型不要做危险操作
```

这不够。

正确说法是：

```text
Prompt 可以引导，但真正的安全边界在工具执行层。
```

因为模型可能误判、被 prompt injection 影响，或者输出危险 tool call。

### 2. sandbox / GitHub push 限制是现实 HITL

我们开发过程中遇到过网络和设备操作权限限制，导致不能由 Agent 直接完成某些 GitHub push 或桌面操作。

这其实是 HITL 的真实体现：

> 有些动作就应该让用户保留控制权，尤其是网络、账号、浏览器登录态和本机高风险操作。

项目文档里可以把它反补成：

```text
local coding agent needs explicit human approval for external side effects
```

### 3. 写文件审批必须给 diff preview

只问：

```text
Approve write_file?
```

没有意义。

用户需要看到：

```text
- old line
+ new line
```

所以 `write_file` 和 `edit_file` 都实现了 preview。

### 4. skipped step 不能算成功

Plan 里如果某个 WRITE step 被用户拒绝，它会变成 `skipped`。

Reviewer 不能把它当成 success。

这说明 HITL 不只是问用户，也是执行状态的一部分。

### 5. MCP 和 Skill 都要强调不能绕过安全

我们写 MCP 和 Skill 文档时都保留了同一个原则：

```text
MCP extends tools, but does not bypass policy.
Skill gives guidance, but does not grant permission.
```

这让整个系统边界一致。

## 你自己开发时大概率会遇到的坑

### 1. 让模型自己决定是否安全

错误做法：

```text
LLM says command is safe -> run it
```

正确做法：

```text
LLM emits tool call
runtime policy checks risk
approval decides execution
```

模型不能做最终安全裁判。

### 2. 只做审批，不做硬拒绝

如果危险命令也只是问用户：

```text
Approve rm -rf .?
```

那就太脆了。

明确危险命令应该直接 DENY。

审批适合灰区，不适合已知高危行为。

### 3. 路径检查只做字符串判断

错误做法：

```text
if "../" in path: deny
```

这会漏掉很多路径变体。

更稳妥：

```text
resolve()
relative_to(workspace_root)
denylist parts
```

### 4. 审计日志记录敏感内容

如果 `write_file` 的 content 完整进入 audit log，可能泄露代码、secret 或用户数据。

PyAgentCLI 对 `content`、`api_key`、`password`、`token` 做 redaction。

### 5. 非交互模式默认批准

CI 或自动 eval 里，如果 ASK 默认批准，会非常危险。

PyAgentCLI 的做法：

```text
ASK + non-interactive -> denied
```

### 6. `edit_file` 替换多个匹配

如果 old_text 出现多次，一次 replace all 可能改错大量位置。

所以要拒绝 ambiguous edit。

### 7. Shell command 没有 timeout

没有 timeout 的 shell 工具可能卡住整个 Agent。

PyAgentCLI 的 `run_shell` 默认 30 秒，上限 300 秒。

### 8. Shell 在错误目录执行

如果 shell 不固定 cwd，可能在用户 home 或系统目录执行。

PyAgentCLI 把 cwd 固定到 workspace root。

### 9. Preview 失败后继续执行

如果 preview 都生成不了，说明参数或路径可能有问题。

PyAgentCLI 会把 preview failure 变成 ToolResult.failure，并写 audit。

### 10. 外部工具默认放行

MCP、Browser、网络工具的能力范围更难预测。

保守做法：

```text
read-only can be allowed
non-read defaults to deny or ask
network/critical defaults deny
```

## 简历上怎么写

保守可信版：

> 为 PyAgentCLI 构建 HITL 安全执行层，按 READ / WRITE / EXECUTE / NETWORK / CRITICAL 对工具分级，在 ToolRegistry 中统一接入路径围栏、危险命令拒绝、写入/执行审批、diff preview 和 JSONL audit log，降低本地 Coding Agent 自动化文件与命令操作风险。

更技术版：

> 设计 `SafetyPolicy + ApprovalHandler + AuditLogger` 工具执行链路：READ 工具默认允许，WRITE/EXECUTE 工具触发人工审批，危险 shell 命令和敏感路径直接拒绝；`write_file` / `edit_file` 在审批前生成 unified diff preview，`edit_file` 拒绝 ambiguous replacement，所有工具调用落盘到 `.pyagent/audit.log.jsonl` 并对敏感参数脱敏。

不要这么写：

> 实现企业级沙箱和完整权限系统。

除非后续真的实现进程级 sandbox、文件权限矩阵、网络 allowlist、policy config 和审计 UI。

## 面试官会怎么追问

### Q1：Tool Call 是执行吗？

一句话答案：

> 不是。Tool Call 是模型输出的结构化意图，真正执行在本地 runtime。

展开回答：

- 模型输出 tool name 和 args。
- ToolRegistry 找到工具。
- SafetyPolicy 判断风险。
- ApprovalHandler 处理审批。
- Tool.run 才执行真实动作。
- AuditLogger 记录结果。

### Q2：为什么写文件要审批？

一句话答案：

> 写文件会产生真实副作用，用户必须在执行前看到 preview 并保留最终决定权。

展开回答：

- WRITE risk -> ASK。
- `write_file` / `edit_file` 提供 diff preview。
- 非交互模式会拒绝。
- 审批拒绝后不会写文件。

### Q3：shell 工具怎么防危险命令？

一句话答案：

> 先用 policy deny 明确危险命令，再对其他 EXECUTE 命令走审批。

展开回答：

- deny `rm -rf`、`sudo`、`chmod -R`、`curl | sh` 等。
- shell cwd 固定在 workspace。
- timeout 限制 1 到 300 秒。
- 失败结果返回 observation。

### Q4：路径围栏怎么实现？

一句话答案：

> 解析成绝对路径后，要求它仍在 workspace 内，并拒绝敏感目录。

展开回答：

- `(workspace_root / raw_path).resolve()`。
- `relative_to(workspace_root)` 检查逃逸。
- denylist 检查 `.env`、`.git`、`.venv` 等。
- 工具层执行，不依赖 prompt。

### Q5：Plan approval 和 tool approval 有什么区别？

一句话答案：

> Plan approval 批准步骤意图，tool approval 批准具体副作用。

展开回答：

- 用户批准 WRITE step，不代表所有写文件都自动允许。
- 具体工具仍要 preview、policy、approval。
- 这样能防止 Executor 在 step 内做额外高风险操作。

### Q6：审计日志有什么用？

一句话答案：

> 它让 Agent 行为可追踪、可复盘、可评估。

展开回答：

- 记录 goal、step、tool、args、risk、decision、ok、error、duration。
- Reviewer 可以读取 audit log。
- Memory 可以提取 tools/paths。
- Eval 可以统计 safety violations。

### Q7：为什么 NETWORK / CRITICAL 默认拒绝？

一句话答案：

> 外部世界副作用更难预测，v0.1 采取保守默认策略。

展开回答：

- MCP server 可能暴露远程能力。
- 浏览器和网络工具可能涉及登录态或外部请求。
- 没有 allowlist 前默认 deny 更安全。
- 后续可以加显式配置和审批。

### Q8：Skill 会不会绕过安全？

一句话答案：

> 不会。Skill 只是 prompt guidance，不是 tool permission。

展开回答：

- Skill 不执行工具。
- Skill 不覆盖用户任务。
- Skill 不覆盖 safety policy。
- 真正执行仍然走 ToolRegistry。

## 标准回答思路

如果面试官让你整体讲 Tool/HITL/Safety，可以按这个顺序：

1. 先说 Tool Call 是意图，不是执行。
2. 讲执行链路：ToolRegistry -> SafetyPolicy -> ApprovalHandler -> Tool.run -> AuditLogger。
3. 讲风险分级：READ / WRITE / EXECUTE / NETWORK / CRITICAL。
4. 讲路径围栏：resolve + workspace boundary + denylist。
5. 讲命令黑名单：危险命令直接 DENY。
6. 讲 HITL：WRITE/EXECUTE 要 preview 和审批。
7. 讲 audit：JSONL、redaction、Reviewer/Memory/Eval 可复用。
8. 讲边界：不是企业级 sandbox，但已经形成本地 Agent 最小安全层。

一版完整回答：

> 在 PyAgentCLI 里，Tool Call 只是模型输出的工具名和参数，不代表模型能直接执行。真正执行发生在 ToolRegistry：它先根据工具 risk level 调 SafetyPolicy，READ 默认允许，WRITE 需要审批，EXECUTE 会先检查危险命令再审批，NETWORK 和 CRITICAL 在 v0.1 默认拒绝。所有路径都通过 resolve 和 relative_to 做 workspace 围栏，并拒绝 `.env`、`.git`、`.venv` 等敏感路径。写文件和 edit_file 会在审批前生成 unified diff preview，edit_file 还要求 old_text 唯一匹配，避免 ambiguous edit。非交互模式下需要审批的动作默认拒绝。执行结果和失败都会写入 `.pyagent/audit.log.jsonl`，并对 content、token 等参数脱敏。这样模型可以提出动作，但真实副作用由本地 runtime 和用户共同控制。

## 还能继续怎么增强

下一阶段可以增强：

- policy config 文件。
- command allowlist。
- network domain allowlist。
- per-tool approval policy。
- approval cache。
- dry-run mode。
- file permission matrix。
- shell command parser。
- stronger sandbox。
- audit log viewer。
- audit log export。
- approval diff UI。
- risk scoring model。

更工程化的方向：

- 将 policy decision 写入 trace。
- Reviewer 读取 audit log 并指出高风险调用。
- Eval 增加更多 forbidden command cases。
- MCP tool 根据 metadata 自动映射 risk。
- Browser 工具按登录态、网络、截图输出分级。

## 这一篇之后做什么

下一篇进入：

> [Multi-Agent](07_multi_agent.md)

Tool/HITL/Safety 解决的是单个工具调用如何安全落地；Multi-Agent 解决的是复杂任务里 Planner、Executor、Reviewer 如何分工和交接。
