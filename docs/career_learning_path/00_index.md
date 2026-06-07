# PyAgentCLI 学习路线总览

这组文档把 PyAgentCLI 按教程网站的结构拆成多个独立板块，方便导入 OCDN、Obsidian 或其他知识库。

它不是把参考网页合并成一篇长文，而是按“网页目录”的方式拆成可独立阅读的主题页。每一页都围绕 PyAgentCLI 当前已经落地的功能和我们开发时真实遇到的问题展开。

它的组织方式是：

```text
先跑起来
  -> 写到简历
  -> 围绕简历深挖源码和面试题
  -> 动手 debug / 改 bug / 加功能
  -> 整理成知识库
```

每篇文档都对应一个可单独阅读、复习和面试准备的主题。

## 文档目录

### 入门和定位

- [01 项目定位：Python 版 Claude Code / Codex mini](01_project_positioning.md)
- [02 先把项目跑起来：本地运行、测试、演示](02_run_project.md)

### 简历篇

- [03 简历篇：AI Agent 岗位写法](03_resume_ai_agent.md)
- [04 简历篇：后端 / 平台 / 工具岗位写法](04_resume_backend_platform.md)

### 面试篇

- [05 面试篇：ReAct、Plan-and-Execute、Multi-Agent](05_interview_react_plan_multi_agent.md)
- [06 面试篇：Memory、RAG、Context Engineering](06_interview_memory_rag_context.md)
- [07 面试篇：Tool Call、HITL、MCP、Skill](07_interview_tool_hitl_mcp_skill.md)
- [08 面试篇：Browser Tools、Eval Harness、Trace Eval](08_interview_browser_eval.md)

### 开发复盘

- [09 开发复盘：我们真实遇到的问题和解决方式](09_debug_pitfalls.md)
- [10 知识库沉淀：怎么把 PyAgentCLI 讲成自己的项目](10_knowledge_base_cards.md)
- [11 一分钟项目介绍和面试追问模板](11_pitch_and_followups.md)

## 推荐阅读顺序

如果你要准备简历：

1. 读 [01 项目定位](01_project_positioning.md)
2. 读 [03 AI Agent 岗位写法](03_resume_ai_agent.md)
3. 读 [04 后端 / 平台 / 工具岗位写法](04_resume_backend_platform.md)
4. 从 [11 一分钟项目介绍](11_pitch_and_followups.md) 里背一版口播

如果你要准备面试：

1. 先读 [05 ReAct / Plan / Multi-Agent](05_interview_react_plan_multi_agent.md)
2. 再读 [06 Memory / RAG / Context](06_interview_memory_rag_context.md)
3. 再读 [07 Tool / HITL / MCP / Skill](07_interview_tool_hitl_mcp_skill.md)
4. 最后读 [08 Browser / Eval / Trace](08_interview_browser_eval.md)

如果你要复盘开发经历：

1. 读 [09 开发复盘](09_debug_pitfalls.md)
2. 把里面的问题转成自己的“踩坑贴”
3. 用 [10 知识库沉淀](10_knowledge_base_cards.md) 整理成长期笔记

## 当前项目完成度

按求职展示标准：

- 核心闭环：已完成
- 简历可写模块：已完成
- 面试可讲材料：已完成
- Eval 和安全边界：已完成基础版
- 高级浏览器和真实模型评估：继续增强中

一句话：

> PyAgentCLI 已经足够作为一个完整 AI Agent 项目写进简历，剩下的工作主要是高级能力、真实模型评估和演示质量打磨。

## 来源说明

这组文档参考 PaiCLI 学习路线的组织方式和主题顺序，但不复制原文内容。所有简历表述、面试回答、开发复盘和知识卡片都围绕 PyAgentCLI 的 Python 实现重新组织。

参考页面：

- https://paicoding.com/paicli-learning-path
- https://paicoding.com/column/17/14
- https://paicoding.com/article/detail/2613300022282240
- https://paicoding.com/memory-context
- https://paicoding.com/article/detail/2614100053739520
