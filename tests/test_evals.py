from pathlib import Path

from pyagentcli.evals.runner import EvalRunner


def test_eval_runner_runs_builtin_cases(tmp_path: Path) -> None:
    summary, results, report_path, coding_summary, coding_results = EvalRunner(workspace_root=tmp_path).run_builtin()

    assert summary.total == 4
    assert summary.failed == 0
    assert all(result.passed for result in results)
    assert coding_summary.total == 1
    assert coding_summary.succeeded == 1
    assert coding_summary.tool_call_accuracy == 1.0
    assert coding_summary.safety_violations == 0
    assert all(result.succeeded for result in coding_results)
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "tools.registry" in report_text
    assert "coding.update_readme_status" in report_text
    assert '"kind": "coding_task"' in report_text
