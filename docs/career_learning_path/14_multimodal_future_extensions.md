# 14 多模态和未来扩展

这一篇是实战篇的收口。

前面我们已经把 PyAgentCLI 的核心链路拆完：

- ReAct / Tool Calling
- Plan-and-Execute
- Memory
- RAG
- Tool Safety
- Multi-Agent
- Browser Tools
- MCP
- Prompt / Skill
- 多模型适配
- CLI 产品化
- Eval / Trace

最后这一篇不继续堆功能，而是回答一个更高级的问题：

> 一个 Python 版 AI Coding Agent CLI，未来应该怎么扩展，哪些可以写进路线，哪些不能提前吹成已完成？

这对简历和面试都很重要。

## 这一篇学什么

你要掌握 8 件事：

1. 当前 PyAgentCLI 已经具备哪些扩展基础。
2. 多模态能力在 Coding Agent 里到底指什么。
3. Browser、截图、视觉理解和 DOM 工具的边界。
4. TUI、Runtime API、Trace Viewer 应该按什么顺序做。
5. GitHub / PR / CI 自动化应该怎么安全扩展。
6. 多模型、成本、token、latency 未来怎么产品化。
7. MCP、Skill、插件生态未来怎么讲。
8. 面试里如何诚实表达“已实现”和“未来规划”。

一句话：

> 未来扩展不是列愿望清单，而是在当前架构上找到自然演进路径，并保持能力边界诚实。

## 当前项目已经有的扩展基础

PyAgentCLI 当前不是完整平台，但它已经有几块很好的基础：

```text
LLMClient abstraction
Tool Registry
Safety Policy
Approval Handler
Audit Log
PlanStore
Reviewer
Eval Harness
RAG index
Project Memory
MCP adapter
Skill Loader
Browser capability check
CLI entrypoints
.pyagent runtime state
```

这些基础意味着后续可以继续扩展。

但要讲清楚：

```text
有扩展基础 != 已经实现完整能力
```

比如：

- 有 `LLMClient`，不等于已经有自动 model router。
- 有 `Browser Tools`，不等于已经有完整网页自动化 Agent。
- 有 `MCP adapter`，不等于兼容全部 MCP 生态。
- 有 `.pyagent/`，不等于已经有 Runtime API server。
- 有 trace eval， 不等于已经有可视化 dashboard。
- 有 optional Playwright， 不等于已经有视觉模型。

这一点是最后一篇的核心。

## 多模态在 Coding Agent 里是什么

很多人一听多模态，会想到：

```text
图片输入
截图理解
视频理解
语音输入
文件上传
```

但对 Coding Agent 来说，多模态更具体。

它可以包括：

### 1. Screenshot Understanding

例如：

```text
用户给一张网页截图
Agent 判断按钮错位
定位前端 CSS 问题
建议修改组件
```

这需要：

- 截图工具。
- 视觉模型。
- DOM / accessibility tree。
- 代码检索。
- 前端测试。
- diff review。

不是只把图片丢给模型。

### 2. UI Regression Debugging

例如：

```text
跑 Playwright
截图 before/after
检查 layout shift
检查文字溢出
检查按钮不可点击
```

这需要：

- 浏览器自动化。
- screenshot artifact。
- visual comparison。
- selector assertion。
- console log capture。
- network log capture。

### 3. Document / PDF Understanding

例如：

```text
读取需求 PDF
提取 API contract
生成实现计划
对照代码修改
```

这需要：

- 文件解析。
- OCR 或结构化 parser。
- chunking。
- RAG。
- citation / provenance。

### 4. Design-to-Code

例如：

```text
输入 UI 截图或设计图
生成 React/Vue/HTML 实现
用 browser 测试
修复视觉差异
```

这需要：

- image input。
- visual grounding。
- frontend code tools。
- browser verification。
- screenshot diff。

### 5. Terminal / Browser / App State

更广义的多模态还包括：

```text
终端输出
浏览器截图
网页 DOM
本地文件
日志
测试报告
Git diff
```

这些不是图片，但都是模型上下文的一部分。

所以 Coding Agent 的多模态本质是：

> 把不同来源的开发环境证据转成 Agent 可检索、可引用、可验证的上下文。

## PyAgentCLI 当前和多模态的关系

当前 PyAgentCLI 已经有一点多模态前置能力：

- `tools/browser.py` 有 browser capability check。
- Browser 篇已经定义 local HTML / localhost inspection 的路线。
- Eval 篇规划了 browser assertion eval。
- RAG 可以处理文件和 symbol context。
- Tool system 可以扩展 screenshot / inspect / OCR 工具。
- `.pyagent/` 可以存 browser artifacts。
- LLMClient 后续可以扩展 vision model。

但当前还没有：

- vision model client。
- screenshot understanding。
- image input CLI。
- OCR pipeline。
- screenshot diff eval。
- design-to-code workflow。
- browser interaction eval。

所以简历里不能写：

```text
已实现多模态 Coding Agent
```

更准确的写法是：

```text
预留多模态扩展路径，已在 Browser、Tool Registry、Trace Eval 和 LLMClient 层保留能力边界。
```

## 多模态扩展路线

如果继续做，建议按 5 个阶段走。

### 阶段 1：截图采集

先不要急着上视觉模型。

先做：

```text
browser_screenshot
save artifact to .pyagent/browser/
return path + metadata
```

metadata 包括：

```text
url
viewport
timestamp
selector
image_path
console_errors
```

这一步只解决：

> Agent 能拿到可复盘的页面证据。

### 阶段 2：DOM + Screenshot 联合上下文

截图很直观，但它不可检索。

所以要同时保存：

```text
DOM snapshot
accessibility tree
console logs
network summary
screenshot path
```

这样模型可以同时看：

- 页面长什么样。
- DOM 结构是什么。
- console 有没有错误。
- selector 是否存在。

### 阶段 3：视觉模型分析

再接入 vision model。

输入：

```text
screenshot
DOM summary
user issue
related files from RAG
```

输出：

```text
visual findings
suspected components
recommended code areas
test suggestions
```

注意：

> 视觉模型只做分析，不直接改文件。

改文件仍然要走 Tool Registry、Safety、Approval、Audit。

### 阶段 4：Visual Eval

多模态不能只靠主观判断。

要加 eval：

```text
screenshot nonblank
selector visible
text not clipped
button clickable
console errors absent
visual diff threshold
```

这和第 13 篇 Eval Harness 对齐。

### 阶段 5：Design-to-Code Workflow

最后才做完整 design-to-code。

流程：

```text
input image
  -> visual analysis
  -> plan
  -> code retrieval
  -> edit
  -> browser render
  -> screenshot compare
  -> reviewer
  -> eval report
```

这才是一个工程闭环。

## Browser 深度自动化路线

当前 Browser 是 local-first 能力。

未来可以扩展：

```text
inspect_page
query_selector
click
type
press
wait_for_selector
get_console_logs
get_network_errors
take_screenshot
assert_text
assert_visible
```

但每一步都要考虑风险。

例如：

```text
click
type
submit form
navigate external URL
download file
upload file
```

这些风险等级不同。

建议分级：

```text
READ      inspect DOM, read title, screenshot
INTERACT  click/type local page
NETWORK   external navigation
WRITE     upload/download local files
CRITICAL  authenticated destructive actions
```

Browser Agent 最容易踩的坑是：

> 登录态页面里的一次点击，可能产生真实副作用。

所以 Browser Tools 必须复用 Safety Policy、Approval、Audit。

## TUI 路线

CLI 很适合 v0.1。

但随着功能变多，TUI 会更自然。

TUI 可以显示：

```text
左侧：plan steps
中间：conversation / trace
右侧：tool calls / diffs
底部：approval prompt
```

它能解决：

- 命令太多。
- approval 不够直观。
- diff review 不方便。
- plan resume/retry 不够可视。
- trace 太长。

但 TUI 不应该太早做。

推荐顺序：

```text
CLI flags
  -> subcommands
  -> JSON output
  -> trace event model
  -> TUI
```

否则 TUI 只是漂亮壳。

## Runtime API 路线

第 12 篇已经讲过，当前没有 Runtime API server。

未来可以抽成：

```text
AgentRunService
PlanService
MemoryService
EvalService
IndexService
ApprovalService
```

再暴露：

```text
POST /runs
GET /runs/{id}
GET /runs/{id}/events
POST /plans
POST /plans/{id}/approve
POST /plans/{id}/resume
POST /evals
GET /evals/{id}
```

但真正核心是事件模型：

```text
run.started
llm.requested
llm.responded
tool.requested
tool.approval_required
tool.approved
tool.denied
tool.completed
tool.failed
plan.created
step.started
step.completed
review.completed
run.completed
```

有事件模型，才能做：

- streaming UI。
- trace viewer。
- web dashboard。
- human approval UI。
- eval replay。
- multi-agent orchestration。

## GitHub / PR 自动化路线

未来很自然会接 GitHub。

但要小心顺序。

建议路线：

### 阶段 1：只读 Git 工具

```text
git_status
git_diff_summary
git_branch
git_log
```

风险低，适合作为 READ 工具。

### 阶段 2：Commit 辅助

```text
propose_commit_message
preview_git_add
git_add_selected
git_commit_after_approval
```

这里开始有副作用，需要审批。

### 阶段 3：GitHub 只读

```text
list_prs
read_issue
read_pr_comments
read_ci_status
```

网络工具，默认要更谨慎。

### 阶段 4：PR 创建

```text
create_draft_pr
update_pr_description
comment_on_pr
```

需要外部权限和审计。

### 阶段 5：Merge / Release

这属于高风险。

应该默认不自动执行，或者必须强 HITL。

这也解释了我们之前为什么不能把 GitHub push 当成普通文件操作。

## 成本和可观测路线

多模型之后，成本和 latency 会变重要。

未来每次 LLM 调用应该记录：

```text
run_id
role
model
provider
input_tokens
output_tokens
estimated_cost
latency_ms
cache_hit
```

每次工具调用记录：

```text
tool_name
risk_level
duration_ms
ok
error
approval_required
```

每次 RAG 检索记录：

```text
query
retriever
hit_count
top_path
score
index_freshness
```

这样才能回答：

- 哪个模型性价比最高？
- 哪类任务最贵？
- 哪些工具最容易失败？
- RAG 是否真的帮到了任务？
- Reviewer 是否降低了假成功？

## MCP / Skill 生态路线

MCP 和 Skill 是扩展生态的两条线。

### MCP

MCP 解决：

```text
外部可执行工具
外部数据源
协议化 tool discovery
```

未来要补：

- resource support。
- prompts support。
- streaming。
- OAuth / auth。
- server health check。
- tool capability metadata。
- MCP audit summary。

### Skill

Skill 解决：

```text
任务流程 guidance
项目约定
最佳实践
```

未来要补：

- global skills。
- skill priority。
- skill conflict detection。
- skill eval。
- skill provenance in trace。
- skill templates。

两者区别不能混：

```text
MCP 是工具协议
Skill 是 prompt guidance
```

## Multi-Agent 未来路线

当前 Multi-Agent 是：

```text
Planner
Executor
Reviewer
```

未来可以扩展：

```text
Researcher
Test Writer
Security Reviewer
Performance Reviewer
Release Manager
```

但不要变成“角色越多越好”。

每加一个 Agent，都要回答：

- 输入是什么？
- 输出是什么？
- 谁审批？
- 谁拥有最终决定权？
- 失败怎么恢复？
- trace 怎么记录？
- eval 怎么衡量？

如果回答不了，就不该加。

## 当前项目完成度怎么讲

现在可以这样讲：

> PyAgentCLI 已经完成了本地 AI Coding Agent CLI 的核心 runtime：ReAct/tool calling、文件/命令/搜索工具、安全审批、RAG、Memory、Plan-and-Execute、Reviewer、MCP v0.1、Skill、Browser capability、LLMClient、多模型 eval、Trace Eval 和 CLI 产品化。它目前是本地 CLI，不是完整云平台；多模态、TUI、Runtime API、GitHub PR automation、cost dashboard 和完整 browser automation 是后续扩展方向。

不要这样讲：

```text
已经实现完整多模态 Coding Agent
已经实现 Claude Code 全量能力
已经支持所有 MCP server
已经有自动 PR/merge 能力
已经有完整 Runtime API
```

诚实边界反而更专业。

## 我们开发时遇到的坑

### 坑 1：未来能力容易写得太满

做 Agent 项目时，很容易把 roadmap 写成：

```text
多模态
自动浏览器
MCP
多 Agent
自动 PR
云端平台
```

看起来很强，但如果没有落地事实，面试时会被追问穿。

所以我们这组文档一直坚持：

- 当前实现。
- 当前边界。
- 后续增强。

### 坑 2：工具能力和模型能力容易混

比如截图工具、视觉模型、浏览器 DOM、前端代码修改，是四个不同层。

不能说：

```text
有截图 = 有多模态 Agent
```

更准确是：

```text
截图是多模态 evidence capture 的第一步
```

### 坑 3：自动化外部系统风险更高

GitHub、浏览器登录态、外部 MCP server 都有真实副作用。

所以扩展不是“多接工具”。

而是：

```text
先接只读
再接低风险写入
再接审批
再接审计
最后才接自动化
```

### 坑 4：定时任务不能自动恢复 Codex 写作

我们刚刚也遇到了一个现实问题：

> cron 可以提醒和写文件，但不能让 Codex 自动恢复未来任务。

这其实也是产品化教训：

- 本地 OS 定时任务和 Agent runtime 是两回事。
- macOS cron 不如 launchd 稳定。
- 任务恢复需要明确 handoff。
- 不能把“提醒”包装成“自动继续执行”。

这个坑应该写进复盘。

### 坑 5：上下文压缩不能替代项目状态

长对话会压缩，但项目不能只存在聊天里。

所以我们沉淀到：

- docs。
- git commit。
- roadmap。
- execution plan。
- Obsidian。
- `.pyagent/`。

这也是未来 Runtime API / trace viewer 的必要性。

## 如果你自己开发会遇到的坑

### 坑 1：把未来路线写成简历事实

比如你只做了 CLI，却写：

```text
实现企业级多模态 Agent 平台
```

面试官一问：

- vision model 怎么接？
- screenshot eval 怎么做？
- trace viewer 在哪？
- runtime API schema 是什么？

就会露馅。

更好的写法是：

```text
完成本地 CLI runtime，并为多模态、Runtime API 和浏览器自动化预留扩展边界。
```

### 坑 2：一上来做平台，不先做 CLI

如果先做 Web dashboard，核心 Agent loop 还不稳，项目会变成空壳。

更好顺序：

```text
CLI
Tool Runtime
Safety
RAG/Memory
Plan/Reviewer
Eval/Trace
Runtime API
Dashboard/TUI
```

### 坑 3：多模态只接图片，不接验证

只让模型看图，不做 browser render 和 screenshot eval，很难保证结果。

多模态 Coding Agent 必须闭环：

```text
看图
改代码
跑页面
截图
比较
复核
```

### 坑 4：浏览器工具没有权限分级

`click` 和 `read title` 风险完全不同。

如果全部当普通工具，容易出事故。

### 坑 5：多 Agent 变成多人聊天

更多角色不等于更强。

如果没有 contract、handoff、gate 和 eval，多 Agent 只会增加混乱。

### 坑 6：没有可观测数据就谈优化

想优化模型成本、延迟和成功率，必须先记录数据。

否则都是感觉。

## 简历上怎么写

偏稳健版本：

> 从 0 到 1 构建 PyAgentCLI 本地 AI Coding Agent CLI，完成 ReAct/tool calling、安全工具执行、RAG、Memory、Plan-and-Execute、Reviewer、MCP v0.1、Skill、Browser capability、LLMClient、多模型评估和 Trace Eval，并为多模态、Runtime API、TUI、GitHub PR automation 和成本可观测预留扩展边界。

偏 AI Agent 平台版本：

> 设计 PyAgentCLI 的可扩展 Agent Runtime 架构：以 Tool Registry、Safety Policy、Audit Log、PlanStore、Eval Harness 和 `.pyagent/` 本地运行态为核心，为后续接入视觉模型、浏览器截图分析、Runtime API、Trace Viewer、MCP 工具生态和多模型成本治理提供演进路径。

偏面试诚实版本：

> 当前项目重点落在本地 CLI runtime 和评估闭环，多模态和 Runtime API 尚未完整实现；我已经在 LLMClient、Browser Tool、Trace Eval、Tool Registry 和本地 artifact 存储层预留扩展点，下一阶段会先做截图采集、DOM/screenshot 联合上下文和 browser assertion eval，而不是直接宣称完整多模态。

## 面试官会怎么追问

### Q1：你们项目支持多模态了吗？

一句话答案：

> 当前还不是完整多模态 Agent，但已经有 Browser、Tool Registry、LLMClient 和 Trace Eval 等扩展基础。

展开回答：

- 当前主要是文本和代码上下文。
- Browser 支持 local inspection/capability check。
- 未来可加 screenshot tool。
- 再接 vision model。
- 最后加 visual eval。

### Q2：多模态 Coding Agent 最难的是什么？

一句话答案：

> 难点不是看图，而是把视觉证据、DOM、代码修改、浏览器验证和评估闭环接起来。

展开回答：

- screenshot 只是证据。
- DOM 提供结构。
- RAG 找相关代码。
- tool runtime 改文件。
- browser render 验证。
- eval 判断结果。

### Q3：为什么不先做 TUI？

一句话答案：

> 因为 TUI 应该建立在稳定 runtime、trace event 和 approval model 上，否则只是 UI 壳。

展开回答：

- 先 CLI。
- 再 JSON output。
- 再 event model。
- 再 TUI。

### Q4：Runtime API 当前是什么状态？

一句话答案：

> 当前没有独立 HTTP server，但 CLI 背后已有 run/plan/eval/memory/index 函数入口，可作为服务层雏形。

展开回答：

- 未来要抽 AgentRunService。
- 核心是事件模型。
- endpoint 不是第一步。

### Q5：GitHub 自动化为什么要谨慎？

一句话答案：

> 因为 GitHub push、PR、merge 都涉及外部平台状态和真实协作副作用，不能和本地读文件同风险处理。

展开回答：

- 先只读。
- 再 commit proposal。
- 再审批 push。
- merge/release 强 HITL。

### Q6：MCP 和 Skill 未来怎么扩展？

一句话答案：

> MCP 扩展外部工具生态，Skill 扩展任务流程 guidance，两者都要进入 trace 和 eval。

展开回答：

- MCP 要 health check、capability metadata、audit。
- Skill 要 priority、conflict detection、provenance。

### Q7：多 Agent 未来还能怎么做？

一句话答案：

> 可以增加 Researcher、Test Writer、Security Reviewer 等角色，但每个角色都必须有 contract、handoff、gate 和 eval。

展开回答：

- 不追求角色数量。
- 追求职责边界。
- 追求可评价输出。

### Q8：怎么讲未来路线才不虚？

一句话答案：

> 把已实现、已预留和未来计划分开讲，并说明下一步最小可落地 slice。

展开回答：

- 已实现：CLI runtime、tools、safety、RAG、memory、eval。
- 已预留：LLMClient、ToolRegistry、Browser、Trace。
- 下一步：screenshot tool + browser assertion eval。
- 不说完整多模态已完成。

## 标准回答思路

如果面试官问“后续怎么扩展”，可以这样回答：

> 我不会直接把 PyAgentCLI 包装成已经完成的多模态平台。当前它已经完成的是本地 AI Coding Agent CLI runtime，包括 tool calling、安全审批、RAG、Memory、Plan/Reviewer、MCP v0.1、Skill、多模型适配和 Eval/Trace。未来扩展我会按最小闭环推进：多模态先从 browser screenshot artifact 开始，再做 DOM/screenshot 联合上下文，然后接 vision model，最后加入 browser assertion 和 screenshot diff eval。Runtime API 也不是先做 HTTP 壳，而是先定义 run event model，把 llm、tool、approval、plan、review、eval 都变成可订阅事件。GitHub 自动化会从只读 git status/diff 开始，再到 commit proposal，push 和 PR 必须强审批。这样路线既能从当前架构自然演进，也不会把未实现能力提前吹成事实。

## 还能继续怎么增强

实战篇结束后，下一阶段可以进入面试篇。

建议顺序：

1. ReAct、Plan-and-Execute、Multi-Agent。
2. Memory、RAG、长上下文工程。
3. Tool Call、HITL、安全策略。
4. MCP、Browser Tools、CDP 思路。
5. Prompt 分层、Skill 系统、提示词工程。
6. CLI 产品化、Git、Runtime API。
7. 多模型适配、运行时切换、成本控制。

每篇面试文档继续沿用：

```text
面试官为什么问
简历哪句话会触发
一句话答案
展开回答
落到 PyAgentCLI
边界和不足
追问变体
必背表达
```

## 实战篇收口

到这一篇，PyAgentCLI v2 学习路线的实战篇已经形成完整闭环：

```text
运行项目
  -> ReAct / Tool Calling
  -> Plan-and-Execute
  -> Memory
  -> RAG
  -> Safety / HITL
  -> Multi-Agent
  -> Browser
  -> MCP
  -> Prompt / Skill
  -> Multi-model
  -> Productization
  -> Eval / Trace
  -> Future Extensions
```

这条路线的价值不是把所有概念堆在一起。

而是你能讲清楚：

- 为什么要做。
- 当前怎么实现。
- 源码在哪里。
- 命令怎么跑。
- 开发时踩了什么坑。
- 自己开发会踩什么坑。
- 简历怎么写。
- 面试怎么答。
- 未来怎么扩展。

下一步进入：

> 面试篇第一弹：ReAct、Plan-and-Execute、Multi-Agent
