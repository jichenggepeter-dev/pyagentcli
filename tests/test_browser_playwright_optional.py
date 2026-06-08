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


def test_browser_interact_success_path_when_playwright_is_available(tmp_path: Path) -> None:
    pytest.importorskip("playwright.sync_api")
    page = tmp_path / "interact.html"
    page.write_text(
        """
<html>
  <head><title>Interact Fixture</title></head>
  <body>
    <input id="name" />
    <button id="apply" onclick="document.querySelector('#status').textContent = 'Hello ' + document.querySelector('#name').value">Apply</button>
    <p id="status">Waiting</p>
  </body>
</html>
""".strip(),
        encoding="utf-8",
    )
    registry = default_registry()
    context = make_context(tmp_path)

    result = registry.execute(
        "browser_interact",
        {
            "url": "interact.html",
            "actions": [
                {"type": "type", "selector": "#name", "text": "PyAgent"},
                {"type": "click", "selector": "#apply"},
                {"type": "wait", "wait_ms": 100},
            ],
        },
        context,
    )

    skip_if_browser_binary_missing(result.error)
    assert result.ok
    assert "Title: Interact Fixture" in result.content
    assert "Hello PyAgent" in result.content


def test_browser_network_logs_success_path_when_playwright_is_available(tmp_path: Path) -> None:
    pytest.importorskip("playwright.sync_api")
    (tmp_path / "data.json").write_text('{"status":"ready"}', encoding="utf-8")
    page = tmp_path / "network.html"
    page.write_text(
        """
<html>
  <head><title>Network Fixture</title></head>
  <body>
    <main>Network Fixture</main>
    <script>
      fetch('data.json').then((response) => response.text()).then(() => {
        document.body.dataset.loaded = 'yes';
      });
    </script>
  </body>
</html>
""".strip(),
        encoding="utf-8",
    )
    registry = default_registry()
    context = make_context(tmp_path)

    result = registry.execute("browser_network_logs", {"url": "network.html", "wait_ms": 300}, context)

    skip_if_browser_binary_missing(result.error)
    assert result.ok
    assert "Network entries:" in result.content
    assert "network.html" in result.content
    assert "data.json" in result.content
    assert "status=200" in result.content
    assert "ready" not in result.content
