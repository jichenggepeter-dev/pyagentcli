# 07 面试篇：Tool Call、HITL、MCP、Skill

这一篇对应 Agent 的工具生态和安全边界。

## 01 Tool Call 的本质

Tool Call 是模型输出的结构化意图。

模型说：

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

但真正执行的是：

```text
ToolRegistry
  -> SafetyPolicy
  -> ApprovalHandler
  -> Tool.run()
  -> AuditLogger
```

面试回答：

> Tool Call 是模型和真实世界之间的协议层，不是执行层。

## 02 Tool Registry 如何设计

PyAgentCLI 的工具都有：

- name
- description
- risk_level
- schema()
- run()

ToolRegistry 负责：

- 注册工具
- 暴露 schema 给模型
- 根据 name 分发调用
- 执行 preview
- 处理 approval
- 记录 audit log

面试回答：

> Tool Registry 是 Agent Runtime 的能力目录，也是安全策略接入点。

## 03 HITL 为什么重要

HITL 是 Human-in-the-loop。

在 coding agent 中，高风险操作包括：

- 写文件
- 修改文件
- 执行 shell
- 访问网络
- 调用外部工具

PyAgentCLI 做法：

- READ 默认允许
- WRITE 需要审批
- EXECUTE 需要审批
- NETWORK / CRITICAL 默认拒绝

面试回答：

> 模型可以建议做什么，但涉及真实副作用时，用户必须保留最终执行权。

## 04 路径围栏

PyAgentCLI 禁止访问：

- `.git`
- `.env`
- `.venv`
- `node_modules`
- `__pycache__`

并且所有相对路径都要 resolve 到 workspace 内。

面试回答：

> 本地 coding agent 的路径安全不能靠 prompt 约束，必须在工具层做路径解析和 denylist。

## 05 命令黑名单

危险命令示例：

- `rm -rf`
- `sudo`
- `chmod -R`
- `chown -R`
- `curl ... | sh`
- `wget ... | bash`

PyAgentCLI 会在 shell 工具执行前检查。

面试回答：

> shell 是最高风险工具之一，必须先 deny 明确危险命令，再对其他命令走审批。

## 06 MCP 解决什么问题

MCP 是 Model Context Protocol。

它解决的是：

> 外部工具如何用统一协议接入 Agent。

PyAgentCLI 已实现：

- stdio MCP client
- initialize
- tools/list
- tools/call
- MCP tool adapter

MCP 工具进入 PyAgentCLI 后，仍然要变成 ToolRegistry 中的工具。

## 07 MCP 和本地 Tool Registry 的区别

本地 Tool：

- 项目内置
- Python 类实现
- 安全策略直接可控

MCP Tool：

- 外部 server 提供
- 通过 JSON-RPC 调用
- 需要 adapter
- 需要根据 metadata 映射风险

面试回答：

> MCP 扩展的是工具来源，不应该绕过本地安全执行层。

## 08 Skill 和 Tool 的区别

Tool：

- 可执行
- 有副作用风险
- 需要 schema
- 要走安全策略

Skill：

- 不执行
- 是 prompt guidance
- 是经验和流程说明
- 不绕过审批

PyAgentCLI Skill：

```text
.pyagent/skills/<skill>/skill.toml
.pyagent/skills/<skill>/SKILL.md
```

面试回答：

> Skill 是知识复用，不是能力授权。

## 09 我们开发中遇到的相关问题

### Skill 边界

开发 Skill System 时，我们明确写进文档：

- Skill 不执行工具
- Skill 不覆盖用户任务
- Skill 不覆盖安全策略

这是因为 Skill 如果有执行能力，就可能绕过 ToolRegistry。

### MCP 风险映射

MCP 工具如果有 `readOnlyHint`，可以按 READ 处理。

如果不是只读，则按 NETWORK / CRITICAL 处理，默认拒绝。

学习点：

> 外部工具越灵活，越需要保守的默认策略。

### Browser screenshot 输出限制

浏览器截图本质上会写文件。

我们没有允许任意路径输出，而是限制到：

```text
.pyagent/browser/
```

学习点：

> 即使是 read-only 观察类工具，只要会写产物，也要限制输出路径。

## 高频面试题

1. Tool Call 是执行吗？
2. Tool Registry 如何设计？
3. 为什么写文件要审批？
4. shell 工具如何防危险命令？
5. 路径围栏怎么实现？
6. MCP 解决什么问题？
7. MCP tool 如何映射到本地工具？
8. Skill 和 Tool 区别是什么？
9. Skill 会不会绕过安全？
10. 外部工具默认应该允许还是拒绝？

