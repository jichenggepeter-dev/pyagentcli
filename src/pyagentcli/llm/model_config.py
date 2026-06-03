from __future__ import annotations

from pyagentcli.config import AppConfig
from pyagentcli.llm.base import LLMClient
from pyagentcli.llm.openai_compatible import LocalFallbackClient, OpenAICompatibleClient


def build_llm_client(config: AppConfig, *, role: str | None = None) -> LLMClient:
    model = config.model
    if role is not None:
        role_model = config.role_config(role).model
        if role_model:
            model = role_model

    if config.api_key:
        return OpenAICompatibleClient(
            api_key=config.api_key,
            base_url=config.base_url,
            model=model,
        )
    return LocalFallbackClient()
