from __future__ import annotations

from pyagentcli.agent.prompts import SYSTEM_PROMPT
from pyagentcli.agent.state import AgentState
from pyagentcli.llm.base import LLMClient, Message
from pyagentcli.tools.base import ToolContext
from pyagentcli.tools.registry import ToolRegistry


class AgentLoop:
    def __init__(
        self,
        *,
        llm: LLMClient,
        tools: ToolRegistry,
        tool_context_factory,
        max_steps: int,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.tool_context_factory = tool_context_factory
        self.max_steps = max_steps
        self.system_prompt = system_prompt

    def run(self, goal: str) -> str:
        context = self.tool_context_factory(goal=goal, step=0)
        state = AgentState(
            user_goal=goal,
            workspace_root=context.workspace_root,
            max_steps=self.max_steps,
            messages=[Message.system(self.system_prompt), Message.user(goal)],
        )

        while state.step_count < state.max_steps:
            state.step_count += 1
            response = self.llm.chat(state.messages, self.tools.schemas())
            state.messages.append(response.assistant_message())

            if not response.tool_calls:
                return response.content or ""

            for call in response.tool_calls:
                tool_context: ToolContext = self.tool_context_factory(goal=goal, step=state.step_count)
                result = self.tools.execute(call.name, call.arguments, tool_context)
                state.messages.append(Message.tool(call.id, result.to_message_content()))

        return f"任务达到最大步数 {state.max_steps}，已停止。"
