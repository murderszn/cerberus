"""
Multi-turn tool-evaluation loop with soft budget control for Cerberus.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from servers.agent.prompts import build_system_prompt, get_orchestrator_prompt
from servers.agent.threads import ThreadBranch, ThreadCheckpoint, ThreadManager
from servers.config import AppConfig
from servers.logging_setup import get_logger
from servers.models import Message, TokenUsage, ToolCall
from servers.provider.client import OpenAICompatibleClient, ProviderError
from servers.tools.registry import ToolRegistry

log = get_logger("agent")


class CircuitBreakerTripped(RuntimeError):
    """Raised when the agent exceeds max sequential tool rounds."""


@dataclass
class LoopResult:
    final_text: str
    tool_rounds: int
    messages: list[Message] = field(default_factory=list)
    stopped_reason: str = "completed"
    usage: TokenUsage = field(default_factory=TokenUsage)


OnToolStart = Callable[[ToolCall, dict[str, Any]], None]
OnToolEnd = Callable[[ToolCall, str], None]
OnAssistantText = Callable[[str], None]
OnStatus = Callable[[str], None]
OnStreamDelta = Callable[[str], None]


class AgentLoop:
    """Stateful multi-turn conversation manager for Cerberus personas and orchestrator."""

    def __init__(
        self,
        config: AppConfig,
        client: OpenAICompatibleClient,
        registry: ToolRegistry,
        *,
        persona_name: Optional[str] = None,
        on_tool_start: Optional[OnToolStart] = None,
        on_tool_end: Optional[OnToolEnd] = None,
        on_assistant_text: Optional[OnAssistantText] = None,
        on_status: Optional[OnStatus] = None,
        on_stream_delta: Optional[OnStreamDelta] = None,
    ):
        self.config = config
        self.client = client
        self.registry = registry
        self.persona_name = persona_name
        self.on_tool_start = on_tool_start
        self.on_tool_end = on_tool_end
        self.on_assistant_text = on_assistant_text
        self.on_status = on_status
        self.on_stream_delta = on_stream_delta
        self.threads = ThreadManager()
        self.session_usage: TokenUsage = TokenUsage()
        self._cancel_requested = False
        self._bootstrap_system()

    @property
    def messages(self) -> list[Message]:
        return self.threads.messages

    @messages.setter
    def messages(self, msgs: list[Message]) -> None:
        self.threads.current_branch.messages = msgs

    def reset(self) -> None:
        self.messages.clear()
        self.session_usage = TokenUsage()
        self._bootstrap_system()

    def set_mode(self, mode: str) -> None:
        """Switch build/plan mid-session, refreshing the system prompt in place."""
        mode = (mode or "").strip().lower()
        if mode not in {"build", "plan"}:
            raise ValueError(f"mode must be 'build' or 'plan', got {mode!r}")
        self.config.agent_mode = mode
        self._bootstrap_system()

    def request_cancel(self) -> None:
        """Ask a running run() to stop after the current step (thread-safe)."""
        self._cancel_requested = True

    def _cancelled(self) -> bool:
        return bool(getattr(self, "_cancel_requested", False))

    def _system_text(self) -> str:
        mode = self.config.agent_mode
        extra = self.config.system_prompt_extra
        if self.persona_name:
            return build_system_prompt(self.persona_name, mode=mode, custom_instructions=extra)
        return get_orchestrator_prompt(mode=mode, custom_instructions=extra)

    def _bootstrap_system(self) -> None:
        text = self._system_text()
        if self.messages and self.messages[0].role == "system":
            self.messages[0] = Message(role="system", content=text)
        else:
            self.messages.insert(0, Message(role="system", content=text))

    def _status(self, text: str) -> None:
        if self.on_status:
            try:
                self.on_status(text)
            except Exception:
                pass

    def run(self, user_input: str) -> LoopResult:
        if not user_input or not user_input.strip():
            return LoopResult(final_text="", tool_rounds=0, messages=self.messages, stopped_reason="empty")
        self._cancel_requested = False

        self.messages.append(Message(role="user", content=user_input.strip()))
        tools = self.registry.openai_tools()
        max_rounds = max(1, self.config.tools.max_tool_rounds)
        tool_executions = 0
        turn = 0
        run_usage = TokenUsage()
        stream_final = bool(self.config.provider.stream_final)

        while True:
            if self._cancelled():
                return LoopResult(
                    final_text="Stopped by user.",
                    tool_rounds=tool_executions,
                    messages=self.messages,
                    stopped_reason="cancelled",
                    usage=run_usage,
                )
            turn += 1
            self._status(f"Consulting {self.config.provider.model}… (turn {turn})")
            log.info("model request turn=%d model=%s", turn, self.config.provider.model)

            prefer_stream = stream_final and tool_executions > 0 and bool(self.on_stream_delta)
            streamed_to_ui = False

            def _delta(chunk: str) -> None:
                nonlocal streamed_to_ui
                streamed_to_ui = True
                if self.on_stream_delta:
                    self.on_stream_delta(chunk)

            try:
                if prefer_stream:
                    assistant = self.client.chat_collect(
                        self.messages,
                        tools=tools if tools else None,
                        model=self.config.provider.model,
                        on_text_delta=_delta,
                        stream=True,
                    )
                    if assistant.tool_calls:
                        streamed_to_ui = False
                else:
                    assistant = self.client.chat(
                        self.messages,
                        tools=tools if tools else None,
                        model=self.config.provider.model,
                    ).first_message
            except ProviderError as exc:
                log.error("Provider error: %s", exc)
                raise

            # Accumulate usage if available
            if hasattr(self.client, "last_usage") and self.client.last_usage:
                u = TokenUsage.from_api(self.client.last_usage)
                run_usage.add(u)
                self.session_usage.add(u)

            self.messages.append(assistant)

            if assistant.tool_calls:
                if tool_executions >= max_rounds:
                    log.warning("Tool budget exceeded (%d/%d rounds)", tool_executions, max_rounds)
                    self._status("Tool budget reached — generating wrap-up summary…")
                    # Force one wrap-up turn without tools
                    self.messages.append(
                        Message(
                            role="user",
                            content="Tool budget exceeded. Please summarize current status, remaining risks, and next steps without executing further tools.",
                        )
                    )
                    final_msg = self.client.chat(
                        self.messages,
                        tools=None,
                        model=self.config.provider.model,
                    ).first_message
                    self.messages.append(final_msg)
                    if self.on_assistant_text and final_msg.content:
                        self.on_assistant_text(final_msg.content)
                    return LoopResult(
                        final_text=final_msg.content or "",
                        tool_rounds=tool_executions,
                        messages=self.messages,
                        stopped_reason="circuit_breaker",
                        usage=run_usage,
                    )

                for tc in assistant.tool_calls:
                    if self._cancelled():
                        break
                    tool_executions += 1
                    fn_name = tc.function.name
                    try:
                        args = tc.function.parsed_args()
                    except Exception as err:
                        args = {}
                        res_str = f"ERROR parsing arguments for {fn_name}: {err}"
                        self.messages.append(
                            Message(role="tool", content=res_str, tool_call_id=tc.id, name=fn_name)
                        )
                        continue

                    if self.on_tool_start:
                        try:
                            self.on_tool_start(tc, args)
                        except Exception:
                            pass

                    self._status(f"Running tool: {fn_name}")
                    result_str = self.registry.dispatch(fn_name, args)

                    if self.on_tool_end:
                        try:
                            self.on_tool_end(tc, result_str)
                        except Exception:
                            pass

                    self.messages.append(
                        Message(role="tool", content=result_str, tool_call_id=tc.id, name=fn_name)
                    )
                continue

            # No tool calls -> Assistant delivered final text
            text = assistant.content or ""
            if self.on_assistant_text and not streamed_to_ui and text:
                self.on_assistant_text(text)

            return LoopResult(
                final_text=text,
                tool_rounds=tool_executions,
                messages=self.messages,
                stopped_reason="completed",
                usage=run_usage,
            )
