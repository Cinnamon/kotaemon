from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, TypeVar

from langchain.schema.messages import AIMessage as LCAIMessage
from langchain.schema.messages import HumanMessage as LCHumanMessage
from langchain.schema.messages import SystemMessage as LCSystemMessage
from llama_index.bridge.pydantic import Field
from llama_index.schema import Document as BaseDocument

if TYPE_CHECKING:
    from haystack.schema import Document as HaystackDocument

IO_Type = TypeVar("IO_Type", "Document", str)
SAMPLE_TEXT = "A sample Document from kotaemon"


class Document(BaseDocument):
    """
    Base document class, mostly inherited from Document class from llama-index.

    This class accept one positional argument `content` of an arbitrary type, which will
        store the raw content of the document. If specified, the class will use
        `content` to initialize the base llama_index class.
    """

    content: Any

    def __init__(self, content: Optional[Any] = None, *args, **kwargs):
        if content is None:
            if kwargs.get("text", None) is not None:
                kwargs["content"] = kwargs["text"]
            elif kwargs.get("embedding", None) is not None:
                kwargs["content"] = kwargs["embedding"]
                # default text indicating this document only contains embedding
                kwargs["text"] = "<EMBEDDING>"
        elif isinstance(content, Document):
            kwargs = content.dict()
        else:
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


class DocumentWithEmbedding(Document):
    """Subclass of Document which must contains embedding

    Use this if you want to enforce component's IOs to must contain embedding.
    """

    def __init__(self, embedding: list[float], *args, **kwargs):
        kwargs["embedding"] = embedding
        super().__init__(*args, **kwargs)


class BaseMessage(Document):
    def __add__(self, other: Any):
        raise NotImplementedError


class SystemMessage(BaseMessage, LCSystemMessage):
    pass


class AIMessage(BaseMessage, LCAIMessage):
    pass


class HumanMessage(BaseMessage, LCHumanMessage):
    pass


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


class LLMInterface(AIMessage):
    candidates: list[str] = Field(default_factory=list)
    completion_tokens: int = -1
    total_tokens: int = -1
    prompt_tokens: int = -1
    total_cost: float = 0
    logits: list[list[float]] = Field(default_factory=list)
    messages: list[AIMessage] = Field(default_factory=list)


class ExtractorOutput(Document):
    """
    Represents the output of an extractor.
    """

    matches: list[str]
