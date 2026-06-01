from pathlib import Path

from pyagentcli.agent.loop import AgentLoop
from pyagentcli.llm.openai_compatible import LocalFallbackClient
from pyagentcli.safety.approval import ApprovalHandler
from pyagentcli.safety.audit_log import AuditLogger
from pyagentcli.safety.policy import SafetyPolicy
from pyagentcli.tools.base import ToolContext
from pyagentcli.tools.registry import default_registry


def test_local_fallback_agent_lists_workspace(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo", encoding="utf-8")
    safety_policy = SafetyPolicy(tmp_path)
    approval_handler = ApprovalHandler(interactive=False)
    audit_logger = AuditLogger(tmp_path)

    def context_factory(*, goal: str, step: int) -> ToolContext:
        return ToolContext(
            workspace_root=tmp_path,
            safety_policy=safety_policy,
            approval_handler=approval_handler,
            audit_logger=audit_logger,
            goal=goal,
            step=step,
        )

    agent = AgentLoop(
        llm=LocalFallbackClient(),
        tools=default_registry(),
        tool_context_factory=context_factory,
        max_steps=3,
    )

    answer = agent.run("总结这个项目")
    assert "README.md" in answer

