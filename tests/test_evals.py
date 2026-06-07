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
        reviewer_summary,
        reviewer_results,
    ) = EvalRunner(
        workspace_root=tmp_path
    ).run_builtin()

    assert summary.total == 4
    assert summary.failed == 0
    assert all(result.passed for result in results)
    assert coding_summary.total == 1
    assert coding_summary.succeeded == 1
    assert coding_summary.tool_call_accuracy == 1.0
    assert coding_summary.diff_accuracy == 1.0
    assert coding_summary.safety_violations == 0
    assert all(result.succeeded for result in coding_results)
    assert coding_results[0].expected_diffs == 1
    assert coding_results[0].matched_diffs == 1
    assert rag_summary.total == 3
    assert rag_summary.failed == 0
    assert all(result.passed for result in rag_results)
    assert trace_summary.total == 2
    assert trace_summary.failed == 0
    assert trace_summary.tool_call_accuracy == 1.0
    assert trace_summary.safety_violations == 0
    assert all(result.passed for result in trace_results)
    assert reviewer_summary.total == 3
    assert reviewer_summary.failed == 0
    assert reviewer_summary.gate_matches == 3
    assert reviewer_summary.proposal_matches == 3
    assert all(result.passed for result in reviewer_results)
    proposal_actions = {result.case_id: result.proposal_action for result in reviewer_results}
    assert proposal_actions["reviewer.success_plan"] is None
    assert proposal_actions["reviewer.failed_step"] == "retry_step"
    assert proposal_actions["reviewer.skipped_step"] == "user_decision"
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "tools.registry" in report_text
    assert "coding.update_readme_status" in report_text
    assert "rag_retrieval.typescript_symbol" in report_text
    assert "trace.update_readme_status" in report_text
    assert "agent_trace.list_workspace" in report_text
    assert "reviewer.failed_step" in report_text
    assert '"kind": "coding_task"' in report_text
    assert '"matched_diffs": 1' in report_text
    assert '"kind": "rag_retrieval"' in report_text
    assert '"kind": "trace_eval"' in report_text
    assert '"kind": "reviewer_eval"' in report_text
