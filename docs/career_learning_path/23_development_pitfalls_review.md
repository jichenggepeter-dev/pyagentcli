# 23 开发复盘：我们真实遇到的问题

这一篇专门复盘 PyAgentCLI 开发过程中遇到的真实问题。

它不是“吐槽记录”，而是把开发中的坑沉淀成：

```text
工程判断
安全边界
排查方法
面试素材
下一步改进方向
```

面试里，项目做了什么很重要；但项目中怎么踩坑、怎么修、怎么避免再踩，往往更能体现工程能力。

## 这一篇怎么读

每个问题都按同一个结构：

```text
现象
原因
我们怎么处理
如果你自己开发会怎么踩坑
面试怎么讲
```

它对应整条学习路线里的所有模块：

- ReAct / Tool Calling。
- Plan-and-Execute。
- Safety / HITL / Audit。
- RAG / Memory。
- Browser / MCP / Skill。
- Reviewer / Eval。
- CLI 产品化。
- 多模型适配。
- GitHub / sandbox / 长上下文协作。

## 总体复盘

PyAgentCLI 的最大难点不是单个函数怎么写，而是这些边界容易混在一起：

```text
模型输出 vs 本地执行
计划预览 vs 实际执行
CLI 入口 vs runtime state
真实模型能力 vs fallback 能力
本地 commit vs 远端 push
文档路线 vs 已落地代码
AI 协作上下文 vs repo 事实
```

所以我们的开发原则逐渐变成：

1. 先确认当前 repo 状态。
2. 把已落地能力写清楚。
3. 未实现能力只写成 roadmap。
4. 每个副作用动作都要有审批或明确边界。
5. 每个长阶段都用文档和 commit 留痕。
6. 出错后先判断错误来自项目、工具、模型还是外部环境。

## 01 长对话和上下文压缩

### 现象

我们这个项目连续聊了很久。

用户也明显感觉到：

```text
上下文变长以后，智能会不会下降？
压缩上下文会不会丢细节？
是不是要 fork 新对话？
```

### 原因

长项目里，上下文会不断累积：

- 产品目标。
- roadmap。
- 已实现模块。
- 用户偏好。
- 文件路径。
- git 状态。
- 已提交 commit。
- 未完成计划。
- 临时错误。

如果这些都只存在聊天里，压缩后就可能丢细节。

### 我们怎么处理

我们把关键状态落到 repo：

```text
docs/roadmap.md
docs/execution_plan_zh.md
docs/career_learning_path/
git commit history
.pyagent/ scheduled handoff
```

继续工作前会检查：

```bash
git status --short --branch
sed -n '...' docs/career_learning_path/00_index.md
sed -n '...' docs/career_resume_interview_zh.md
```

### 如果你自己开发会怎么踩坑

你可能会：

- 只靠聊天记忆推进。
- 忘记前面已经实现了什么。
- 文档写成未来愿景，和代码不一致。
- 改了很多文件但没有 commit。
- 新对话里重新解释半天。

### 面试怎么讲

> 在长周期 AI 协作项目里，我不会只依赖对话上下文，而是把 roadmap、execution plan、学习文档和阶段性 commit 作为项目记忆。这样即使对话压缩或换线程，也能从 repo 事实恢复，而不是靠模型猜。

## 02 文档不能复制教程原文

### 现象

项目一开始参考 PaiCLI 学习路线。

但我们的目标不是复制教程全文，而是：

```text
借鉴项目设计思路
用 Python 从 0 到 1 重写 AI Coding Agent CLI
把文档沉淀成 PyAgentCLI 自己的学习路线
```

### 原因

如果直接复制：

- 版权和原创性有问题。
- Java 项目结构不一定适合 Python。
- 面试时讲不清自己做了什么。
- 文档和 PyAgentCLI 代码会脱节。

### 我们怎么处理

文档采用：

```text
参考栏目节奏
不复制原文
不照搬 Java 实现
全部回到 PyAgentCLI 源码、命令、测试、坑
```

比如：

- 实战篇对应 PyAgentCLI 的 ReAct、Plan、Memory、RAG、Safety。
- 简历篇对应 PyAgentCLI 的真实能力。
- 面试篇对应我们自己的源码追问。
- 复盘篇加入我们开发中真实遇到的问题。

### 如果你自己开发会怎么踩坑

你可能会：

- 把学习路线写成教程摘要。
- 用别人的术语讲自己的项目。
- 简历 bullet 写得很像课程作业。
- 面试时被问源码，答不上来。

### 面试怎么讲

> 这个项目借鉴的是成熟 Agent CLI 教程的学习路线和模块拆分思路，但实现和文档都回到 PyAgentCLI 自己的 Python 代码。比如我不是复述 ReAct 概念，而是能讲 `AgentLoop`、`ToolRegistry`、`SafetyPolicy`、`PlanStore`、`Reviewer` 和 `EvalRunner` 的具体实现。

## 03 GitHub push 和 sandbox 权限

### 现象

本地 commit 可以完成，但 push 到 GitHub 曾经受限：

```text
Could not resolve host: github.com
```

或者需要用户自己在本机 Terminal 操作。

### 原因

GitHub push 涉及：

- 外部网络。
- 账号认证。
- 远端仓库权限。
- sandbox policy。
- 用户设备状态。

这和本地 `git commit` 不是同一类能力。

### 我们怎么处理

我们把流程拆开：

```text
Agent 负责：
  - 检查 git status
  - 只暂存相关文件
  - 本地 commit
  - 告诉用户 ahead N

用户或授权环境负责：
  - git push
  - GitHub 认证
  - 远端确认
```

### 如果你自己开发会怎么踩坑

你可能会：

- 把 commit 和 push 都当成本地操作。
- 忽略认证失败。
- 为了推送绕过安全边界。
- 没有告诉用户本地和远端状态差异。
- 在简历里写“自动 GitHub 发布”，但其实没有做。

### 面试怎么讲

> 我们把本地版本控制和远端副作用分开处理。PyAgentCLI 当前已经能在 Reviewer 里读取本地 git diff 做复核，但没有把自动 push/PR 包装成已实现能力，因为那涉及网络、身份和远端副作用。未来会从只读 status/diff、commit proposal、用户审批后 push 逐步推进。

## 04 Computer Use 不是万能权限

### 现象

用户安装了 Computer Use 插件，希望它直接操作本机启动提交 GitHub。

但桌面自动化对 Terminal 这类高风险应用有限制。

### 原因

Terminal 可以执行任意命令。

如果 AI 自动操作 Terminal：

- 风险极高。
- 很难审计每个动作。
- 容易越过 CLI 工具本身的安全策略。

### 我们怎么处理

我们没有绕过限制，而是回到：

- 本地 repo 状态检查。
- 本地 commit。
- 用户手动 push 或明确授权。

### 如果你自己开发会怎么踩坑

你可能会：

- 以为桌面自动化可以代替 CLI 权限。
- 让 AI 点 UI 来绕过命令审批。
- 忽略桌面操作的审计缺失。

### 面试怎么讲

> Desktop automation 不是无限权限。尤其是 Terminal、GitHub push、登录态网页这类高风险入口，应该把 AI 的能力限制在可审计、可审批的动作里，而不是用 UI 自动化绕过本地安全策略。

## 05 不存在的模型名

### 现象

某次会话里出现：

```text
The model 'gpt-image-2' does not exist.
```

用户要求：

```text
不要调用 gpt-image-2
避开这个不可用模型
检查刚刚改了哪个文件，然后接着完成
```

### 原因

这类错误可能来自：

- 客户端路由。
- 模型名过期。
- 账号没有权限。
- 工具误选模型。
- 外部模型配置漂移。

不一定是 PyAgentCLI 项目代码本身。

### 我们怎么处理

处理顺序是：

1. 不继续调用不可用模型。
2. 回到文本和本地文件工具。
3. 检查 `git status`。
4. 确认刚刚改了哪个文件。
5. 从 repo 事实继续。

### 如果你自己开发会怎么踩坑

你可能会：

- 以为模型报错就是项目 bug。
- 继续重试同一个不可用模型。
- 不检查工作区就继续写。
- 把外部模型问题误写进项目代码。

### 面试怎么讲

> 多模型 Agent 里，模型可用性本身就是工程问题。不能假设模型名永远有效，所以 PyAgentCLI 提供 `--check-model` 做最小 tool-calling 探针；真实模型 eval 也必须显式 opt-in，并保留 disabled reason 或错误信息。

## 06 Plan Preview 不能产生副作用

### 现象

Plan-and-Execute 很容易写成：

```text
生成计划时顺便读写文件或执行命令
```

这样用户还没审批，系统已经产生副作用。

### 原因

很多 Agent 会把 planning 和 acting 混在一起。

但 PyAgentCLI 的 `--plan` 是审查入口，不是执行入口。

### 我们怎么处理

明确拆分：

```text
--plan
  -> 只生成 PlanPreview
  -> 保存 plan artifact
  -> 不执行工具

--execute-plan
  -> 展示计划
  -> 用户审批
  -> Executor 执行 step
  -> Reviewer gate
```

### 如果你自己开发会怎么踩坑

你可能会：

- 让 Planner 直接调用工具。
- 预览阶段修改文件。
- 没有把计划保存起来。
- 失败后不能 resume。

### 面试怎么讲

> Plan Preview 的价值是让用户在副作用发生前看到 Agent 准备做什么，所以它必须是无副作用的。真正执行要进入 `--execute-plan`，并经过审批、step 状态持久化和 Reviewer 复核。

## 07 Reviewer 防止“假成功”

### 现象

计划执行完成后，最终文本可能说：

```text
Task completed.
```

但中间 step 可能是：

```text
failed
skipped
cancelled
```

如果只看最终回答，就会误判成功。

### 原因

Agent 很容易在最后生成一个乐观总结。

但 coding task 是否成功要看：

- step status。
- audit log。
- git diff。
- changed-file risk。
- suggested tests。

### 我们怎么处理

Reviewer 读取：

```text
PlanRun
step status
audit log
git diff
changed files
```

只要出现 blocking status，就给 gate block，并生成 retry proposal。

### 如果你自己开发会怎么踩坑

你可能会：

- 只相信模型最终回答。
- 没有中间状态。
- 没有 review artifact。
- 没有失败恢复建议。

### 面试怎么讲

> 我没有只用最终回答判断任务成功，而是让 Reviewer 基于 PlanRun、step status、audit log 和 git diff 做 gate。如果出现 failed、skipped、cancelled，就算 Agent 文本说完成，也会 block 并给出 retry 或用户决策建议。

## 08 Retry 不是所有失败都重试

### 现象

早期容易把所有非成功状态都处理成：

```text
retry_step
```

但不同状态含义不同。

### 原因

- failed：可能可以重试。
- skipped：通常是用户决策。
- cancelled：可能需要 resume。

如果全都 retry，会让恢复策略错误。

### 我们怎么处理

区分：

```text
failed    -> retry_step
skipped   -> user_decision
cancelled -> resume_plan
```

### 如果你自己开发会怎么踩坑

你可能会：

- 设计一个统一 retry 按钮。
- 不记录失败原因。
- 让用户不知道下一步怎么接管。

### 面试怎么讲

> 失败恢复不是简单 retry。PyAgentCLI 区分 failed、skipped、cancelled，不同状态对应不同恢复动作，这样用户能接管，而不是被 Agent 带着盲目重跑。

## 09 RAG stale index

### 现象

用户修改文件后，RAG index 可能还是旧的。

Agent 如果继续用旧索引，就会基于过期代码回答或修改。

### 原因

RAG 不只是检索，还涉及：

- index 新鲜度。
- 文件 mtime。
- chunk provenance。
- 显式上下文优先级。

### 我们怎么处理

PyAgentCLI 对 stale paths 给出 warning。

不会偷偷自动重建所有 index，因为：

- 可能耗时。
- 可能改变用户预期。
- 用户需要知道检索上下文是否新鲜。

### 如果你自己开发会怎么踩坑

你可能会：

- 只做向量检索。
- 不保存 chunk 来源。
- 不检查文件是否变更。
- 把旧检索结果当成当前事实。

### 面试怎么讲

> RAG 的难点不只是召回，而是上下文可信度。PyAgentCLI 把检索结果和文件路径、chunk、mtime 关联，并在 index 可能过期时提醒用户，避免 Agent 用旧代码做决策。

## 10 Memory 会变成黑箱

### 现象

Memory 如果只能追加，不能查看、删除、压缩或检查 stale，会变成：

```text
模型背后的一团隐形偏好
```

错误记忆会持续影响任务。

### 原因

Memory 是跨任务状态。

它一旦进入 prompt，就可能影响后续输出。

### 我们怎么处理

提供：

```bash
pyagent --memory
pyagent --remember "..."
pyagent --compress-memory
pyagent --delete-memory-line 3
pyagent --stale-memory-days 30
```

并明确：

> Memory 只是辅助上下文，不能覆盖当前用户任务。

### 如果你自己开发会怎么踩坑

你可能会：

- 只实现 append。
- 不给用户查看。
- 不标记 stale。
- 不让用户删除。
- 把 memory 当系统指令。

### 面试怎么讲

> Memory 必须有生命周期管理。PyAgentCLI 不只支持 remember，还支持查看、压缩、删除和 stale 检查，避免长期记忆变成不可控黑箱。

## 11 Browser 工具不能随便上网

### 现象

Browser Tools 如果开放任意 URL，会引入：

- 登录态泄露。
- prompt injection。
- cookie/token 暴露。
- 不可控网络访问。
- 外部网页脚本风险。

### 原因

PyAgentCLI 是本地 Coding Agent，不是通用浏览器代理。

它的浏览器能力主要服务：

- workspace HTML。
- localhost app。
- DOM inspection。
- console/network debugging。
- screenshot artifact。

### 我们怎么处理

默认允许：

```text
workspace file
workspace 内 file URL
localhost
127.0.0.1
::1
```

外部 HTTP/HTTPS 默认拒绝。

### 如果你自己开发会怎么踩坑

你可能会：

- 让浏览器工具访问任意网站。
- 把登录态当成普通上下文。
- 把 screenshot 输出到任意路径。
- 不区分 inspect 和 interact 风险。

### 面试怎么讲

> Browser Tools 的边界不是“能打开网页就行”。PyAgentCLI 采用 local-first 策略，只允许 workspace file 和 localhost 相关目标，交互型 browser tool 需要更高风险等级和审批，截图也限制写到 `.pyagent/browser/`。

## 12 Playwright optional dependency

### 现象

Playwright 能提供截图、console logs、network summaries。

但如果放进默认依赖：

- 安装变慢。
- 浏览器 binary 很重。
- CI 复杂。
- 不做前端任务的用户也要安装。

### 原因

不是所有用户都需要 Browser Tools。

### 我们怎么处理

拆成 optional extra：

```toml
[project.optional-dependencies]
browser = ["playwright>=1.44"]
```

并提供：

```bash
pyagent --check-browser
```

### 如果你自己开发会怎么踩坑

你可能会：

- 把所有高级能力塞进默认依赖。
- 导致安装失败。
- CI 因缺浏览器 binary 失败。
- 用户不知道能力缺在哪里。

### 面试怎么讲

> 我把 Playwright 做成 optional extra，并提供 `--check-browser` 做能力检测，让核心 CLI 保持轻量，同时让浏览器能力可以渐进启用。

## 13 `pytest.importorskip` 的位置

### 现象

早期如果把：

```python
pytest.importorskip("playwright.sync_api")
```

放在测试文件顶部，单独运行该文件时可能出现：

```text
collected 0 items / 1 skipped
exit code 5
```

### 原因

pytest 对“没有收集到测试”和“跳过测试”的退出码处理容易让 CI/本地命令体验变差。

### 我们怎么处理

把 `importorskip` 放进具体测试函数。

这样：

```text
test collected
test skipped
exit code 0
```

### 如果你自己开发会怎么踩坑

你可能会：

- 只看全量测试通过。
- 不单独运行 optional test file。
- CI 上才发现 exit code 不对。

### 面试怎么讲

> optional dependency 的测试不只是 skip 就行，还要保证单文件运行和 CI exit code 合理。我把 importorskip 放到测试函数里，避免没有收集到测试导致命令失败。

## 14 MCP 不能绕过本地安全策略

### 现象

MCP 很容易被理解成：

```text
外部工具接进来后，模型可以直接用
```

### 原因

MCP 扩展的是工具生态，但风险也随之扩大。

外部工具可能：

- 访问网络。
- 读取敏感数据。
- 写外部系统。
- 返回 prompt injection 内容。

### 我们怎么处理

PyAgentCLI 的 MCP v0.1 走 adapter：

```text
MCP tool
  -> risk mapping
  -> preview
  -> ToolRegistry
  -> SafetyPolicy
  -> Approval
  -> Audit
```

### 如果你自己开发会怎么踩坑

你可能会：

- 把 MCP 工具直接暴露给模型。
- 不做 risk classification。
- preview 阶段就调用远端工具。
- 不记录审计。

### 面试怎么讲

> MCP 是工具接入协议，不是权限豁免。PyAgentCLI 会把 MCP 工具适配回本地 ToolRegistry，让它继续经过 risk、preview、approval 和 audit。

## 15 Skill 容易被误解成工具

### 现象

用户或面试官可能会问：

```text
Skill 是不是插件？
Skill 能不能执行工具？
Skill 能不能绕过审批？
```

### 原因

“Skill”这个词听起来像能力扩展。

### 我们怎么处理

PyAgentCLI 明确：

```text
Skill = prompt-only workflow guidance
Tool = executable capability
```

Skill：

- 不执行代码。
- 不调外部服务。
- 不授予权限。
- 不覆盖用户任务。
- 不绕过 safety。

### 如果你自己开发会怎么踩坑

你可能会：

- 把 skill 写成隐形工具。
- 让 skill 影响权限。
- 不限制 skill 数量和长度。
- 不处理 skill trigger 冲突。

### 面试怎么讲

> Skill 是知识复用，不是权限扩展。PyAgentCLI 的 Skill 只是 prompt guidance，真正副作用仍然必须通过 ToolRegistry、安全策略和审批。

## 16 Eval 不能只看最终回答

### 现象

如果 eval 只判断最终文本是否包含某句话，会漏掉很多问题：

- 用了 forbidden tool。
- 没用 expected tool。
- 中途失败但最后说完成。
- 越权访问文件。
- 工具参数错了。

### 原因

Agent 的质量在行为轨迹里，不只在最终回答里。

### 我们怎么处理

Trace Eval 检查：

```text
tool calls
observations
final output
expected tools
forbidden tools
success/failure
```

并把 report 写入 `.pyagent/eval_reports/`。

### 如果你自己开发会怎么踩坑

你可能会：

- 只写 deterministic unit tests。
- 不记录 trace。
- 不检查 forbidden tool。
- 不评估越权。

### 面试怎么讲

> Agent Eval 不能只看最终回答，要看行为轨迹。PyAgentCLI 的 Trace Eval 会检查工具调用、禁止工具、最终输出和 report artifact，帮助发现“答得像成功但行为不对”的问题。

## 17 真实模型 Eval 不能默认开启

### 现象

如果 `pyagent --eval` 默认调用真实模型，会带来：

- API 费用。
- 网络依赖。
- 输出波动。
- CI 不稳定。
- API key 泄露风险。

### 原因

真实模型 eval 和本地 deterministic eval 不是同一类验证。

### 我们怎么处理

默认：

```bash
pyagent --eval
```

不调用外部模型。

真实模型需要：

```bash
pyagent --eval --eval-real-model
pyagent --eval --eval-compare-models
```

### 如果你自己开发会怎么踩坑

你可能会：

- 在 CI 默认跑真实模型。
- 没有 disabled reason。
- 把模型波动当成代码 bug。
- 产生意外费用。

### 面试怎么讲

> 我把真实模型 eval 做成显式 opt-in，默认 eval 只跑本地稳定链路，这样能控制费用和不确定性，同时保留真实模型 trace 验证入口。

## 18 CLI 产品化不是命令越多越好

### 现象

做 CLI 时容易不断加 flag。

但如果没有围绕使用生命周期组织，命令会变乱。

### 原因

产品化不是：

```text
加很多参数
```

而是：

```text
安装、运行、计划、执行、恢复、复核、评估、发布
```

### 我们怎么处理

PyAgentCLI 的 CLI 命令围绕生命周期：

```text
pyagent --help
pyagent "goal"
pyagent
pyagent --plan
pyagent --execute-plan
pyagent --resume-plan
pyagent --retry-step
pyagent --index
pyagent --memory
pyagent --eval
pyagent --check-model
pyagent --check-browser
```

### 如果你自己开发会怎么踩坑

你可能会：

- 只有 run，没有 plan。
- 只有执行，没有恢复。
- 没有 workspace。
- 没有 release checklist。
- 没有 packaging tests。

### 面试怎么讲

> CLI 产品化不是 argparse，而是让 Agent 能被安装、运行、预览、审批、失败恢复、复核和验证。PyAgentCLI 的命令结构就是围绕这个生命周期设计的。

## 19 运行态不能污染源码

### 现象

Agent 会产生很多运行产物：

- plans。
- reviews。
- audit logs。
- memory。
- RAG index。
- eval reports。
- browser screenshots。

如果随便写，会污染项目。

### 原因

运行态和源码是不同东西。

运行态需要：

- 可复盘。
- 可删除。
- 可忽略。
- 可按 workspace 隔离。

### 我们怎么处理

统一放进：

```text
.pyagent/
```

### 如果你自己开发会怎么踩坑

你可能会：

- 把 eval report 写到根目录。
- 把 screenshot 写到用户指定任意路径。
- 不知道哪些文件该 commit。
- 多个 workspace 的 memory 混在一起。

### 面试怎么讲

> 我把 Agent 运行态集中放在 `.pyagent/`，包括 plans、reviews、audit logs、memory、eval reports 和 browser artifacts，这样既方便复盘，也能和源码边界分开。

## 20 简历不能超过实现事实

### 现象

项目 roadmap 很大：

```text
MCP
Browser
Multi-Agent
Runtime API
TUI
GitHub automation
Multimodal
Cost dashboard
```

但不是所有都已经实现。

### 原因

简历如果把 roadmap 写成已完成，会在面试中被追问穿。

### 我们怎么处理

文档里反复区分：

```text
已实现
当前边界
下一步增强
```

比如：

- Runtime API server：未实现。
- GitHub PR automation：未实现。
- Cost dashboard：未实现。
- Browser external web automation：未实现。
- Multi-modal vision model：未实现。

### 如果你自己开发会怎么踩坑

你可能会：

- 把“计划做”写成“已支持”。
- 把 local fallback 当真实模型能力。
- 把 MCP v0.1 写成完整生态。
- 把 Browser capability check 写成完整浏览器代理。

### 面试怎么讲

> 我会把 v0.1 已落地能力和 roadmap 分开讲。已落地的是本地 CLI runtime、工具调用、安全审批、RAG、Memory、Plan/Reviewer、MCP v0.1、Skill、多模型配置和 Eval；Runtime API、GitHub automation、TUI、多模态和 cost dashboard 是后续增强。

## 21 文档要反补开发

### 现象

一开始文档可能只是说明项目。

但随着开发推进，文档开始反过来帮助开发：

- 明确下一步。
- 避免重复讨论。
- 面试素材沉淀。
- 记录坑。
- 校准简历表述。

### 原因

大型 AI Agent 项目很容易发散。

文档能把发散收回来。

### 我们怎么处理

把文档拆成独立章节：

```text
00 index
01-14 实战篇
15 简历篇
16-22 面试篇
23-25 复盘和复习篇
```

每章都能单独进 Obsidian/OCDN。

### 如果你自己开发会怎么踩坑

你可能会：

- 写一个巨大的文档，后面没人读。
- 不分章节，导入知识库很乱。
- 文档没有源码路径。
- 文档不更新。

### 面试怎么讲

> 我把项目文档拆成学习路线、实战、简历、面试和复盘，不只是为了记录，而是用文档反向约束开发范围和简历表述，保证项目讲法和代码事实一致。

## 22 最重要的排查顺序

遇到问题时，不要先猜。

推荐顺序：

```text
1. 看 git status
2. 确认当前 workspace
3. 看刚改了哪些文件
4. 判断错误来自项目代码、模型、工具、sandbox 还是外部网络
5. 先跑最小验证命令
6. 修最小范围
7. 更新文档或测试
8. 单独 commit
```

我们反复使用这个顺序，尤其是在：

- 不存在模型名。
- GitHub push 受限。
- Computer Use 不可操作 Terminal。
- 长对话压缩后继续。
- 文档章节连续生成。

## 必背 10 句

1. 长项目不能只靠聊天上下文，关键状态要落到 repo 文档和 commit。
2. 参考教程可以借鉴结构，但项目文档必须回到自己的源码事实。
3. 本地 commit 和远端 push 是两类能力，不能混讲。
4. Desktop automation 不能绕过 Terminal 和 GitHub 这类高风险权限。
5. 模型名不可用是多模型工程问题，需要 `--check-model` 和清晰错误。
6. Plan Preview 必须无副作用，否则审批就失去意义。
7. Reviewer 要看 step status、audit log 和 git diff，不能只信最终回答。
8. RAG 不只是召回，还要处理 index 新鲜度和上下文可信度。
9. Memory 必须可查看、可删除、可压缩，否则会变成黑箱。
10. 简历必须区分已实现能力和 roadmap。

## 一版完整复盘回答

如果面试官问：

> 这个项目开发中你遇到过哪些坑？怎么解决？

可以这样答：

> 这个项目最大的坑不是某个模块写不出来，而是 Agent 工程里的边界很容易混在一起。比如模型返回 ToolCall 不等于真实执行，所以我把执行统一放到 ToolRegistry、SafetyPolicy、ApprovalHandler 和 AuditLogger；Plan Preview 不等于执行，所以 `--plan` 必须无副作用，`--execute-plan` 才审批后执行；最终回答不等于任务成功，所以 Reviewer 会看 step status、audit log 和 git diff，如果有 failed、skipped、cancelled 就 block。
>
> 第二类坑是上下文和状态。长对话会压缩，所以我们把 roadmap、execution plan、学习文档和 commit history 作为项目记忆；RAG index 可能 stale，所以要提示用户上下文新鲜度；Memory 不能只追加，所以做了查看、压缩、删除和 stale 检查。这样项目不是靠模型记忆推进，而是靠 repo 事实推进。
>
> 第三类坑是外部环境。GitHub push 涉及网络和认证，不能和本地 commit 混讲；Computer Use 不能绕过 Terminal 权限；模型名可能不可用，所以需要 `--check-model` 和真实模型 eval opt-in；Playwright 这类重依赖要做 optional extra。整体上，我学到的是：Agent 项目的工程质量不在于功能堆得多，而在于每个能力都有边界、审计、恢复和验证。

## 复习方式

建议这样复习：

1. 先把 22 个坑扫一遍。
2. 每类挑 1 个能讲 2 分钟的例子。
3. 把“我们怎么处理”和“如果自己开发会怎么踩坑”背熟。
4. 面试时不要讲成抱怨，要讲成工程判断。
5. 最后回到 PyAgentCLI 的源码、命令和文档。

## 下一篇

下一篇：

> 24 一分钟项目介绍和高频追问。

它会把整个 PyAgentCLI 压缩成：

- 15 秒版本。
- 30 秒版本。
- 60 秒版本。
- 简历 bullet 触发追问。
- 面试官连续追问路线。
- 如何把项目讲得可信但不过度包装。
