"""Session-local user history for bounded multi-turn retrieval."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from numbers import Real
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ktem.local_qa_ollama import OllamaLocalClient

DEFAULT_MAX_TURNS = 3
DEFAULT_HISTORY_TOKEN_LIMIT = 1024
_MAX_REWRITE_CHARS = 1024
_MAX_REWRITE_TURNS = 3
_MAX_REWRITE_HISTORY_CHARS = 8192


def _validate_count(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("token counter must return a non-negative integer")
    return value


@dataclass(frozen=True)
class ConversationState:
    """Immutable, bounded user-only conversation history."""

    user_turns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.user_turns, tuple) or any(
            not isinstance(turn, str) for turn in self.user_turns
        ):
            raise TypeError("user_turns must be a tuple of strings")

    def append_user(
        self,
        question: str,
        *,
        max_turns: int,
        token_limit: int,
        count_tokens: Callable[[str], int],
    ) -> ConversationState:
        if not isinstance(question, str):
            raise TypeError("question must be a string")
        if (
            isinstance(max_turns, bool)
            or not isinstance(max_turns, int)
            or max_turns < 0
        ):
            raise ValueError("max_turns must be a non-negative integer")
        if (
            isinstance(token_limit, bool)
            or not isinstance(token_limit, int)
            or token_limit < 0
        ):
            raise ValueError("token_limit must be a non-negative integer")
        if not callable(count_tokens):
            raise TypeError("count_tokens must be callable")

        clean_question = question.strip()
        if not clean_question or max_turns == 0 or token_limit == 0:
            return self._bounded_existing(
                max_turns=max_turns,
                token_limit=token_limit,
                count_tokens=count_tokens,
            )

        candidates = (*self.user_turns, clean_question)[-max_turns:]
        start = len(candidates)
        for candidate_start in range(len(candidates) - 1, -1, -1):
            joined = "\n".join(candidates[candidate_start:])
            token_count = _validate_count(count_tokens(joined))
            if token_count > token_limit:
                break
            start = candidate_start
        return ConversationState(tuple(candidates[start:]))

    def _bounded_existing(
        self,
        *,
        max_turns: int,
        token_limit: int,
        count_tokens: Callable[[str], int],
    ) -> ConversationState:
        if max_turns == 0 or token_limit == 0:
            return ConversationState()
        candidates = self.user_turns[-max_turns:]
        start = len(candidates)
        for candidate_start in range(len(candidates) - 1, -1, -1):
            token_count = _validate_count(
                count_tokens("\n".join(candidates[candidate_start:]))
            )
            if token_count > token_limit:
                break
            start = candidate_start
        return ConversationState(tuple(candidates[start:]))

    def clear(self) -> ConversationState:
        return ConversationState()


def user_turns_from_history(
    history: Sequence[Any] | None,
    *,
    max_turns: int = DEFAULT_MAX_TURNS,
    token_limit: int = DEFAULT_HISTORY_TOKEN_LIMIT,
    count_tokens: Callable[[str], int],
) -> tuple[str, ...]:
    """Extract only prior user messages from product chat pairs and bound them."""
    state = ConversationState()
    if history is None:
        return state.user_turns
    if isinstance(history, (str, bytes)):
        return state.user_turns
    for exchange in history:
        if not isinstance(exchange, (list, tuple)) or not exchange:
            continue
        user_message = exchange[0]
        if isinstance(user_message, str):
            state = state.append_user(
                user_message,
                max_turns=max_turns,
                token_limit=token_limit,
                count_tokens=count_tokens,
            )
    return state.user_turns


class OllamaQueryRewriter:
    """Resolve a follow-up with recent user turns using a loopback Ollama client."""

    def __init__(self, client: OllamaLocalClient, *, timeout: float = 10.0) -> None:
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, Real)
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError("rewrite timeout must be a finite positive number")
        endpoint = getattr(client, "endpoint", None)
        from ktem.local_qa_ollama import _validate_endpoint

        _validate_endpoint(endpoint)
        if not callable(getattr(client, "rewrite_query", None)):
            raise TypeError("client must provide rewrite_query")
        self.client = client
        self.timeout = float(timeout)

    def __call__(self, query: str, user_turns: tuple[str, ...]) -> str:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must not be empty")
        if not isinstance(user_turns, tuple) or any(
            not isinstance(turn, str) for turn in user_turns
        ):
            raise TypeError("user_turns must be a tuple of strings")
        if len(user_turns) > _MAX_REWRITE_TURNS:
            raise ValueError("user history exceeds the rewrite turn limit")
        if sum(len(turn) for turn in user_turns) > _MAX_REWRITE_HISTORY_CHARS:
            raise ValueError("user history exceeds the rewrite size limit")

        result = self.client.rewrite_query(
            query.strip(), user_turns, timeout=self.timeout
        )
        if not isinstance(result, str):
            raise ValueError("Ollama rewrite must be plain text")
        candidate = result.strip()
        if (
            not candidate
            or len(candidate) > _MAX_REWRITE_CHARS
            or "\n" in candidate
            or "\r" in candidate
            or candidate.startswith(("{", "[", "```"))
            or any(ord(character) < 32 for character in candidate)
        ):
            raise ValueError("Ollama rewrite must be one bounded plain question")
        return candidate
