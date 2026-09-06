"""
HTTP client for OpenAI-compatible chat completions APIs for Cerberus.

Works with Pollinations (`https://gen.pollinations.ai/v1`), Ollama
(`http://localhost:11434/v1`), vLLM, LM Studio, and any other endpoint
that implements `/v1/chat/completions`.
"""

from __future__ import annotations

import json
import time
from typing import Any, Iterator, Optional

import httpx

from servers.config import ProviderConfig
from servers.logging_setup import get_logger
from servers.models import ChatChoice, ChatCompletion, Message, ToolCall, ToolCallFunction, message_from_api

log = get_logger("provider")


class ProviderError(RuntimeError):
    """Raised when the remote model endpoint returns an error or bad payload."""

    def __init__(self, message: str, *, status_code: Optional[int] = None, body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class OpenAICompatibleClient:
    """
    Thin, dependency-light client for OpenAI-compatible completions.
    """

    def __init__(self, config: ProviderConfig, api_key: str = ""):
        self.config = config
        self.api_key = api_key
        self.last_usage: dict[str, Any] = {}
        self._client = httpx.Client(
            base_url=config.base_url.rstrip("/"),
            timeout=httpx.Timeout(config.timeout, connect=30.0),
            headers=self._build_headers(),
        )

    def _record_usage(self, raw: Any) -> None:
        if not isinstance(raw, dict) or not raw:
            self.last_usage = {}
            return
        prompt = int(
            raw.get("prompt_tokens")
            or raw.get("input_tokens")
            or raw.get("promptTokens")
            or 0
        )
        completion = int(
            raw.get("completion_tokens")
            or raw.get("output_tokens")
            or raw.get("completionTokens")
            or 0
        )
        total = int(raw.get("total_tokens") or raw.get("totalTokens") or 0)
        if not total:
            total = prompt + completion
        self.last_usage = {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
        }

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Cerberus/2.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def set_api_key(self, api_key: str) -> None:
        self.api_key = api_key or ""
        if self.api_key:
            self._client.headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            self._client.headers.pop("Authorization", None)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "OpenAICompatibleClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _build_body(
        self,
        messages: list[Message],
        tools: Optional[list[dict[str, Any]]],
        *,
        stream: bool,
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model or self.config.model,
            "messages": [m.to_api_dict() for m in messages],
            "temperature": self.config.temperature,
            "stream": stream,
        }
        if self.config.max_tokens is not None:
            body["max_tokens"] = self.config.max_tokens
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        return body

    def chat(
        self,
        messages: list[Message],
        tools: Optional[list[dict[str, Any]]] = None,
        *,
        model: Optional[str] = None,
    ) -> ChatCompletion:
        body = self._build_body(messages, tools, stream=False, model=model)
        model_id = body.get("model")
        log.info(
            "POST %s/chat/completions  model=%s  msgs=%d  tools=%s  stream=false",
            self.config.base_url.rstrip("/"),
            model_id,
            len(messages),
            bool(tools),
        )
        t0 = time.monotonic()
        try:
            resp = self._client.post("/chat/completions", json=body)
        except httpx.TimeoutException as exc:
            log.error("provider timeout after %.1fs (limit=%ss)", time.monotonic() - t0, self.config.timeout)
            raise ProviderError(f"Request timed out after {self.config.timeout}s") from exc
        except httpx.HTTPError as exc:
            log.error("provider transport error: %s", exc)
            raise ProviderError(f"HTTP transport error: {exc}") from exc

        if resp.status_code >= 400:
            log.error("provider HTTP %s: %s", resp.status_code, resp.text[:400])
            raise ProviderError(
                f"Provider returned HTTP {resp.status_code}: {resp.text[:800]}",
                status_code=resp.status_code,
                body=resp.text,
            )

        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            log.error("provider non-JSON body: %s", resp.text[:200])
            raise ProviderError(f"Non-JSON response: {resp.text[:400]}") from exc

        usage_raw = data.get("usage") or {}
        self._record_usage(usage_raw)
        log.info(
            "provider OK  HTTP %s  %.1fs  usage=%s",
            resp.status_code,
            time.monotonic() - t0,
            self.last_usage or usage_raw,
        )
        return self._parse_completion(data)

    def chat_stream(
        self,
        messages: list[Message],
        tools: Optional[list[dict[str, Any]]] = None,
        *,
        model: Optional[str] = None,
    ) -> Iterator[str]:
        msg = self.chat_collect(messages, tools=tools, model=model)
        if msg.tool_calls:
            raise _StreamHasToolCalls()
        if msg.content:
            yield msg.content

    def chat_collect(
        self,
        messages: list[Message],
        tools: Optional[list[dict[str, Any]]] = None,
        *,
        model: Optional[str] = None,
        on_text_delta: Optional[Any] = None,
        stream: bool = False,
    ) -> Message:
        if not stream:
            return self.chat(messages, tools=tools, model=model).first_message

        body = self._build_body(messages, tools, stream=True, model=model)
        body.setdefault("stream_options", {"include_usage": True})
        content_parts: list[str] = []
        tool_acc: dict[int, dict[str, str]] = {}
        saw_tool_calls = False
        stream_usage: dict[str, Any] = {}

        try:
            with self._client.stream("POST", "/chat/completions", json=body) as resp:
                if resp.status_code >= 400:
                    err_text = resp.read().decode("utf-8", errors="replace")
                    if resp.status_code in {400, 404, 422, 501}:
                        return self.chat(messages, tools=tools, model=model).first_message
                    raise ProviderError(
                        f"Provider returned HTTP {resp.status_code}: {err_text[:800]}",
                        status_code=resp.status_code,
                        body=err_text,
                    )
                for line in resp.iter_lines():
                    if not line:
                        continue
                    if line.startswith("data:"):
                        payload = line[5:].strip()
                    else:
                        payload = line.strip()
                    if not payload:
                        continue
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(chunk.get("usage"), dict) and chunk["usage"]:
                        stream_usage = chunk["usage"]
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    if "message" in choices[0] and not delta:
                        if isinstance(chunk.get("usage"), dict):
                            self._record_usage(chunk["usage"])
                        return message_from_api(choices[0]["message"])

                    piece = delta.get("content")
                    if piece:
                        content_parts.append(piece)
                        if on_text_delta and not saw_tool_calls:
                            on_text_delta(piece)

                    for tc_delta in delta.get("tool_calls") or []:
                        saw_tool_calls = True
                        idx = int(tc_delta.get("index") or 0)
                        slot = tool_acc.setdefault(
                            idx, {"id": "", "name": "", "arguments": ""}
                        )
                        if tc_delta.get("id"):
                            slot["id"] = str(tc_delta["id"])
                        fn = tc_delta.get("function") or {}
                        if fn.get("name"):
                            slot["name"] = str(fn["name"])
                        if fn.get("arguments"):
                            slot["arguments"] += str(fn["arguments"])
        except httpx.TimeoutException as exc:
            raise ProviderError(f"Stream timed out after {self.config.timeout}s") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"HTTP transport error: {exc}") from exc

        self._record_usage(stream_usage)

        tool_calls = None
        if tool_acc:
            tool_calls = [
                ToolCall(
                    id=tool_acc[i]["id"] or f"call_{i}",
                    type="function",
                    function=ToolCallFunction(
                        name=tool_acc[i]["name"],
                        arguments=tool_acc[i]["arguments"] or "{}",
                    ),
                )
                for i in sorted(tool_acc.keys())
            ]

        return Message(
            role="assistant",
            content="".join(content_parts) if content_parts else None,
            tool_calls=tool_calls,
        )

    def chat_auto(
        self,
        messages: list[Message],
        tools: Optional[list[dict[str, Any]]] = None,
        *,
        model: Optional[str] = None,
        prefer_stream: bool = False,
        on_text_delta: Optional[Any] = None,
    ) -> Message:
        if tools and not prefer_stream:
            completion = self.chat(messages, tools=tools, model=model)
            return completion.first_message

        return self.chat_collect(
            messages,
            tools=tools,
            model=model,
            on_text_delta=on_text_delta,
            stream=prefer_stream,
        )

    @staticmethod
    def _parse_completion(data: dict[str, Any]) -> ChatCompletion:
        choices_raw = data.get("choices") or []
        choices: list[ChatChoice] = []
        for ch in choices_raw:
            msg_data = ch.get("message") or {}
            choices.append(
                ChatChoice(
                    message=message_from_api(msg_data),
                    finish_reason=ch.get("finish_reason"),
                )
            )
        return ChatCompletion(
            id=str(data.get("id") or ""),
            model=str(data.get("model") or ""),
            choices=choices,
            usage=dict(data.get("usage") or {}),
        )


class _StreamHasToolCalls(Exception):
    """Internal signal: streaming response included tool_calls."""
