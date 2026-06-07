from pathlib import Path

from pyagentcli.evals.runner import EvalRunner


def test_eval_runner_runs_builtin_cases(tmp_path: Path) -> None:
    (
        summary,
        results,
        report_path,
        coding_summary,
        coding_results,
        rag_summary,
        rag_results,
        trace_summary,
        trace_results,
    ) = EvalRunner(
        workspace_root=tmp_path
    ).run_builtin()

    assert summary.total == 4
    assert summary.failed == 0
    assert all(result.passed for result in results)
    assert coding_summary.total == 1
    assert coding_summary.succeeded == 1
    assert coding_summary.tool_call_accuracy == 1.0
    assert coding_summary.safety_violations == 0
    assert all(result.succeeded for result in coding_results)
    assert rag_summary.total == 3
    assert rag_summary.failed == 0
    assert all(result.passed for result in rag_results)
    assert trace_summary.total == 2
    assert trace_summary.failed == 0
    assert trace_summary.tool_call_accuracy == 1.0
    assert trace_summary.safety_violations == 0
    assert all(result.passed for result in trace_results)
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "tools.registry" in report_text
    assert "coding.update_readme_status" in report_text
    assert "rag_retrieval.typescript_symbol" in report_text
    assert "trace.update_readme_status" in report_text
    assert "agent_trace.list_workspace" in report_text
    assert '"kind": "coding_task"' in report_text
    assert '"kind": "rag_retrieval"' in report_text
    assert '"kind": "trace_eval"' in report_text
