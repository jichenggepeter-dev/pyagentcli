from pathlib import Path

from pyagentcli.safety.approval import ApprovalResult
from pyagentcli.safety.audit_log import AuditLogger
from pyagentcli.safety.policy import SafetyDecision, SafetyPolicy
from pyagentcli.tools.base import RiskLevel, ToolContext
from pyagentcli.tools.registry import default_registry


class ApproveAll:
    def __init__(self) -> None:
        self.preview: str | None = None

    def request(
        self,
        *,
        tool_name: str,
        risk_level: RiskLevel,
        args: dict,
        decision: SafetyDecision,
        preview: str | None = None,
    ) -> ApprovalResult:
        self.preview = preview
        return ApprovalResult(True, "approved in test")


class DenyAll:
    def request(
        self,
        *,
        tool_name: str,
        risk_level: RiskLevel,
        args: dict,
        decision: SafetyDecision,
        preview: str | None = None,
    ) -> ApprovalResult:
        return ApprovalResult(False, "denied in test")


def make_context(tmp_path: Path, approval) -> ToolContext:
    return ToolContext(
        workspace_root=tmp_path,
        safety_policy=SafetyPolicy(tmp_path),
        approval_handler=approval,
        audit_logger=AuditLogger(tmp_path),
        goal="test goal",
        step=1,
    )


def test_read_and_write_file_tool(tmp_path: Path) -> None:
    registry = default_registry()
    approval = ApproveAll()
    context = make_context(tmp_path, approval)

    write_result = registry.execute(
        "write_file",
        {"path": "notes/hello.md", "content": "hello pyagent"},
        context,
    )
    assert write_result.ok
    assert (tmp_path / "notes" / "hello.md").read_text(encoding="utf-8") == "hello pyagent"
    assert approval.preview is not None
    assert "+hello pyagent" in approval.preview

    read_result = registry.execute("read_file", {"path": "notes/hello.md"}, context)
    assert read_result.ok
    assert read_result.content == "hello pyagent"


def test_write_file_denied_by_approval(tmp_path: Path) -> None:
    registry = default_registry()
    context = make_context(tmp_path, DenyAll())

    result = registry.execute("write_file", {"path": "x.txt", "content": "nope"}, context)
    assert not result.ok
    assert not (tmp_path / "x.txt").exists()


def test_run_shell_dangerous_command_denied_by_policy(tmp_path: Path) -> None:
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute("run_shell", {"command": "rm -rf ."}, context)
    assert not result.ok
    assert "denied" in (result.error or "").lower()


def test_list_files_skips_pyagent_dir(tmp_path: Path) -> None:
    (tmp_path / ".pyagent").mkdir()
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute("list_files", {"path": "."}, context)
    assert result.ok
    assert "README.md" in result.content
    assert ".pyagent" not in result.content


def test_write_file_preview_shows_update_diff(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text("old\n", encoding="utf-8")
    registry = default_registry()
    approval = ApproveAll()
    context = make_context(tmp_path, approval)

    result = registry.execute("write_file", {"path": "notes.md", "content": "new\n"}, context)
    assert result.ok
    assert approval.preview is not None
    assert "-old" in approval.preview
    assert "+new" in approval.preview


def test_edit_file_replaces_unique_text_and_shows_diff(tmp_path: Path) -> None:
    target = tmp_path / "app.py"
    target.write_text("def hello():\n    return 'old'\n", encoding="utf-8")
    registry = default_registry()
    approval = ApproveAll()
    context = make_context(tmp_path, approval)

    result = registry.execute(
        "edit_file",
        {
            "path": "app.py",
            "old_text": "return 'old'",
            "new_text": "return 'new'",
        },
        context,
    )

    assert result.ok
    assert target.read_text(encoding="utf-8") == "def hello():\n    return 'new'\n"
    assert approval.preview is not None
    assert "-    return 'old'" in approval.preview
    assert "+    return 'new'" in approval.preview


def test_edit_file_refuses_missing_text(tmp_path: Path) -> None:
    target = tmp_path / "app.py"
    target.write_text("print('hello')\n", encoding="utf-8")
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute(
        "edit_file",
        {"path": "app.py", "old_text": "missing", "new_text": "replacement"},
        context,
    )

    assert not result.ok
    assert "not found" in (result.error or "")
    assert target.read_text(encoding="utf-8") == "print('hello')\n"


def test_edit_file_refuses_ambiguous_text(tmp_path: Path) -> None:
    target = tmp_path / "app.py"
    target.write_text("x = 1\nx = 1\n", encoding="utf-8")
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute(
        "edit_file",
        {"path": "app.py", "old_text": "x = 1", "new_text": "x = 2"},
        context,
    )

    assert not result.ok
    assert "ambiguous" in (result.error or "")
    assert target.read_text(encoding="utf-8") == "x = 1\nx = 1\n"


def test_edit_file_denied_by_approval(tmp_path: Path) -> None:
    target = tmp_path / "app.py"
    target.write_text("x = 1\n", encoding="utf-8")
    registry = default_registry()
    context = make_context(tmp_path, DenyAll())

    result = registry.execute(
        "edit_file",
        {"path": "app.py", "old_text": "x = 1", "new_text": "x = 2"},
        context,
    )

    assert not result.ok
    assert target.read_text(encoding="utf-8") == "x = 1\n"


def test_default_registry_exposes_edit_file_schema() -> None:
    registry = default_registry()
    tool_names = [schema["function"]["name"] for schema in registry.schemas()]
    assert "edit_file" in tool_names
    assert "inspect_page" in tool_names
    assert "browser_dom_snapshot" in tool_names
    assert "browser_query_selector" in tool_names
    assert "browser_console_logs" in tool_names
    assert "browser_screenshot" in tool_names
    assert "browser_interact" in tool_names


def test_inspect_page_reads_workspace_html_file(tmp_path: Path) -> None:
    page = tmp_path / "index.html"
    page.write_text(
        "<html><head><title>Demo Page</title><style>.x{}</style></head>"
        "<body><h1>Hello PyAgent</h1><script>ignore()</script><p>Status READY</p></body></html>",
        encoding="utf-8",
    )
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute("inspect_page", {"url": page.as_uri()}, context)

    assert result.ok
    assert "Title: Demo Page" in result.content
    assert "Hello PyAgent" in result.content
    assert "Status READY" in result.content
    assert "ignore()" not in result.content


def test_inspect_page_accepts_workspace_relative_path(tmp_path: Path) -> None:
    (tmp_path / "site").mkdir()
    (tmp_path / "site" / "index.html").write_text(
        "<title>Relative</title><main>Local snapshot</main>",
        encoding="utf-8",
    )
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute("inspect_page", {"url": "site/index.html"}, context)

    assert result.ok
    assert "Title: Relative" in result.content
    assert "Local snapshot" in result.content


def test_inspect_page_rejects_external_url(tmp_path: Path) -> None:
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute("inspect_page", {"url": "https://example.com"}, context)

    assert not result.ok
    assert "Only local browser URLs are allowed" in (result.error or "")


def test_browser_dom_snapshot_returns_structure(tmp_path: Path) -> None:
    page = tmp_path / "index.html"
    page.write_text(
        """
<html>
  <head><title>DOM Demo</title></head>
  <body>
    <h1>Welcome</h1>
    <a href="/docs">Docs</a>
    <button aria-label="Save changes">Save</button>
    <input name="query" />
    <p>Ready for inspection.</p>
  </body>
</html>
""".strip(),
        encoding="utf-8",
    )
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute("browser_dom_snapshot", {"url": "index.html"}, context)

    assert result.ok
    assert "Title: DOM Demo" in result.content
    assert "h1: Welcome" in result.content
    assert "- /docs" in result.content
    assert "button: Save changes" in result.content
    assert "input: query" in result.content


def test_browser_dom_snapshot_rejects_external_url(tmp_path: Path) -> None:
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute("browser_dom_snapshot", {"url": "https://example.com"}, context)

    assert not result.ok
    assert "Only local browser URLs are allowed" in (result.error or "")


def test_browser_query_selector_matches_id_class_and_tag(tmp_path: Path) -> None:
    page = tmp_path / "index.html"
    page.write_text(
        """
<html>
  <head><title>Selector Demo</title></head>
  <body>
    <main id="app">
      <h1 class="title">Dashboard</h1>
      <p class="status">Ready</p>
      <p class="status">Healthy</p>
    </main>
  </body>
</html>
""".strip(),
        encoding="utf-8",
    )
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    id_result = registry.execute("browser_query_selector", {"url": "index.html", "selector": "#app"}, context)
    class_result = registry.execute(
        "browser_query_selector",
        {"url": "index.html", "selector": ".status", "max_results": 1},
        context,
    )
    tag_result = registry.execute("browser_query_selector", {"url": "index.html", "selector": "h1"}, context)

    assert id_result.ok
    assert "main#app" in id_result.content
    assert "Dashboard Ready Healthy" in id_result.content
    assert class_result.ok
    assert "Matches: 1" in class_result.content
    assert "p.status: Ready" in class_result.content
    assert tag_result.ok
    assert "h1.title: Dashboard" in tag_result.content


def test_browser_query_selector_rejects_complex_selector(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<main id='app'>Hello</main>", encoding="utf-8")
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute("browser_query_selector", {"url": "index.html", "selector": "main .status"}, context)

    assert not result.ok
    assert "Only simple tag, #id, or .class selectors are supported" in (result.error or "")


def test_browser_query_selector_rejects_external_url(tmp_path: Path) -> None:
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute("browser_query_selector", {"url": "https://example.com", "selector": "main"}, context)

    assert not result.ok
    assert "Only local browser URLs are allowed" in (result.error or "")


def test_browser_console_logs_gracefully_reports_missing_playwright(tmp_path: Path) -> None:
    page = tmp_path / "index.html"
    page.write_text("<title>Console</title><script>console.log('hello')</script>", encoding="utf-8")
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute("browser_console_logs", {"url": "index.html"}, context)

    if not result.ok:
        assert "Playwright is not installed" in (result.error or "")
    else:
        assert "Console logs:" in result.content


def test_browser_screenshot_restricts_output_path(tmp_path: Path) -> None:
    page = tmp_path / "index.html"
    page.write_text("<title>Shot</title><main>Hello</main>", encoding="utf-8")
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute(
        "browser_screenshot",
        {"url": "index.html", "output_path": "screenshots/out.png"},
        context,
    )

    assert not result.ok
    assert (
        "Screenshot output_path must be under .pyagent/browser/" in (result.error or "")
        or "Playwright is not installed" in (result.error or "")
    )


def test_browser_interact_rejects_external_url(tmp_path: Path) -> None:
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute(
        "browser_interact",
        {"url": "https://example.com", "actions": [{"type": "click", "selector": "#save"}]},
        context,
    )

    assert not result.ok
    assert "Only local browser URLs are allowed" in (result.error or "")


def test_browser_interact_requires_approval(tmp_path: Path) -> None:
    page = tmp_path / "index.html"
    page.write_text("<button id='save'>Save</button>", encoding="utf-8")
    registry = default_registry()
    context = make_context(tmp_path, DenyAll())

    result = registry.execute(
        "browser_interact",
        {"url": "index.html", "actions": [{"type": "click", "selector": "#save"}]},
        context,
    )

    assert not result.ok
    assert "denied in test" in (result.error or "")


def test_browser_interact_gracefully_reports_missing_playwright(tmp_path: Path) -> None:
    page = tmp_path / "index.html"
    page.write_text("<button id='save'>Save</button>", encoding="utf-8")
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute(
        "browser_interact",
        {"url": "index.html", "actions": [{"type": "click", "selector": "#save"}]},
        context,
    )

    if not result.ok:
        assert (
            "Playwright is not installed" in (result.error or "")
            or "Could not run browser interaction" in (result.error or "")
        )
    else:
        assert "Actions: 1" in result.content


def test_search_text_finds_matches(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def project_status():\n    return 'READY'\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("Project status: READY\n", encoding="utf-8")
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute("search_text", {"query": "READY", "path": ".", "max_results": 10}, context)

    assert result.ok
    assert "README.md:1: Project status: READY" in result.content
    assert "src/app.py:2: return 'READY'" in result.content


def test_search_text_is_case_insensitive_by_default(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Project status: READY\n", encoding="utf-8")
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute("search_text", {"query": "ready"}, context)

    assert result.ok
    assert "README.md:1" in result.content


def test_search_text_respects_max_results_and_ignores_pyagent(tmp_path: Path) -> None:
    (tmp_path / ".pyagent").mkdir()
    (tmp_path / ".pyagent" / "secret.txt").write_text("needle\n", encoding="utf-8")
    (tmp_path / "a.txt").write_text("needle\nneedle\n", encoding="utf-8")
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute("search_text", {"query": "needle", "max_results": 1}, context)

    assert result.ok
    assert result.content.count("needle") == 1
    assert ".pyagent" not in result.content


def test_default_registry_exposes_search_text_schema() -> None:
    registry = default_registry()
    tool_names = [schema["function"]["name"] for schema in registry.schemas()]
    assert "search_text" in tool_names
    assert "search_dependencies" in tool_names


def test_search_index_reads_sqlite_fts_index(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def project_status():\n    return 'READY'\n", encoding="utf-8")
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    missing = registry.execute("search_index", {"query": "project_status"}, context)

    assert not missing.ok
    assert "Index not found" in (missing.error or "")

    from pyagentcli.rag.indexer import CodeIndexer

    CodeIndexer(tmp_path).rebuild()
    result = registry.execute("search_index", {"query": "project_status"}, context)

    assert result.ok
    assert "src/app.py:1-2 function project_status:" in result.content
    assert "[project_status]" in result.content
    assert result.metadata["stale_paths"] == []


def test_search_index_warns_when_index_is_stale(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    target = tmp_path / "src" / "app.py"
    target.write_text("def project_status():\n    return 'READY'\n", encoding="utf-8")
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    from pyagentcli.rag.indexer import CodeIndexer

    CodeIndexer(tmp_path).rebuild()
    target.write_text("def project_status():\n    return 'STALE'\n", encoding="utf-8")
    result = registry.execute("search_index", {"query": "project_status"}, context)

    assert result.ok
    assert "Warning: index may be stale for: src/app.py" in result.content
    assert result.metadata["stale_paths"] == ["src/app.py"]


def test_search_dependencies_requires_index(tmp_path: Path) -> None:
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute("search_dependencies", {"path": "src/app.py"}, context)

    assert not result.ok
    assert "Index not found" in (result.error or "")


def test_search_dependencies_finds_imports_for_file(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text(
        "import os\nfrom helpers import normalize\n",
        encoding="utf-8",
    )
    from pyagentcli.rag.indexer import CodeIndexer

    CodeIndexer(tmp_path).rebuild()
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute("search_dependencies", {"path": "src/app.py"}, context)

    assert result.ok
    assert "src/app.py:1 imports os" in result.content
    assert "src/app.py:2 imports helpers:normalize" in result.content
    assert result.metadata["mode"] == "imports_for"


def test_search_dependencies_finds_imported_by_module(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("from helpers import normalize\n", encoding="utf-8")
    (tmp_path / "src" / "other.py").write_text("import helpers\n", encoding="utf-8")
    from pyagentcli.rag.indexer import CodeIndexer

    CodeIndexer(tmp_path).rebuild()
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute("search_dependencies", {"module": "helpers"}, context)

    assert result.ok
    assert "src/app.py:1 imports helpers:normalize" in result.content
    assert "src/other.py:1 imports helpers" in result.content
    assert result.metadata["mode"] == "imported_by"


def test_default_registry_exposes_search_index_schema() -> None:
    registry = default_registry()
    tool_names = [schema["function"]["name"] for schema in registry.schemas()]
    assert "search_index" in tool_names


def test_search_files_finds_filename_and_relative_path(tmp_path: Path) -> None:
    (tmp_path / "src" / "pyagentcli").mkdir(parents=True)
    (tmp_path / "src" / "pyagentcli" / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    by_name = registry.execute("search_files", {"query": "main.py"}, context)
    by_path = registry.execute("search_files", {"query": "pyagentcli/main"}, context)

    assert by_name.ok
    assert "src/pyagentcli/main.py" in by_name.content
    assert by_path.ok
    assert "src/pyagentcli/main.py" in by_path.content


def test_search_files_is_case_insensitive_and_respects_max_results(tmp_path: Path) -> None:
    (tmp_path / "Alpha.py").write_text("", encoding="utf-8")
    (tmp_path / "alpha_test.py").write_text("", encoding="utf-8")
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute("search_files", {"query": "ALPHA", "max_results": 1}, context)

    assert result.ok
    assert len(result.content.splitlines()) == 1
    assert "Alpha.py" in result.content or "alpha_test.py" in result.content


def test_search_files_ignores_pyagent_dir(tmp_path: Path) -> None:
    (tmp_path / ".pyagent").mkdir()
    (tmp_path / ".pyagent" / "plan_secret.json").write_text("{}", encoding="utf-8")
    (tmp_path / "plan_public.txt").write_text("", encoding="utf-8")
    registry = default_registry()
    context = make_context(tmp_path, ApproveAll())

    result = registry.execute("search_files", {"query": "plan"}, context)

    assert result.ok
    assert "plan_public.txt" in result.content
    assert ".pyagent" not in result.content


def test_default_registry_exposes_search_files_schema() -> None:
    registry = default_registry()
    tool_names = [schema["function"]["name"] for schema in registry.schemas()]
    assert "search_files" in tool_names
