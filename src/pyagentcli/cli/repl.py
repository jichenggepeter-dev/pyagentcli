from __future__ import annotations

from pyagentcli.agent.loop import AgentLoop


def run_repl(agent: AgentLoop, goal_transform=None) -> None:
    print("PyAgentCLI ready. Type /exit or /quit to leave.")
    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if not user_input:
            continue
        if user_input in {"/exit", "/quit"}:
            return

        try:
            goal = goal_transform(user_input) if goal_transform else user_input
            answer = agent.run(goal)
        except Exception as exc:  # noqa: BLE001 - keep CLI alive in v0.1.
            print(f"Error: {exc}")
            continue
        print(answer)
