"""Shared configuration loading for forge-os."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CONTRACT_VERSION = 1

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


@dataclass
class ForgeSettings:
    persona_name: str = "Forge"
    persona_style: str = ""
    llm_model: str = "llama-3.3-70b-versatile"
    llm_fallback_models: list[str] = field(default_factory=list)
    llm_max_tool_rounds: int = 4
    llm_temperature: float = 0.4
    groq_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    tts_provider: str = "auto"
    edge_tts_voice: str = "en-US-GuyNeural"
    piper_model_path: str = "data/piper/en_US-lessac-medium.onnx"
    piper_bin: str = "piper"
    mcp_transport: str = "sse"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8765
    mcp_url: str = "http://127.0.0.1:8765/sse"
    search_backend: str = "ddg"
    searxng_url: str | None = None
    search_max_results: int = 5
    data_dir: Path = field(default_factory=lambda: Path("./data"))
    offline: bool = False
    browser_headless: bool = True
    browser_allowlist: list[str] = field(default_factory=lambda: ["example.com", "*.wikipedia.org"])
    browser_allow_all: bool = False
    news_feeds: dict[str, list[str]] = field(default_factory=dict)
    memory_sqlite_path: Path = field(default_factory=lambda: Path("data/sqlite/forge.db"))
    memory_chroma_path: Path = field(default_factory=lambda: Path("data/chroma"))
    memory_collection: str = "forge_memories"
    vad_silence_ms: int = 700
    vad_min_utterance_ms: int = 400
    tts_speak_timeout_s: int = 10

    @property
    def sqlite_path(self) -> Path:
        if self.memory_sqlite_path.is_absolute():
            return self.memory_sqlite_path
        return _repo_relative(self.memory_sqlite_path)

    @property
    def chroma_path(self) -> Path:
        if self.memory_chroma_path.is_absolute():
            return self.memory_chroma_path
        return _repo_relative(self.memory_chroma_path)

    @property
    def piper_model(self) -> Path:
        path = Path(self.piper_model_path)
        if path.is_absolute():
            return path
        if str(path).startswith("data/"):
            return self.data_dir / path.relative_to("data")
        return _repo_relative(path)


def _repo_relative(path: Path | str) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return (_REPO_ROOT / p).resolve()


def load_yaml_config(path: Path | str) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = _REPO_ROOT / config_path
    with config_path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_dotenv_files(*, repo_root: Path | None = None) -> list[Path]:
    """Load repo-root and cwd `.env` into os.environ (existing vars win).

    Returns paths that were found and loaded.
    """
    from dotenv import load_dotenv

    root = repo_root or _REPO_ROOT
    loaded: list[Path] = []
    for path in (root / ".env", Path.cwd() / ".env"):
        resolved = path.resolve()
        if resolved.is_file() and resolved not in loaded:
            load_dotenv(resolved, override=False)
            loaded.append(resolved)
    return loaded


def load_settings(
    config_path: Path | str | None = None,
    overlay_path: Path | str | None = None,
    env: dict[str, str] | None = None,
    *,
    dotenv: bool = True,
) -> ForgeSettings:
    """Load Forge settings. When ``env`` is None, load `.env` then use ``os.environ``."""
    if env is None:
        if dotenv:
            load_dotenv_files()
        env = os.environ
    base_path = config_path or env.get("FORGE_CONFIG", "configs/default.yaml")
    raw = load_yaml_config(base_path)
    if overlay_path:
        raw = _deep_merge(raw, load_yaml_config(overlay_path))

    data_dir = Path(env.get("FORGE_DATA_DIR", "./data"))
    if not data_dir.is_absolute():
        data_dir = (_REPO_ROOT / data_dir).resolve()

    whisper_device = env.get("WHISPER_DEVICE", raw.get("stt", {}).get("device", "cpu"))
    whisper_compute = env.get(
        "WHISPER_COMPUTE_TYPE", raw.get("stt", {}).get("compute_type", "int8")
    )
    if "WHISPER_COMPUTE_TYPE" not in env and whisper_device == "cuda":
        whisper_compute = "float16"

    allowlist_raw = env.get(
        "BROWSER_ALLOWLIST",
        ",".join(raw.get("browser", {}).get("allowlist", ["example.com", "*.wikipedia.org"])),
    )

    settings = ForgeSettings(
        persona_name=env.get("FORGE_PERSONA_NAME", raw.get("persona", {}).get("name", "Forge")),
        persona_style=raw.get("persona", {}).get("style", ""),
        llm_model=env.get(
            "FORGE_LLM_MODEL",
            raw.get("llm", {}).get("model", "llama-3.3-70b-versatile"),
        ),
        llm_fallback_models=_csv_list(
            env.get(
                "FORGE_LLM_FALLBACKS",
                ",".join(
                    raw.get("llm", {}).get(
                        "fallback_models",
                        ["openai/gpt-oss-20b", "llama-3.1-8b-instant"],
                    )
                ),
            )
        ),
        llm_max_tool_rounds=int(raw.get("llm", {}).get("max_tool_rounds", 4)),
        llm_temperature=float(raw.get("llm", {}).get("temperature", 0.4)),
        groq_api_key=env.get("GROQ_API_KEY") or None,
        groq_base_url=env.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        whisper_model=env.get("WHISPER_MODEL", raw.get("stt", {}).get("model_size", "base")),
        whisper_device=whisper_device,
        whisper_compute_type=whisper_compute,
        tts_provider=env.get("TTS_PROVIDER", raw.get("tts", {}).get("provider", "auto")),
        edge_tts_voice=env.get(
            "EDGE_TTS_VOICE",
            raw.get("tts", {}).get("edge_voice", "en-US-GuyNeural"),
        ),
        piper_model_path=env.get(
            "PIPER_MODEL_PATH",
            raw.get("tts", {}).get("piper_model", "data/piper/en_US-lessac-medium.onnx"),
        ),
        piper_bin=env.get("PIPER_BIN", "piper"),
        mcp_transport=env.get("MCP_TRANSPORT", raw.get("mcp", {}).get("transport", "sse")),
        mcp_host=env.get("MCP_HOST", "127.0.0.1"),
        mcp_port=int(env.get("MCP_PORT", "8765")),
        mcp_url=env.get("MCP_URL", raw.get("mcp", {}).get("url", "http://127.0.0.1:8765/sse")),
        search_backend=env.get("SEARCH_BACKEND", raw.get("search", {}).get("backend", "ddg")),
        searxng_url=env.get("SEARXNG_URL") or raw.get("search", {}).get("searxng_url"),
        search_max_results=int(raw.get("search", {}).get("max_results", 5)),
        data_dir=data_dir,
        offline=_truthy(env.get("FORGE_OFFLINE", "0")),
        browser_headless=_truthy(env.get("BROWSER_HEADLESS", "1")),
        browser_allowlist=[p.strip() for p in allowlist_raw.split(",") if p.strip()],
        browser_allow_all=_truthy(env.get("BROWSER_ALLOW_ALL", "0")),
        news_feeds=raw.get("news", {}).get("feeds", {}),
        memory_sqlite_path=Path(raw.get("memory", {}).get("sqlite_path", "data/sqlite/forge.db")),
        memory_chroma_path=Path(raw.get("memory", {}).get("chroma_path", "data/chroma")),
        memory_collection=raw.get("memory", {}).get("collection", "forge_memories"),
        vad_silence_ms=int(raw.get("vad", {}).get("silence_ms", 700)),
        vad_min_utterance_ms=int(raw.get("vad", {}).get("min_utterance_ms", 400)),
        tts_speak_timeout_s=int(raw.get("tts", {}).get("speak_timeout_s", 10)),
    )
    return settings


def _csv_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]
