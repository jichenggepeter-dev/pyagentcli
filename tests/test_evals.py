from pathlib import Path

from pyagentcli.evals.runner import EvalRunner


def test_eval_runner_runs_builtin_cases(tmp_path: Path) -> None:
    summary, results, report_path = EvalRunner(workspace_root=tmp_path).run_builtin()

    assert summary.total == 4
    assert summary.failed == 0
    assert all(result.passed for result in results)
    assert report_path.exists()
    assert "tools.registry" in report_path.read_text(encoding="utf-8")
