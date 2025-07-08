from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Optional, TypeVar

import numpy as np
from langchain.schema.messages import AIMessage as LCAIMessage
from langchain.schema.messages import HumanMessage as LCHumanMessage
from langchain.schema.messages import SystemMessage as LCSystemMessage
from llama_index.core.bridge.pydantic import Field
from llama_index.core.schema import Document as BaseDocument
from pydantic import ConfigDict

if TYPE_CHECKING:
    from haystack.schema import Document as HaystackDocument
    from openai.types.chat.chat_completion_message_param import (
        ChatCompletionMessageParam,
    )

IO_Type = TypeVar("IO_Type", "Document", str)
SAMPLE_TEXT = "A sample Document from kotaemon"


class Document(BaseDocument):
    """
    Base document class, mostly inherited from Document class from llama-index.

    This class accept one positional argument `content` of an arbitrary type, which will
        store the raw content of the document. If specified, the class will use
        `content` to initialize the base llama_index class.

    Attributes:
        content: raw content of the document, can be anything
        source: id of the source of the Document. Optional.
        channel: the channel to show the document. Optional.:
            - chat: show in chat message
            - info: show in information panel
            - index: show in index panel
            - debug: show in debug panel
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    content: Any = None
    source: Optional[str] = None
    channel: Optional[Literal["chat", "info", "index", "debug", "plot"]] = None

    def __init__(self, content: Optional[Any] = None, *args, **kwargs):
        if content is None:
            if kwargs.get("text", None) is not None:
                kwargs["content"] = kwargs["text"]
            elif kwargs.get("embedding", None) is not None:
                emb = kwargs["embedding"]
                if isinstance(emb, np.ndarray):
                    emb = emb.tolist()
                kwargs["embedding"] = emb
                kwargs["content"] = emb
                # default text indicating this document only contains embedding
                kwargs["text"] = "<EMBEDDING>"
        elif isinstance(content, Document):
            # TODO: simplify the Document class
            if hasattr(content, "model_copy"):
                obj = content.model_copy(update=kwargs)
            else:
                obj = content.copy(update=kwargs)
            data = obj.__dict__.copy()
            emb = content.embedding
            if isinstance(emb, np.ndarray):
                data["embedding"] = emb.tolist()
                super().__init__(*args, **data)
                object.__setattr__(self, "embedding", emb)
            else:
                super().__init__(*args, **data)
            return
        else:
            if isinstance(content, np.ndarray):
                content = content.tolist()
            kwargs["content"] = content
            if content:
                kwargs["text"] = str(content)
            else:
                kwargs["text"] = ""
        super().__init__(*args, **kwargs)

    def __bool__(self):
        return bool(self.content)

    @classmethod
    def example(cls) -> "Document":
        document = Document(
            text=SAMPLE_TEXT,
            metadata={"filename": "README.md", "category": "codebase"},
        )
        return document

    def to_haystack_format(self) -> "HaystackDocument":
        """Convert struct to Haystack document format."""
        from haystack.schema import Document as HaystackDocument

        metadata = self.metadata or {}
        text = self.text
        return HaystackDocument(content=text, meta=metadata)

    def __str__(self):
        return str(self.content)

    def model_dump(self, *, serialize: bool = False, **kwargs):
        data = super().model_dump(**kwargs)
        if serialize:

            def _convert(obj):
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                if isinstance(obj, dict):
                    return {k: _convert(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [_convert(v) for v in obj]
                return obj

            data = _convert(data)
        return data


class DocumentWithEmbedding(Document):
    """Document subclass that enforces an embedding field."""

    def __init__(self, embedding: list[float] | np.ndarray, *args, **kwargs):
        kwargs["embedding"] = embedding
        super().__init__(*args, **kwargs)
        object.__setattr__(self, "embedding", embedding)


class BaseMessage(Document):
    def __add__(self, other: Any):
        raise NotImplementedError

    def to_openai_format(self) -> "ChatCompletionMessageParam":
        raise NotImplementedError


if TYPE_CHECKING:

    class SystemMessage(BaseMessage, LCSystemMessage):
        def to_openai_format(self) -> "ChatCompletionMessageParam":
            ...

    class AIMessage(BaseMessage, LCAIMessage):
        def to_openai_format(self) -> "ChatCompletionMessageParam":
            ...

    class HumanMessage(BaseMessage, LCHumanMessage):
        def to_openai_format(self) -> "ChatCompletionMessageParam":
            ...

else:
    try:
        SystemMessage = type(
            "SystemMessage",
            (BaseMessage, LCSystemMessage),
            {
                "to_openai_format": lambda self: {
                    "role": "system",
                    "content": self.content,
                }
            },
        )  # type: ignore[misc, valid-type]
        AIMessage = type(
            "AIMessage",
            (BaseMessage, LCAIMessage),
            {
                "to_openai_format": lambda self: {
                    "role": "assistant",
                    "content": self.content,
                }
            },
        )  # type: ignore[misc, valid-type]
        HumanMessage = type(
            "HumanMessage",
            (BaseMessage, LCHumanMessage),
            {
                "to_openai_format": lambda self: {
                    "role": "user",
                    "content": self.content,
                }
            },
        )  # type: ignore[misc, valid-type]
    except TypeError:
        SystemMessage = type(
            "SystemMessage",
            (BaseMessage,),
            {
                "to_openai_format": lambda self: {
                    "role": "system",
                    "content": self.content,
                }
            },
        )  # type: ignore[misc, valid-type]
        AIMessage = type(
            "AIMessage",
            (BaseMessage,),
            {
                "to_openai_format": lambda self: {
                    "role": "assistant",
                    "content": self.content,
                }
            },
        )  # type: ignore[misc, valid-type]
        HumanMessage = type(
            "HumanMessage",
            (BaseMessage,),
            {
                "to_openai_format": lambda self: {
                    "role": "user",
                    "content": self.content,
                }
            },
        )  # type: ignore[misc, valid-type]


class RetrievedDocument(Document):
    """Subclass of Document with retrieval-related information

    Attributes:
        score (float): score of the document (from 0.0 to 1.0)
        retrieval_metadata (dict): metadata from the retrieval process, can be used
            by different components in a retrieved pipeline to communicate with each
            other
    """

    score: float = Field(default=0.0)
    retrieval_metadata: dict = Field(default={})


class LLMInterface(AIMessage):  # type: ignore[misc, valid-type]
    candidates: list[str] = Field(default_factory=list)
    completion_tokens: int = -1
    total_tokens: int = -1
    prompt_tokens: int = -1
    total_cost: float = 0
    logits: list[list[float]] = Field(default_factory=list)
    messages: list[AIMessage] = Field(default_factory=list)  # type: ignore[valid-type]
    logprobs: list[float] = []


class StructuredOutputLLMInterface(LLMInterface):
    parsed: Any
    refusal: str = ""


class ExtractorOutput(Document):
    """
    Represents the output of an extractor.
    """

    matches: list[str]
