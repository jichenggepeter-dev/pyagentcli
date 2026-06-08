# PyAgentCLI 学习路线 v2 设计稿

这份文档用于重构 PyAgentCLI 的学习路线、简历篇和面试篇。它不是最终正文，而是新版写作总规划。

## 1. Computer Use 阅读复盘

这次重新用 Computer Use 阅读 PaiCLI 登录态页面时，遇到了几个真实问题。这些问题本身也值得写进 PyAgentCLI 的开发复盘，因为它们正好说明浏览器工具、桌面自动化和登录态读取之间的边界。

### 1.1 一开始能看到 Safari，但不能稳定操作

现象：

- `get_app_state("Safari")` 可以读到 Safari 当前页面标题、URL 和截图。
- 但早期点击和滚动多次返回 `noWindowsAvailable`。
- 这导致页面能看见，但不能稳定翻页或点击左侧目录。

原因判断：

- Computer Use 读屏和 UI 操作不是同一条能力链路。
- 当 Safari 不是前台应用，或者焦点被其他应用占用时，Computer Use 可能能抓到窗口状态，但不能对窗口执行滚动/点击。

本次解决方式：

- 先用 `list_apps` 发现前台应用其实是 Screen Studio。
- 再用 `osascript` 把 Safari 激活到前台。
- 激活后，Computer Use 能更稳定地读取 HTML content 和链接结构。

对 PyAgentCLI 的启发：

> 浏览器能力不能只看“能不能截图”，还要区分窗口激活、DOM 读取、滚动、点击、登录态访问和页面脚本权限。

### 1.2 登录态页面不能直接靠普通网页抓取

现象：

- 用户已经在 Safari 登录。
- 普通网络抓取无法自动继承 Safari cookie。
- 如果只用公开搜索或普通浏览，很可能只能看到试读内容或旧内容。

本次解决方式：

- 使用 Computer Use 读取用户 Safari 中已登录页面。
- 只做阅读和结构提炼，不复制付费内容全文。
- 通过页面可访问性树读取标题、目录链接、部分正文和右侧目录。

对 PyAgentCLI 的启发：

> 登录态浏览器能力和普通 HTTP 抓取是两种不同能力。前者依赖用户本地浏览器状态，后者依赖网络请求和 cookie 管理。

### 1.3 Safari Apple Events 读取正文需要额外设置

尝试：

- 用 `osascript` 调 Safari 的 `do JavaScript` 读取 `document.body.innerText`。

结果：

- Safari 返回错误：需要开启 `Allow JavaScript from Apple Events`。

这说明：

- 即使本地 Safari 已登录，脚本读取网页正文也受到浏览器安全设置限制。
- 不应该绕过这个限制。

本次处理：

- 没有要求用户立即修改 Safari 设置。
- 改为继续使用 Computer Use 的可访问性树读页面结构。

对 PyAgentCLI 的启发：

> 浏览器工具应该清楚标注能力前提，比如是否需要用户授权、是否能执行页面脚本、是否只是只读 DOM snapshot。

### 1.4 Computer Use 每次交互前需要重新获取状态

现象：

- 有几次滚动/点击报错：必须先调用 `get_app_state`。
- 这说明 Computer Use 的操作上下文不是永久有效的。

本次解决方式：

- 后续每次操作前先重新 `get_app_state`。
- 尽量减少连续 UI 操作，优先读取当前页可访问性树。

对 PyAgentCLI 的启发：

> 浏览器/桌面自动化工具需要“状态刷新”机制，不能假设上一次页面状态仍然可用。

### 1.5 可访问性树适合提炼结构，不适合复制全文

本次真正读到的信息包括：

- 页面标题。
- 左侧教程目录。
- 右侧文章目录。
- 部分正文开头。
- 简历篇核心 bullet。
- 面试篇每一弹的主题和题目组织方式。

但它不适合：

- 长篇逐字搬运。
- 复制付费内容全文。
- 把图片里的所有细节解析出来。

本次写作原则：

> 只提炼结构、学习节奏、主题顺序和写法方法，不复制原文。PyAgentCLI 文档必须围绕我们自己的 Python 项目事实重写。

## 2. 已确认的 PaiCLI 结构

### 2.1 实战篇

本次在登录态页面里确认到的实战篇目录包括：

1. PaiCLI 学习路线
2. ReAct 和 tool call
3. plan 和 DAG
4. Memory 系统
5. Multi-Agent
6. RAG 代码检索
7. 人工审批
8. 多并发
9. 联网搜索
10. 接入 MCP
14. 多模态

其中 11-13 因为左侧目录中间滚动不稳定，本次没有完整确认，后续继续补齐。

### 2.2 简历篇

已确认：

15. PaiCLI 如何写简历

这篇不是泛泛讲“简历技巧”，而是直接给：

- 项目名称和时间范围。
- 项目描述。
- 技术栈。
- 核心职责。
- 大量可以直接进入简历的项目 bullet。

对 PyAgentCLI 的启发：

> 简历篇应该先给一份完整项目经历，再逐条拆解每个 bullet 背后的实现、追问和风险边界。

### 2.3 面试篇

已确认：

16. ReAct + plan + Multi-Agent
17. Memory 与 Context
18. tool call 和 HITL
19. MCP + CDP
20. Prompt 与 Skill
21. TUI、LSP、Git、Runtime API
22. 多模型和提示词缓存

这些文章的共同结构是：

- 标题写清楚“第几弹 + 主题 + 题数”。
- 开头用面试官追问简历的方式引出问题。
- 每篇围绕一个大主题，拆成 12-13 个高频问题。
- 每个问题不是只给定义，而是解释原理、工程实现、边界、常见追问。

对 PyAgentCLI 的启发：

> 面试篇应该拆成多弹专题，而不是把所有问题混在一个大 FAQ 里。

## 3. v1 文档的问题

当前 PyAgentCLI 文档 v1 的优点：

- 已经把大文档拆成多个页面。
- 已覆盖简历、面试、复盘、知识库卡片。
- 内容基于 PyAgentCLI 当前已经落地的真实功能。

但问题是：

- 更像项目总结资料包，不够像学习路线。
- 实战篇不够强，没有逐模块写“怎么学、怎么跑、怎么改、怎么讲”。
- 简历篇还不够像完整项目经历，bullet 和追问没有充分绑定。
- 面试篇分组太粗，没有按“第一弹、第二弹”组织。
- 产品化能力不足，TUI、Git、Runtime API、多模型、成本控制这些还没独立成章。
- 开发过程真实问题集中在复盘篇，没有穿插到每个实战模块。

因此 v2 目标不是小修 v1，而是重构学习路线。

## 4. v2 总体定位

v2 的定位：

> PyAgentCLI 项目学习路线：从跑通 Python 版 AI Coding Agent CLI，到吃透 Agent Runtime 核心模块，再把它写进简历、讲进面试、沉淀成长期知识库。

v2 的核心读者是：

- 想把 PyAgentCLI 写进简历的开发者。
- 想通过 PyAgentCLI 学 AI Agent 工程的人。
- 想准备 AI Agent / 后端 / 开发者工具岗位面试的人。
- 未来的自己，用 Obsidian 复习项目时能快速找回上下文。

v2 的写法原则：

- 不复制 PaiCLI 原文。
- 不照搬 Java 实现。
- 只借鉴学习路线、栏目节奏和问题组织方式。
- 所有实现细节回到 PyAgentCLI 当前 Python 项目。
- 对还没实现的能力必须标注为“可增强方向”，不能写成已完成事实。

## 5. v2 学习节奏

### 5.1 第一天：跑通和写简历

目标：

- 本地安装 PyAgentCLI。
- 跑通 CLI、eval、plan、browser check。
- 理解项目一句话。
- 写出第一版简历项目描述和 3-5 条 bullet。

对应页面：

- 00 学习路线总览
- 01 先跑通 PyAgentCLI
- 15 PyAgentCLI 如何写简历
- 24 一分钟项目介绍

### 5.2 第一周：吃透核心 Agent Runtime

目标：

- ReAct 和 Tool Calling。
- Plan-and-Execute。
- Memory。
- RAG。
- Safety / HITL。
- Reviewer / Eval。

对应页面：

- 02 ReAct 和 Tool Calling
- 03 Plan-and-Execute / DAG
- 04 Memory 系统
- 05 RAG 代码检索
- 06 Tool Call / HITL / Safety
- 13 Eval Harness / Trace Eval

### 5.3 第二周：补高级能力和面试深挖

目标：

- Multi-Agent。
- MCP。
- Browser。
- Prompt / Skill。
- 多模型。
- 产品化。
- 面试专题问答。

对应页面：

- 07 Multi-Agent
- 08 Browser / 联网搜索
- 09 MCP
- 10 Prompt 分层和 Skill System
- 11 多模型适配
- 12 产品化：CLI UX / Git / Runtime API
- 16-22 面试专题

## 6. v2 目录规划

### 总览篇

```text
00 PyAgentCLI 学习路线总览
01 先跑通 PyAgentCLI：安装、命令、演示、自检
```

### 实战篇

```text
02 ReAct 和 Tool Calling
03 Plan-and-Execute / DAG
04 Memory 系统
05 RAG 代码检索
06 Tool Call、HITL 和安全策略
07 Multi-Agent
08 Browser Tools 和联网搜索
09 接入 MCP
10 Prompt 分层和 Skill System
11 多模型适配和 LLM Client
12 产品化：CLI UX、Git、Runtime API
13 Eval Harness 和 Trace Eval
14 多模态和未来扩展
```

### 简历篇

```text
15 PyAgentCLI 如何写到简历上
```

### 面试篇

```text
16 面试题第一弹：ReAct、Plan-and-Execute、Multi-Agent
17 面试题第二弹：Memory、RAG、长上下文工程
18 面试题第三弹：Tool Call、HITL、安全策略
19 面试题第四弹：MCP、Browser Tools、CDP 思路
20 面试题第五弹：Prompt 分层、Skill 系统、提示词工程
21 面试题第六弹：CLI 产品化、Git、Runtime API
22 面试题第七弹：多模型适配、运行时切换、成本控制
```

### 复盘篇

```text
23 开发复盘：我们真实遇到的问题
24 一分钟项目介绍和高频追问
25 知识库卡片和复习路线
```

## 7. 每篇文章的标准模板

每篇实战篇使用同一个模板：

```text
这一篇学什么
为什么 Agent CLI 需要这个模块
PyAgentCLI 当前实现了什么
对应源码和命令
最小运行例子
源码阅读路线
我们开发时遇到的坑
简历上怎么写
面试官会怎么追问
标准回答思路
还能继续怎么增强
```

每篇面试篇使用同一个模板：

```text
这一弹考什么
面试官为什么会问
简历里哪句话会触发这个追问
问题 01
  - 先给一句话答案
  - 再讲原理
  - 再落到 PyAgentCLI
  - 最后讲边界和不足
问题 02...
最后：本弹必背 5 句
```

## 8. PyAgentCLI 与 PaiCLI 的映射关系

| PaiCLI 主题 | PyAgentCLI v2 对应主题 | 说明 |
| --- | --- | --- |
| ReAct 和 tool call | ReAct 和 Tool Calling | 映射到 `AgentLoop`、LLM tool call、ToolRegistry |
| plan 和 DAG | Plan-and-Execute / DAG | PyAgentCLI 有 plan preview、execute、resume、retry、Reviewer gate；DAG 可作为增强方向 |
| Memory 系统 | Memory 系统 | 映射到 project memory、session summary、compress、delete、stale check |
| Multi-Agent | Multi-Agent | 映射到 Planner / Executor / Reviewer / handoff |
| RAG 代码检索 | RAG 代码检索 | 映射到 SQLite FTS、AST chunk、import graph、embedding provider |
| 人工审批 | Tool Call、HITL 和安全策略 | 映射到 SafetyPolicy、ApprovalHandler、audit log |
| 多并发 | 并发执行和任务恢复 | 当前 PyAgentCLI 可讲 plan state 和 retry；并发执行作为后续增强 |
| 联网搜索 | Browser Tools 和联网搜索 | 当前有 local-first browser tools；外部联网搜索作为增强 |
| 接入 MCP | MCP | 映射到 stdio MCP client、tools/list、tools/call、adapter |
| 多模态 | 多模态和未来扩展 | 当前不写成已完成，只写扩展方向 |
| Prompt 与 Skill | Prompt 分层和 Skill System | 映射到 prompts、skill loader、prompt-only guidance |
| TUI / LSP / Git / Runtime API | 产品化 | 当前已有 CLI、release、eval；TUI/LSP/Runtime API 标注增强 |
| 多模型和提示词缓存 | 多模型适配和 LLM Client | 映射到 OpenAI-compatible client、model config、fallback；prompt cache 标注增强 |

## 9. 我们自己的开发经历要如何反补进去

每个模块都要插入“真实开发复盘”，而不是只放到最后。

示例：

- Browser 篇：写 Computer Use 能读 Safari 但点击/滚动不稳定、Safari Apple Events 需要额外授权。
- Tool/HITL 篇：写 sandbox 网络权限、shell 和写文件必须审批。
- Eval 篇：写从 deterministic eval 到 trace eval。
- Reviewer 篇：写 skipped / failed / cancelled 不能被误判为 success。
- Memory 篇：写 memory 必须可见、可删除、可检查 stale。
- Skill 篇：写 skill 是 prompt guidance，不是隐形工具权限。
- MCP 篇：写外部工具进来之后仍要映射 risk level。
- 多模型篇：写不可用模型错误，例如 `gpt-image-2` 不存在，说明 model config 和 capability check 必须存在。

## 10. 下一步执行计划

### Step 1：确认 v2 目录

用户确认本设计稿的大纲是否合适。

### Step 2：先重写 00-01

重写：

- `00_index.md`
- 新增/重写 `01_run_project.md`

目标是让读者知道：

- 一天怎么跑通。
- 一周怎么吃透。
- 两周怎么准备面试。

### Step 3：写实战篇 02-06

优先写核心闭环：

- ReAct
- Plan
- Memory
- RAG
- Tool/HITL/Safety

### Step 4：写高级实战篇 07-14

再写：

- Multi-Agent
- Browser
- MCP
- Skill
- 多模型
- 产品化
- Eval
- 多模态未来扩展

### Step 5：重写简历篇和面试篇

把 v1 的简历和面试内容改成：

- 一份完整项目经历。
- 每条 bullet 的源码依据。
- 每条 bullet 的追问清单。
- 七弹面试专题。

### Step 6：同步 Obsidian

等仓库文档定稿后，再沉淀到 Obsidian。

不要每改一页就同步，避免知识库来回 churn。

