from __future__ import annotations

from pyagentcli.config import AppConfig
from pyagentcli.llm.base import LLMClient
from pyagentcli.llm.openai_compatible import LocalFallbackClient, OpenAICompatibleClient


def build_llm_client(config: AppConfig) -> LLMClient:
    if config.api_key:
        return OpenAICompatibleClient(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model,
        )
    return LocalFallbackClient()

