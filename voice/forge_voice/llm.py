"""Groq LLM client with tool-calling loop."""

from __future__ import annotations

import json
import logging
import re
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from forge_memory.config import ForgeSettings
from openai import APIStatusError, AsyncOpenAI, RateLimitError

from forge_voice.persona import build_system_prompt

logger = logging.getLogger(__name__)

ToolCaller = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]

# Only these warrant switching models. 400 tool_use_failed is handled separately.
_FALLBACK_STATUS_CODES = {429, 503}


def sanitize_message(message: dict[str, Any]) -> dict[str, Any]:
    """Keep only Groq-compatible chat message fields."""
    role = message.get("role")
    clean: dict[str, Any] = {"role": role}

    if role == "tool":
        clean["tool_call_id"] = message["tool_call_id"]
        clean["content"] = message.get("content") or ""
        return clean

    if "content" in message:
        clean["content"] = message.get("content")

    if role == "assistant" and message.get("tool_calls"):
        clean_calls: list[dict[str, Any]] = []
        for call in message["tool_calls"]:
            if isinstance(call, dict):
                fn = call.get("function") or {}
                clean_calls.append(
                    {
                        "id": call["id"],
                        "type": call.get("type", "function"),
                        "function": {
                            "name": fn.get("name", ""),
                            "arguments": fn.get("arguments") or "{}",
                        },
                    }
                )
            else:
                clean_calls.append(
                    {
                        "id": call.id,
                        "type": getattr(call, "type", None) or "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments or "{}",
                        },
                    }
                )
        clean["tool_calls"] = clean_calls

    return clean


def sanitize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [sanitize_message(m) for m in messages]


def assistant_message_to_dict(message: Any) -> dict[str, Any]:
    """Convert an OpenAI assistant message to a Groq-safe dict (no annotations)."""
    payload: dict[str, Any] = {
        "role": "assistant",
        "content": message.content,
    }
    tool_calls = getattr(message, "tool_calls", None) or []
    if tool_calls:
        payload["tool_calls"] = tool_calls
    return sanitize_message(payload)


def parse_failed_generation(failed_generation: str) -> list[dict[str, Any]]:
    """Parse Groq failed_generation XML-ish tool calls into {name, arguments} dicts."""
    if not failed_generation:
        return []

    parsed_calls: list[dict[str, Any]] = []
    # Patterns seen from Groq:
    #   <function=web_search{"query": "x", "max_results": 5}</function>
    #   <function=web_search({"query": "x", "max_results": 5}</function>
    pattern = re.compile(
        r"<function\s*=\s*(?P<name>[A-Za-z0-9_]+)\s*\(?\s*(?P<body>\{.*)",
        re.DOTALL,
    )
    for match in pattern.finditer(failed_generation):
        name = match.group("name")
        body = match.group("body")
        # Trim trailing </function> and balance braces if truncated
        body = re.sub(r"</function>\s*$", "", body.strip())
        body = _balance_json_object(body)
        try:
            arguments = json.loads(body)
        except json.JSONDecodeError:
            logger.warning("Could not parse failed_generation args for %s: %r", name, body)
            continue
        if isinstance(arguments, dict):
            parsed_calls.append({"name": name, "arguments": arguments})
    return parsed_calls


def _balance_json_object(text: str) -> str:
    """Append missing closing braces for truncated JSON objects."""
    text = text.strip()
    # Drop a trailing unmatched '(' from patterns like web_search({...}
    if text.endswith(")"):
        text = text[:-1].rstrip()
    open_braces = text.count("{") - text.count("}")
    if open_braces > 0:
        text += "}" * open_braces
    return text


def _should_fallback(exc: Exception) -> bool:
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, APIStatusError):
        return getattr(exc, "status_code", None) in _FALLBACK_STATUS_CODES
    return False


def _extract_tool_failure(exc: APIStatusError) -> tuple[str | None, str | None]:
    """Return (error_code, failed_generation) from a Groq/OpenAI status error.

    The OpenAI SDK unwraps ``{"error": {...}}`` and stores the inner object on
    ``exc.body``, so we must read ``code`` / ``failed_generation`` at the top
    level. Nested ``body["error"]`` is kept as a fallback for mocks/tests.
    """
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        if "failed_generation" in body or body.get("code") == "tool_use_failed":
            return body.get("code") or getattr(exc, "code", None), body.get("failed_generation")
        nested = body.get("error")
        if isinstance(nested, dict):
            return nested.get("code"), nested.get("failed_generation")
    return getattr(exc, "code", None), None


@dataclass
class LLMClient:
    settings: ForgeSettings
    _client: AsyncOpenAI | None = None
    _active_models: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self._active_models:
            self._active_models = [self.settings.llm_model, *self.settings.llm_fallback_models]

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.settings.groq_api_key or "missing",
                base_url=self.settings.groq_base_url,
            )
        return self._client

    async def chat_text(
        self,
        user_text: str,
        *,
        history: list[dict[str, Any]] | None = None,
    ) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": build_system_prompt(self.settings)},
        ]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_text})

        response = await self._create_with_fallback(messages)
        return response.choices[0].message.content or ""

    async def chat_with_tools(
        self,
        user_text: str,
        *,
        tools: list[dict[str, Any]],
        tool_caller: ToolCaller,
        history: list[dict[str, Any]] | None = None,
        turn_cancelled: Callable[[], bool] | None = None,
    ) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": build_system_prompt(self.settings, tools_enabled=True)},
        ]
        if history:
            messages.extend(sanitize_messages(history))
        messages.append({"role": "user", "content": user_text})

        for _ in range(self.settings.llm_max_tool_rounds):
            try:
                response = await self._create_with_fallback(messages, tools=tools)
            except APIStatusError as exc:
                recovered = await self._recover_failed_tool_call(
                    exc,
                    messages=messages,
                    tools=tools,
                    tool_caller=tool_caller,
                    turn_cancelled=turn_cancelled,
                )
                if recovered is not None:
                    if recovered.get("final"):
                        return recovered["text"]
                    continue
                raise

            message = response.choices[0].message
            tool_calls = message.tool_calls or []
            if not tool_calls:
                return message.content or ""

            messages.append(assistant_message_to_dict(message))
            for call in tool_calls:
                if turn_cancelled and turn_cancelled():
                    logger.info("Turn cancelled; abandoning tool calls")
                    return message.content or "Cancelled."
                name = call.function.name
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                logger.info("Calling tool %s(%s)", name, args)
                result = await tool_caller(name, args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result),
                    }
                )

        return "I hit the tool limit for this turn."

    async def _recover_failed_tool_call(
        self,
        exc: APIStatusError,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_caller: ToolCaller,
        turn_cancelled: Callable[[], bool] | None,
    ) -> dict[str, Any] | None:
        """Parse failed_generation and execute tools; return continue/final marker."""
        code, failed_gen = _extract_tool_failure(exc)

        if code != "tool_use_failed":
            logger.debug(
                "APIStatusError not recoverable as tool_use_failed (code=%r body=%r)",
                code,
                getattr(exc, "body", None),
            )
            return None

        parsed_calls = parse_failed_generation(failed_gen or "")
        if not parsed_calls:
            logger.warning(
                "tool_use_failed (unparseable); answering without tools"
            )
            response = await self._create_with_fallback(messages, tools=None)
            return {"final": True, "text": response.choices[0].message.content or ""}

        # Synthesize a proper assistant tool_calls message, then execute
        synthetic_calls = []
        for parsed in parsed_calls:
            call_id = f"call_{uuid.uuid4().hex[:8]}"
            synthetic_calls.append(
                {
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": parsed["name"],
                        "arguments": json.dumps(parsed["arguments"]),
                    },
                }
            )

        messages.append(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": synthetic_calls,
            }
        )

        for call in synthetic_calls:
            if turn_cancelled and turn_cancelled():
                return {"final": True, "text": "Cancelled."}
            name = call["function"]["name"]
            args = json.loads(call["function"]["arguments"])
            logger.info("Recovered tool call %s(%s)", name, args)
            result = await tool_caller(name, args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result),
                }
            )

        return {"final": False}

    async def _create_with_fallback(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> Any:
        clean_messages = sanitize_messages(messages)
        last_error: Exception | None = None
        for index, model in enumerate(self._active_models):
            try:
                kwargs: dict[str, Any] = {
                    "model": model,
                    "messages": clean_messages,
                    "temperature": self.settings.llm_temperature,
                }
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"
                return await self.client.chat.completions.create(**kwargs)
            except (RateLimitError, APIStatusError) as exc:
                last_error = exc
                if _should_fallback(exc) and index + 1 < len(self._active_models):
                    next_model = self._active_models[index + 1]
                    logger.warning("Forge: switching LLM to %s (%s)", next_model, exc)
                    continue
                raise
        if last_error:
            raise last_error
        raise RuntimeError("No LLM models configured")
