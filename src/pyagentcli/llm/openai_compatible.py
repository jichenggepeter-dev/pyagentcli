from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any
from uuid import uuid4

from pyagentcli.llm.base import LLMResponse, Message, ToolCall, message_to_openai


class OpenAICompatibleClient:
    def __init__(self, *, api_key: str, base_url: str, model: str, timeout_seconds: int = 120) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def chat(self, messages: list[Message], tools: list[dict[str, Any]]) -> LLMResponse:
        body = {
            "model": self.model,
            "messages": [message_to_openai(message) for message in messages],
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM HTTP error {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM connection error: {exc.reason}") from exc

        choice = data["choices"][0]["message"]
        return LLMResponse(
            content=choice.get("content"),
            tool_calls=_parse_tool_calls(choice.get("tool_calls") or []),
        )


class LocalFallbackClient:
    """A no-key fallback that proves the CLI works before a real model is configured."""

    def chat(self, messages: list[Message], tools: list[dict[str, Any]]) -> LLMResponse:
        tool_messages = [message for message in messages if message.role == "tool"]
        if tool_messages:
            latest = tool_messages[-1].content or ""
            return LLMResponse(content=f"本地 fallback 已收到工具结果：\n{latest[:2000]}")

        user_message = next((message.content or "" for message in reversed(messages) if message.role == "user"), "")
        if any(keyword in user_message.lower() for keyword in ["list", "文件", "目录", "project", "项目", "summarize", "总结"]):
            return LLMResponse(
                content=None,
                tool_calls=[ToolCall(id=f"local_{uuid4().hex}", name="list_files", arguments={"path": "."})],
            )
        return LLMResponse(
            content=(
                "PyAgentCLI 本地 fallback 已启动。配置 OPENAI_API_KEY 后可使用真实模型和工具调用。"
            )
        )


def _parse_tool_calls(raw_tool_calls: list[dict[str, Any]]) -> list[ToolCall]:
    parsed: list[ToolCall] = []
    for raw in raw_tool_calls:
        function = raw.get("function") or {}
        arguments_raw = function.get("arguments") or "{}"
        try:
            arguments = json.loads(arguments_raw)
        except json.JSONDecodeError:
            arguments = {"_raw": arguments_raw}
        parsed.append(
            ToolCall(
                id=raw.get("id") or f"call_{uuid4().hex}",
                name=function.get("name") or "",
                arguments=arguments,
            )
        )
    return parsed
