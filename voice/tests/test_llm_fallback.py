"""LLM fallback, sanitization, and tool_use_failed recovery tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from forge_memory.config import ForgeSettings
from forge_voice.llm import (
    LLMClient,
    _extract_tool_failure,
    assistant_message_to_dict,
    parse_failed_generation,
    sanitize_message,
)
from openai import APIStatusError, RateLimitError


@pytest.mark.asyncio
async def test_switches_model_on_rate_limit():
    settings = ForgeSettings(
        llm_model="llama-3.3-70b-versatile",
        llm_fallback_models=["openai/gpt-oss-20b"],
        groq_api_key="test-key",
    )
    client = LLMClient(settings)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Hi", tool_calls=None))]

    create = AsyncMock(
        side_effect=[
            RateLimitError("429", response=MagicMock(status_code=429), body=None),
            mock_response,
        ]
    )
    client._client = MagicMock()
    client._client.chat.completions.create = create

    text = await client.chat_text("hello")
    assert text == "Hi"
    assert create.await_count == 2
    assert create.await_args_list[1].kwargs["model"] == "openai/gpt-oss-20b"


def test_sanitize_strips_annotations():
    dirty = {
        "role": "assistant",
        "content": "hi",
        "annotations": [{"type": "foo"}],
        "refusal": None,
    }
    clean = sanitize_message(dirty)
    assert clean == {"role": "assistant", "content": "hi"}
    assert "annotations" not in clean


def test_assistant_message_to_dict_keeps_tool_calls_only():
    call = MagicMock()
    call.id = "call_1"
    call.type = "function"
    call.function.name = "web_search"
    call.function.arguments = '{"query":"ai"}'
    message = MagicMock()
    message.content = None
    message.tool_calls = [call]
    message.annotations = [{"x": 1}]

    payload = assistant_message_to_dict(message)
    assert "annotations" not in payload
    assert payload["tool_calls"][0]["function"]["name"] == "web_search"


@pytest.mark.parametrize(
    "failed_gen,expected_name,expected_query",
    [
        (
            '<function=web_search{"query": "recent updates", "max_results": 5}</function>',
            "web_search",
            "recent updates",
        ),
        (
            '<function=web_search({"query": "cyber security updates", "max_results": 5}</function>\n',
            "web_search",
            "cyber security updates",
        ),
        (
            '<function=web_search({"query": "recent tech updates", "max_results": 5})</function>',
            "web_search",
            "recent tech updates",
        ),
    ],
)
def test_parse_failed_generation(failed_gen, expected_name, expected_query):
    calls = parse_failed_generation(failed_gen)
    assert len(calls) == 1
    assert calls[0]["name"] == expected_name
    assert calls[0]["arguments"]["query"] == expected_query


def test_extract_tool_failure_reads_unwrapped_openai_body():
    """OpenAI SDK stores body.get('error'), not the outer envelope."""
    failed = '<function=web_search({"query": "recent tech updates", "max_results": 5})</function>'
    err = APIStatusError(
        "bad",
        response=MagicMock(status_code=400, headers={}),
        body={
            "message": "Failed to call a function",
            "type": "invalid_request_error",
            "code": "tool_use_failed",
            "failed_generation": failed,
        },
    )
    code, failed_gen = _extract_tool_failure(err)
    assert code == "tool_use_failed"
    assert failed_gen == failed


@pytest.mark.asyncio
async def test_recovers_tool_use_failed_by_executing_parsed_call():
    settings = ForgeSettings(
        llm_model="llama-3.3-70b-versatile",
        llm_fallback_models=["openai/gpt-oss-20b"],
        groq_api_key="test-key",
    )
    client = LLMClient(settings)
    # Mirror real OpenAI SDK: body is the unwrapped error object
    err = APIStatusError(
        "bad",
        response=MagicMock(status_code=400, headers={}),
        body={
            "code": "tool_use_failed",
            "message": "Failed to call a function",
            "failed_generation": (
                '<function=web_search({"query": "recent updates", "max_results": 5})</function>'
            ),
        },
    )
    err.status_code = 400
    final = MagicMock()
    final.choices = [
        MagicMock(message=MagicMock(content="Here are the updates…", tool_calls=None))
    ]
    create = AsyncMock(side_effect=[err, final])
    client._client = MagicMock()
    client._client.chat.completions.create = create

    called: list[tuple[str, dict]] = []

    async def tool_caller(name, args):
        called.append((name, args))
        return {"ok": True, "results": [{"title": "Update"}]}

    reply = await client.chat_with_tools(
        "news please",
        tools=[{"type": "function", "function": {"name": "web_search", "parameters": {}}}],
        tool_caller=tool_caller,
    )
    assert reply == "Here are the updates…"
    assert called == [("web_search", {"query": "recent updates", "max_results": 5})]
    # Same model both times; second call has tool result in messages
    assert create.await_args_list[0].kwargs["model"] == "llama-3.3-70b-versatile"
    assert create.await_args_list[1].kwargs["model"] == "llama-3.3-70b-versatile"
    assert "tools" in create.await_args_list[1].kwargs


@pytest.mark.asyncio
async def test_unparseable_tool_use_failed_retries_without_tools():
    settings = ForgeSettings(
        llm_model="llama-3.3-70b-versatile",
        llm_fallback_models=["openai/gpt-oss-20b"],
        groq_api_key="test-key",
    )
    client = LLMClient(settings)
    err = APIStatusError(
        "bad",
        response=MagicMock(status_code=400, headers={}),
        body={"code": "tool_use_failed", "message": "Failed to call a function"},
    )
    err.status_code = 400
    plain = MagicMock()
    plain.choices = [MagicMock(message=MagicMock(content="Summary without tools", tool_calls=None))]
    create = AsyncMock(side_effect=[err, plain])
    client._client = MagicMock()
    client._client.chat.completions.create = create

    async def tool_caller(name, args):
        return {"ok": True}

    reply = await client.chat_with_tools(
        "news please",
        tools=[{"type": "function", "function": {"name": "web_search", "parameters": {}}}],
        tool_caller=tool_caller,
    )
    assert reply == "Summary without tools"
    assert create.await_args_list[0].kwargs["model"] == "llama-3.3-70b-versatile"
    assert "tools" in create.await_args_list[0].kwargs
    assert create.await_args_list[1].kwargs.get("tools") is None
