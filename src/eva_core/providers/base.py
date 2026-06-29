"""Shared types and the base interface for chat providers."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Literal

Role = Literal["system", "user", "assistant"]


class ProviderError(RuntimeError):
    """Raised when a provider cannot fulfil a request."""


@dataclass
class ChatMessage:
    """A single message in a conversation."""

    role: Role
    content: str


@dataclass
class ChatResult:
    """The outcome of a chat completion request."""

    provider: str
    model: str
    content: str
    raw: dict = field(default_factory=dict)


class ChatProvider(abc.ABC):
    """Base class every chat provider implements."""

    #: Short, stable identifier used in the API (e.g. "openai").
    name: str = "base"
    #: Human-friendly label shown in the UI.
    label: str = "Base"

    def __init__(self, model: str) -> None:
        self.model = model

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Return True when the provider has the credentials it needs."""

    @abc.abstractmethod
    def complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> ChatResult:
        """Run a chat completion and return the assistant reply."""

    def _split_system(self, messages: list[ChatMessage]) -> tuple[str | None, list[ChatMessage]]:
        """Split out leading/extra system messages from the conversation."""
        system_parts = [m.content for m in messages if m.role == "system"]
        convo = [m for m in messages if m.role != "system"]
        system = "\n\n".join(system_parts) if system_parts else None
        return system, convo
