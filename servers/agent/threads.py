"""
Conversation threading, branching, checkpoints, and context compaction for Cerberus.
"""

from __future__ import annotations

import copy
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from servers.logging_setup import get_logger
from servers.models import Message, ToolCall, ToolCallFunction, message_from_api

log = get_logger("threads")


def clone_message(msg: Message) -> Message:
    tool_calls = None
    if msg.tool_calls is not None:
        tool_calls = [
            ToolCall(
                id=tc.id,
                type=tc.type,
                function=ToolCallFunction(
                    name=tc.function.name,
                    arguments=tc.function.arguments,
                ),
            )
            for tc in msg.tool_calls
        ]
    return Message(
        role=msg.role,
        content=msg.content,
        tool_calls=tool_calls,
        tool_call_id=msg.tool_call_id,
        name=msg.name,
    )


def clone_messages(messages: list[Message]) -> list[Message]:
    return [clone_message(m) for m in messages]


@dataclass
class ThreadBranch:
    id: str
    name: str
    parent_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    messages: list[Message] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id,
            "created_at": self.created_at,
            "messages": [m.to_api_dict() for m in self.messages],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ThreadBranch":
        raw_msgs = data.get("messages") or []
        messages = [message_from_api(m) if isinstance(m, dict) else m for m in raw_msgs]
        return cls(
            id=str(data.get("id") or f"br_{uuid.uuid4().hex[:8]}"),
            name=str(data.get("name") or "unnamed"),
            parent_id=data.get("parent_id"),
            created_at=float(data.get("created_at") or time.time()),
            messages=messages,
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class ThreadCheckpoint:
    id: str
    name: str
    branch_id: str
    turn_index: int
    messages: list[Message]
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "branch_id": self.branch_id,
            "turn_index": self.turn_index,
            "messages": [m.to_api_dict() for m in self.messages],
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ThreadCheckpoint":
        raw_msgs = data.get("messages") or []
        messages = [message_from_api(m) if isinstance(m, dict) else m for m in raw_msgs]
        return cls(
            id=str(data.get("id") or f"chk_{uuid.uuid4().hex[:8]}"),
            name=str(data.get("name") or "checkpoint"),
            branch_id=str(data.get("branch_id") or "main"),
            turn_index=int(data.get("turn_index") or 0),
            messages=messages,
            created_at=float(data.get("created_at") or time.time()),
            metadata=dict(data.get("metadata") or {}),
        )


class ThreadManager:
    """Manages conversational branches and checkpoints."""

    def __init__(self, initial_messages: Optional[list[Message]] = None):
        main_branch = ThreadBranch(
            id="main",
            name="main",
            messages=clone_messages(initial_messages or []),
        )
        self.branches: dict[str, ThreadBranch] = {"main": main_branch}
        self.active_branch_id: str = "main"
        self.checkpoints: dict[str, ThreadCheckpoint] = {}

    @property
    def current_branch(self) -> ThreadBranch:
        return self.branches[self.active_branch_id]

    @property
    def messages(self) -> list[Message]:
        return self.current_branch.messages

    def append(self, message: Message) -> None:
        self.current_branch.messages.append(message)

    def branch(self, name: str) -> ThreadBranch:
        new_id = f"br_{uuid.uuid4().hex[:8]}"
        b = ThreadBranch(
            id=new_id,
            name=name,
            parent_id=self.active_branch_id,
            messages=clone_messages(self.current_branch.messages),
        )
        self.branches[new_id] = b
        self.active_branch_id = new_id
        return b

    def switch_branch(self, branch_id: str) -> None:
        if branch_id not in self.branches:
            raise KeyError(f"Unknown branch {branch_id}")
        self.active_branch_id = branch_id

    def checkpoint(self, name: str) -> ThreadCheckpoint:
        chk_id = f"chk_{uuid.uuid4().hex[:8]}"
        chk = ThreadCheckpoint(
            id=chk_id,
            name=name,
            branch_id=self.active_branch_id,
            turn_index=len(self.current_branch.messages),
            messages=clone_messages(self.current_branch.messages),
        )
        self.checkpoints[chk_id] = chk
        return chk

    def restore_checkpoint(self, checkpoint_id: str) -> None:
        if checkpoint_id not in self.checkpoints:
            raise KeyError(f"Unknown checkpoint {checkpoint_id}")
        chk = self.checkpoints[checkpoint_id]
        self.current_branch.messages = clone_messages(chk.messages)
