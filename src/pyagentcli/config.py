from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MCPServerConfig:
    name: str
    command: tuple[str, ...]
    enabled: bool = True


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str = "none"
    model: str = "text-embedding-3-small"
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "OPENAI_API_KEY"
    dimensions: int = 16


@dataclass(frozen=True)
class AppConfig:
    workspace_root: Path
    model: str
    api_key: str | None
    base_url: str
    max_steps: int
    interactive: bool = True
    mcp_servers: tuple[MCPServerConfig, ...] = ()
    embedding: EmbeddingConfig = EmbeddingConfig()


def load_config(workspace: str | None = None, *, interactive: bool = True) -> AppConfig:
    load_dotenv(Path.cwd() / ".env")
    workspace_value = workspace or os.getenv("PYAGENT_WORKSPACE") or "."
    workspace_root = Path(workspace_value).expanduser().resolve()
    load_dotenv(workspace_root / ".env")
    max_steps_raw = os.getenv("PYAGENT_MAX_STEPS", "10")
    try:
        max_steps = int(max_steps_raw)
    except ValueError:
        max_steps = 10

    return AppConfig(
        workspace_root=workspace_root,
        model=os.getenv("PYAGENT_MODEL", "gpt-4.1-mini"),
        api_key=os.getenv("OPENAI_API_KEY") or None,
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        max_steps=max_steps,
        interactive=interactive,
        mcp_servers=load_project_mcp_servers(workspace_root),
        embedding=load_project_embedding_config(workspace_root),
    )


def load_dotenv(path: Path) -> None:
    if not path.exists() or not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = _normalize_env_value(value.strip())
        if key and key not in os.environ:
            os.environ[key] = value


def _normalize_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_project_mcp_servers(workspace_root: Path) -> tuple[MCPServerConfig, ...]:
    data = _load_project_toml(workspace_root)
    servers = ((data.get("mcp") or {}).get("servers") or {})
    if not isinstance(servers, dict):
        return ()

    parsed: list[MCPServerConfig] = []
    for name, raw_server in servers.items():
        if not isinstance(raw_server, dict):
            continue
        enabled = bool(raw_server.get("enabled", True))
        command = raw_server.get("command")
        if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
            continue
        if not command:
            continue
        parsed.append(MCPServerConfig(name=str(name), command=tuple(command), enabled=enabled))
    return tuple(parsed)


def load_project_embedding_config(workspace_root: Path) -> EmbeddingConfig:
    data = _load_project_toml(workspace_root)
    raw = ((data.get("rag") or {}).get("embeddings") or {})
    if not isinstance(raw, dict):
        return EmbeddingConfig()

    dimensions_raw = raw.get("dimensions", 16)
    try:
        dimensions = int(dimensions_raw)
    except (TypeError, ValueError):
        dimensions = 16

    return EmbeddingConfig(
        provider=str(raw.get("provider") or "none"),
        model=str(raw.get("model") or "text-embedding-3-small"),
        base_url=str(raw.get("base_url") or "https://api.openai.com/v1").rstrip("/"),
        api_key_env=str(raw.get("api_key_env") or "OPENAI_API_KEY"),
        dimensions=max(4, dimensions),
    )


def _load_project_toml(workspace_root: Path) -> dict:
    config_path = workspace_root / "pyagent.toml"
    if not config_path.exists():
        return {}
    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {}
    return data if isinstance(data, dict) else {}
