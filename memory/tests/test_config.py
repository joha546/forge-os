"""Tests for forge_memory configuration."""

from pathlib import Path

from forge_memory.config import CONTRACT_VERSION, load_settings


def test_contract_version_is_one():
    assert CONTRACT_VERSION == 1


def test_default_config_matches_spec():
    settings = load_settings(config_path="configs/default.yaml", env={})
    assert settings.llm_model == "llama-3.3-70b-versatile"
    assert settings.llm_fallback_models == ["openai/gpt-oss-20b", "llama-3.1-8b-instant"]
    assert settings.whisper_model == "base"
    assert settings.whisper_device == "cpu"
    assert settings.edge_tts_voice == "en-US-GuyNeural"
    assert settings.tts_provider == "auto"
    assert settings.mcp_url == "http://127.0.0.1:8765/sse"
    assert settings.persona_name == "Forge"


def test_cpu_overlay_overrides_stt():
    settings = load_settings(
        config_path="configs/default.yaml",
        overlay_path="configs/cpu.yaml",
        env={},
    )
    assert settings.whisper_model == "base"
    assert settings.whisper_device == "cpu"


def test_gpu_overlay_overrides_stt():
    settings = load_settings(
        config_path="configs/default.yaml",
        overlay_path="configs/gpu.yaml",
        env={},
    )
    assert settings.whisper_model == "small"
    assert settings.whisper_device == "cuda"
    assert settings.whisper_compute_type == "float16"


def test_env_overrides_yaml():
    settings = load_settings(
        config_path="configs/default.yaml",
        env={
            "FORGE_LLM_MODEL": "llama-3.1-8b-instant",
            "TTS_PROVIDER": "piper",
            "MCP_URL": "http://localhost:9999/sse",
        },
    )
    assert settings.llm_model == "llama-3.1-8b-instant"
    assert settings.tts_provider == "piper"
    assert settings.mcp_url == "http://localhost:9999/sse"


def test_configs_exist():
    root = Path(__file__).resolve().parents[2]
    for name in ("default.yaml", "cpu.yaml", "gpu.yaml"):
        assert (root / "configs" / name).is_file()


def test_dotenv_file_loads_into_settings(tmp_path: Path, monkeypatch):
    from forge_memory.config import load_dotenv_files, load_settings

    env_file = tmp_path / ".env"
    env_file.write_text("GROQ_API_KEY=gsk_test_from_dotenv\nFORGE_LLM_MODEL=llama-3.1-8b-instant\n")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("FORGE_LLM_MODEL", raising=False)

    loaded = load_dotenv_files(repo_root=tmp_path)
    assert env_file.resolve() in loaded

    settings = load_settings(config_path="configs/default.yaml", dotenv=False)
    assert settings.groq_api_key == "gsk_test_from_dotenv"
    assert settings.llm_model == "llama-3.1-8b-instant"
