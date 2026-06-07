from pathlib import Path

import pytest

from pyagentcli.safety.approval import ApprovalResult
from pyagentcli.safety.audit_log import AuditLogger
from pyagentcli.safety.policy import SafetyDecision, SafetyPolicy
from pyagentcli.tools.base import RiskLevel, ToolContext
from pyagentcli.tools.registry import default_registry


class ApproveAll:
    def request(
        self,
        *,
        tool_name: str,
        risk_level: RiskLevel,
        args: dict,
        decision: SafetyDecision,
        preview: str | None = None,
    ) -> ApprovalResult:
        return ApprovalResult(True, "approved in optional browser test")


def make_context(tmp_path: Path) -> ToolContext:
    return ToolContext(
        workspace_root=tmp_path,
        safety_policy=SafetyPolicy(tmp_path),
        approval_handler=ApproveAll(),
        audit_logger=AuditLogger(tmp_path),
        goal="optional browser success path",
        step=1,
    )


def skip_if_browser_binary_missing(error: str | None) -> None:
    if error and ("Executable doesn't exist" in error or "playwright install" in error):
        pytest.skip("Playwright package is installed, but browser binaries are missing.")


def test_browser_console_logs_success_path_when_playwright_is_available(tmp_path: Path) -> None:
    pytest.importorskip("playwright.sync_api")
    page = tmp_path / "console.html"
    page.write_text(
        """
<html>
  <head><title>Console Fixture</title></head>
  <body>
    <h1>Console Fixture</h1>
    <script>console.log("pyagent browser smoke");</script>
  </body>
</html>
""".strip(),
        encoding="utf-8",
    )
    registry = default_registry()
    context = make_context(tmp_path)

    result = registry.execute("browser_console_logs", {"url": "console.html", "wait_ms": 100}, context)

    skip_if_browser_binary_missing(result.error)
    assert result.ok
    assert "pyagent browser smoke" in result.content


def test_browser_screenshot_success_path_when_playwright_is_available(tmp_path: Path) -> None:
    pytest.importorskip("playwright.sync_api")
    page = tmp_path / "screenshot.html"
    page.write_text(
        """
<html>
  <head><title>Screenshot Fixture</title></head>
  <body><main style="font-size: 32px;">PyAgent Browser Screenshot</main></body>
</html>
""".strip(),
        encoding="utf-8",
    )
    registry = default_registry()
    context = make_context(tmp_path)
    output = ".pyagent/browser/smoke.png"

    result = registry.execute("browser_screenshot", {"url": "screenshot.html", "output_path": output}, context)

    skip_if_browser_binary_missing(result.error)
    assert result.ok
    screenshot = tmp_path / output
    assert screenshot.exists()
    assert screenshot.stat().st_size > 0
